"""Pipeline orchestration."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from . import config, io_csv, transform, validate


def run(input_dir: Path, output_dir: Path) -> dict[str, Path]:
    """Run the full pipeline and write the three output CSVs.

    Returns a dict of {logical_name: written_path}.
    """
    input_dir = Path(input_dir)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    advisers = io_csv.load_advisers(input_dir / config.ADVISERS_FILE)
    engagements = io_csv.load_engagements(input_dir / config.ENGAGEMENTS_FILE)
    claims = io_csv.load_claims(input_dir / config.CLAIMS_FILE)

    flags = validate.validate(advisers, engagements, claims)
    summary, lineage = transform.build_outputs(advisers, engagements, claims, flags)

    summary_path = output_dir / config.SUMMARY_FILE
    dq_path = output_dir / config.DQ_REPORT_FILE
    lineage_path = output_dir / config.LINEAGE_FILE

    summary.to_csv(summary_path, index=False)

    if flags.empty:
        pd.DataFrame(columns=validate.FLAG_COLUMNS).to_csv(dq_path, index=False)
    else:
        flags_sorted = flags.sort_values(
            ["adviser_id", "engagement_id", "claim_id", "flag_code"],
            na_position="last",
        ).reset_index(drop=True)
        flags_sorted.to_csv(dq_path, index=False)

    lineage.to_csv(lineage_path, index=False)

    return {"summary": summary_path, "data_quality": dq_path, "lineage": lineage_path}
