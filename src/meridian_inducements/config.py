"""Static configuration: schemas, category mappings, thresholds."""

from __future__ import annotations

# Source filenames expected in the input directory.
ADVISERS_FILE = "adviser_registry.csv"
ENGAGEMENTS_FILE = "engagements.csv"
CLAIMS_FILE = "claims.csv"

# Output filenames.
SUMMARY_FILE = "inducements_summary.csv"
DQ_REPORT_FILE = "data_quality_report.csv"
LINEAGE_FILE = "lineage.csv"

# Required columns per source file. Loaders raise if missing.
ADVISER_REQUIRED_COLS = [
    "adviser_id",
    "full_name",
    "specialisation",
    "firm_name",
    "city",
    "country",
    "inducement_disclosure_required",
]
ENGAGEMENT_REQUIRED_COLS = [
    "engagement_id",
    "engagement_date",
    "engagement_type",
    "venue_city",
    "venue_country",
    "adviser_id",
    "adviser_name",
    "role",
    "agreed_fee_gbp",
    "crm_recorded_total_gbp",
    "hospitality_provided",
    "status",
]
CLAIM_REQUIRED_COLS = [
    "claim_id",
    "engagement_ref",
    "adviser_ref",
    "claim_date",
    "claim_category",
    "amount_gbp",
    "row_type",
    "submitted_by",
]

# Map each MiFID II disclosure category to the claim categories that feed it.
DISCLOSURE_CATEGORY_MAP = {
    "hospitality_gbp": ["HOSPITALITY"],
    "travel_accommodation_gbp": ["TRAVEL", "ACCOMMODATION"],
    "training_cpd_gbp": ["TRAINING_CPD"],
}
# Advisory fees come from engagements.agreed_fee_gbp, not from claims.
ADVISORY_FEE_COL = "advisory_fees_gbp"
TOTAL_COL = "total_disclosed_inducement_gbp"

# Categorical claim values that are not MiFID disclosure categories.
NON_DISCLOSURE_CLAIM_CATEGORIES = {"QUARTERLY_SETTLEMENT"}

# Late-claim threshold in days from engagement date.
LATE_CLAIM_DAYS = 30

# Tolerance when comparing CRM-recorded totals to (agreed_fee + claim sum).
CRM_TOTAL_TOLERANCE_GBP = 1.0

# Output column order for the consolidated summary CSV.
SUMMARY_COLUMNS = [
    "adviser_id",
    "full_name",
    "firm_name",
    "country",
    "advisory_fees_gbp",
    "hospitality_gbp",
    "travel_accommodation_gbp",
    "training_cpd_gbp",
    "total_disclosed_inducement_gbp",
    "inducement_disclosure_required",
    "data_quality_flags",
]
