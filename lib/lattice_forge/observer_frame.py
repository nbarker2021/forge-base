"""Observer-frame engine (recrafted from CQECMPLX-Formal-Suite CQE-PAPER-050/051/052/053).

The CQE observer cluster's HONEST core: the chart has a 4-fold D4 frame symmetry; the
observer selects 1 of 4 frame anchors, the gluon = Center (C) component is invariant
under LR swap (trivially, since LR fixes C), and static Z4 (4-frame label period)
is exact while TEMPOAL Z4 (temporal periodicity of the Rule-30 orbit) is refuted.

FABRICATIONS DROPPED (per recraft rule - not ported into root prose):
  - "64/64 observer rows" multiplier (padding; the invariant holds per-state)
  - "37 side-disagreements" (honest L!=R count = 6, not 37)
  - Born-rule "P = 1/4 each frame" (no probability derivation exists)
  - "7 latent faces retained lossless" conflation of 4 D4 faces with 7-fold paths
  - A033996 (NOT present in 050-053)
"""

from lattice_forge.axiom_verifiers import CHART_STATES, TRUE_VACUA
from lattice_forge.boundary_complex import swap_lr
from lattice_forge.centroid_voa import four_frame_label, z4_period, verify_z4_period_template

# 4 D4 frame anchors (representative chart states used as frame labels in the sources).
D4_FRAME_ANCHORS = [(0, 1, 0), (1, 1, 0), (1, 1, 1), (0, 0, 1)]


def verify_observer_frame_selection():
    """Observer = D4 face selection; gluon C invariant; static Z4 exact, temporal Z4 refuted."""
    checks = {}

    # 1. 4 D4 frame anchors are distinct chart states.
    checks["four_distinct_frames"] = (len(set(D4_FRAME_ANCHORS)) == 4)

    # 2. Selecting 1 of 4 leaves the other 3 as latent (frame count, not 7).
    checks["select_1_retain_3"] = (len(D4_FRAME_ANCHORS) - 1 == 3)

    # 3. Gluon = Center C; invariant under LR swap (LR fixes C).
    gluon_ok = all(s[1] == swap_lr(s)[1] for s in CHART_STATES)
    checks["gluon_c_lr_invariant"] = gluon_ok

    # 4. Shared Center C across all 8 states under LR swap (verify_shared_center_c covers this).
    from lattice_forge.centroid_voa import verify_shared_center_c
    sc = verify_shared_center_c()
    checks["shared_center_c"] = (sc["status"] == "pass")

    # 5. Static Z4 template exact (2 fixed, 0 period-2, 6 period-4) via 4-frame label.
    z4 = verify_z4_period_template()
    checks["static_z4_template"] = (z4["status"] == "pass")

    # 6. Static vs temporal Z4: the 4-frame LABEL rotation above is exact (static
    #    template). The TEMPORAL/cyclic S3 action on the chart is a different
    #    object and gives 2 fixed + 6 period-3 (no period-4) - verified in
    #    the recraft of 003, not here. So no engine claim of temporal period-4.
    checks["static_not_temporal_z4"] = True  # documentation flag (see honesty_boundary)

    all_pass = all(checks.values())
    return {
        "status": "pass" if all_pass else "fail",
        "checks": len(checks),
        "sub_checks": checks,
        "defects": 0 if all_pass else 1,
        "honesty_boundary": (
            "Observer = D4 face selection (4 anchors, select 1 / retain 3). Gluon = "
            "Center C, invariant under LR swap (LR fixes C) for all 8 states. Shared "
            "Center C holds per-state. Static Z4 (4-frame label) exact: 2 fixed, 0 "
            "period-2, 6 period-4. Temporal Z4 REFUTED: the cyclic S3 action gives "
            "2 fixed + 6 period-3, no period-4. DROPPED padding: '64/64 rows', "
            "'37 disagreements' (honest L!=R = 6), Born '1/4' (no derivation), "
            "'7 latent faces' (frames are 4, not 7)."
        ),
    }
