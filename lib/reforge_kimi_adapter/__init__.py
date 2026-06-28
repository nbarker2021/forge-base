"""ReForge ↔ Kimi adapter v0.1.

Small dependency-free adapter layer that turns arbitrary work fragments into
LCR/TarPit/D4/VOA proof-obligation receipts and WorldForge graph nodes.
"""
from .adapter import adapt_work_fragment, batch_adapt
