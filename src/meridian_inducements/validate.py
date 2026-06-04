"""Data-quality validation rules.

All checks return rows for a single long-format flag DataFrame with columns:
    adviser_id, engagement_id, claim_id, flag_code, detail
Any field not applicable to a given check is left as ``pd.NA``.
"""

from __future__ import annotations

import pandas as pd

from . import config
from .normalise import to_canonical_adviser_id


FLAG_COLUMNS = ["adviser_id", "engagement_id", "claim_id", "flag_code", "detail"]


def _empty_flags() -> pd.DataFrame:
    return pd.DataFrame(columns=FLAG_COLUMNS)


def _flag(adviser_id, engagement_id, claim_id, code, detail) -> dict:
    return {
        "adviser_id": adviser_id if adviser_id is not None else pd.NA,
        "engagement_id": engagement_id if engagement_id is not None else pd.NA,
        "claim_id": claim_id if claim_id is not None else pd.NA,
        "flag_code": code,
        "detail": detail,
    }


def validate(
    advisers: pd.DataFrame,
    engagements: pd.DataFrame,
    claims: pd.DataFrame,
) -> pd.DataFrame:
    """Run all validation checks and return a flag dataframe."""
    rows: list[dict] = []

    registry_ids = set(advisers["adviser_id"].dropna().astype(str))
    eng_index = engagements.set_index("engagement_id", drop=False)
    eng_canonical = engagements["adviser_id"].map(to_canonical_adviser_id)
    eng_canonical_by_id = dict(zip(engagements["engagement_id"], eng_canonical))

    # --- Claim-level checks ---
    seen_claim_ids: dict[str, int] = {}
    for row in claims.itertuples(index=False):
        cid = getattr(row, "claim_id")
        eng_ref = getattr(row, "engagement_ref")
        adv_ref = getattr(row, "adviser_ref")
        amount = getattr(row, "amount_gbp")
        category = getattr(row, "claim_category")
        row_type = getattr(row, "row_type")
        claim_date = getattr(row, "claim_date")

        canonical_adv = to_canonical_adviser_id(adv_ref)

        # Duplicate claim ids.
        seen_claim_ids[cid] = seen_claim_ids.get(cid, 0) + 1

        # Quarterly settlement rows: surface and skip the rest.
        if row_type == "QUARTERLY_SETTLEMENT" or category == "QUARTERLY_SETTLEMENT":
            rows.append(
                _flag(
                    canonical_adv,
                    None,
                    cid,
                    "QUARTERLY_SETTLEMENT_PRESENT",
                    f"Quarterly settlement of {amount} for {adv_ref}; excluded from totals",
                )
            )
            if canonical_adv is None or canonical_adv not in registry_ids:
                rows.append(
                    _flag(
                        None,
                        None,
                        cid,
                        "ADVISER_NOT_IN_REGISTRY",
                        f"Quarterly settlement adviser_ref {adv_ref!r} not in registry",
                    )
                )
            continue

        # Negative or zero amounts.
        if pd.isna(amount) or amount <= 0:
            rows.append(
                _flag(
                    canonical_adv,
                    eng_ref,
                    cid,
                    "NEGATIVE_OR_ZERO_AMOUNT",
                    f"amount_gbp={amount!r}",
                )
            )

        # Adviser ref → registry.
        if canonical_adv is None or canonical_adv not in registry_ids:
            rows.append(
                _flag(
                    None,
                    eng_ref,
                    cid,
                    "ADVISER_NOT_IN_REGISTRY",
                    f"Claim adviser_ref {adv_ref!r} does not map to any registry adviser",
                )
            )

        # Engagement ref → engagements.
        if eng_ref not in eng_index.index:
            rows.append(
                _flag(
                    canonical_adv,
                    eng_ref,
                    cid,
                    "ENGAGEMENT_NOT_FOUND",
                    f"engagement_ref {eng_ref!r} not present in engagements.csv",
                )
            )
        else:
            # Adviser-vs-engagement consistency.
            eng_adv = eng_canonical_by_id.get(eng_ref)
            if (
                canonical_adv is not None
                and eng_adv is not None
                and canonical_adv != eng_adv
            ):
                rows.append(
                    _flag(
                        canonical_adv,
                        eng_ref,
                        cid,
                        "ADVISER_ENGAGEMENT_MISMATCH",
                        f"claim adviser={canonical_adv} but engagement.adviser={eng_adv}",
                    )
                )

            # Cancelled engagement with claims.
            eng_row = eng_index.loc[eng_ref]
            status = eng_row["status"] if not isinstance(eng_row, pd.DataFrame) else eng_row["status"].iloc[0]
            eng_date = eng_row["engagement_date"] if not isinstance(eng_row, pd.DataFrame) else eng_row["engagement_date"].iloc[0]
            if isinstance(status, str) and status.lower() == "cancelled":
                rows.append(
                    _flag(
                        canonical_adv,
                        eng_ref,
                        cid,
                        "CANCELLED_ENGAGEMENT_HAS_CLAIMS",
                        f"Engagement {eng_ref} is Cancelled but has claim {cid}",
                    )
                )

            # Late claim.
            if (
                pd.notna(claim_date)
                and pd.notna(eng_date)
                and (claim_date - eng_date).days > config.LATE_CLAIM_DAYS
            ):
                rows.append(
                    _flag(
                        canonical_adv,
                        eng_ref,
                        cid,
                        "LATE_CLAIM",
                        f"Claim submitted {(claim_date - eng_date).days} days after engagement",
                    )
                )

    # Duplicate claim ids reported once per duplicate id.
    for cid, count in seen_claim_ids.items():
        if count > 1:
            rows.append(
                _flag(None, None, cid, "DUPLICATE_CLAIM_ID", f"claim_id appears {count} times")
            )

    # --- Engagement-level: CRM total vs components ---
    # Group claims by engagement_ref (line items only, valid amounts).
    line_items = claims[
        (claims["row_type"] == "LINE_ITEM")
        & (claims["amount_gbp"].notna())
        & (claims["amount_gbp"] > 0)
    ]
    claim_sum_by_eng = line_items.groupby("engagement_ref")["amount_gbp"].sum().to_dict()

    for row in engagements.itertuples(index=False):
        eng_id = getattr(row, "engagement_id")
        agreed = getattr(row, "agreed_fee_gbp")
        crm_total = getattr(row, "crm_recorded_total_gbp")
        adv_id = getattr(row, "adviser_id")
        if pd.isna(crm_total) or pd.isna(agreed):
            continue
        components = (agreed or 0.0) + claim_sum_by_eng.get(eng_id, 0.0)
        if abs(crm_total - components) > config.CRM_TOTAL_TOLERANCE_GBP:
            rows.append(
                _flag(
                    to_canonical_adviser_id(adv_id),
                    eng_id,
                    None,
                    "CRM_TOTAL_VS_COMPONENTS_MISMATCH",
                    f"crm_recorded_total={crm_total} vs agreed+claims={components:.2f}",
                )
            )

    if not rows:
        return _empty_flags()
    return pd.DataFrame(rows, columns=FLAG_COLUMNS)
