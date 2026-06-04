"""Joins, aggregations, and lineage construction."""

from __future__ import annotations

import pandas as pd

from . import config
from .normalise import to_canonical_adviser_id


def _category_to_output_col(category: str) -> str | None:
    for out_col, cats in config.DISCLOSURE_CATEGORY_MAP.items():
        if category in cats:
            return out_col
    return None


def build_outputs(
    advisers: pd.DataFrame,
    engagements: pd.DataFrame,
    claims: pd.DataFrame,
    flags: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return (summary_df, lineage_df).

    Only resolved rows feed the summary numbers:
      - engagements with status == 'Completed' and a known canonical adviser
        contribute to advisory_fees_gbp.
      - line-item claims whose adviser_ref AND engagement_ref both resolve
        consistently contribute to category totals. Mismatched/orphan rows are
        excluded (they are surfaced via the data-quality report).
    """
    registry_ids = set(advisers["adviser_id"].astype(str))

    # ---- Advisory fees from engagements ----
    eng = engagements.copy()
    eng["adviser_canonical"] = eng["adviser_id"].map(to_canonical_adviser_id)
    eng_completed = eng[
        (eng["status"].str.lower() == "completed")
        & (eng["adviser_canonical"].isin(registry_ids))
        & (eng["agreed_fee_gbp"].notna())
    ]

    advisory_lineage = pd.DataFrame(
        {
            "adviser_id": eng_completed["adviser_canonical"],
            "category": config.ADVISORY_FEE_COL,
            "source_file": config.ENGAGEMENTS_FILE,
            "source_row_id": eng_completed["engagement_id"],
            "amount_gbp": eng_completed["agreed_fee_gbp"].astype(float),
            "included": True,
        }
    )

    advisory_by_adv = (
        eng_completed.groupby("adviser_canonical")["agreed_fee_gbp"]
        .sum()
        .rename(config.ADVISORY_FEE_COL)
    )

    # ---- Claim-derived categories ----
    cl = claims.copy()
    cl["adviser_canonical"] = cl["adviser_ref"].map(to_canonical_adviser_id)
    cl["output_col"] = cl["claim_category"].map(_category_to_output_col)

    eng_canonical_lookup = dict(zip(eng["engagement_id"], eng["adviser_canonical"]))
    cl["engagement_adviser"] = cl["engagement_ref"].map(eng_canonical_lookup)

    resolved_mask = (
        (cl["row_type"] == "LINE_ITEM")
        & cl["adviser_canonical"].isin(registry_ids)
        & cl["engagement_ref"].isin(eng["engagement_id"])
        & (cl["adviser_canonical"] == cl["engagement_adviser"])
        & cl["output_col"].notna()
        & cl["amount_gbp"].notna()
        & (cl["amount_gbp"] > 0)
    )
    cl_resolved = cl[resolved_mask]

    claim_lineage = pd.DataFrame(
        {
            "adviser_id": cl["adviser_canonical"],
            "category": cl["output_col"].fillna("UNCATEGORISED"),
            "source_file": config.CLAIMS_FILE,
            "source_row_id": cl["claim_id"],
            "amount_gbp": cl["amount_gbp"].astype(float),
            "included": resolved_mask,
        }
    )

    if cl_resolved.empty:
        category_pivot = pd.DataFrame(
            columns=list(config.DISCLOSURE_CATEGORY_MAP.keys())
        )
    else:
        category_pivot = (
            cl_resolved.groupby(["adviser_canonical", "output_col"])["amount_gbp"]
            .sum()
            .unstack(fill_value=0.0)
        )

    # ---- Per-adviser flag aggregation ----
    if flags.empty:
        flags_per_adv: dict[str, str] = {}
    else:
        flags_with_adv = flags[flags["adviser_id"].notna()]
        flags_per_adv = (
            flags_with_adv.groupby("adviser_id")["flag_code"]
            .apply(lambda s: "|".join(sorted(set(s))))
            .to_dict()
        )

    # ---- Build summary on the registry spine ----
    summary = advisers[
        ["adviser_id", "full_name", "firm_name", "country", "inducement_disclosure_required"]
    ].copy()

    summary[config.ADVISORY_FEE_COL] = (
        summary["adviser_id"].map(advisory_by_adv).fillna(0.0)
    )
    for out_col in config.DISCLOSURE_CATEGORY_MAP:
        if out_col in category_pivot.columns:
            summary[out_col] = (
                summary["adviser_id"].map(category_pivot[out_col]).fillna(0.0)
            )
        else:
            summary[out_col] = 0.0

    money_cols = [config.ADVISORY_FEE_COL, *config.DISCLOSURE_CATEGORY_MAP.keys()]
    summary[money_cols] = summary[money_cols].round(2)
    summary[config.TOTAL_COL] = summary[money_cols].sum(axis=1).round(2)

    summary["data_quality_flags"] = (
        summary["adviser_id"].map(flags_per_adv).fillna("")
    )

    summary = summary[config.SUMMARY_COLUMNS].sort_values("adviser_id").reset_index(drop=True)

    # ---- Lineage ----
    lineage = pd.concat([advisory_lineage, claim_lineage], ignore_index=True)
    lineage["amount_gbp"] = lineage["amount_gbp"].round(2)
    lineage = lineage.sort_values(
        ["adviser_id", "category", "source_file", "source_row_id"],
        na_position="last",
    ).reset_index(drop=True)

    return summary, lineage
