"""
GraphStax AGRM — Adaptive Geometric Resonance Matrix routing engine.

Stripped from donor routing source. Names preserved for logic clarity;
identity stripped. GR-spiral sweep + zone classification + midpoint routing.

Uses Golden Ratio sweeps to rank candidate nodes in nD geometric space.
Node density zones (sparse/medium/dense) modulate routing quality.
Routes are cached after first computation.

All mathematical constants are import-time lookup tables.
"""
import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

# ─── Lookup tables (import-time, read-only) ────────────────────────────────────

PHI: float = (1.0 + math.sqrt(5.0)) / 2.0
COUPLING: float = math.log(PHI) / 16.0   # κ ≈ 0.030076

# GR spiral reference angles for first 24 nodes (import-time)
_GR_ANGLES: Tuple[float, ...] = tuple((i * PHI) % 1.0 for i in range(24))

# Zone classification thresholds: neighbor count → density
_ZONE_THRESHOLDS: Tuple[Tuple[int, str], ...] = ((3, "sparse"), (8, "medium"), (999, "dense"))


# ─── Zone density ─────────────────────────────────────────────────────────────

class ZoneDensity(Enum):
    SPARSE = "sparse"
    MEDIUM = "medium"
    DENSE  = "dense"


# ─── Data classes ─────────────────────────────────────────────────────────────

@dataclass
class StaxNode:
    """A node in AGRM routing space. Represents a resolved Stax sheet position."""
    node_id: str
    position: List[float]       # nD position (default 24D)
    resonance: str              # resonance signature (hash of content identity)
    metadata: Dict[str, Any] = field(default_factory=dict)

    # AGRM classification (computed by router after registration)
    shell_index: int = 0
    sector: int = 0
    density: ZoneDensity = ZoneDensity.MEDIUM

    def distance_to(self, other: "StaxNode") -> float:
        n = min(len(self.position), len(other.position))
        return math.sqrt(sum((self.position[i] - other.position[i]) ** 2 for i in range(n)))


@dataclass
class StaxRoute:
    """A route between StaxNodes."""
    path: List[str]             # node_id sequence
    total_distance: float
    legs: List[Tuple[str, str, float]]
    quality: float = 0.0        # 0..1, higher = better

    def __len__(self) -> int:
        return len(self.path)


@dataclass
class SweepResult:
    """Result of a GR sweep scan."""
    ranked: List[Tuple[StaxNode, float]]   # (node, score) sorted descending
    center: List[float]
    max_radius: float


# ─── GR Sweep Scanner ─────────────────────────────────────────────────────────

class AGRMSweepScanner:
    """Ranks nodes by alignment with Golden Ratio spiral sweep pattern."""

    def __init__(self, dimensions: int = 24):
        self.dimensions = dimensions

    def centroid(self, nodes: List[StaxNode]) -> List[float]:
        if not nodes:
            return [0.0] * self.dimensions
        n = self.dimensions
        return [
            sum(nd.position[d] for nd in nodes) / len(nodes)
            for d in range(n)
        ]

    def _score(self, node: StaxNode, center: List[float],
               radius: float, index: int) -> float:
        """GR spiral score: how well does this node align with the sweep at index?"""
        d = self.dimensions
        dist = math.sqrt(sum((node.position[i] - center[i]) ** 2 for i in range(d)))
        if dist > radius or dist < 1e-9:
            return 0.0
        normalized = dist / radius
        spiral = _GR_ANGLES[index % len(_GR_ANGLES)]
        score = 1.0 - abs(normalized - spiral)
        if node.density == ZoneDensity.SPARSE:
            score *= 1.2       # exploration bonus for sparse zones
        return max(0.0, score)

    def sweep(self, nodes: List[StaxNode],
              center: Optional[List[float]] = None) -> SweepResult:
        if not nodes:
            return SweepResult([], [0.0] * self.dimensions, 0.0)
        if center is None:
            center = self.centroid(nodes)
        d = self.dimensions
        max_radius = max(
            math.sqrt(sum((n.position[i] - center[i]) ** 2 for i in range(d)))
            for n in nodes
        ) or 1.0
        scored = sorted(
            [(n, self._score(n, center, max_radius, i)) for i, n in enumerate(nodes)],
            key=lambda x: -x[1],
        )
        return SweepResult(scored, center, max_radius)


