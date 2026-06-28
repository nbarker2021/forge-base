
from __future__ import annotations
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Any

@dataclass(frozen=True)
class EngineRecord:
    key: str
    name: str
    role: str
    port: int | None
    package: str
    status: str = "mounted"

ENGINE_REGISTRY: Dict[str, EngineRecord] = {
    "rhenium": EngineRecord("rhenium", "Rhenium Engine", "global orchestrator/product engine", 8777, "rhenium_engine"),
    "kimi": EngineRecord("kimi", "Kimi/LCR Adapter", "work fragment -> LCR/D4/VOA receipt", None, "reforge_kimi_adapter"),
    "worldforge": EngineRecord("worldforge", "WorldForge UI Adapter", "receipt -> graph view", 8771, "reforge_worldforge_ui_adapter"),
    "researchcraft": EngineRecord("researchcraft", "ResearchCraft Module", "local-first journal persistence", 8772, "reforge_researchcraft"),
    "glyphforge": EngineRecord("glyphforge", "GlyphForge/FuMu", "text semantics -> fragments/papers/obligations", 8773, "reforge_glyphforge"),
    "pixleforge": EngineRecord("pixleforge", "PixleForge", "image/pixels -> LCR color graph", 8774, "reforge_pixleforge"),
    "wireforge": EngineRecord("wireforge", "WireForge", "orientation wireframe templates", 8775, "reforge_wireforge"),
    "frameforge": EngineRecord("frameforge", "FrameForge", "dynamic movement over wireframes", 8775, "reforge_frameforge"),
    "pixl8forge": EngineRecord("pixl8forge", "PixL8Forge", "Rote8/Devi8/Concat8 frame transitions", 8776, "reforge_pixl8forge"),
}

def list_engines() -> List[Dict[str, Any]]:
    return [asdict(v) for v in ENGINE_REGISTRY.values()]

def layer_map() -> List[Dict[str, str]]:
    return [
        {"layer":"source", "engine":"GlyphForge / PixleForge / WireForge", "meaning":"convert user work/media/templates into state objects"},
        {"layer":"carrier", "engine":"Kimi/LCR Adapter", "meaning":"encode into LCR blocks, D4 labels, and correction receipts"},
        {"layer":"orientation", "engine":"WireForge / FrameForge", "meaning":"preplace internal/external boundaries and movement frames"},
        {"layer":"media", "engine":"PixleForge / PixL8Forge", "meaning":"map pixels and frames into visible color dynamics"},
        {"layer":"world", "engine":"WorldForge", "meaning":"render graph/world/readout interaction"},
        {"layer":"memory", "engine":"ResearchCraft", "meaning":"persist journal, nodes, edges, receipts, obligations"},
        {"layer":"product", "engine":"Rhenium", "meaning":"compose engines into ReForge product flows"},
    ]
