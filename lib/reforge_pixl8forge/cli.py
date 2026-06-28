from __future__ import annotations
import argparse, json
from .pipeline import pixl8_receipt

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", default="demo")
    ap.add_argument("--width", type=int, default=8)
    ap.add_argument("--height", type=int, default=8)
    args = ap.parse_args()
    print(json.dumps(pixl8_receipt(args.seed, args.width, args.height), indent=2))
if __name__ == "__main__": main()
