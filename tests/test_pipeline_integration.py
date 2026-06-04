"""End-to-end test against the real ``requirements/`` fixtures."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from meridian_inducements import pipeline


REPO_ROOT = Path(__file__).resolve().parents[1]
INPUT_DIR = REPO_ROOT / "requirements"


def test_pipeline_against_requirements_fixtures(tmp_path: Path):
    out = tmp_path / "out"
    paths = pipeline.run(INPUT_DIR, out)

    summary = pd.read_csv(paths["summary"])
    dq = pd.read_csv(paths["data_quality"])

    # Registry has 25 advisers; summary spine should match exactly.
    assert len(summary) == 25
    assert summary["adviser_id"].is_monotonic_increasing

    # ADV-001 spot check: ENG-001 + ENG-026 = £3000 advisory; £500 hospitality;
    # £700 travel+accommodation across CLM-001/002/058/059.
    a1 = summary.set_index("adviser_id").loc["ADV-001"]
    assert a1["advisory_fees_gbp"] == 3000.0
    assert a1["hospitality_gbp"] == 500.0
    assert a1["travel_accommodation_gbp"] == 700.0
    assert a1["training_cpd_gbp"] == 0.0
    assert a1["total_disclosed_inducement_gbp"] == 4200.0

    # Orphan engagements ENG-036/037/038 should appear as ENGAGEMENT_NOT_FOUND.
    orphans = set(
        dq[dq["flag_code"] == "ENGAGEMENT_NOT_FOUND"]["engagement_id"].dropna()
    )
    assert {"ENG-036", "ENG-037", "ENG-038"}.issubset(orphans)

    # Unknown advisers A-00026/27/28 should produce ADVISER_NOT_IN_REGISTRY.
    assert (dq["flag_code"] == "ADVISER_NOT_IN_REGISTRY").any()

    # The three rigged mismatches sit on advisers ADV-015, ADV-022, ADV-005.
    mism = dq[dq["flag_code"] == "ADVISER_ENGAGEMENT_MISMATCH"]
    # claim references map to adv ADV-026/27/28 (unknown), so adviser_id is the
    # canonical of the claim's adviser_ref; mismatch detail mentions engagement.
    assert not mism.empty


def test_pipeline_is_idempotent(tmp_path: Path):
    out_a = tmp_path / "a"
    out_b = tmp_path / "b"
    pipeline.run(INPUT_DIR, out_a)
    pipeline.run(INPUT_DIR, out_b)
    for name in ("inducements_summary.csv", "data_quality_report.csv", "lineage.csv"):
        assert (out_a / name).read_bytes() == (out_b / name).read_bytes()