# ─── Zone Classifier ─────────────────────────────────────────────────────────

class AGRMZoneClassifier:
    """Classifies nodes by neighbor density within a radius."""

    def __init__(self, dimensions: int = 24):
        self.dimensions = dimensions

    def classify(self, node: StaxNode, all_nodes: List[StaxNode],
                 radius: float) -> ZoneDensity:
        neighbors = sum(
            1 for n in all_nodes
            if n.node_id != node.node_id and node.distance_to(n) < radius
        )
        for threshold, label in _ZONE_THRESHOLDS:
            if neighbors < threshold:
                return ZoneDensity(label)
        return ZoneDensity.DENSE

    def assign_shells(self, nodes: List[StaxNode], center: List[float],
                      num_shells: int = 5) -> Dict[str, int]:
        d = self.dimensions
        distances = [
            (n, math.sqrt(sum((n.position[i] - center[i]) ** 2 for i in range(d))))
            for n in nodes
        ]
        if not distances:
            return {}
        max_dist = max(dist for _, dist in distances) or 1.0
        shell_width = max_dist / num_shells
        result = {}
        for node, dist in distances:
            shell = min(int(dist / shell_width), num_shells - 1)
            node.shell_index = shell
            result[node.node_id] = shell
        return result


# ─── Path Builder ─────────────────────────────────────────────────────────────

class AGRMPathBuilder:
    """Builds routes via GR-guided midpoint traversal."""

    def __init__(self, dimensions: int = 24):
        self.dimensions = dimensions
        self._scanner = AGRMSweepScanner(dimensions)

    def build(self, start: StaxNode, end: StaxNode,
              candidates: List[StaxNode], max_hops: int = 5) -> StaxRoute:
        if start.node_id == end.node_id:
            return StaxRoute([start.node_id], 0.0, [])

        direct = start.distance_to(end)

        if candidates:
            d = self.dimensions
            midpoint = [(start.position[i] + end.position[i]) / 2.0 for i in range(d)]
            sweep = self._scanner.sweep(candidates, center=midpoint)

            path = [start.node_id]
            current = start
            total = 0.0
            legs = []

            for node, score in sweep.ranked[:max_hops]:
                if score < 0.3:
                    continue
                dist = current.distance_to(node)
                legs.append((current.node_id, node.node_id, dist))
                total += dist
                path.append(node.node_id)
                current = node
                if current.distance_to(end) < direct * 0.5:
                    break

            final = current.distance_to(end)
            legs.append((current.node_id, end.node_id, final))
            total += final
            path.append(end.node_id)
            quality = 1.0 / (1.0 + total / max(len(legs), 1))
            return StaxRoute(path, total, legs, quality)

        return StaxRoute(
            [start.node_id, end.node_id], direct,
            [(start.node_id, end.node_id, direct)], 0.5,
        )


# ─── AGRMRouter ───────────────────────────────────────────────────────────────

