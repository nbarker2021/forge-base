from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Tuple
import base64, io, json, math, time, uuid
from reforge_engine_contracts import LCRBlock, GraphNode, GraphEdge, Receipt

try:
    from PIL import Image
except Exception:  # pragma: no cover
    Image = None

Color = Tuple[int, int, int, int]

@dataclass
class PixelPatch:
    index: int
    x: int
    y: int
    rgba: Color
    luminance: float
    saturation: float
    gradient: float
    color_state: str
    fourth_bit: int
    state16: int

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["rgba"] = list(self.rgba)
        return d


def _require_pillow() -> None:
    if Image is None:
        raise RuntimeError("Pillow is required for image file encoding in PixleForge v0.1")


def classify_color(r: int, g: int, b: int, a: int = 255) -> str:
    if a < 32:
        return "clear"
    mx, mn = max(r, g, b), min(r, g, b)
    lum = (0.2126*r + 0.7152*g + 0.0722*b) / 255.0
    sat = (mx - mn) / 255.0
    # Preserve quark-color identity before brightness collapse.
    # A saturated low-luminance blue is still blue, not black.
    if sat >= 0.18:
        if mx == r:
            return "red"
        if mx == g:
            return "green"
        if mx == b:
            return "blue"
    if lum < 0.12:
        return "black"
    if lum > 0.88 and sat < 0.16:
        return "white"
    if sat < 0.12:
        return "grey"
    return "unknown"


def luminance(r: int, g: int, b: int) -> float:
    return (0.2126*r + 0.7152*g + 0.0722*b) / 255.0


def saturation(r: int, g: int, b: int) -> float:
    return (max(r,g,b)-min(r,g,b)) / 255.0


def _resize_sample(img: "Image.Image", grid_size: int) -> List[List[Color]]:
    _require_pillow()
    img = img.convert("RGBA")
    # Use BOX to average each patch into one visible readout cell.
    small = img.resize((grid_size, grid_size), Image.Resampling.BOX)
    data = list(small.getdata())
    return [data[y*grid_size:(y+1)*grid_size] for y in range(grid_size)]


def _compute_patches(matrix: List[List[Color]]) -> List[PixelPatch]:
    h = len(matrix)
    w = len(matrix[0]) if h else 0
    patches: List[PixelPatch] = []
    for y in range(h):
        for x in range(w):
            r,g,b,a = matrix[y][x]
            lum = luminance(r,g,b)
            sat = saturation(r,g,b)
            # local gradient against left/up neighbors, deliberately simple and deterministic
            diffs = []
            if x > 0:
                lr,lg,lb,la = matrix[y][x-1]
                diffs.append(abs(lum-luminance(lr,lg,lb)))
            if y > 0:
                ur,ug,ub,ua = matrix[y-1][x]
                diffs.append(abs(lum-luminance(ur,ug,ub)))
            grad = max(diffs) if diffs else 0.0
            cstate = classify_color(r,g,b,a)
            # 2x2x2x2 block axes for pixel readout:
            # bit3 L: left/up contrast pressure; bit2 C: visible-center brightness; bit1 R: chroma/saturation; bit0 Q: alpha/edge-active fourth bit
            L = int(grad >= 0.12)
            C = int(lum >= 0.50)
            R = int(sat >= 0.18)
            Q = int((a >= 128 and grad >= 0.06) or sat >= 0.35)
            state16 = (L<<3) | (C<<2) | (R<<1) | Q
            patches.append(PixelPatch(index=len(patches),x=x,y=y,rgba=(int(r),int(g),int(b),int(a)),luminance=lum,saturation=sat,gradient=grad,color_state=cstate,fourth_bit=Q,state16=state16))
    return patches


def patches_to_lcr_blocks(patches: List[PixelPatch]) -> List[LCRBlock]:
    # Preserve spatial stream order, with L/C/R read as previous/current/next visibility bit.
    centers = [int(p.luminance >= 0.5) for p in patches]
    padded = [0] + centers + [0]
    blocks: List[LCRBlock] = []
    for i, p in enumerate(patches):
        L, C, R = padded[i], padded[i+1], padded[i+2]
        correction = int(C == 1 and R == 0)  # Rule30 = Rule90 XOR correction term C AND NOT R
        axis = f"PX{p.state16:02X}:A{(L<<2)|(C<<1)|R}"
        sheet = "positive" if C else "negative"
        voa_weight = 5 if (L+C+R) not in (0,3) else 0
        b = LCRBlock(index=i,left=L,center=C,right=R,gamma=C,axis=axis,sheet=sheet,voa_weight=voa_weight,correction=correction,color_state=p.color_state)
        b.validate()
        blocks.append(b)
    return blocks


