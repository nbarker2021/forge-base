"""
PixelForge Splat Vulkan — GPU compute backend for the same
(splats, width, height) -> (Picture, stats) contract as
PixelForge.splat.rasterize_splats (the CPU reference path).

Division of labor, deliberately not duplicated on the GPU: tile assignment
and farthest-first ordering are computed once on CPU via
PixelForge.splat.project_splats / bin_splats — the exact same
backend-agnostic functions the CPU path uses — and handed to the compute
shader (shaders/splat_raster.comp) as a CSR tile->splat-index buffer. The
shader only does the part that is actually GPU work: each invocation is one
pixel, walking its tile's splat list in the given order and accumulating
the same Gaussian-falloff alpha blend as the CPU path's inner loop. Any
CPU/GPU divergence in the result is therefore attributable to float32 (GPU)
vs float64 (CPU) rounding in that one shared formula, not to a different
tile layout or a different blend order — the precise, narrow thing GS-08's
parity check is meant to measure.

The float32 RGBA the GPU computes is converted to the Picture's uint8 RGB
via PixelForge.quantize.quantize_scalar_pixel, with every pixel's rounding
residual folded into a ResidualLedger rather than discarded — see
quantize.py's docstring for why that residual is tracked instead of a
"D4 lattice" rounding rule (measured worse at this point density, not used).

Requires: VULKAN_SDK installed (for glslc, to compile shaders/splat_raster
.comp on first use) and the `vulkan` PyPI package (thin cffi bindings to
the same Vulkan C API libvulkan/vulkan-1.dll already provides).
"""
from __future__ import annotations

import os
import struct
import subprocess
from typing import Dict, List, Sequence, Tuple

import vulkan as vk

from PixelForge.picture import Picture
from PixelForge.quantize import ResidualLedger, quantize_scalar_pixel
from PixelForge.splat import TILE_SIZE, bin_splats, classify_tile_lcr, project_splats

_SHADER_DIR = os.path.join(os.path.dirname(__file__), "shaders")
_SHADER_SRC = os.path.join(_SHADER_DIR, "splat_raster.comp")
_SHADER_SPV = os.path.join(_SHADER_DIR, "splat_raster.spv")

_USAGE_STORAGE = vk.VK_BUFFER_USAGE_STORAGE_BUFFER_BIT
_HOST_VISIBLE_COHERENT = (vk.VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT
                           | vk.VK_MEMORY_PROPERTY_HOST_COHERENT_BIT)


class VulkanUnavailable(RuntimeError):
    """Raised when no Vulkan-capable device or no glslc is found. Callers
    decide whether to fall back to the CPU path; this module never falls
    back silently."""


def _find_glslc() -> str:
    sdk = os.environ.get("VULKAN_SDK")
    if sdk:
        for sub in ("Bin", "bin"):
            candidate = os.path.join(sdk, sub, "glslc.exe" if os.name == "nt" else "glslc")
            if os.path.exists(candidate):
                return candidate
    return "glslc"  # rely on PATH


def _ensure_spv() -> bytes:
    """Compile splat_raster.comp with glslc if the .spv is missing or older
    than the .comp source, so the checked-in GLSL is always ground truth —
    no precompiled binary that can silently drift from it."""
    stale = (not os.path.exists(_SHADER_SPV)
             or os.path.getmtime(_SHADER_SPV) < os.path.getmtime(_SHADER_SRC))
    if stale:
        glslc = _find_glslc()
        try:
            subprocess.run([glslc, "-fshader-stage=compute", _SHADER_SRC,
                             "-o", _SHADER_SPV], check=True,
                            capture_output=True, text=True)
        except (FileNotFoundError, subprocess.CalledProcessError) as exc:
            raise VulkanUnavailable(f"glslc shader compile failed: {exc}") from exc
    with open(_SHADER_SPV, "rb") as f:
        return f.read()


