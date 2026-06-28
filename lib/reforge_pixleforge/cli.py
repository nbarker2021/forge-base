from __future__ import annotations
import argparse, json
from .encoder import encode_image_file, demo_image, encode_pil_image, image_receipt_to_worldforge

def main() -> None:
    p = argparse.ArgumentParser(description="PixleForge v0.1: image -> 2x2x2x2/LCR receipt -> WorldForge graph")
    p.add_argument("image", nargs="?", help="Image path. If omitted, generate demo image.")
    p.add_argument("--grid", type=int, default=8)
    p.add_argument("--graph", action="store_true", help="Emit WorldForge graph instead of receipt")
    args = p.parse_args()
    if args.image:
        receipt = encode_image_file(args.image, grid_size=args.grid)
    else:
        receipt = encode_pil_image(demo_image(), label="demo", grid_size=args.grid)
    obj = image_receipt_to_worldforge(receipt) if args.graph else receipt.to_dict()
    print(json.dumps(obj, indent=2, sort_keys=True))

if __name__ == "__main__":
    main()
