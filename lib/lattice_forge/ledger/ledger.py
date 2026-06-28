from __future__ import annotations

import json
import sqlite3
from collections import deque
from pathlib import Path
from typing import Any, Iterable

from .schema import SCHEMA_SQL
from ..terminal_tree import build_terminal_composition_tree, terminal_tree_summary


class Ledger:
    """SQLite-backed morphism/admissibility ledger."""

    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn
        self.conn.row_factory = sqlite3.Row
        self.defer_commit = False

    @classmethod
    def open(cls, path: str | Path) -> "Ledger":
        conn = sqlite3.connect(str(path))
        conn.row_factory = sqlite3.Row
        return cls(conn)

    @classmethod
    def create(cls, path: str | Path, overwrite: bool = False) -> "Ledger":
        path = Path(path)
        if overwrite and path.exists():
            path.unlink()
        conn = sqlite3.connect(str(path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=MEMORY")
        conn.execute("PRAGMA synchronous=OFF")
        conn.executescript(SCHEMA_SQL)
        conn.commit()
        return cls(conn)

    def close(self) -> None:
        self.conn.close()

    def execute(self, sql: str, params: Iterable[Any] = ()) -> sqlite3.Cursor:
        cur = self.conn.execute(sql, tuple(params))
        if not self.defer_commit:
            self.conn.commit()
        return cur

    def query(self, sql: str, params: Iterable[Any] = ()) -> list[dict[str, Any]]:
        return [dict(row) for row in self.conn.execute(sql, tuple(params)).fetchall()]

    def object(self, object_id: str) -> dict[str, Any] | None:
        rows = self.query("SELECT * FROM object_registry WHERE object_id=?", [object_id])
        return rows[0] if rows else None

    def objects(self, kind: str | None = None) -> list[dict[str, Any]]:
        if kind:
            return self.query("SELECT * FROM object_registry WHERE kind=? ORDER BY family,name", [kind])
        return self.query("SELECT * FROM object_registry ORDER BY family,name")

    def invariants(self, object_id: str) -> list[dict[str, Any]]:
        return self.query("SELECT * FROM object_invariants WHERE object_id=? ORDER BY invariant_type", [object_id])

    def components(self, object_id: str) -> list[dict[str, Any]]:
        return self.query("SELECT * FROM component_decompositions WHERE object_id=? ORDER BY component_family,component_rank", [object_id])

    def vectors(self, object_id: str, limit: int | None = None) -> list[dict[str, Any]]:
        sql = "SELECT * FROM exact_vectors WHERE object_id=? ORDER BY vector_id"
        params: list[Any] = [object_id]
        if limit is not None:
            sql += " LIMIT ?"
            params.append(limit)
        return self.query(sql, params)

    def gram(self, object_id: str) -> dict[str, Any] | None:
        rows = self.query("SELECT * FROM gram_forms WHERE object_id=?", [object_id])
        return rows[0] if rows else None

    def morphisms_from(self, object_id: str) -> list[dict[str, Any]]:
        return self.query(
            "SELECT * FROM morphism_registry WHERE source_id=? ORDER BY target_id,morphism_type",
            [object_id],
        )

    def morphisms_to(self, object_id: str) -> list[dict[str, Any]]:
        return self.query(
            "SELECT * FROM morphism_registry WHERE target_id=? ORDER BY source_id,morphism_type",
            [object_id],
        )

    def edges_from(self, object_id: str, status: str | None = None) -> list[dict[str, Any]]:
        if status:
            return self.query(
                "SELECT * FROM admissibility_edges WHERE source_id=? AND status=? ORDER BY target_id",
                [object_id, status],
            )
        return self.query("SELECT * FROM admissibility_edges WHERE source_id=? ORDER BY target_id", [object_id])

    def descendants(self, object_id: str, max_depth: int = 8, status: str = "legal") -> list[dict[str, Any]]:
        """Return reachable admissibility descendants with a BFS path."""
        seen = {object_id}
        q: deque[tuple[str, list[str]]] = deque([(object_id, [object_id])])
        out: list[dict[str, Any]] = []
        while q:
            current, path = q.popleft()
            if len(path) - 1 >= max_depth:
                continue
            for edge in self.edges_from(current, status=status):
                target = edge["target_id"]
                if target in seen:
                    continue
                seen.add(target)
                next_path = path + [target]
                obj = self.object(target) or {"name": target, "kind": "unknown"}
                out.append({"object_id": target, "name": obj.get("name"), "kind": obj.get("kind"), "path": next_path})
                q.append((target, next_path))
        return out

    def terminal_futures(self, object_id: str, max_depth: int = 10) -> list[dict[str, Any]]:
        terminals = {row["terminal_id"] for row in self.query("SELECT terminal_id FROM terminal_24d_forms")}
        return [x for x in self.descendants(object_id, max_depth=max_depth) if x["object_id"] in terminals]

    def terminal_candidates(self, object_id: str, max_depth: int = 10) -> list[dict[str, Any]]:
        """Return reachable 24D terminals with terminal/discriminant profiles."""
        out: list[dict[str, Any]] = []
        for item in self.terminal_futures(object_id, max_depth=max_depth):
            terminal_id = item["object_id"]
            term = self.query("SELECT * FROM terminal_24d_forms WHERE terminal_id=?", [terminal_id])
            disc = self.discriminant_profile(terminal_id)
            tree = self.terminal_tree(terminal_id)
            out.append({
                **item,
                "terminal": term[0] if term else None,
                "discriminant_profile": disc,
                "terminal_tree_summary": terminal_tree_summary(tree),
                "glue_templates": self.path_glue_templates(item["path"], terminal_id),
            })
        return out

    def discriminant_profile(self, object_id: str) -> dict[str, Any] | None:
        rows = self.query("SELECT * FROM discriminant_registry WHERE object_id=?", [object_id])
        return rows[0] if rows else None

    def reflection_actions(self, object_id: str, generator_index: int | None = None, limit: int | None = 50) -> list[dict[str, Any]]:
        sql = "SELECT * FROM reflection_action_registry WHERE object_id=?"
        params: list[Any] = [object_id]
        if generator_index is not None:
            sql += " AND generator_index=?"
            params.append(generator_index)
        sql += " ORDER BY generator_index, source_vector_id"
        if limit is not None:
            sql += " LIMIT ?"
            params.append(limit)
        return self.query(sql, params)

    def root_neighborhood_profile(self, object_id: str) -> dict[str, Any] | None:
        rows = self.query("SELECT * FROM root_neighborhood_profiles WHERE object_id=?", [object_id])
        return rows[0] if rows else None

    def root_adjacencies(self, object_id: str, adjacency_kind: str | None = None, limit: int | None = 50) -> list[dict[str, Any]]:
        sql = "SELECT * FROM root_adjacency_registry WHERE object_id=?"
        params: list[Any] = [object_id]
        if adjacency_kind:
            sql += " AND adjacency_kind=?"
            params.append(adjacency_kind)
        sql += " ORDER BY adjacency_kind, source_vector_id, target_vector_id"
        if limit is not None:
            sql += " LIMIT ?"
            params.append(limit)
        return self.query(sql, params)

    def morphism_witnesses(self, source_id: str | None = None, target_id: str | None = None, morphism_id: str | None = None) -> list[dict[str, Any]]:
        clauses: list[str] = []
        params: list[Any] = []
        if morphism_id:
            clauses.append("morphism_id=?")
            params.append(morphism_id)
        if source_id:
            clauses.append("source_id=?")
            params.append(source_id)
        if target_id:
            clauses.append("target_id=?")
            params.append(target_id)
        sql = "SELECT * FROM morphism_witness_registry"
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        sql += " ORDER BY source_id,target_id,witness_type"
        return self.query(sql, params)

    def nsl_boundary(self, source_id: str | None = None, target_id: str | None = None) -> list[dict[str, Any]]:
        clauses: list[str] = []
        params: list[Any] = []
        if source_id:
            clauses.append("source_id=?")
            params.append(source_id)
        if target_id:
            clauses.append("target_id=?")
            params.append(target_id)
        sql = "SELECT * FROM nsl_boundary_registry"
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        sql += " ORDER BY source_id,target_id"
        return self.query(sql, params)

    def build_manifests(self) -> list[dict[str, Any]]:
        return self.query("SELECT * FROM build_manifest_registry ORDER BY created_utc DESC")

    def edge_between(self, source_id: str, target_id: str, status: str = "legal") -> dict[str, Any] | None:
        rows = self.query(
            "SELECT * FROM admissibility_edges WHERE source_id=? AND target_id=? AND status=? ORDER BY edge_id LIMIT 1",
            [source_id, target_id, status],
        )
        return rows[0] if rows else None

    def path_edges(self, path: list[str]) -> list[dict[str, Any]]:
        out = []
        for source, target in zip(path, path[1:], strict=False):
            edge = self.edge_between(source, target) or {"source_id": source, "target_id": target, "status": "missing"}
            out.append(edge)
        return out

    def path_glue_templates(self, path: list[str], target_id: str) -> list[dict[str, Any]]:
        candidates: list[dict[str, Any]] = []
        for source in path:
            candidates.extend(self.query("SELECT * FROM glue_requirements WHERE source_id=? AND target_id=?", [source, target_id]))
        return candidates

    def can_close(self, source_id: str, target_id: str, max_depth: int = 10) -> dict[str, Any]:
        """Query whether an object has a legal path to a target terminal/object."""
        requested_target_id = target_id
        target_id = self.resolve_terminal_id(target_id) or target_id
        if source_id == target_id:
            return {
                "answer": "yes",
                "path": [source_id],
                "target": target_id,
                "requested_target": requested_target_id,
                "notes": "source is target",
            }
        for item in self.descendants(source_id, max_depth=max_depth):
            if item["object_id"] == target_id:
                path = item["path"]
                glue = self.path_glue_templates(path, target_id)
                return {
                    "answer": "yes_with_template_glue" if glue else "yes",
                    "path": path,
                    "path_edges": self.path_edges(path),
                    "target": target_id,
                    "requested_target": requested_target_id,
                    "glue_templates": glue,
                    "discriminant_profile": self.discriminant_profile(target_id),
                }
        forbidden = self.query(
            "SELECT * FROM admissibility_edges WHERE source_id=? AND target_id=? AND status='forbidden'",
            [source_id, target_id],
        )
        if forbidden:
            return {
                "answer": "no",
                "target": target_id,
                "requested_target": requested_target_id,
                "obstruction": forbidden[0].get("obstruction_json"),
            }
        return {
            "answer": "unknown",
            "target": target_id,
            "requested_target": requested_target_id,
            "notes": "no seeded admissibility path found",
        }

    def terminal_profile(self, terminal_id: str) -> dict[str, Any]:
        terminal_id = self.resolve_terminal_id(terminal_id) or terminal_id
        obj = self.object(terminal_id)
        terminal = self.query("SELECT * FROM terminal_24d_forms WHERE terminal_id=?", [terminal_id])
        return {
            "object": obj,
            "terminal": terminal[0] if terminal else None,
            "components": self.components(terminal_id),
            "component_embeddings": self.terminal_component_embeddings(terminal_id=terminal_id, limit=100),
            "invariants": self.invariants(terminal_id),
            "gram": self.gram(terminal_id),
            "vector_count": self.conn.execute("SELECT COUNT(*) FROM exact_vectors WHERE object_id=?", [terminal_id]).fetchone()[0],
            "discriminant_profile": self.discriminant_profile(terminal_id),
        }

    def resolve_terminal_id(self, terminal_ref: str) -> str | None:
        rows = self.query(
            """
            SELECT terminal_id FROM terminal_24d_forms
            WHERE terminal_id=? OR name=? OR root_system=?
            ORDER BY terminal_id
            LIMIT 1
            """,
            [terminal_ref, terminal_ref, terminal_ref],
        )
        return rows[0]["terminal_id"] if rows else None

    def terminal_tree(self, terminal_id: str) -> dict[str, Any]:
        terminal_id = self.resolve_terminal_id(terminal_id) or terminal_id
        return build_terminal_composition_tree(self, terminal_id)

    def terminal_trees(self) -> list[dict[str, Any]]:
        rows = self.query("SELECT terminal_id FROM terminal_24d_forms ORDER BY terminal_id")
        return [terminal_tree_summary(self.terminal_tree(row["terminal_id"])) for row in rows]

    def verify_terminal_trees(self) -> dict[str, Any]:
        diagnostics: list[dict[str, Any]] = []
        errors: list[str] = []
        rows = self.query("SELECT terminal_id, name, root_system FROM terminal_24d_forms ORDER BY terminal_id")
        for row in rows:
            terminal_id = row["terminal_id"]
            tree = self.terminal_tree(terminal_id)
            summary = terminal_tree_summary(tree)
            embedding_count = len(tree.get("component_instances", []))
            action_count = len(tree.get("action_edges", []))
            is_leech = terminal_id == "Niemeier:Leech"
            terminal_errors: list[str] = []
            if summary["ambient_dimension"] != 24:
                terminal_errors.append(f"ambient dimension is {summary['ambient_dimension']}, expected 24")
            if is_leech:
                if summary["root_rank"] != 0:
                    terminal_errors.append(f"Leech root rank is {summary['root_rank']}, expected 0")
                if action_count != 0:
                    terminal_errors.append(f"Leech action count is {action_count}, expected 0")
            else:
                if summary["root_rank"] != 24:
                    terminal_errors.append(f"root rank is {summary['root_rank']}, expected 24")
                if action_count != embedding_count:
                    terminal_errors.append(
                        f"action count {action_count} does not equal embedding count {embedding_count}"
                    )
                if summary["compact_involution_count"] <= 0:
                    terminal_errors.append("compact involution/action coverage is empty")
                if summary["residue_status"] != "residue_closes_by_required_index":
                    terminal_errors.append(f"residue status is {summary['residue_status']}")
            for alias in {terminal_id, row["name"], row["root_system"]}:
                if self.resolve_terminal_id(alias) != terminal_id:
                    terminal_errors.append(f"alias did not resolve: {alias}")
            diagnostics.append(
                {
                    **summary,
                    "embedding_count": embedding_count,
                    "action_edge_count": action_count,
                    "errors": terminal_errors,
                }
            )
            errors.extend(f"{terminal_id}: {error}" for error in terminal_errors)
        return {
            "status": "pass" if not errors and len(diagnostics) == 24 else "fail",
            "terminal_count": len(diagnostics),
            "errors": errors,
            "diagnostics": diagnostics,
        }

    def rag_card(self, object_id: str) -> dict[str, Any] | None:
        rows = self.query("SELECT * FROM rag_cards WHERE object_id=?", [object_id])
        return rows[0] if rows else None

    def external_resources(self) -> list[dict[str, Any]]:
        return self.query("SELECT * FROM external_resource_registry ORDER BY source,resource_type,title")


    def construction_status(self, object_id: str) -> list[dict[str, Any]]:
        return self.query(
            "SELECT * FROM construction_status_registry WHERE object_id=? ORDER BY surface_type",
            [object_id],
        )

    def prime_factor_profile(self, object_id: str) -> list[dict[str, Any]]:
        return self.query(
            "SELECT * FROM prime_factor_registry WHERE object_id=? ORDER BY integer_name",
            [object_id],
        )

    def pariah_profile(self, object_id: str) -> dict[str, Any]:
        obj = self.object(object_id)
        if not obj:
            return {"error": f"no object found: {object_id}"}
        return {
            "object": obj,
            "prime_factor_profiles": self.prime_factor_profile(object_id),
            "construction_status": self.construction_status(object_id),
            "rag_card": self.rag_card(object_id),
            "outgoing_boundary_edges": self.edges_from(object_id),
            "incoming_boundary_edges": self.query("SELECT * FROM admissibility_edges WHERE target_id=? ORDER BY source_id", [object_id]),
        }

    def path_metric(self, path_hash: str | None = None, source_id: str | None = None, target_id: str | None = None) -> list[dict[str, Any]]:
        if path_hash:
            return self.query("SELECT * FROM path_metrics WHERE path_hash=?", [path_hash])
        if source_id and target_id:
            return self.query("SELECT * FROM path_metrics WHERE source_id=? AND target_id=? ORDER BY edge_count,evidence_level", [source_id, target_id])
        if source_id:
            return self.query("SELECT * FROM path_metrics WHERE source_id=? ORDER BY target_id,edge_count", [source_id])
        return self.query("SELECT * FROM path_metrics ORDER BY source_id,target_id,edge_count")

    def future_cone(self, object_id: str, max_depth: int = 8) -> dict[str, Any]:
        obj = self.object(object_id)
        descendants = self.descendants(object_id, max_depth=max_depth)
        terminal_candidates = self.terminal_candidates(object_id, max_depth=max_depth)
        return {
            "object": obj,
            "construction_status": self.construction_status(object_id),
            "prime_factor_profiles": self.prime_factor_profile(object_id),
            "root_neighborhood_profile": self.root_neighborhood_profile(object_id),
            "dynkin_profile": self.dynkin_profile(object_id),
            "morphism_verifications": self.morphism_verifications(source_id=object_id),
            "closure_obstructions": self.closure_obstructions(source_id=object_id),
            "descendant_count": len(descendants),
            "descendants": descendants,
            "terminal_candidate_count": len(terminal_candidates),
            "terminal_candidates": terminal_candidates,
            "path_metrics": self.path_metric(source_id=object_id),
            "nsl_boundaries": self.nsl_boundary(source_id=object_id),
        }

    def dynkin_profile(self, object_id: str) -> dict[str, Any] | None:
        rows = self.query("SELECT * FROM dynkin_registry WHERE object_id=?", [object_id])
        return rows[0] if rows else None

    def terminal_component_embeddings(self, terminal_id: str | None = None, source_id: str | None = None, limit: int | None = None) -> list[dict[str, Any]]:
        clauses: list[str] = []
        params: list[Any] = []
        if terminal_id:
            clauses.append("terminal_id=?")
            params.append(terminal_id)
        if source_id:
            clauses.append("source_id=?")
            params.append(source_id)
        sql = "SELECT * FROM terminal_component_embeddings"
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        sql += " ORDER BY terminal_id, rank_offset, component_instance_index"
        if limit is not None:
            sql += " LIMIT ?"
            params.append(limit)
        return self.query(sql, params)

    def morphism_verifications(self, source_id: str | None = None, target_id: str | None = None, morphism_id: str | None = None) -> list[dict[str, Any]]:
        clauses: list[str] = []
        params: list[Any] = []
        if morphism_id:
            clauses.append("morphism_id=?")
            params.append(morphism_id)
        if source_id:
            clauses.append("source_id=?")
            params.append(source_id)
        if target_id:
            clauses.append("target_id=?")
            params.append(target_id)
        sql = "SELECT * FROM morphism_verification_registry"
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        sql += " ORDER BY source_id,target_id,verification_type"
        return self.query(sql, params)

    def closure_obstructions(self, source_id: str | None = None, target_id: str | None = None) -> list[dict[str, Any]]:
        clauses: list[str] = []
        params: list[Any] = []
        if source_id:
            clauses.append("source_id=?")
            params.append(source_id)
        if target_id:
            clauses.append("target_id=?")
            params.append(target_id)
        sql = "SELECT * FROM closure_obstruction_registry"
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        sql += " ORDER BY severity DESC, source_id, target_id, obstruction_type"
        return self.query(sql, params)

    def exactness_dashboard(self, object_id: str) -> dict[str, Any]:
        return {
            "object": self.object(object_id),
            "construction_status": self.construction_status(object_id),
            "dynkin_profile": self.dynkin_profile(object_id),
            "invariants": self.invariants(object_id),
            "root_neighborhood_profile": self.root_neighborhood_profile(object_id),
            "morphism_witnesses_from": self.morphism_witnesses(source_id=object_id),
            "morphism_verifications_from": self.morphism_verifications(source_id=object_id),
            "component_embeddings_as_source": self.terminal_component_embeddings(source_id=object_id, limit=50),
            "closure_obstructions_from": self.closure_obstructions(source_id=object_id),
        }

    def export_object_bundle(self, object_id: str, vector_limit: int = 12) -> dict[str, Any]:
        return {
            "object": self.object(object_id),
            "construction_status": self.construction_status(object_id),
            "prime_factor_profiles": self.prime_factor_profile(object_id),
            "invariants": self.invariants(object_id),
            "components": self.components(object_id),
            "gram": self.gram(object_id),
            "root_neighborhood_profile": self.root_neighborhood_profile(object_id),
            "dynkin_profile": self.dynkin_profile(object_id),
            "vector_count": self.conn.execute("SELECT COUNT(*) FROM exact_vectors WHERE object_id=?", [object_id]).fetchone()[0],
            "vector_sample": self.vectors(object_id, limit=vector_limit),
            "morphisms_from": self.morphisms_from(object_id),
            "morphisms_to": self.morphisms_to(object_id),
            "morphism_witnesses_from": self.morphism_witnesses(source_id=object_id),
            "morphism_verifications_from": self.morphism_verifications(source_id=object_id),
            "terminal_component_embeddings_as_source": self.terminal_component_embeddings(source_id=object_id, limit=50),
            "edges_from": self.edges_from(object_id),
            "nsl_boundaries_from": self.nsl_boundary(source_id=object_id),
            "rag_card": self.rag_card(object_id),
        }

    def closure_report(self, source_id: str, target_id: str, max_depth: int = 10) -> dict[str, Any]:
        target_ref = target_id
        target_id = self.resolve_terminal_id(target_ref) or target_ref
        close = self.can_close(source_id, target_ref, max_depth=max_depth)
        terminal_tree = None
        if self.query("SELECT 1 FROM terminal_24d_forms WHERE terminal_id=? LIMIT 1", [target_id]):
            terminal_tree = self.terminal_tree(target_id)
            if close.get("answer", "").startswith("yes"):
                close = {
                    **close,
                    "closure_model": "canonical_terminal_composition_tree",
                    "composition_residue_status": terminal_tree.get("closure_residue", {}).get("status"),
                }
        metrics = []
        if close.get("path"):
            import json as _json
            path = close["path"]
            rows = self.query("SELECT * FROM path_metrics WHERE path_json=?", [_json.dumps(path, sort_keys=True)])
            metrics = rows or self.path_metric(source_id=source_id, target_id=target_id)
        return {
            "can_close": close,
            "source_status": self.construction_status(source_id),
            "target_status": self.construction_status(target_id),
            "terminal_tree": terminal_tree,
            "path_metrics": metrics,
            "nsl_boundary": self.nsl_boundary(source_id=source_id, target_id=target_id),
            "morphism_witnesses": self.morphism_witnesses(source_id=source_id, target_id=target_id),
            "morphism_verifications": self.morphism_verifications(source_id=source_id, target_id=target_id),
            "closure_obstructions": self.closure_obstructions(source_id=source_id, target_id=target_id),
            "source_prime_profile": self.prime_factor_profile(source_id),
            "target_prime_profile": self.prime_factor_profile(target_id),
        }

    def verify(self) -> dict[str, Any]:
        """Run integrity checks over seeded exact root counts and terminal profiles."""
        errors: list[str] = []
        root_expect = {"A1": 2, "A2": 6, "D4": 24, "G2": 12, "F4": 48, "E6": 72, "E7": 126, "E8": 240}
        for object_id, expected in root_expect.items():
            actual = self.conn.execute("SELECT COUNT(*) FROM exact_vectors WHERE object_id=?", [object_id]).fetchone()[0]
            if actual != expected:
                errors.append(f"{object_id}: expected {expected} roots, found {actual}")
        for row in self.query("SELECT terminal_id, root_system FROM terminal_24d_forms"):
            terminal_id = row["terminal_id"]
            inv_rows = self.query("SELECT payload_json FROM object_invariants WHERE object_id=? AND invariant_type='terminal_root_shell'", [terminal_id])
            if not inv_rows:
                errors.append(f"{terminal_id}: missing terminal_root_shell invariant")
                continue
            payload = json.loads(inv_rows[0]["payload_json"])
            expected = int(payload.get("root_count", -1))
            actual = self.conn.execute("SELECT COUNT(*) FROM exact_vectors WHERE object_id=?", [terminal_id]).fetchone()[0]
            if actual != expected:
                errors.append(f"{terminal_id}: expected {expected} terminal roots, found {actual}")
            if terminal_id != "Niemeier:Leech" and payload.get("rank") != 24:
                errors.append(f"{terminal_id}: expected rank 24, found {payload.get('rank')}")
        for row in self.query("SELECT object_id, rank FROM object_registry WHERE kind='root_system'"):
            object_id = row["object_id"]
            rank = int(row["rank"] or 0)
            roots = self.conn.execute("SELECT COUNT(*) FROM exact_vectors WHERE object_id=?", [object_id]).fetchone()[0]
            actions = self.conn.execute("SELECT COUNT(*) FROM reflection_action_registry WHERE object_id=?", [object_id]).fetchone()[0]
            # Reflection actions are seeded only for the compact/core operator set in v0.3.
            if actions and rank and roots and actions != rank * roots:
                errors.append(f"{object_id}: expected {rank * roots} reflection actions, found {actions}")
        for row in self.query("SELECT terminal_id FROM terminal_24d_forms"):
            if not self.discriminant_profile(row["terminal_id"]):
                errors.append(f"{row['terminal_id']}: missing discriminant profile")
        for oid in ["Monster:M", "Pariah:J1", "Pariah:J3", "Pariah:ON", "Pariah:Ru", "Pariah:J4", "Pariah:Ly"]:
            if not self.prime_factor_profile(oid):
                errors.append(f"{oid}: missing prime factor profile")
        if self.conn.execute("SELECT COUNT(*) FROM construction_status_registry").fetchone()[0] == 0:
            errors.append("construction_status_registry is empty")
        if self.conn.execute("SELECT COUNT(*) FROM path_metrics").fetchone()[0] == 0:
            errors.append("path_metrics is empty")
        if self.conn.execute("SELECT COUNT(*) FROM root_neighborhood_profiles").fetchone()[0] == 0:
            errors.append("root_neighborhood_profiles is empty")
        if self.conn.execute("SELECT COUNT(*) FROM morphism_witness_registry").fetchone()[0] == 0:
            errors.append("morphism_witness_registry is empty")
        if self.conn.execute("SELECT COUNT(*) FROM nsl_boundary_registry").fetchone()[0] == 0:
            errors.append("nsl_boundary_registry is empty")
        if self.conn.execute("SELECT COUNT(*) FROM dynkin_registry").fetchone()[0] == 0:
            errors.append("dynkin_registry is empty")
        if self.conn.execute("SELECT COUNT(*) FROM terminal_component_embeddings").fetchone()[0] == 0:
            errors.append("terminal_component_embeddings is empty")
        if self.conn.execute("SELECT COUNT(*) FROM morphism_verification_registry").fetchone()[0] == 0:
            errors.append("morphism_verification_registry is empty")
        if self.conn.execute("SELECT COUNT(*) FROM closure_obstruction_registry").fetchone()[0] == 0:
            errors.append("closure_obstruction_registry is empty")
        return {"status": "pass" if not errors else "fail", "errors": errors, "summary": self.summary()}

    def summary(self) -> dict[str, int]:
        tables = [
            "object_registry",
            "exact_vectors",
            "gram_forms",
            "morphism_registry",
            "involution_registry",
            "convolution_registry",
            "admissibility_edges",
            "terminal_24d_forms",
            "glue_requirements",
            "residue_registry",
            "rag_cards",
            "object_invariants",
            "component_decompositions",
            "external_resource_registry",
            "verification_runs",
            "path_registry",
            "discriminant_registry",
            "reflection_action_registry",
            "terminal_admissibility_profiles",
            "construction_status_registry",
            "prime_factor_registry",
            "path_metrics",
            "root_neighborhood_profiles",
            "root_adjacency_registry",
            "morphism_witness_registry",
            "nsl_boundary_registry",
            "build_manifest_registry",
            "dynkin_registry",
            "terminal_component_embeddings",
            "morphism_verification_registry",
            "closure_obstruction_registry",
        ]
        return {t: self.conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in tables}
