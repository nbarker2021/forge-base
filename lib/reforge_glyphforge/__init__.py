"""GlyphForge / FuMu: document-language demand engine for ReForge.

This module parses entered work into typed semantic fragments, routes each
fragment through the Kimi/LCR receipt adapter, and emits ResearchCraft-ready
nodes, obligations, paper skeletons, and supplement skeletons.
"""
from .fumu import classify_fragment, split_fragments, analyze_work, export_markdown_bundle
__all__ = ["classify_fragment", "split_fragments", "analyze_work", "export_markdown_bundle"]