def build_graph(patches: List[PixelPatch], blocks: List[LCRBlock], grid_size: int) -> Tuple[List[GraphNode], List[GraphEdge]]:
    nodes: List[GraphNode] = []
    edges: List[GraphEdge] = []
    for p, b in zip(patches, blocks):
        node_id = f"px_{p.x}_{p.y}"
        node = GraphNode(
            id=node_id,
            label=f"({p.x},{p.y}) {p.color_state} s{p.state16:02X}",
            node_type="lcr_block",
            color_state=p.color_state,
            payload={
                "x": p.x, "y": p.y, "rgba": list(p.rgba), "luminance": round(p.luminance,4),
                "saturation": round(p.saturation,4), "gradient": round(p.gradient,4), "state16": p.state16,
                "fourth_bit": p.fourth_bit, "axis": b.axis, "sheet": b.sheet,
                "gamma": b.gamma, "correction": b.correction, "voa_weight": b.voa_weight,
            },
        )
        node.validate()
        nodes.append(node)
    for p in patches:
        src = f"px_{p.x}_{p.y}"
        if p.x + 1 < grid_size:
            edges.append(GraphEdge(source=src, target=f"px_{p.x+1}_{p.y}", edge_type="spatial_right"))
        if p.y + 1 < grid_size:
            edges.append(GraphEdge(source=src, target=f"px_{p.x}_{p.y+1}", edge_type="spatial_down"))
    return nodes, edges


def encode_pil_image(img: "Image.Image", *, label: str = "image", grid_size: int = 8) -> Receipt:
    matrix = _resize_sample(img, grid_size)
    patches = _compute_patches(matrix)
    blocks = patches_to_lcr_blocks(patches)
    nodes, edges = build_graph(patches, blocks, grid_size)
    followup = "proof" if sum(b.correction for b in blocks) % 2 == 0 else "obligation"
    metadata = {
        "encoder": "PixleForge.v0.1",
        "label": label,
        "grid_size": grid_size,
        "block_model": "2x2x2x2 pixel carrier -> LCR visible readout",
        "patches": [p.to_dict() for p in patches],
        "color_histogram": color_histogram(patches),
        "correction_count": sum(b.correction for b in blocks),
    }
    r = Receipt.new(source_text=f"PixleForge image:{label}", followup=followup, blocks=blocks, nodes=nodes, edges=edges, metadata=metadata)
    r.validate()
    return r


def encode_image_file(path: str, *, grid_size: int = 8) -> Receipt:
    _require_pillow()
    img = Image.open(path)
    return encode_pil_image(img, label=path, grid_size=grid_size)


def encode_image_bytes(data: bytes, *, label: str = "upload", grid_size: int = 8) -> Receipt:
    _require_pillow()
    img = Image.open(io.BytesIO(data))
    return encode_pil_image(img, label=label, grid_size=grid_size)


def encode_data_url(data_url: str, *, grid_size: int = 8) -> Receipt:
    if "," not in data_url:
        raise ValueError("expected data URL containing comma")
    header, b64 = data_url.split(",", 1)
    return encode_image_bytes(base64.b64decode(b64), label=header[:80], grid_size=grid_size)


def encode_rgb_matrix(matrix: List[List[Tuple[int,int,int]]], *, label: str = "matrix") -> Receipt:
    rgba = [[(int(r),int(g),int(b),255) for (r,g,b) in row] for row in matrix]
    patches = _compute_patches(rgba)
    grid_size = len(rgba)
    blocks = patches_to_lcr_blocks(patches)
    nodes, edges = build_graph(patches, blocks, grid_size)
    followup = "proof" if sum(b.correction for b in blocks) % 2 == 0 else "obligation"
    r = Receipt.new(source_text=f"PixleForge matrix:{label}", followup=followup, blocks=blocks, nodes=nodes, edges=edges, metadata={"encoder":"PixleForge.v0.1","label":label,"grid_size":grid_size,"patches":[p.to_dict() for p in patches],"color_histogram":color_histogram(patches)})
    r.validate()
    return r


def color_histogram(patches: List[PixelPatch]) -> Dict[str,int]:
    hist: Dict[str,int] = {}
    for p in patches:
        hist[p.color_state] = hist.get(p.color_state, 0) + 1
    return dict(sorted(hist.items()))


def image_receipt_to_worldforge(receipt: Receipt) -> Dict[str, Any]:
    receipt.validate()
    return {
        "kind": "worldforge_graph",
        "engine": "PixleForge.v0.1",
        "receipt_id": receipt.receipt_id,
        "source": receipt.source_text,
        "followup": receipt.followup,
        "metadata": receipt.metadata,
        "nodes": [n.__dict__ for n in receipt.nodes],
        "edges": [e.__dict__ for e in receipt.edges],
        "summary": {
            "blocks": len(receipt.blocks),
            "corrections": sum(b.correction for b in receipt.blocks),
            "colors": receipt.metadata.get("color_histogram", {}),
        },
    }


def demo_image(size: int = 64):
    _require_pillow()
    img = Image.new("RGBA", (size,size), (0,0,0,255))
    px = img.load()
    for y in range(size):
        for x in range(size):
            r = int(255*x/(size-1))
            g = int(255*y/(size-1))
            b = int(255*((x//8 + y//8) % 2))
            px[x,y] = (r,g,b,255)
    return img
