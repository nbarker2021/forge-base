from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List
import json, time, uuid, hashlib

VALID_COLORS = {"red","green","blue","white","black","grey","clear","neon","unknown"}
VALID_FOLLOWUPS = {"proof","obligation","guess","new_item","unresolved","receipt","pass"}
VALID_NODE_TYPES = {"fragment","lcr_block","claim","definition","axiom","lemma","example","test","obligation","receipt","paper_section","supplement","source","world_state","wire_node","frame","frame_wire_node","pixel_patch","carrier"}


def stable_id(prefix: str, payload: Any) -> str:
    blob = json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
    return f"{prefix}_{hashlib.sha256(blob).hexdigest()[:16]}"


def now() -> float:
    return time.time()

@dataclass(init=False)
class LCRBlock:
    index: int = 0
    left: int = 0
    center: int = 0
    right: int = 0
    gamma: int = 0
    axis: str = "unknown"
    sheet: str = "unknown"
    voa_weight: int = 0
    correction: int = 0
    color_state: str = "unknown"
    copy_index: int = 0
    role: str = "carrier"

    def __init__(self, *args: Any, **kw: Any):
        # Supports both hardening form: LCRBlock(index,left,center,right,gamma,...)
        # and wire/media form: LCRBlock(L,C,R,color_state,copy_index,role).
        if args and len(args) >= 3 and "left" not in kw and "L" not in kw:
            if len(args) == 3 or (len(args) >= 4 and isinstance(args[3], str)):
                kw.update({"left": args[0], "center": args[1], "right": args[2]})
                if len(args) >= 4: kw["color_state"] = args[3]
                if len(args) >= 5: kw["copy_index"] = args[4]
                if len(args) >= 6: kw["role"] = args[5]
            else:
                keys=["index","left","center","right","gamma","axis","sheet","voa_weight","correction","color_state"]
                kw.update({k:v for k,v in zip(keys,args)})
        # alternate dict keys
        if "L" in kw: kw["left"] = kw.pop("L")
        if "C" in kw: kw["center"] = kw.pop("C")
        if "R" in kw: kw["right"] = kw.pop("R")
        self.index=int(kw.get("index", kw.get("copy_index", 0)))
        self.left=int(kw.get("left", 0)); self.center=int(kw.get("center", 0)); self.right=int(kw.get("right", 0))
        self.gamma=int(kw.get("gamma", self.center))
        self.axis=str(kw.get("axis", "unknown")); self.sheet=str(kw.get("sheet", "unknown"))
        self.voa_weight=int(kw.get("voa_weight", 0)); self.correction=int(kw.get("correction", 0))
        self.color_state=str(kw.get("color_state", "unknown"))
        self.copy_index=int(kw.get("copy_index", self.index)); self.role=str(kw.get("role", "carrier"))

    @property
    def L(self) -> int: return self.left
    @property
    def C(self) -> int: return self.center
    @property
    def R(self) -> int: return self.right

    def Gamma(self) -> int: return self.center

    def validate(self) -> None:
        for name in ("left","center","right","gamma","correction"):
            v = getattr(self, name)
            if v not in (0,1):
                raise ValueError(f"{name} must be binary, got {v!r}")
        if self.gamma != self.center:
            raise ValueError("gamma invariant violated: gamma must equal center")
        if self.color_state not in VALID_COLORS:
            raise ValueError(f"invalid color_state {self.color_state!r}")

    def to_dict(self) -> Dict[str, Any]:
        return {"index":self.index,"L":self.left,"C":self.center,"R":self.right,"Gamma":self.gamma,"left":self.left,"center":self.center,"right":self.right,"gamma":self.gamma,"axis":self.axis,"sheet":self.sheet,"voa_weight":self.voa_weight,"correction":self.correction,"color_state":self.color_state,"copy_index":self.copy_index,"role":self.role}

@dataclass
class GraphNode:
    id: str
    label: str
    node_type: str
    color_state: str = "unknown"
    payload: Dict[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        if not self.id or not self.label:
            raise ValueError("node id and label required")
        if self.color_state not in VALID_COLORS:
            raise ValueError(f"invalid color_state {self.color_state!r}")

    def to_dict(self) -> Dict[str, Any]:
        d=asdict(self); d["payload"] = self.payload or {}; return d

@dataclass
class GraphEdge:
    source: str
    target: str
    edge_type: str = "continues"
    color_state: str = "grey"
    payload: Dict[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        if not self.source or not self.target:
            raise ValueError("edge source and target required")

    def to_dict(self) -> Dict[str, Any]:
        d=asdict(self); d["payload"] = self.payload or {}; return d

@dataclass(init=False)
class Receipt:
    receipt_id: str
    source_text: str
    followup: str
    blocks: List[Any]
    nodes: List[Any]
    edges: List[Any]
    metadata: Dict[str, Any]
    created_at: float
    engine: str
    status: str
    payload: Dict[str, Any]

    def __init__(self, receipt_id: str, *args: Any, **kw: Any):
        self.receipt_id = receipt_id
        # Wire/media form: Receipt(rid, engine, status, lcr, nodes, edges, payload, timestamp)
        if args and len(args) >= 7:
            self.engine=str(args[0]); self.status=str(args[1]); self.blocks=list(args[2]); self.nodes=list(args[3]); self.edges=list(args[4]); self.payload=dict(args[5] or {}); self.created_at=float(args[6])
            self.source_text=str(kw.get("source_text", "")); self.followup=str(kw.get("followup", self.status)); self.metadata=dict(kw.get("metadata", {}))
        else:
            self.source_text=str(kw.get("source_text", args[0] if len(args)>0 else ""))
            self.followup=str(kw.get("followup", args[1] if len(args)>1 else "unresolved"))
            self.blocks=list(kw.get("blocks", args[2] if len(args)>2 else []))
            self.nodes=list(kw.get("nodes", [])); self.edges=list(kw.get("edges", []))
            self.metadata=dict(kw.get("metadata", {})); self.created_at=float(kw.get("created_at", time.time()))
            self.engine=str(kw.get("engine", "unknown")); self.status=str(kw.get("status", self.followup)); self.payload=dict(kw.get("payload", {}))

    @classmethod
    def new(cls, source_text: str, followup: str, blocks: List[LCRBlock], **kw: Any) -> "Receipt":
        return cls("rcpt_" + uuid.uuid4().hex[:12], source_text=source_text, followup=followup, blocks=blocks, **kw)

    def validate(self) -> None:
        if self.followup not in VALID_FOLLOWUPS:
            raise ValueError(f"invalid followup {self.followup!r}")
        for b in self.blocks:
            if hasattr(b, "validate"): b.validate()

    def to_dict(self) -> Dict[str, Any]:
        def conv(x):
            if hasattr(x, "to_dict"): return x.to_dict()
            if hasattr(x, "__dict__"): return dict(x.__dict__)
            return x
        return {"receipt_id":self.receipt_id,"source_text":self.source_text,"followup":self.followup,"engine":self.engine,"status":self.status,"blocks":[conv(b) for b in self.blocks],"lcr_blocks":[conv(b) for b in self.blocks],"nodes":[conv(n) for n in self.nodes],"edges":[conv(e) for e in self.edges],"metadata":self.metadata,"payload":self.payload,"created_at":self.created_at,"timestamp":self.created_at}

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, sort_keys=True, default=str)