class AGRMRouter:
    """
    Main AGRM router for Stax graph navigation.

    Registers StaxNodes, sweeps by GR spiral, builds cached routes between nodes.
    Route queries can filter by resonance similarity for identity-guided traversal.
    """

    def __init__(self, dimensions: int = 24):
        self.dimensions = dimensions
        self._scanner = AGRMSweepScanner(dimensions)
        self._classifier = AGRMZoneClassifier(dimensions)
        self._builder = AGRMPathBuilder(dimensions)
        self._nodes: Dict[str, StaxNode] = {}
        self._routes: Dict[Tuple[str, str], StaxRoute] = {}

    def register(self, node_id: str, position: List[float],
                 resonance: str, metadata: Dict[str, Any] = None,
                 reclassify: bool = True) -> StaxNode:
        """Register a StaxNode. Reclassifies all nodes unless reclassify=False.

        For bulk registration, pass reclassify=False per node and call
        reclassify() once at the end — classification is O(n²) per call.
        """
        node = StaxNode(
            node_id=node_id,
            position=list(position[:self.dimensions]),
            resonance=resonance,
            metadata=metadata or {},
        )
        self._nodes[node_id] = node
        if reclassify:
            self._reclassify()
        return node

    def reclassify(self) -> None:
        """Public batch reclassification — call after bulk register(reclassify=False)."""
        self._reclassify()

    def _reclassify(self) -> None:
        nodes = list(self._nodes.values())
        if not nodes:
            return
        center = self._scanner.centroid(nodes)
        d = self.dimensions
        max_r = max(
            math.sqrt(sum((n.position[i] - center[i]) ** 2 for i in range(d)))
            for n in nodes
        ) or 1.0
        for node in nodes:
            node.density = self._classifier.classify(node, nodes, max_r * 0.2)
        self._classifier.assign_shells(nodes, center)
        # Invalidate cached routes after reclassification
        self._routes.clear()

    def find_nearest(self, position: List[float], n: int = 5) -> List[Tuple[StaxNode, float]]:
        """Find n nearest registered nodes to a position."""
        pos = list(position[:self.dimensions])
        d = self.dimensions
        distances = [
            (node, math.sqrt(sum((node.position[i] - pos[i]) ** 2 for i in range(d))))
            for node in self._nodes.values()
        ]
        distances.sort(key=lambda x: x[1])
        return distances[:n]

    def sweep_from(self, node_id: str,
                   predicate: Optional[Callable[[StaxNode], bool]] = None) -> SweepResult:
        """GR sweep from a registered node, optionally filtered by predicate."""
        center_node = self._nodes.get(node_id)
        if not center_node:
            return SweepResult([], [0.0] * self.dimensions, 0.0)
        candidates = [n for n in self._nodes.values() if predicate is None or predicate(n)]
        return self._scanner.sweep(candidates, center_node.position)

    def route(self, from_id: str, to_id: str,
              max_hops: int = 5) -> Optional[StaxRoute]:
        """Build or retrieve cached route between two nodes."""
        key = (from_id, to_id)
        if key in self._routes:
            return self._routes[key]
        start = self._nodes.get(from_id)
        end   = self._nodes.get(to_id)
        if not start or not end:
            return None
        candidates = [n for n in self._nodes.values()
                      if n.node_id not in (from_id, to_id)]
        r = self._builder.build(start, end, candidates, max_hops)
        self._routes[key] = r
        return r

    def query_resonance(self, from_id: str, target_resonance: str,
                        threshold: float = 0.7,
                        max_results: int = 3) -> List[Tuple[str, StaxRoute]]:
        """Route query to nodes with matching resonance prefix."""
        from_node = self._nodes.get(from_id)
        if not from_node:
            return []
        def similar(n: StaxNode) -> bool:
            return n.resonance[:8] == target_resonance[:8]
        sweep = self.sweep_from(from_id, similar)
        results = []
        for node, score in sweep.ranked:
            if score < threshold:
                continue
            r = self.route(from_id, node.node_id)
            if r:
                results.append((node.node_id, r))
            if len(results) >= max_results:
                break
        return results

    def get_node(self, node_id: str) -> Optional[StaxNode]:
        return self._nodes.get(node_id)

    def stats(self) -> Dict[str, Any]:
        density_counts = {"sparse": 0, "medium": 0, "dense": 0}
        for node in self._nodes.values():
            density_counts[node.density.value] += 1
        return {
            "nodes": len(self._nodes),
            "cached_routes": len(self._routes),
            "density": density_counts,
            "dimensions": self.dimensions,
        }

    @property
    def node_count(self) -> int:
        return len(self._nodes)
