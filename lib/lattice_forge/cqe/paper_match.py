"""Paper-to-sheet adapter for CQE current-frame matching."""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256

from .frame import CQECurrentFrame, HistoricalSheet, TermBundleResult


@dataclass(frozen=True)
class PaperDatum:
    """One paper or report to mount as a historical sheet."""

    title: str
    path: str
    text: str


@dataclass(frozen=True)
class PaperSheet:
    """A paper plus its derived current-frame sheet."""

    path: str
    sheet: HistoricalSheet


@dataclass(frozen=True)
class PaperBundleMatch:
    """CQE bundle match over paper-derived historical sheets."""

    sheets: tuple[PaperSheet, ...]
    bundle: TermBundleResult


KEYWORD_FAMILIES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("cqe", ("cqe", "cartan quadratic", "quadratic equivalence")),
    ("cmplx", ("cmplx", "managed processing")),
    ("n", ("n|-n", "-n", "enumerated validation", "enumeration", "dr8")),
    ("jo3", ("jo3", "jordanian", "su(3)", "su3")),
    ("f4", ("f4", "closure/lift", "closure", "lift")),
    ("weyl", ("weyl", "weyl transition", "lie conjunction")),
    ("lambda", ("lambda", "beta", "reduction", "normal form")),
    ("rule30", ("rule 30", "rule30", "cellular", "automaton")),
    ("light-cone", ("light-cone", "causal cone", "cone")),
    ("e8", ("e8", "lattice", "exceptional")),
    ("route", ("route", "routing", "lane", "control")),
    ("receipt", ("receipt", "portal", "emit")),
    ("oloid", ("oloid", "roll", "rolling")),
    ("spinor", ("spinor", "chirality", "su(2)", "so(3)")),
    ("d4", ("d4", "antipodal", "axis", "sheet")),
    ("actuation", ("actuation", "paired", "antipode")),
    ("moonshine", ("moonshine", "mckay", "thompson", "monster")),
    ("softmax", ("softmax", "gaussian", "rehydrate", "negative lane")),
    ("nudge", ("nudge", "read", "write", "correction")),
)


def paper_sheet_from_text(paper: PaperDatum) -> PaperSheet:
    """Derive a CQE historical sheet from paper content."""

    signature = _function_signature(paper.text)
    return PaperSheet(
        path=paper.path,
        sheet=HistoricalSheet(
            name=paper.title,
            size=_sheet_size(paper.text),
            terms=_terms(paper.title, paper.text),
            spectral_signature=_spectral_signature(paper.text),
            function_signature=signature,
            their_c=paper.title,
            their_n=len(paper.text),
            their_k=max(1, len(signature)),
        ),
    )


def match_paper_bundle(
    frame: CQECurrentFrame,
    terms: tuple[str, ...],
    papers: tuple[PaperDatum, ...],
) -> PaperBundleMatch:
    sheets = tuple(paper_sheet_from_text(paper) for paper in papers)
    bundle = frame.process_term_bundle(terms, tuple(paper.sheet for paper in sheets))
    return PaperBundleMatch(sheets=sheets, bundle=bundle)


def _function_signature(text: str) -> tuple[str, ...]:
    lowered = text.casefold()
    return tuple(
        family
        for family, needles in KEYWORD_FAMILIES
        if any(needle in lowered for needle in needles)
    )


def _terms(title: str, text: str) -> tuple[str, ...]:
    lowered = f"{title} {text}".casefold()
    return tuple(
        family
        for family, needles in KEYWORD_FAMILIES
        if family in lowered or any(needle in lowered for needle in needles)
    )


def _spectral_signature(text: str) -> tuple[int, ...]:
    digest = sha256(text.encode("utf-8", errors="ignore")).digest()
    return tuple((digest[index] >> (index % 8)) & 1 for index in range(8))


def _sheet_size(text: str) -> int:
    words = max(1, len(text.split()))
    # Keep paper sheets in the same dimensional window used by current-frame
    # tests: 15 maps to 4096 under score = 16 * (size + 1)^2.
    return max(1, min(15, int((words / 16) ** 0.5)))
