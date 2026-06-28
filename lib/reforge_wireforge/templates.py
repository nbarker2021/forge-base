from math import cos, sin, pi

def available_templates():
    return ['lcr_2x2','carrier_2x2x2x2','octad_faces','podal_24d_triplet','lattice_8x8','radial_boundary']

def _node(i,label,x,y,z=0,role='carrier',color='grey'):
    return {'id':f'n{i}', 'label':label, 'x':x, 'y':y, 'z':z, 'role':role, 'color_state':color}

def _edge(a,b,kind='bond',color='clear'):
    return {'source':a,'target':b,'edge_type':kind,'color_state':color}

def make_wire_template(name='carrier_2x2x2x2', center=(0,0,0), scale=1.0, orientation='external'):
    cx,cy,cz=center
    nodes=[]; edges=[]
    if name=='lcr_2x2':
        pts=[(-1,-1,0),(1,-1,0),(-1,1,0),(1,1,0)]
        labels=['L0','C0','C1','R1']
        for i,(x,y,z) in enumerate(pts): nodes.append(_node(i,labels[i],cx+x*scale,cy+y*scale,cz+z,'visible'))
        edges=[_edge('n0','n1','horizontal'),_edge('n0','n2','vertical'),_edge('n1','n3','vertical'),_edge('n2','n3','horizontal')]
    elif name=='carrier_2x2x2x2':
        i=0
        for a in (0,1):
            for b in (0,1):
                for c in (0,1):
                    for d in (0,1):
                        nodes.append(_node(i,f'{a}{b}{c}{d}',cx+(a-.5)*2*scale,cy+(b-.5)*2*scale,cz+(c-.5)*2*scale, role='visible' if d==0 else 'conjugate', color='grey' if d==0 else 'black'))
                        i+=1
        for i,n in enumerate(nodes):
            bits=n['label']
            for j,m in enumerate(nodes):
                if j>i and sum(aa!=bb for aa,bb in zip(bits,m['label']))==1:
                    edges.append(_edge(n['id'],m['id'],'hypercube_edge','clear'))
    elif name=='octad_faces':
        for i in range(8):
            ang=2*pi*i/8
            nodes.append(_node(i,f'face_{i}',cx+cos(ang)*scale,cy+sin(ang)*scale,cz,role='face',color=['red','green','blue','white','black','clear','grey','neon'][i]))
        for i in range(8): edges.append(_edge(f'n{i}',f'n{(i+1)%8}','octad_ring','clear'))
        for i in range(4): edges.append(_edge(f'n{i}',f'n{i+4}','podal_axis','neon'))
    elif name=='podal_24d_triplet':
        # 3 E8-like rings: head, center, tail; 24 nodes total
        idx=0
        for layer,z,label in [(-1,-1,'tail'),(0,0,'center'),(1,1,'head')]:
            for i in range(8):
                ang=2*pi*i/8 + layer*pi/16
                role=label
                nodes.append(_node(idx,f'{label}_e8_{i}',cx+cos(ang)*scale,cy+sin(ang)*scale,cz+z*scale,role=role,color=['red','green','blue','white','black','clear','grey','neon'][i]))
                idx+=1
        for base in (0,8,16):
            for i in range(8): edges.append(_edge(f'n{base+i}',f'n{base+(i+1)%8}','e8_ring','clear'))
        for i in range(8):
            edges.append(_edge(f'n{i}',f'n{8+i}','tail_center','blue'))
            edges.append(_edge(f'n{8+i}',f'n{16+i}','center_head','red'))
    elif name=='lattice_8x8':
        idx=0
        for y in range(8):
            for x in range(8):
                nodes.append(_node(idx,f'{x},{y}',cx+(x-3.5)*scale,cy+(y-3.5)*scale,cz,role='lattice',color='grey'))
                idx+=1
        for y in range(8):
            for x in range(8):
                i=y*8+x
                if x<7: edges.append(_edge(f'n{i}',f'n{i+1}','x_step','clear'))
                if y<7: edges.append(_edge(f'n{i}',f'n{i+8}','y_step','clear'))
    else: # radial_boundary
        nodes.append(_node(0,'C',cx,cy,cz,role='center',color='white'))
        for i in range(8):
            ang=2*pi*i/8
            nodes.append(_node(i+1,f'boundary_{i}',cx+cos(ang)*scale,cy+sin(ang)*scale,cz,role='boundary',color='neon'))
            edges.append(_edge('n0',f'n{i+1}','radial_boundary','neon'))
    return {'template':name,'orientation':orientation,'center':center,'scale':scale,'nodes':nodes,'edges':edges}
