
from __future__ import annotations
import hashlib, json, sys
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
VENDOR = ROOT / "vendor_engines"
for p in [VENDOR, ROOT]:
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from rhenium_engine.registry import list_engines, layer_map


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()[:16]


def _fallback_text_receipt(text: str) -> Dict[str, Any]:
    bits = ''.join(format(b, '08b') for b in text.encode('utf-8', errors='replace')) or '0'
    blocks=[]
    for i in range(0, min(len(bits), 256), 3):
        tri=bits[i:i+3].ljust(3,'0')
        L,C,R = map(int, tri)
        blocks.append({
            'index': i//3,
            'L': L, 'C': C, 'R': R,
            'gamma': C,
            'rule90': L ^ R,
            'rule30_correction': C & (1-R),
            'followup': 'proof' if C else 'obligation',
            'color_state': ['red','green','blue','white','black','grey','neon','clear'][(L*4+C*2+R)%8]
        })
    return {'receipt_id':'fallback_'+_sha(text), 'kind':'text', 'text_sha':_sha(text), 'blocks':blocks}


def encode_text(text: str) -> Dict[str, Any]:
    """Use Kimi adapter if available; otherwise fallback to local block encoder."""
    try:
        from reforge_kimi_adapter.adapter import adapt_fragment
        return adapt_fragment(text)
    except Exception as exc:
        r=_fallback_text_receipt(text)
        r['adapter_warning']=repr(exc)
        return r


def glyph_analyze(text: str) -> Dict[str, Any]:
    try:
        from reforge_glyphforge.fumu import analyze_text
        return analyze_text(text)
    except Exception:
        lines=[ln.strip() for ln in text.splitlines() if ln.strip()]
        frags=[]
        for i,ln in enumerate(lines or [text[:160]]):
            typ='claim' if any(w in ln.lower() for w in ['must','is','therefore','because']) else 'note'
            frags.append({'fragment_id':f'frag_{i:03d}','text':ln,'type':typ,'color_state':'grey'})
        return {'analysis_id':'glyph_fallback_'+_sha(text),'fragments':frags}


def make_world_graph(receipt: Dict[str, Any], title: str = "Rhenium graph") -> Dict[str, Any]:
    blocks=receipt.get('blocks') or receipt.get('lcr_blocks') or []
    nodes=[]; edges=[]
    prev=None
    for b in blocks[:128]:
        idx=b.get('index', len(nodes))
        nid=f"n{idx}"
        nodes.append({
            'id': nid,
            'label': f"{b.get('L','?')}{b.get('C','?')}{b.get('R','?')}",
            'color_state': b.get('color_state','grey'),
            'followup': b.get('followup','obligation'),
            'payload': b
        })
        if prev is not None:
            edges.append({'id':f'e{prev}_{nid}','source':prev,'target':nid,'kind':'sequence'})
        prev=nid
    return {'graph_id':'world_'+_sha(json.dumps(receipt,sort_keys=True,default=str)), 'title':title, 'nodes':nodes, 'edges':edges}


def compose_work(text: str) -> Dict[str, Any]:
    receipt=encode_text(text)
    glyph=glyph_analyze(text)
    graph=make_world_graph(receipt, title="Rhenium composed work")
    obligations=[n for n in graph['nodes'] if n.get('followup')=='obligation']
    proofs=[n for n in graph['nodes'] if n.get('followup')=='proof']
    return {
        'product':'ReForge',
        'engine':'Rhenium Engine',
        'input_sha':_sha(text),
        'engines':list_engines(),
        'layers':layer_map(),
        'glyph_analysis':glyph,
        'receipt':receipt,
        'world_graph':graph,
        'summary':{
            'node_count':len(graph['nodes']),
            'edge_count':len(graph['edges']),
            'proof_count':len(proofs),
            'obligation_count':len(obligations),
            'fragment_count':len(glyph.get('fragments',[]))
        }
    }


def export_composition(result: Dict[str, Any], outdir: Path) -> Dict[str,str]:
    outdir.mkdir(parents=True, exist_ok=True)
    paths={}
    for name,key in [('composition',''),('receipt','receipt'),('graph','world_graph'),('glyph','glyph_analysis')]:
        payload=result if key=='' else result.get(key,{})
        path=outdir/f'{name}.json'
        path.write_text(json.dumps(payload,indent=2,default=str),encoding='utf-8')
        paths[name]=str(path)
    md=outdir/'summary.md'
    s=result['summary']
    md.write_text(f"""# Rhenium Composition Summary\n\n- Nodes: {s['node_count']}\n- Edges: {s['edge_count']}\n- Proofs: {s['proof_count']}\n- Obligations: {s['obligation_count']}\n- Fragments: {s['fragment_count']}\n\nThis export is a global ReForge/Rhenium composition result.\n""", encoding='utf-8')
    paths['summary_md']=str(md)
    return paths
