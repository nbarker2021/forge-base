from __future__ import annotations
import argparse, json, sys
from .registry import list_engines, layer_map
from .factory import compose, export_project


def _cmd_engines(args):
    print(json.dumps({"engines":list_engines(), "layers":layer_map()}, indent=2))


def _cmd_compose(args):
    res = compose(args.text)
    if args.out:
        paths = export_project(res, args.out)
        print(json.dumps({"summary":res.get("summary",{}), "paths":paths}, indent=2))
    else:
        print(json.dumps(res.get("summary", res), indent=2))



def _cmd_paper00(args):
    import json
    from forgefactory.papers.paper00_transport_contract import run_manufacturing_example, build_workbook_sheet
    payload={"example": run_manufacturing_example(), "workbook_sheet": build_workbook_sheet()}
    print(json.dumps(payload, indent=2))

def _cmd_smoke(args):
    failures=[]
    for pkg in ["lattice_forge", "reforge_engine_contracts", "reforge_kimi_adapter", "reforge_glyphforge", "reforge_researchcraft", "reforge_pixleforge", "reforge_wireforge", "reforge_frameforge", "reforge_pixl8forge", "rhenium_engine"]:
        try:
            __import__(pkg)
        except Exception as exc:
            failures.append({"package":pkg,"error":repr(exc)})
    res=compose("ForgeFactory smoke test: color moves through LCR into proof or obligation.")
    payload={"ok":not failures, "failures":failures, "summary":res.get("summary",{})}
    print(json.dumps(payload, indent=2))
    if failures:
        sys.exit(1)


def main(argv=None):
    p=argparse.ArgumentParser(prog="forgefactory")
    sub=p.add_subparsers(dest="cmd", required=True)
    e=sub.add_parser("engines"); e.set_defaults(func=_cmd_engines)
    c=sub.add_parser("compose"); c.add_argument("text"); c.add_argument("--out"); c.set_defaults(func=_cmd_compose)
    p00=sub.add_parser("paper00"); p00.set_defaults(func=_cmd_paper00)
    s=sub.add_parser("smoke"); s.set_defaults(func=_cmd_smoke)
    args=p.parse_args(argv); args.func(args)

if __name__ == "__main__": main()
