from math import cos, sin, pi
from reforge_wireforge.templates import make_wire_template
from reforge_wireforge.encoder import encode_wireframe
from reforge_engine_contracts.core import GraphNode, GraphEdge, Receipt, stable_id, now, LCRBlock
from reforge_engine_contracts.validation import validate_lcr, validate_graph

def make_motion_sequence(template='octad_faces', frames=8, path='rotation', orientation='external'):
    seq=[]
    base=make_wire_template(template, orientation=orientation)
    for t in range(frames):
        theta=2*pi*t/frames
        nodes=[]
        for n in base['nodes']:
            x,y,z=n.get('x',0),n.get('y',0),n.get('z',0)
            if path=='rotation':
                xr=x*cos(theta)-y*sin(theta); yr=x*sin(theta)+y*cos(theta); zr=z
            elif path=='eversion_hint':
                xr=x; yr=y*cos(theta); zr=z + y*sin(theta)
            else: # oscillation
                xr=x; yr=y; zr=z + .25*sin(theta)
            nn=dict(n); nn.update({'x':xr,'y':yr,'z':zr,'frame':t})
            nodes.append(nn)
        seq.append({'frame':t,'theta':theta,'nodes':nodes,'edges':base['edges']})
    return {'template':template,'frames':frames,'path':path,'orientation':orientation,'sequence':seq}

def encode_frame_sequence(template='octad_faces', frames=8, path='rotation', orientation='external'):
    seq=make_motion_sequence(template,frames,path,orientation)
    nodes=[]; edges=[]; lcr=[]
    for frame in seq['sequence']:
        fid=f"frame_{frame['frame']}"
        nodes.append(GraphNode(fid,fid,'frame','clear',{'theta':frame['theta']}).to_dict())
        for i,n in enumerate(frame['nodes']):
            nid=f"f{frame['frame']}_{n['id']}"
            nodes.append(GraphNode(nid,n['label'],'frame_wire_node',n.get('color_state','grey'),n).to_dict())
            edges.append(GraphEdge(fid,nid,'contains','clear',{}).to_dict())
            L=1 if n.get('x',0)<0 else 0; C=1 if n.get('role') in ('center','visible','face','lattice') else 0; R=1 if n.get('y',0)>=0 else 0
            b=LCRBlock(L,C,R,n.get('color_state','grey'),i,n.get('role','carrier')).to_dict(); validate_lcr(b); lcr.append(b)
        # temporal links
        if frame['frame']>0: edges.append(GraphEdge(f"frame_{frame['frame']-1}",fid,'next_frame','neon',{}).to_dict())
    validate_graph(nodes, edges)
    payload={'frame_sequence':seq,'summary':{'frames':frames,'template':template,'path':path,'orientation':orientation,'node_count':len(nodes),'edge_count':len(edges)}}
    return Receipt(stable_id('frame',payload),'FrameForge','pass',lcr,nodes,edges,payload,now()).to_dict()
