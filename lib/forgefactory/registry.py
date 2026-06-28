from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Any

@dataclass(frozen=True)
class EngineRecord:
    key: str
    name: str
    role: str
    package: str
    status: str = "curated"
    port: int | None = None

ENGINE_REGISTRY: dict[str, EngineRecord] = {
    "latticeforge": EngineRecord("latticeforge", "LatticeForge", "math substrate: Rule30/Rule90, D4 codecs, VOA, J3(O), oloid, Leech/Niemeier, transport obligations", "lattice_forge"),
    "contracts": EngineRecord("contracts", "Engine Contracts", "shared LCR/graph/receipt types", "reforge_engine_contracts"),
    "hardening": EngineRecord("hardening", "Engine Hardening", "contract validation and health checks", "reforge_engine_hardening"),
    "kimi": EngineRecord("kimi", "Kimi/LCR Adapter", "work fragment to LCR/D4/VOA receipt", "reforge_kimi_adapter"),
    "glyphforge": EngineRecord("glyphforge", "GlyphForge/FuMu", "document and language-demand fragment routing", "reforge_glyphforge", port=8773),
    "researchcraft": EngineRecord("researchcraft", "ResearchCraft Module", "local-first graph and receipt persistence", "reforge_researchcraft", port=8772),
    "pixleforge": EngineRecord("pixleforge", "PixleForge", "image/pixel carrier encoding", "reforge_pixleforge", port=8774),
    "wireforge": EngineRecord("wireforge", "WireForge", "orientation wireframe templates", "reforge_wireforge", port=8775),
    "frameforge": EngineRecord("frameforge", "FrameForge", "movement paths over wireframes", "reforge_frameforge", port=8775),
    "pixl8forge": EngineRecord("pixl8forge", "PixL8Forge", "Rote8/Devi8/Concat8 frame transitions", "reforge_pixl8forge", port=8776),
    "rhenium": EngineRecord("rhenium", "Rhenium Engine", "global ReForge product composition", "rhenium_engine", port=8777),
    "paper00": EngineRecord("paper00", "Paper 00 Transport Contract Tool", "paper-bound claim-to-receipt validator and workbook sheet generator", "forgefactory.papers.paper00_transport_contract"),
    "morphonix": EngineRecord("morphonix", "MorphoniX planned layer", "1x1..9x9 grid sweep, dyads, bifurcations, token/form database", "forgefactory.morphonix", status="planned"),
}

def list_engines() -> list[dict[str, Any]]:
    return [asdict(v) for v in ENGINE_REGISTRY.values()]

def layer_map() -> list[dict[str, str]]:
    return [
        {"layer":"math-substrate", "engine":"LatticeForge", "meaning":"source math substrate: Rule30/Rule90, D4/J3/VOA, oloid, Leech/Niemeier, transport obligations"},
        {"layer":"contract", "engine":"Engine Contracts", "meaning":"one shared LCR/graph/receipt schema"},
        {"layer":"proof", "engine":"Kimi/LCR Adapter", "meaning":"work fragments become proof/obligation receipts"},
        {"layer":"document", "engine":"GlyphForge/FuMu", "meaning":"documents become semantic fragments and paper/supplement routes"},
        {"layer":"memory", "engine":"ResearchCraft", "meaning":"local journals, nodes, edges, receipts, obligations"},
        {"layer":"pixel", "engine":"PixleForge", "meaning":"images become color-state block graphs"},
        {"layer":"orientation", "engine":"WireForge/FrameForge", "meaning":"internal/external boundary orientation and movement templates"},
        {"layer":"video", "engine":"PixL8Forge", "meaning":"Rote8/Devi8/Concat8 frame transitions"},
        {"layer":"global", "engine":"Rhenium Engine", "meaning":"compose all engines as one ReForge product layer"},
        {"layer":"paper-tools", "engine":"Paper 00 Tool", "meaning":"formal claim-to-receipt transport validation and analog workbook sheet generation"},
        {"layer":"future-token", "engine":"MorphoniX", "meaning":"grid sweep and bifurcation database for token/form production"},
    ]
