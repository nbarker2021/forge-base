"""Witness API request/response models."""
from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class LCRReadoutRequest(BaseModel):
    left: int = Field(ge=0, le=1)
    center: int = Field(ge=0, le=1)
    right: int = Field(ge=0, le=1)


class NthBitRequest(BaseModel):
    depth: int = Field(ge=1, le=1_000_000)
    path: str = "auto"


class ParticipationRequest(BaseModel):
    max_depth: int = Field(default=512, ge=8, le=10_000)


class MaxDepthRequest(BaseModel):
    max_depth: int = Field(default=512, ge=8, le=10_000)


class SyndromeRequest(BaseModel):
    syndrome_keys: list[str] = Field(default_factory=lambda: ["non_glue", "ecc_shed"])


class ProofBundleFullRequest(BaseModel):
    quick: bool = False
    max_depth: int | None = None


class ClassifyRequest(BaseModel):
    source_id: Optional[str] = None
    target_id: Optional[str] = None
    morphism_id: Optional[str] = None


class RegimeAQueryRequest(BaseModel):
    n: int = Field(..., ge=1, description="1-indexed Rule 30 center depth")
    max_depth: int = Field(4096, ge=64, le=65536)
    base_page: int = Field(64, ge=8, le=256)


class RegimeARangeRequest(BaseModel):
    start: int = Field(..., ge=1)
    end: int = Field(..., ge=1)
    max_depth: int = Field(4096, ge=64, le=65536)
    base_page: int = Field(64, ge=8, le=256)


class ProofBundleRequest(BaseModel):
    max_depth: int = 128
    page_count: int = 2
    page_size: int = 128
    block_size: int = 8
    max_order: int = 4
    verify: bool = True


class WitnessResponse(BaseModel):
    kind: str
    status: str
    honesty: str
    result: dict[str, Any]
    provenance: dict[str, Any] = Field(default_factory=dict)
