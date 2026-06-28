from reforge_engine_contracts.core import LCRBlock, GraphNode, GraphEdge, Receipt, stable_id, now
from reforge_engine_contracts.validation import validate_lcr, validate_graph
from .templates import make_wire_template

def _lcr_for_node(node, index):
    # boundary-based binary: L=x sign, C=center/visible role, R=y sign
    L = 1 if node.get('x',0) < 0 else 0
    C = 1 if node.get('role') in ('center','visible','face','lattice') else 0
    R = 1 if node.get('y',0) >= 0 else 0
    return LCRBlock(L,C,R,node.get('color_state','grey'),index,node.get('role','carrier')).to_dict()

def encode_wireframe(name='carrier_2x2x2x2', orientation='external'):
    tpl=make_wire_template(name=name, orientation=orientation)
    lcr=[_lcr_for_node(n,i) for i,n in enumerate(tpl['nodes'])]
    for b in lcr: validate_lcr(b)
    nodes=[GraphNode(n['id'],n['label'],'wire_node',n.get('color_state','grey'),n).to_dict() for n in tpl['nodes']]
    edges=[GraphEdge(e['source'],e['target'],e['edge_type'],e.get('color_state','clear'),e).to_dict() for e in tpl['edges']]
    validate_graph(nodes, edges)
    payload={'wire_template':tpl,'summary':{'node_count':len(nodes),'edge_count':len(edges),'orientation':orientation}}
    rid=stable_id('wire', payload)
    return Receipt(rid,'WireForge','pass',lcr,nodes,edges,payload,now()).to_dict()
