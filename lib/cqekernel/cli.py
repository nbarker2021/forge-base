"""
The CQE kernel CLI.

Examples::

    python -m cqekernel observe input.txt
    python -m cqekernel run input.txt --mode audit
    python -m cqekernel replay <snapshot_id>
    python -m cqekernel verify
    python -m cqekernel workbook
    python -m cqekernel firmware
    python -m cqekernel packet '{"op":"observe","payload":"hello","mode":"AUDIT"}'
    python -m cqekernel witness "010110"  # D4 token readout
    python -m cqekernel witness --split-bias 4
    python -m cqekernel d4 "hello"        # D4 tokens for utf-8 bytes
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict

from .core.kernel import Kernel
from .core.request import RequestMode


def _emit_json(d: Dict[str, Any]) -> None:
    print(json.dumps(d, sort_keys=True, indent=2, default=str))


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="cqekernel",
        description="CQE/CMPLX stdlib-only kernel CLI",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    s1 = sub.add_parser("observe", help="observe a text file")
    s1.add_argument("path", help="path to a text file")
    s1.add_argument("--mode", default="READ_ONLY",
                    choices=[m.value for m in RequestMode])
    s1.add_argument("--anchor", default=None,
                    help="workspace anchor (overrides CQE_ANCHOR)")

    s2 = sub.add_parser("run", help="observe stdin (or --text) and run the pipeline")
    s2.add_argument("path", nargs="?", default=None, help="path to a text file (or --text)")
    s2.add_argument("--text", default=None, help="raw text to observe")
    s2.add_argument("--mode", default="AUDIT",
                    choices=[m.value for m in RequestMode])
    s2.add_argument("--anchor", default=None)

    s3 = sub.add_parser("replay", help="replay a snapshot by id")
    s3.add_argument("snapshot_id")
    s3.add_argument("--anchor", default=None)

    sub.add_parser("verify", help="run the kernel's own falsifier suite")
    sub.add_parser("workbook", help="emit and check the default workbook")
    sub.add_parser("firmware", help="probe the firmware registry")
    sub.add_parser("list-snapshots", help="list all snapshot ids")

    s4 = sub.add_parser("packet", help="observe a JSON host packet")
    s4.add_argument("packet", help="JSON packet string")
    s4.add_argument("--anchor", default=None)

    s5 = sub.add_parser("witness", help="emit a LightCone frame for a binary string")
    s5.add_argument("bits", nargs="?", default=None,
                    help="binary string like '0101101' (default: read from stdin)")
    s5.add_argument("--text", default=None,
                    help="treat input as utf-8 text and convert to bits")
    s5.add_argument("--split-bias", type=int, default=1,
                    choices=[1, 2, 4, 8],
                    help="D4 light-cone split_bias (1,2,4,8)")
    s5.add_argument("--anchor", default=None)

    s6 = sub.add_parser("d4", help="emit D4 tokens for a string (utf-8 -> bits)")
    s6.add_argument("text", help="text to convert")
    s6.add_argument("--anchor", default=None)

    s7 = sub.add_parser("lcr-windows", help="envelope an input into 2x2/4x4/8x8 windows and show the channel resolution")
    s7.add_argument("text", help="text to envelope")
    s7.add_argument("--anchor", default=None)

    sub.add_parser("cqe-info", help="print CQE primitive info (D4Token fields, lattice_forge manifest)")

    return p


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    kernel = Kernel(
        anchor=getattr(args, "anchor", None),
        split_bias=getattr(args, "split_bias", 1),
    )

    if args.cmd == "observe":
        text = Path(args.path).read_text(encoding="utf-8")
        res = kernel.observe(text, mode=args.mode)
        _emit_json(res.to_dict())
        return 0

    if args.cmd == "run":
        if args.text is not None:
            text = args.text
        elif args.path is not None:
            text = Path(args.path).read_text(encoding="utf-8")
        else:
            text = sys.stdin.read()
        res = kernel.observe(text, mode=args.mode)
        _emit_json(res.to_dict())
        return 0

    if args.cmd == "replay":
        res = kernel.replay(args.snapshot_id)
        _emit_json(res.to_dict())
        return 0 if res.passed else 1

    if args.cmd == "verify":
        v = kernel.verify_kernel()
        _emit_json(v)
        all_ok = all(r["passed"] for r in v["reports"])
        return 0 if all_ok else 1

    if args.cmd == "workbook":
        _emit_json(kernel.workbook_check())
        return 0

    if args.cmd == "firmware":
        _emit_json(kernel.firmware_manifest())
        return 0

    if args.cmd == "cqe-info":
        # Detailed view: which CQE primitives are wired in this kernel
        from .cqe import D4Token
        from .firmware import lattice_forge_bridge
        _emit_json({
            "kernel_d4_token_fields": list(D4Token.__dataclass_fields__.keys())
                if hasattr(D4Token, "__dataclass_fields__") else [],
            "lattice_forge_manifest": lattice_forge_bridge.manifest(),
        })
        return 0

    if args.cmd == "list-snapshots":
        for sid in kernel.list_snapshots():
            print(sid)
        return 0

    if args.cmd == "packet":
        packet = json.loads(args.packet)
        res = kernel.observe_packet(packet)
        _emit_json(res.to_dict())
        return 0

    if args.cmd == "witness":
        from .firmware import lattice_forge_bridge
        if args.text is not None:
            data = args.text.encode("utf-8")
        elif args.bits is not None:
            data = args.bits.encode("ascii")
        else:
            data = sys.stdin.read().encode("utf-8")
        result = lattice_forge_bridge.light_cone(
            data, split_bias=args.split_bias, tick=0
        )
        _emit_json(result.to_dict())
        return 0 if result.status in ("OK", "EXTERNAL_REQUIRED") else 1

    if args.cmd == "d4":
        from .cqe import tokens_from_bits
        bits = "".join(f"{b:08b}" for b in args.text.encode("utf-8"))
        toks = tokens_from_bits(bits)
        _emit_json({
            "input_text": args.text,
            "bit_count": len(bits),
            "token_count": len(toks),
            "tokens": [t.to_dict() for t in toks],
        })
        return 0

    if args.cmd == "lcr-windows":
        from .lcr import (
            WindowSize, envelope_into_windows, resolve_channel,
        )
        bit_stream = tuple(
            int(bit)
            for byte in args.text.encode("utf-8")
            for bit in f"{byte:08b}"
        )
        all_windows = []
        envelope = {}
        for size in (WindowSize.W_2x2, WindowSize.W_4x4, WindowSize.W_8x8):
            windows = envelope_into_windows(bit_stream, size)
            envelope[size.value] = [w.to_dict() for w in windows]
            all_windows.extend(windows)
        channel = resolve_channel(all_windows)
        _emit_json({
            "input_text": args.text,
            "bit_count": len(bit_stream),
            "envelope": envelope,
            "channel": channel.to_dict() if channel else None,
            "summary": {
                "total_windows": len(all_windows),
                "closed_windows": sum(1 for w in all_windows if w.closed),
            },
        })
        return 0

    parser.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