class _Device:
    """One Vulkan instance/device/queue context, torn down on close()."""

    def __init__(self) -> None:
        app_info = vk.VkApplicationInfo(
            pApplicationName="PixelForge.splat_vulkan",
            applicationVersion=1, pEngineName="PixelForge",
            engineVersion=1, apiVersion=vk.VK_API_VERSION_1_0,
        )
        try:
            self.instance = vk.vkCreateInstance(
                vk.VkInstanceCreateInfo(pApplicationInfo=app_info), None)
        except Exception as exc:  # no loader / driver present
            raise VulkanUnavailable(f"vkCreateInstance failed: {exc}") from exc

        devices = vk.vkEnumeratePhysicalDevices(self.instance)
        if not devices:
            raise VulkanUnavailable("no Vulkan physical devices enumerated")
        self.phys = devices[0]
        self.props = vk.vkGetPhysicalDeviceProperties(self.phys)

        qfi = None
        for i, q in enumerate(vk.vkGetPhysicalDeviceQueueFamilyProperties(self.phys)):
            if q.queueFlags & vk.VK_QUEUE_COMPUTE_BIT:
                qfi = i
                break
        if qfi is None:
            raise VulkanUnavailable("no compute-capable queue family")
        self.queue_family_index = qfi

        self.device = vk.vkCreateDevice(self.phys, vk.VkDeviceCreateInfo(
            pQueueCreateInfos=[vk.VkDeviceQueueCreateInfo(
                queueFamilyIndex=qfi, queueCount=1, pQueuePriorities=[1.0])]
        ), None)
        self.queue = vk.vkGetDeviceQueue(self.device, qfi, 0)
        self.mem_props = vk.vkGetPhysicalDeviceMemoryProperties(self.phys)

    def gpu_profile(self) -> str:
        return f"{self.props.deviceName} (Vulkan API {self.props.apiVersion})"

    def memory_type_index(self, type_bits: int, required: int) -> int:
        for i in range(self.mem_props.memoryTypeCount):
            if (type_bits & (1 << i)) and (self.mem_props.memoryTypes[i].propertyFlags & required) == required:
                return i
        raise VulkanUnavailable("no host-visible/coherent memory type for a storage buffer")

    def make_buffer(self, size: int, usage: int = _USAGE_STORAGE) -> Tuple[object, object, int]:
        size = max(1, size)
        buf = vk.vkCreateBuffer(self.device, vk.VkBufferCreateInfo(
            size=size, usage=usage, sharingMode=vk.VK_SHARING_MODE_EXCLUSIVE), None)
        req = vk.vkGetBufferMemoryRequirements(self.device, buf)
        idx = self.memory_type_index(req.memoryTypeBits, _HOST_VISIBLE_COHERENT)
        mem = vk.vkAllocateMemory(self.device, vk.VkMemoryAllocateInfo(
            allocationSize=req.size, memoryTypeIndex=idx), None)
        vk.vkBindBufferMemory(self.device, buf, mem, 0)
        return buf, mem, req.size

    def write_buffer(self, mem: object, alloc_size: int, data: bytes) -> None:
        mapped = vk.vkMapMemory(self.device, mem, 0, alloc_size, 0)
        mapped[:len(data)] = data
        vk.vkUnmapMemory(self.device, mem)

    def read_buffer(self, mem: object, size: int) -> bytes:
        mapped = vk.vkMapMemory(self.device, mem, 0, size, 0)
        data = bytes(mapped[:size])
        vk.vkUnmapMemory(self.device, mem)
        return data

    def close(self) -> None:
        vk.vkDestroyDevice(self.device, None)
        vk.vkDestroyInstance(self.instance, None)


def _pack_splats(screen) -> bytes:
    """ScreenSplat[] -> the shader's std430 Splat[] layout: vec4
    (cx, cy, depth, radius_px) + vec4 (r, g, b, opacity), all floats,
    colors normalized 0..1 (the CPU path keeps 0..255 ints; the shader
    works in 0..1 to match GLSL's usual color convention)."""
    out = bytearray()
    for sp in screen:
        r, g, b = sp.color
        out += struct.pack("<4f4f", sp.cx, sp.cy, sp.depth, sp.radius_px,
                            r / 255.0, g / 255.0, b / 255.0, sp.opacity)
    return bytes(out)


def _pack_tile_csr(bins: Dict[Tuple[int, int], List[int]], screen,
                    tiles_x: int, tiles_y: int) -> Tuple[bytes, bytes]:
    """bin_splats' dict -> CSR (offsets, indices), farthest-first per tile —
    the exact ordering rasterize_splats uses, so the GPU sees the same
    per-tile sequence the CPU path does."""
    n_tiles = tiles_x * tiles_y
    offsets = [0] * (n_tiles + 1)
    indices: List[int] = []
    for ty in range(tiles_y):
        for tx in range(tiles_x):
            tile_index = ty * tiles_x + tx
            ordered = sorted(bins.get((tx, ty), []), key=lambda i: screen[i].depth)
            offsets[tile_index] = len(indices)
            indices.extend(ordered)
    offsets[n_tiles] = len(indices)
    if not indices:
        indices = [0]  # buffers may not be zero-sized
    return (struct.pack(f"<{len(offsets)}I", *offsets),
            struct.pack(f"<{len(indices)}I", *indices))


