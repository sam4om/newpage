"""Unit tests for validate.validate using small handcrafted frames."""

from __future__ import annotations

import pandas as pd

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
            "inducement_disclosure_required": [True, True],
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
            "crm_recorded_total_gbp": [1250.0, 2200.0],
            "hospitality_provided": [True, True],
            "status": ["Completed", "Completed"],
        }
    )


def test_orphan_engagement_and_unknown_adviser():
    advisers = _advisers()
    engagements = _engagements()
    claims = pd.DataFrame(
        [
            {
                "claim_id": "CLM-1",
                "engagement_ref": "ENG-999",  # orphan
                "adviser_ref": "A-00001",
                "claim_date": pd.Timestamp("2025-01-02"),
                "claim_category": "HOSPITALITY",
                "amount_gbp": 100.0,
                "row_type": "LINE_ITEM",
                "submitted_by": "X",
            },
            {
                "claim_id": "CLM-2",
                "engagement_ref": "ENG-001",
                "adviser_ref": "A-00099",  # unknown adviser
                "claim_date": pd.Timestamp("2025-01-02"),
                "claim_category": "TRAVEL",
                "amount_gbp": 50.0,
                "row_type": "LINE_ITEM",
                "submitted_by": "X",
            },
        ]
    )
    flags = validate(advisers, engagements, claims)
    codes = set(flags["flag_code"])
    assert "ENGAGEMENT_NOT_FOUND" in codes
    assert "ADVISER_NOT_IN_REGISTRY" in codes


def test_adviser_engagement_mismatch_and_late_claim():
    advisers = _advisers()
    engagements = _engagements()
    claims = pd.DataFrame(
        [
            {
                "claim_id": "CLM-1",
                "engagement_ref": "ENG-001",
                "adviser_ref": "A-00002",  # mismatch: ENG-001 belongs to ADV-001
                "claim_date": pd.Timestamp("2025-03-15"),  # >30d after engagement
                "claim_category": "HOSPITALITY",
                "amount_gbp": 100.0,
                "row_type": "LINE_ITEM",
                "submitted_by": "X",
            },
        ]
    )
    flags = validate(advisers, engagements, claims)
    codes = set(flags["flag_code"])
    assert "ADVISER_ENGAGEMENT_MISMATCH" in codes
    assert "LATE_CLAIM" in codes


def test_quarterly_settlement_flagged_not_summed():
    advisers = _advisers()
    engagements = _engagements()
    claims = pd.DataFrame(
        [
            {
                "claim_id": "QS-1",
                "engagement_ref": "QUARTERLY_SETTLEMENT_Q1_2025",
                "adviser_ref": "A-00001",
                "claim_date": pd.Timestamp("2025-04-05"),
                "claim_category": "QUARTERLY_SETTLEMENT",
                "amount_gbp": 600.0,
                "row_type": "QUARTERLY_SETTLEMENT",
                "submitted_by": "Finance Team",
            },
        ]
    )
    flags = validate(advisers, engagements, claims)
    assert "QUARTERLY_SETTLEMENT_PRESENT" in set(flags["flag_code"])


def test_crm_total_mismatch_detected():
    advisers = _advisers()
    engagements = _engagements()
    # Provide claims that don't reconcile with crm_recorded_total.
    claims = pd.DataFrame(
        [
            {
                "claim_id": "CLM-1",
                "engagement_ref": "ENG-001",
                "adviser_ref": "A-00001",
                "claim_date": pd.Timestamp("2025-01-02"),
                "claim_category": "HOSPITALITY",
                "amount_gbp": 50.0,  # 1000 + 50 = 1050 ≠ 1250
                "row_type": "LINE_ITEM",
                "submitted_by": "X",
            }
        ]
    )
    flags = validate(advisers, engagements, claims)
    assert "CRM_TOTAL_VS_COMPONENTS_MISMATCH" in set(flags["flag_code"])


def test_negative_amount_flagged():
    advisers = _advisers()
    engagements = _engagements()
    claims = pd.DataFrame(
        [
            {
                "claim_id": "CLM-1",
                "engagement_ref": "ENG-001",
                "adviser_ref": "A-00001",
                "claim_date": pd.Timestamp("2025-01-02"),
                "claim_category": "HOSPITALITY",
                "amount_gbp": -10.0,
                "row_type": "LINE_ITEM",
                "submitted_by": "X",
            }
        ]
    )
    flags = validate(advisers, engagements, claims)
    assert "NEGATIVE_OR_ZERO_AMOUNT" in set(flags["flag_code"])
