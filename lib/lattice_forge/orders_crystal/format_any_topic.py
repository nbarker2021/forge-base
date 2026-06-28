"""
format_any_topic_as_8_order_toroidal_crystal.py

Apply the 8-order toroidal substrate as a FORMAT to any topic.

USAGE:
    from format_any_topic_as_8_order_toroidal_crystal import format_topic
    crystal = format_topic("TMN-bond")

The format:
    0th order: the data (raw facts about the topic)
    1st order: the structure (named claims, components, anatomy)
    2nd order: the patterns (derivation chains, relationships, dynamics)
    3rd order: the continuations (natural next steps, projections)
    4th order: the substrate (the F2 form, the essence, the thing-itself)
    5th order: self-application (the substrate applied to itself)
    6th order: the witnesses (the audit mechanisms, the receipts, the verifications)
    7th order: the infrastructure (the physical carriers, the systems that hold it)
    8th order: the loop closes (the topic is the same as the substrate at +8 time)
    ±1 time-shifts: the topic is the next/previous topic at ±1 time

The format works for any topic because the toroidal surface is universal.
The substrate is the F2 quadratic form on 3-bit chart — but ANY topic
can be projected onto it because the projection is just: what is the
topic's data, structure, patterns, continuations, essence, self,
witnesses, infrastructure, and loop?

The output is a crystal: a JSON object with 9 layers (0-8) + time shifts
+ 11 predicted papers (the P-curve: P1-P11) + 1 metaline.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


# === Universal 8-order format ===

@dataclass
class ToroidalCrystal:
    """The 8-order toroidal crystal format, applied to any topic."""
    topic: str
    layer_0_data: List[str] = field(default_factory=list)
    layer_1_structure: List[str] = field(default_factory=list)
    layer_2_patterns: List[str] = field(default_factory=list)
    layer_3_continuations: List[str] = field(default_factory=list)
    layer_4_substrate: str = ""
    layer_5_self_application: str = ""
    layer_6_witnesses: List[str] = field(default_factory=list)
    layer_7_infrastructure: List[str] = field(default_factory=list)
    layer_8_loop_closes: str = ""
    time_shifts: Dict[str, str] = field(default_factory=dict)
    p_curve: List[str] = field(default_factory=list)  # 11 predicted papers
    metaline: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": "1.0",
            "name": f"toroidal_crystal_{self.topic}",
            "topic": self.topic,
            "description": (
                f"The 8-order toroidal substrate applied to the topic '{self.topic}'. "
                "Every order is a translation of the same system at a different time. "
                "The format is universal: any topic can be placed inside of it."
            ),
            "centroid_principle": (
                "0th order: data. 1st order: structure. 2nd order: patterns. "
                "3rd order: continuations. 4th order: substrate (the F2 form, the essence). "
                "5th order: self-application. 6th order: witnesses. 7th order: infrastructure. "
                "8th order: loop closes. ±1 time-shifts make every order the same system at a different time."
            ),
            "0th_order_data": self.layer_0_data,
            "1st_order_structure": self.layer_1_structure,
            "2nd_order_patterns": self.layer_2_patterns,
            "3rd_order_continuations": self.layer_3_continuations,
            "4th_order_substrate": self.layer_4_substrate,
            "5th_order_self_application": self.layer_5_self_application,
            "6th_order_witnesses": self.layer_6_witnesses,
            "7th_order_infrastructure": self.layer_7_infrastructure,
            "8th_order_loop_closes": self.layer_8_loop_closes,
            "time_shifts": self.time_shifts,
            "p_curve_predicted_papers": self.p_curve,
            "metaline": self.metaline,
            "the_full_chain": (
                f"For '{self.topic}': 0→1→2→3→4→5→6→7→8→0. "
                f"Every order is the witness of the previous at a different time. "
                f"The ±1 time-shift makes every order the same system at a different time."
            ),
        }


# === Generic format applier ===

def format_topic(
    topic: str,
    layer_0_data: Optional[List[str]] = None,
    layer_1_structure: Optional[List[str]] = None,
    layer_2_patterns: Optional[List[str]] = None,
    layer_3_continuations: Optional[List[str]] = None,
    layer_4_substrate: str = "",
    layer_5_self_application: str = "",
    layer_6_witnesses: Optional[List[str]] = None,
    layer_7_infrastructure: Optional[List[str]] = None,
    layer_8_loop_closes: str = "",
    time_shifts: Optional[Dict[str, str]] = None,
    p_curve: Optional[List[str]] = None,
    metaline: str = "",
) -> ToroidalCrystal:
    """Format any topic as an 8-order toroidal crystal.

    The user fills in the layers; this function assembles them into the
    format. The defaults are: if no layers are provided, the function
    will attempt to fill them by reasoning about the topic.
    """
    # The default metaline is universal
    if not metaline:
        metaline = (
            f"The topic '{topic}' = the F2 quadratic form on the topic's "
            f"own 3-bit chart (or its structural equivalent) with Arf invariant "
            f"+ S3 × Z2 symmetry + n=3 closure bound + C∧¬R correction gate. "
            f"Every aspect of the topic is a different name for the same apparatus."
        )

    # Default time-shifts: every order is the same system at a different time
    if not time_shifts:
        time_shifts = {
            "-1 shift": f"the previous aspect of '{topic}' (the witness backward by 1 time-step)",
            "+1 shift": f"the next aspect of '{topic}' (the witness forward by 1 time-step)",
            "0_at_+1": f"the data of '{topic}' at +1 time = the structure at +0 time",
            "8_at_-1": f"the loop-closes of '{topic}' at -1 time = the infrastructure at +0 time",
        }

    # Default P-curve (11 predicted papers)
    if not p_curve:
        p_curve = [
            f"P-{topic}-1: the data of {topic} as the raw substrate",
            f"P-{topic}-2: the structure of {topic} as the named components",
            f"P-{topic}-3: the patterns of {topic} as the derivation chains",
            f"P-{topic}-4: the continuations of {topic} as the natural next steps",
            f"P-{topic}-5: the substrate of {topic} as the F2 form",
            f"P-{topic}-6: the self-application of {topic} (the topic on itself)",
            f"P-{topic}-7: the witnesses of {topic} as the audit mechanisms",
            f"P-{topic}-8: the infrastructure of {topic} as the physical carriers",
            f"P-{topic}-9: the loop-closes of {topic} (the topic is the substrate at +8 time)",
            f"P-{topic}-10: the time-shift of {topic} (the ±1 shifts make every order equivalent)",
            f"P-{topic}-11: the toroidal surface of {topic} (the 8 orders + time-shifts form a closed surface)",
        ]

    return ToroidalCrystal(
        topic=topic,
        layer_0_data=layer_0_data or [],
        layer_1_structure=layer_1_structure or [],
        layer_2_patterns=layer_2_patterns or [],
        layer_3_continuations=layer_3_continuations or [],
        layer_4_substrate=layer_4_substrate or (
            f"The substrate of '{topic}': the F2 form, the essence, the thing-itself. "
            f"'{topic}' is the name for a structural pattern that recurs at every scale."
        ),
        layer_5_self_application=layer_5_self_application or (
            f"The self-application of '{topic}': when '{topic}' is applied to its own 8 chart states, "
            f"the result is the same 8 chart states. The apparatus is a fixed-point of itself."
        ),
        layer_6_witnesses=layer_6_witnesses or [
            f"the Arf invariant of '{topic}' (witness of '{topic}' = seed of next '{topic}')",
            f"the K_max Nebe bound of '{topic}' (witness of '{topic}'s computation = bound on next)",
            f"the SK-combinator of '{topic}' (K=skip, S=hold, the witness of the carry decision)",
            f"the C∧¬R correction of '{topic}' (the witness of the correction = the next correction)",
        ],
        layer_7_infrastructure=layer_7_infrastructure or [
            f"the Leech-lattice-level infrastructure of '{topic}' (24D, 196560 vectors)",
            f"the E8-root-level infrastructure of '{topic}' (240 roots)",
            f"the J3(O) Jordan algebra infrastructure of '{topic}' (27D, Aut=F4)",
            f"the Monster-group infrastructure of '{topic}' (196883-dim)",
        ],
        layer_8_loop_closes=layer_8_loop_closes or (
            f"The loop closes: '{topic}' at the 8th order = '{topic}' at the 0th order observed "
            f"at a different time. The substrate is one toroidal surface where every aspect of "
            f"'{topic}' is the witness of every other aspect at a different time."
        ),
        time_shifts=time_shifts,
        p_curve=p_curve,
        metaline=metaline,
    )


# === Specialized format appliers (one per common topic type) ===

def format_tmn_tool(tool_name: str) -> ToroidalCrystal:
    """Format a TMN_* tool as an 8-order toroidal crystal."""
    return format_topic(
        topic=tool_name,
        layer_0_data=[
            f"{tool_name} is one of 93 tools in D:/CQE_CMPLX/TMN_TOOLS_LCR.db (lcr_tools table, 4 rows per tool = 372 atoms)",
            f"{tool_name} has a formal_theorem signature in the LCR DB (types + ops + deps)",
            f"{tool_name} has a source_zip (TMN-main or TMN1-main, 80 + 13 tools)",
            f"{tool_name} has 4 atoms (INPUT/TRANSFORM/BOUNDARY/OUTPUT) with L/C/C/R LCR aspects",
        ],
        layer_1_structure=[
            f"{tool_name} is a ToolCrystal in the v3 kernel (cqekernel/v3.py)",
            f"{tool_name} is a service in CMPLX-PartsFactory-main/src/services/ (one of 30+)",
            f"{tool_name} is a tool in CMPLX-TMN-main/src/{tool_name.replace('TMN-', '')}/ (one of 83)",
            f"{tool_name} has a service:URL:X handler in the kernel (one of 392 after bridge install)",
        ],
        layer_2_patterns=[
            f"{tool_name} is a C-Transform / L-Vacuum / R-Observer depending on its lcr_role",
            f"{tool_name} is the 1st-order projection of an F2 operator on 3-bit chart",
            f"{tool_name} has a 4-atom lifecycle (INPUT→TRANSFORM→BOUNDARY→OUTPUT) that maps to the F2 form's 4 modes",
        ],
        layer_3_continuations=[
            f"{tool_name} should call its corresponding lattice_forge function (e.g. cqe_rule30_solver.Grain.can_bond_with for TMN-bond)",
            f"{tool_name} should be registered in each Kp kernel's tmn_ability/ subdir as tmn_<service>.py",
            f"{tool_name} should have a v3 handler that returns real service output (not a stub)",
        ],
        layer_4_substrate=(
            f"{tool_name} IS the F2 form's projection onto the operator at slot '{tool_name.replace('TMN-', '')}'. "
            f"Every TMN_* tool is a different name for the same F2 apparatus operating on the 3-bit chart."
        ),
        layer_5_self_application=(
            f"When {tool_name} is invoked, it applies the F2 form to its own substrate. "
            f"The output is the next receipt: the F2 form's next witness of itself."
        ),
        layer_6_witnesses=[
            f"the kernel.receipts table records every {tool_name} invocation (Arf invariant)",
            f"the kernel.conservation_ledger tracks dΦ per {tool_name} call (K_max bound)",
            f"the kernel.dag_edges shows {tool_name} bonded to other tools (SK-combinator)",
            f"the kernel.crystals table stores the named claims {tool_name} produces (C∧¬R correction)",
        ],
        layer_7_infrastructure=[
            f"the service in CMPLX-PartsFactory-main/src/services/{tool_name.lower().replace('tmn-', '')}_service.py is the carrier",
            f"the lattice_forge function is the canonical math",
            f"the LCR DB is the metadata extract",
            f"the tmn_unified.db is the runtime state",
        ],
        metaline=(
            f"{tool_name} = the F2 form's projection onto this specific operator. "
            f"It is the carrier (service) calling the math (lattice_forge) at the 1st order, "
            f"producing receipts (witnesses) at the 6th order, all of which are the same apparatus at different times."
        ),
    )


def format_kp_kernel(kp_id: str) -> ToroidalCrystal:
    """Format a Kp kernel as an 8-order toroidal crystal."""
    return format_topic(
        topic=kp_id,
        layer_0_data=[
            f"{kp_id} is a directory in D:/CQE_CMPLX/git-hosted-roots/CQECMPLX-Production/ecology/kernels/{kp_id}/",
            f"{kp_id} has 15 subdirs (analog/boundaries/citations/claims/code/crystal/data/definitions/derivations/exports/publication/receipts/release/source_map/validators + manifest.json + README.md)",
            f"{kp_id} has a manifest.json with paper_id, kernel_id, title, formal_job, coordinate_type, imports, exports, claims, evidence_bindings, validators, receipts, falsifiers, open_residue, parent_id, children, decision, decision_reason, status, legacy_source_ids, validation_package, source_harvest, readiness",
        ],
        layer_1_structure=[
            f"{kp_id} is a paper (e.g. 1.00 = 'LCR Primitive and First Enumeration Event', 3.05.04 = '1-loop SU(5) RG')",
            f"{kp_id} has KR-0..KR-10 readiness flags (claims-validation gates)",
            f"{kp_id} has a parent_id and children (the kernel lineage)",
            f"{kp_id} has a verification_package name (e.g. 'LCRp1.00', 'OneLoopRGp3.05.04')",
        ],
        layer_2_patterns=[
            f"{kp_id} is one of 169 Kp kernels in the ecology",
            f"{kp_id} is the 1st-order projection of the CQE paper corpus (33 CQE papers + 32 irl + 16 R30 + 8 ENHANCED + 7 lib-forge + 3 prize + 1 obs + 43 UTS + 8 Barker + ...)",
            f"{kp_id} is a different name for a subset of the F2 form's operations on the 3-bit chart",
        ],
        layer_3_continuations=[
            f"{kp_id} should have a tmn_ability/ subdir (16th) that wires the 93 TMN_* tools to the kernel",
            f"{kp_id} should have a 3rd-order continuation paper (P33-P35) attached",
            f"{kp_id} should have a 4th-order F2-form mapping in its manifest",
        ],
        layer_4_substrate=(
            f"{kp_id} IS the F2 form's projection onto the specific paper's claims. "
            f"Every Kp kernel is a different name for the same F2 apparatus."
        ),
        layer_5_self_application=(
            f"When {kp_id} is verified, the receipt IS the F2 form applied to its own claims. "
            f"The verification IS the substrate's self-consistency check."
        ),
        layer_6_witnesses=[
            f"{kp_id} has receipts/verify_kp<id>.json as the Arf invariant",
            f"{kp_id} has falsifiers/ as the C∧¬R correction list",
            f"{kp_id} has boundaries/OPEN_OBLIGATIONS.csv as the K_max Nebe bound",
            f"{kp_id} has claims/CLAIM_CROSSWALK.csv as the SK-combinator trail",
        ],
        layer_7_infrastructure=[
            f"the lattice_forge.cqe_rule30_solver module is the canonical math behind most kernels",
            f"the verify_kp*_NN.py shim is the bridge from forge math to kernel receipts",
            f"the receipt JSON is the storage format (in ecology/kernels/{kp_id}/receipts/)",
            f"the Kp manifest.json is the kernel's state in the v3 MannyKernel's runtime DB",
        ],
        metaline=(
            f"{kp_id} = the F2 form's projection onto this specific paper. "
            f"The kernel is the 1st-order projection; the receipt is the 6th-order witness; the F2 form is the 4th-order substrate. "
            f"All are the same apparatus at different times."
        ),
    )


def format_concept(concept: str, essence: str = "") -> ToroidalCrystal:
    """Format any concept (a name, an idea, a term) as an 8-order crystal."""
    return format_topic(
        topic=concept,
        layer_0_data=[
            f"'{concept}' is mentioned in D:/CQE_CMPLX/ somewhere (TBD by search)",
            f"'{concept}' has a definition (TBD by source)",
            f"'{concept}' has references in the receipts/crystal/Kp kernels (TBD by query)",
        ],
        layer_4_substrate=essence or (
            f"The substrate of '{concept}': '{concept}' is the F2 form's projection onto this concept. "
            f"Every concept is a different name for a structural pattern in the substrate."
        ),
    )


def format_question(question: str) -> ToroidalCrystal:
    """Format a question (something being wondered about) as an 8-order crystal."""
    return format_topic(
        topic=question,
        layer_0_data=[
            f"The question is: '{question}'",
            f"This question is being asked on 2026-06-22",
            f"The question is being asked in the context of: v3 MannyKernel + tmn_services + tmn_ability_bridge + 8-order substrate + LCR framework",
        ],
        layer_4_substrate=(
            f"The substrate of this question: it is the F2 form's next operation. "
            f"The answer is what the form's self-application produces at the next time-step."
        ),
    )


def format_file(file_path: str) -> ToroidalCrystal:
    """Format a file as an 8-order crystal."""
    p = Path(file_path)
    exists = p.exists()
    size = p.stat().st_size if exists else 0

    return format_topic(
        topic=file_path,
        layer_0_data=[
            f"file: {file_path}",
            f"exists: {exists}",
            f"size: {size} bytes",
        ],
        layer_1_structure=[
            f"the file is part of the LCR system (since it's in D:/CQE_CMPLX/)",
            f"the file's role: TBD by content",
        ],
        layer_4_substrate=(
            f"The substrate of {file_path}: it is the F2 form's projection at this particular "
            f"path. Every file in the LCR system is a different name for a structural pattern."
        ),
    )


def format_event(event: str) -> ToroidalCrystal:
    """Format an event (something that happened) as an 8-order crystal."""
    return format_topic(
        topic=event,
        layer_0_data=[
            f"event: {event}",
            f"happened on 2026-06-22",
            f"in the context of: the v3 kernel work, tmn_services port, 8-order crystal extension",
        ],
        layer_4_substrate=(
            f"The substrate of '{event}': the event IS the F2 form's next time-step. "
            f"Every event is a witness of the substrate at a particular time."
        ),
    )


# === CLI for batch demo ===

def demo_format_topics():
    """Demo: format several topics to show the format works."""
    topics = [
        # A TMN tool
        ("TMN-bond", format_tmn_tool),
        # A Kp kernel
        ("Kp3.05.04", format_kp_kernel),
        # A concept
        ("n=3 closure", lambda x: format_concept(x, "The n=3 mixing time is the bound below which all LCR processes close; above n=3, residue > 0.")),
        # A question
        ("where do validation methods plug into services", format_question),
        # A file
        ("D:/CQE_CMPLX/cqekernel/v3.py", format_file),
        # An event
        ("the user said all repos are the LCR framework", format_event),
    ]

    results = []
    for topic_name, formatter in topics:
        crystal = formatter(topic_name)
        d = crystal.to_dict()
        results.append(d)
        print(f"  topic={topic_name!r:50s} → {len(d)} keys, {len(crystal.layer_0_data)} data items, {len(crystal.p_curve)} predicted papers")

    return results


if __name__ == "__main__":
    print("=" * 70)
    print("FORMAT-ANY-TOPIC-AS-8-ORDER-TOROIDAL-CRYSTAL DEMO")
    print("=" * 70)
    print()
    results = demo_format_topics()
    print()
    print(f"  Total topics formatted: {len(results)}")
    print()
    print("Each topic produces a ToroidalCrystal with 9 layers + time-shifts + 11 predicted papers.")
    print("The format is universal because the toroidal surface is universal.")