def rasterize_splats_vulkan(splats: Sequence[Dict], width: int, height: int,
                             background: Tuple[int, int, int] = (0, 0, 0),
                             scale: float = 0.25, depth_cam: float = 5.0,
                             tile_size: int = TILE_SIZE,
                             ) -> Tuple[Picture, Dict]:
    """GPU mirror of PixelForge.splat.rasterize_splats. Same signature,
    same (splats, width, height) -> (Picture, stats) contract, so callers
    can swap backends and diff the two Pictures directly."""
    spv = _ensure_spv()
    dev = _Device()
    try:
        return _dispatch(dev, spv, splats, width, height, background,
                          scale, depth_cam, tile_size)
    finally:
        dev.close()


def _dispatch(dev: _Device, spv: bytes, splats: Sequence[Dict], width: int,
              height: int, background: Tuple[int, int, int], scale: float,
              depth_cam: float, tile_size: int) -> Tuple[Picture, Dict]:
    screen = project_splats(splats, width, height, scale=scale, depth_cam=depth_cam)
    bins = bin_splats(screen, width, height, tile_size=tile_size)
    tiles_x = max(1, (width + tile_size - 1) // tile_size)
    tiles_y = max(1, (height + tile_size - 1) // tile_size)

    splat_bytes = _pack_splats(screen) if screen else struct.pack("<8f", *([0.0] * 8))
    offsets_bytes, indices_bytes = _pack_tile_csr(bins, screen, tiles_x, tiles_y)
    pixel_count = width * height
    pixel_buf_size = pixel_count * 16  # vec4 per pixel

    device = dev.device
    # Every vkCreateX below is paired with a vkDestroyX in `teardown`, run in
    # reverse-creation order before this device is destroyed by the caller —
    # vkDestroyDevice on a device that still owns live buffers/pipelines is
    # undefined behavior, and was the actual cause of a VK_ERROR_DEVICE_LOST
    # on the *next* call (corrupted driver state from this call's leak), not
    # a bug in the shader or this call's own data.
    teardown: List[Tuple[object, tuple]] = []

    def track(destroy_fn, *handles) -> None:
        teardown.append((destroy_fn, handles))

    try:
        splat_buf, splat_mem, splat_size = dev.make_buffer(len(splat_bytes))
        track(vk.vkDestroyBuffer, device, splat_buf, None)
        track(vk.vkFreeMemory, device, splat_mem, None)
        dev.write_buffer(splat_mem, splat_size, splat_bytes)

        off_buf, off_mem, off_size = dev.make_buffer(len(offsets_bytes))
        track(vk.vkDestroyBuffer, device, off_buf, None)
        track(vk.vkFreeMemory, device, off_mem, None)
        dev.write_buffer(off_mem, off_size, offsets_bytes)

        idx_buf, idx_mem, idx_size = dev.make_buffer(len(indices_bytes))
        track(vk.vkDestroyBuffer, device, idx_buf, None)
        track(vk.vkFreeMemory, device, idx_mem, None)
        dev.write_buffer(idx_mem, idx_size, indices_bytes)

        pix_buf, pix_mem, pix_size = dev.make_buffer(pixel_buf_size)
        track(vk.vkDestroyBuffer, device, pix_buf, None)
        track(vk.vkFreeMemory, device, pix_mem, None)

        shader_module = vk.vkCreateShaderModule(
            device, vk.VkShaderModuleCreateInfo(codeSize=len(spv), pCode=spv), None)
        track(vk.vkDestroyShaderModule, device, shader_module, None)

        bindings = [vk.VkDescriptorSetLayoutBinding(
            binding=i, descriptorType=vk.VK_DESCRIPTOR_TYPE_STORAGE_BUFFER,
            descriptorCount=1, stageFlags=vk.VK_SHADER_STAGE_COMPUTE_BIT)
            for i in range(4)]
        dsl = vk.vkCreateDescriptorSetLayout(
            device, vk.VkDescriptorSetLayoutCreateInfo(pBindings=bindings), None)
        track(vk.vkDestroyDescriptorSetLayout, device, dsl, None)

        pc_range = vk.VkPushConstantRange(
            stageFlags=vk.VK_SHADER_STAGE_COMPUTE_BIT, offset=0, size=32)
        pipeline_layout = vk.vkCreatePipelineLayout(device, vk.VkPipelineLayoutCreateInfo(
            pSetLayouts=[dsl], pPushConstantRanges=[pc_range]), None)
        track(vk.vkDestroyPipelineLayout, device, pipeline_layout, None)

        stage_info = vk.VkPipelineShaderStageCreateInfo(
            stage=vk.VK_SHADER_STAGE_COMPUTE_BIT, module=shader_module, pName="main")
        pipeline = vk.vkCreateComputePipelines(device, None, 1, [vk.VkComputePipelineCreateInfo(
            stage=stage_info, layout=pipeline_layout)], None)[0]
        track(vk.vkDestroyPipeline, device, pipeline, None)

        pool = vk.vkCreateDescriptorPool(device, vk.VkDescriptorPoolCreateInfo(
            maxSets=1, pPoolSizes=[vk.VkDescriptorPoolSize(
                type=vk.VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, descriptorCount=4)]), None)
        track(vk.vkDestroyDescriptorPool, device, pool, None)
        dset = vk.vkAllocateDescriptorSets(device, vk.VkDescriptorSetAllocateInfo(
            descriptorPool=pool, pSetLayouts=[dsl]))[0]
        # descriptor sets are freed implicitly when their pool is destroyed

        def buf_info(buf, size):
            return vk.VkDescriptorBufferInfo(buffer=buf, offset=0, range=size)

        writes = [
            vk.VkWriteDescriptorSet(dstSet=dset, dstBinding=0, descriptorType=vk.VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, pBufferInfo=[buf_info(splat_buf, splat_size)]),
            vk.VkWriteDescriptorSet(dstSet=dset, dstBinding=1, descriptorType=vk.VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, pBufferInfo=[buf_info(off_buf, off_size)]),
            vk.VkWriteDescriptorSet(dstSet=dset, dstBinding=2, descriptorType=vk.VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, pBufferInfo=[buf_info(idx_buf, idx_size)]),
            vk.VkWriteDescriptorSet(dstSet=dset, dstBinding=3, descriptorType=vk.VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, pBufferInfo=[buf_info(pix_buf, pix_size)]),
        ]
        vk.vkUpdateDescriptorSets(device, len(writes), writes, 0, None)

        cmd_pool = vk.vkCreateCommandPool(device, vk.VkCommandPoolCreateInfo(
            queueFamilyIndex=dev.queue_family_index), None)
        track(vk.vkDestroyCommandPool, device, cmd_pool, None)
        cmd = vk.vkAllocateCommandBuffers(device, vk.VkCommandBufferAllocateInfo(
            commandPool=cmd_pool, level=vk.VK_COMMAND_BUFFER_LEVEL_PRIMARY,
            commandBufferCount=1))[0]
        # command buffers are freed implicitly when their pool is destroyed

        vk.vkBeginCommandBuffer(cmd, vk.VkCommandBufferBeginInfo(
            flags=vk.VK_COMMAND_BUFFER_USAGE_ONE_TIME_SUBMIT_BIT))
        vk.vkCmdBindPipeline(cmd, vk.VK_PIPELINE_BIND_POINT_COMPUTE, pipeline)
        vk.vkCmdBindDescriptorSets(cmd, vk.VK_PIPELINE_BIND_POINT_COMPUTE,
                                    pipeline_layout, 0, 1, [dset], 0, None)
        bg = [c / 255.0 for c in background]
        pc_bytes = struct.pack("<4i4f", width, height, tile_size, tiles_x,
                                bg[0], bg[1], bg[2], 1.0)
        vk.vkCmdPushConstants(cmd, pipeline_layout, vk.VK_SHADER_STAGE_COMPUTE_BIT,
                               0, len(pc_bytes), vk.ffi.from_buffer(pc_bytes))
        group_x = (width + 7) // 8
        group_y = (height + 7) // 8
        vk.vkCmdDispatch(cmd, group_x, group_y, 1)
        vk.vkEndCommandBuffer(cmd)

        vk.vkQueueSubmit(dev.queue, 1, [vk.VkSubmitInfo(pCommandBuffers=[cmd])], None)
        vk.vkQueueWaitIdle(dev.queue)

        raw = dev.read_buffer(pix_mem, pixel_buf_size)
    finally:
        for destroy_fn, handles in reversed(teardown):
            destroy_fn(*handles)

    pic = Picture(width, height)
    ledger = ResidualLedger()
    for i in range(pixel_count):
        r, g, b, a = struct.unpack_from("<4f", raw, i * 16)
        px, residual = quantize_scalar_pixel((r, g, b, a))
        pic.buf[i * 3], pic.buf[i * 3 + 1], pic.buf[i * 3 + 2] = px
        ledger.add(residual)

    stats = {
        "splat_count": len(splats),
        "width": width, "height": height,
        "tile_size": tile_size,
        "tile_count": len(bins),
        "max_splats_per_tile": max((len(v) for v in bins.values()), default=0),
        "gpu_profile": dev.gpu_profile(),
        "quantization": ledger.stats(),
        **classify_tile_lcr(bins, tiles_x, tiles_y),
    }
    return pic, stats
