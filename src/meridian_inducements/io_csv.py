"""Typed CSV loaders with schema declaration.

Each loader:
- Validates that required columns are present (schema-drift seam).
- Coerces types (dates, numerics, booleans).
- Trims string columns.
- Returns a DataFrame; coercion errors surface as NaN/NaT and are caught by
  downstream validation.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from . import config


class SchemaError(ValueError):
    """Raised when a source CSV is missing required columns."""


def _check_required(df: pd.DataFrame, required: list[str], source: str) -> None:
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise SchemaError(f"{source}: missing required columns {missing}")


def _strip_strings(df: pd.DataFrame) -> pd.DataFrame:
    for col in df.select_dtypes(include="object").columns:
        df[col] = df[col].astype("string").str.strip()
    return df


def _to_bool(series: pd.Series) -> pd.Series:
    truthy = {"true", "t", "yes", "y", "1"}
    falsy = {"false", "f", "no", "n", "0"}

    def coerce(v: object) -> bool | None:
        if v is None:
            return None
        s = str(v).strip().lower()
        if s in truthy:
            return True
        if s in falsy:
            return False
        return None

    return series.map(coerce).astype("boolean")


def load_advisers(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, dtype=str)
    _check_required(df, config.ADVISER_REQUIRED_COLS, "adviser_registry.csv")
    df = _strip_strings(df)
    df["inducement_disclosure_required"] = _to_bool(df["inducement_disclosure_required"])
    return df


def load_engagements(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, dtype=str)
    _check_required(df, config.ENGAGEMENT_REQUIRED_COLS, "engagements.csv")
    df = _strip_strings(df)
    df["engagement_date"] = pd.to_datetime(df["engagement_date"], errors="coerce")
    df["agreed_fee_gbp"] = pd.to_numeric(df["agreed_fee_gbp"], errors="coerce")
    df["crm_recorded_total_gbp"] = pd.to_numeric(df["crm_recorded_total_gbp"], errors="coerce")
    df["hospitality_provided"] = _to_bool(df["hospitality_provided"])
    return df


def load_claims(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, dtype=str)
    _check_required(df, config.CLAIM_REQUIRED_COLS, "claims.csv")
    df = _strip_strings(df)
    df["claim_date"] = pd.to_datetime(df["claim_date"], errors="coerce")
    df["amount_gbp"] = pd.to_numeric(df["amount_gbp"], errors="coerce")
    df["claim_category"] = df["claim_category"].str.upper()
    df["row_type"] = df["row_type"].str.upper()
    return df
