"""Current CQE frame over historical sheets."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class HistoricalSheet:
    """One historical build item viewed as a sheet under the current CQE frame."""

    name: str
    size: int
    terms: tuple[str, ...]
    spectral_signature: tuple[int, ...]
    function_signature: tuple[str, ...] = ()
    their_c: str = ""
    their_n: int = 0
    their_k: int = 0


@dataclass(frozen=True)
class SheetSelection:
    """Result of selecting and relating historical sheets to current C."""

    term: str
    ceiling: int
    selected: HistoricalSheet | None
    selected_score: int
    exceeded: tuple[HistoricalSheet, ...]
    conjugate_edges: tuple[HistoricalSheet, ...]
    nudge: str
    need: str


@dataclass(frozen=True)
class TermBundleResult:
    """One eight-term CQE pass over historical sheets."""

    terms: tuple[str, ...]
    currents: dict[str, SheetSelection]
    orbit_edges: dict[str, tuple[str, ...]]
    doubling_edges: dict[str, tuple[str, ...]]
    nudges: tuple[str, ...]


@dataclass(frozen=True)
class DiagonalBundleResult:
    """Two eight-term bundles on opposite diagonals around current C."""

    target_ceiling: int
    orbit_cycle: tuple[str, str, str, str, str]
    left_diagonal: TermBundleResult
    right_diagonal: TermBundleResult
    left_diagonal_id: str
    right_diagonal_id: str


@dataclass(frozen=True)
class CQECurrentFrame:
    """The current observer frame: all historical work is mounted relative to this C."""

    current_c: str
    current_n: int
    current_k: int

    @property
    def dimensional_ceiling(self) -> int:
        return self.current_n

    def select_build_item(
        self,
        term: str,
        sheets: Iterable[HistoricalSheet],
    ) -> SheetSelection:
        candidates = tuple(sheets)
        named = tuple(sheet for sheet in candidates if _matches_term(term, sheet))
        scored = tuple((sheet, _dimensional_score(sheet)) for sheet in named)
        fitting = tuple((sheet, score) for sheet, score in scored if score <= self.dimensional_ceiling)
        exceeded = tuple(sheet for sheet, score in scored if score > self.dimensional_ceiling)
        selected, selected_score = _closest_fit(fitting)
        conjugates = _conjugate_edges(selected, candidates)
        if selected is None:
            return SheetSelection(
                term=term,
                ceiling=self.dimensional_ceiling,
                selected=None,
                selected_score=0,
                exceeded=exceeded,
                conjugate_edges=(),
                nudge="NUDGE_L",
                need="compress historical sheets into singular compositions",
            )
        if conjugates:
            return SheetSelection(
                term=term,
                ceiling=self.dimensional_ceiling,
                selected=selected,
                selected_score=selected_score,
                exceeded=exceeded,
                conjugate_edges=conjugates,
                nudge="NUDGE_R",
                need="install conjugate edge lanes before canonizing transfer",
            )
        return SheetSelection(
            term=term,
            ceiling=self.dimensional_ceiling,
            selected=selected,
            selected_score=selected_score,
            exceeded=exceeded,
            conjugate_edges=(),
            nudge="COAST",
            need="",
        )

    def process_term_bundle(
        self,
        terms: tuple[str, ...],
        sheets: Iterable[HistoricalSheet],
    ) -> TermBundleResult:
        if len(terms) != 8:
            raise ValueError("term bundles must contain exactly 8 terms")
        candidates = tuple(sheets)
        currents = {term: self.select_build_item(term, candidates) for term in terms}
        orbit_edges = {
            selection.selected.name: _orbit_edges(selection.selected, candidates)
            for selection in currents.values()
            if selection.selected is not None and _orbit_edges(selection.selected, candidates)
        }
        doubling_edges = {
            selection.selected.name: _doubling_edges(selection.selected, candidates)
            for selection in currents.values()
            if selection.selected is not None and _doubling_edges(selection.selected, candidates)
        }
        nudges = tuple(
            sorted({selection.nudge for selection in currents.values() if selection.nudge != "COAST"})
        )
        if (orbit_edges or doubling_edges) and "NUDGE_R" not in nudges:
            nudges = tuple(sorted((*nudges, "NUDGE_R")))
        return TermBundleResult(
            terms=terms,
            currents=currents,
            orbit_edges=orbit_edges,
            doubling_edges=doubling_edges,
            nudges=nudges,
        )

    def process_diagonal_bundles(
        self,
        left_terms: tuple[str, ...],
        right_terms: tuple[str, ...],
        sheets: Iterable[HistoricalSheet],
    ) -> DiagonalBundleResult:
        target = self.current_n // 4
        diagonal_frame = CQECurrentFrame(
            current_c=self.current_c,
            current_n=target,
            current_k=self.current_k,
        )
        candidates = tuple(sheets)
        return DiagonalBundleResult(
            target_ceiling=target,
            orbit_cycle=("C", "L", "C", "R", "C"),
            left_diagonal=diagonal_frame.process_term_bundle(left_terms, candidates),
            right_diagonal=diagonal_frame.process_term_bundle(right_terms, candidates),
            left_diagonal_id="C->L->C",
            right_diagonal_id="C->R->C",
        )


def _matches_term(term: str, sheet: HistoricalSheet) -> bool:
    normalized = term.casefold()
    return sheet.name.casefold() == normalized or any(t.casefold() == normalized for t in sheet.terms)


def _dimensional_score(sheet: HistoricalSheet) -> int:
    # Add the singular transfer term, square the sheet extent, then concatenate
    # across the sixteen transfer lanes of the current frame.
    return 16 * (sheet.size + 1) ** 2


def _closest_fit(
    fitting: tuple[tuple[HistoricalSheet, int], ...],
) -> tuple[HistoricalSheet | None, int]:
    if not fitting:
        return None, 0
    return max(fitting, key=lambda item: item[1])


def _conjugate_edges(
    selected: HistoricalSheet | None,
    candidates: tuple[HistoricalSheet, ...],
) -> tuple[HistoricalSheet, ...]:
    if selected is None:
        return ()
    return tuple(
        sheet
        for sheet in candidates
        if sheet is not selected
        and sheet.name != selected.name
        and sheet.spectral_signature == selected.spectral_signature
    )


def _orbit_edges(
    selected: HistoricalSheet | None,
    candidates: tuple[HistoricalSheet, ...],
) -> tuple[str, ...]:
    if selected is None:
        return ()
    return tuple(
        sheet.name
        for sheet in candidates
        if sheet is not selected
        and sheet.function_signature
        and len(set(sheet.function_signature) & set(selected.function_signature)) >= 2
    )


def _doubling_edges(
    selected: HistoricalSheet | None,
    candidates: tuple[HistoricalSheet, ...],
) -> tuple[str, ...]:
    if selected is None:
        return ()
    doubled = selected.spectral_signature + selected.spectral_signature
    return tuple(
        sheet.name
        for sheet in candidates
        if sheet is not selected and sheet.spectral_signature == doubled
    )
