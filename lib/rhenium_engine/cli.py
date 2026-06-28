
from __future__ import annotations
import argparse, json
from pathlib import Path
from rhenium_engine.orchestrator import compose_work, export_composition

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('text', nargs='?', default='Color moves through a 2x2 grid into a proof or obligation receipt.')
    ap.add_argument('--out', default='exports/cli')
    args=ap.parse_args()
    res=compose_work(args.text)
    paths=export_composition(res, Path(args.out))
    print(json.dumps({'summary':res['summary'],'paths':paths}, indent=2))
if __name__=='__main__': main()
