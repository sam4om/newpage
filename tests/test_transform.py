import pandas as pd

from meridian_inducements.transform import build_outputs
from meridian_inducements.validate import validate


def _advisers():
    return pd.DataFrame(
        {
            "adviser_id": ["ADV-001", "ADV-002"],
            "full_name": ["A One", "B Two"],
            "specialisation": ["", ""],
            "firm_name": ["F1", "F2"],
            "city": ["", ""],
            "country": ["GB", "GB"],
            "inducement_disclosure_required": [True, False],
        }
    )


def _engagements():
    return pd.DataFrame(
        {
            "engagement_id": ["ENG-001", "ENG-002"],
            "engagement_date": pd.to_datetime(["2025-01-01", "2025-01-15"]),
            "engagement_type": ["Product Roadshow", "Advisory Panel"],
            "venue_city": ["London", "London"],
            "venue_country": ["GB", "GB"],
            "adviser_id": ["ADV-001", "ADV-002"],
            "adviser_name": ["A One", "B Two"],
            "role": ["Presenter", "Panellist"],
            "agreed_fee_gbp": [1000.0, 2000.0],
            "crm_recorded_total_gbp": [1300.0, 2400.0],
            "hospitality_provided": [True, True],
            "status": ["Completed", "Completed"],
        }
    )


def _claims():
    return pd.DataFrame(
        [
            {
                "claim_id": "C1",
                "engagement_ref": "ENG-001",
                "adviser_ref": "A-00001",
                "claim_date": pd.Timestamp("2025-01-02"),
                "claim_category": "HOSPITALITY",
                "amount_gbp": 100.0,
                "row_type": "LINE_ITEM",
                "submitted_by": "x",
            },
            {
                "claim_id": "C2",
                "engagement_ref": "ENG-001",
                "adviser_ref": "A-00001",
                "claim_date": pd.Timestamp("2025-01-03"),
                "claim_category": "TRAVEL",
                "amount_gbp": 150.0,
                "row_type": "LINE_ITEM",
                "submitted_by": "x",
            },
            {
                "claim_id": "C3",
                "engagement_ref": "ENG-001",
                "adviser_ref": "A-00001",
                "claim_date": pd.Timestamp("2025-01-04"),
                "claim_category": "ACCOMMODATION",
                "amount_gbp": 50.0,
                "row_type": "LINE_ITEM",
                "submitted_by": "x",
            },
            {
                "claim_id": "C4",
                "engagement_ref": "ENG-002",
                "adviser_ref": "A-00002",
                "claim_date": pd.Timestamp("2025-01-16"),
                "claim_category": "TRAINING_CPD",
                "amount_gbp": 400.0,
                "row_type": "LINE_ITEM",
                "submitted_by": "x",
            },
        ]
    )


def test_summary_aggregates_per_adviser():
    advisers, engagements, claims = _advisers(), _engagements(), _claims()
    flags = validate(advisers, engagements, claims)
    summary, lineage = build_outputs(advisers, engagements, claims, flags)

    assert list(summary["adviser_id"]) == ["ADV-001", "ADV-002"]

    a1 = summary.set_index("adviser_id").loc["ADV-001"]
    assert a1["advisory_fees_gbp"] == 1000.0
    assert a1["hospitality_gbp"] == 100.0
    assert a1["travel_accommodation_gbp"] == 200.0
    assert a1["training_cpd_gbp"] == 0.0
    assert a1["total_disclosed_inducement_gbp"] == 1300.0

    a2 = summary.set_index("adviser_id").loc["ADV-002"]
    assert a2["advisory_fees_gbp"] == 2000.0
    assert a2["training_cpd_gbp"] == 400.0
    assert a2["total_disclosed_inducement_gbp"] == 2400.0


def test_unresolved_claim_excluded_from_totals():
    advisers, engagements, claims = _advisers(), _engagements(), _claims()
    # Append a claim with mismatched adviser/engagement; it must NOT be summed.
    bad = pd.DataFrame(
        [
            {
                "claim_id": "C5",
                "engagement_ref": "ENG-001",
                "adviser_ref": "A-00002",  # mismatch
                "claim_date": pd.Timestamp("2025-01-02"),
                "claim_category": "HOSPITALITY",
                "amount_gbp": 999.0,
                "row_type": "LINE_ITEM",
                "submitted_by": "x",
            }
        ]
    )
    claims = pd.concat([claims, bad], ignore_index=True)
    flags = validate(advisers, engagements, claims)
    summary, lineage = build_outputs(advisers, engagements, claims, flags)

    a1 = summary.set_index("adviser_id").loc["ADV-001"]
    assert a1["hospitality_gbp"] == 100.0  # unchanged

    flag_codes = summary.set_index("adviser_id").loc["ADV-002", "data_quality_flags"]
    assert "ADVISER_ENGAGEMENT_MISMATCH" in flag_codes


def test_lineage_marks_excluded_rows():
    advisers, engagements, claims = _advisers(), _engagements(), _claims()
    flags = validate(advisers, engagements, claims)
    _, lineage = build_outputs(advisers, engagements, claims, flags)
    # Each engagement contributes one advisory row, each claim one row.
    assert (lineage["source_file"] == "engagements.csv").sum() == 2
    assert (lineage["source_file"] == "claims.csv").sum() == 4
    assert lineage["included"].all()
