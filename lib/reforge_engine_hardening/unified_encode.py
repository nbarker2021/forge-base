from __future__ import annotations
from reforge_engine_contracts import LCRBlock, GraphNode, GraphEdge, Receipt

def text_to_bits(text: str) -> list[int]:
    return [int(bit) for byte in text.encode("utf-8") for bit in f"{byte:08b}"] or [0]

def bits_to_lcr_blocks(bits: list[int], color_state: str = "grey") -> list[LCRBlock]:
    padded = [0] + bits + [0]
    blocks = []
    for i in range(1, len(padded)-1):
        L,C,R = padded[i-1], padded[i], padded[i+1]
        correction = int(C == 1 and R == 0)
        axis = f"A{(L<<2)|(C<<1)|R}"
        sheet = "positive" if C else "negative"
        voa_weight = 5 if (L+C+R) not in (0,3) else 0
        blocks.append(LCRBlock(index=i-1,left=L,center=C,right=R,gamma=C,axis=axis,sheet=sheet,voa_weight=voa_weight,correction=correction,color_state=color_state))
    return blocks

def encode_fragment(text: str, color_state: str = "grey") -> Receipt:
    blocks = bits_to_lcr_blocks(text_to_bits(text), color_state=color_state)
    nodes=[GraphNode(id=f"n{i}",label=f"block {i}",node_type="lcr_block",color_state=color_state,payload={"axis":b.axis,"sheet":b.sheet,"gamma":b.gamma}) for i,b in enumerate(blocks[:64])]
    edges=[GraphEdge(source=f"n{i}",target=f"n{i+1}",edge_type="continues") for i in range(max(0,len(nodes)-1))]
    followup = "proof" if sum(b.correction for b in blocks) % 2 == 0 else "obligation"
    r=Receipt.new(source_text=text, followup=followup, blocks=blocks, nodes=nodes, edges=edges, metadata={"encoder":"reforge_engine_hardening.unified_encode"})
    r.validate()
    return r
