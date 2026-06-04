# Meridian IFA Inducements Consolidation — Pipeline Prototype

A Python pipeline that consolidates three CSV exports (Salesforce CRM
engagements, SAP Concur expense claims, internal adviser registry) into a
single per-adviser MiFID II inducements disclosure CSV with full data-quality
flagging and row-level lineage.

## Quick start

```powershell
# from repo root
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .[dev]

# run pipeline
python -m meridian_inducements --input requirements --output output

# tests
pytest -q
```

Outputs are written to `output/`:

| File | Purpose |
|---|---|
| `inducements_summary.csv` | Required deliverable: one row per adviser. |
| `data_quality_report.csv` | One row per validation flag (orphan refs, mismatches, late claims, etc.). |
| `lineage.csv` | Row-level contributions from source CSVs into each adviser/category figure. |

## Source data assumptions

- Adviser identifiers differ across systems and are canonicalised to
  `ADV-NNN`:
  - Registry: `ADV-001` … `ADV-025`
  - Concur claims: `A-00001` … `A-00025` (zero-padded)
- Salesforce `crm_recorded_total_gbp` is treated as a **cross-check only**, in
  line with the Finance Controller's directive that Concur is the system of
  record for actual payments. Where it disagrees with `agreed_fee + sum(claims)`
  by more than £1, a `CRM_TOTAL_VS_COMPONENTS_MISMATCH` flag is raised.
- `QUARTERLY_SETTLEMENT` claim rows are **excluded from disclosure totals**
  (they don't fit any of the four MiFID II buckets) but surface as a
  `QUARTERLY_SETTLEMENT_PRESENT` flag per adviser so compliance can investigate.
- Only `LINE_ITEM` claims with a resolvable `(adviser_ref, engagement_ref)`
  pair AND a recognised category feed the totals. Unresolved rows never
  silently drop — they appear in `data_quality_report.csv`.

## Categorisation

| Output column | Source |
|---|---|
| `advisory_fees_gbp` | Sum of `engagements.agreed_fee_gbp` over `Completed` engagements |
| `hospitality_gbp` | Claims where `claim_category = HOSPITALITY` |
| `travel_accommodation_gbp` | Claims where `claim_category in (TRAVEL, ACCOMMODATION)` |
| `training_cpd_gbp` | Claims where `claim_category = TRAINING_CPD` |
| `total_disclosed_inducement_gbp` | Sum of the four above |

## Validation flag codes

| Code | Meaning |
|---|---|
| `ADVISER_NOT_IN_REGISTRY` | Claim's `adviser_ref` does not canonicalise to a registered adviser. |
| `ENGAGEMENT_NOT_FOUND` | Claim's `engagement_ref` not in `engagements.csv`. |
| `ADVISER_ENGAGEMENT_MISMATCH` | Claim's adviser disagrees with the engagement's adviser. |
| `CRM_TOTAL_VS_COMPONENTS_MISMATCH` | `crm_recorded_total_gbp` ≠ `agreed_fee + Σclaims` (>£1 tolerance). |
| `CANCELLED_ENGAGEMENT_HAS_CLAIMS` | Claim recorded against a cancelled engagement. |
| `LATE_CLAIM` | `claim_date > engagement_date + 30 days`. |
| `QUARTERLY_SETTLEMENT_PRESENT` | A QS row exists for this adviser; excluded from totals. |
| `DUPLICATE_CLAIM_ID` | Same `claim_id` appears more than once. |
| `NEGATIVE_OR_ZERO_AMOUNT` | Defensive check on `amount_gbp`. |

## Architecture notes (production-readiness discussion)

Implemented for the prototype, but designed with these in mind:

- **Idempotency** — Re-running against unchanged inputs yields byte-identical
  output (deterministic sort by `adviser_id`, stable column order, 2-dp
  rounding). Verified by `test_pipeline_is_idempotent`.
- **Late-arriving data** — In production, replace the static load with an
  incremental load keyed on `claim_id` and a watermark on
  `submission_timestamp`; aggregations are pure, so re-aggregating a single
  affected adviser is cheap. The output schema is naturally re-statable
  (every figure traces to source rows in `lineage.csv`).
- **Schema evolution** — `io_csv.py` declares required columns explicitly; a
  rename or removal in Concur fails fast with a `SchemaError` naming the
  missing column rather than silently producing wrong totals. New columns are
  ignored. This is the single seam to update for upstream schema drift.
- **Data lineage** — `lineage.csv` lists every source row that contributes
  (or was excluded from) each adviser/category figure with `source_file` and
  `source_row_id`. Compliance can challenge any number and trace it back to
  the originating row in CRM or Concur.
- **Scale** — At 35 engagements, in-memory pandas is trivial. At 2,000
  engagements/quarter and 30 countries the same code still runs in seconds;
  beyond that, swap loaders for partitioned reads (e.g. Parquet on object
  storage) and lift transforms into DuckDB or a warehouse (BigQuery /
  Snowflake) — the categorisation rules in `transform.build_outputs` are
  expressible as straightforward SQL window/group-by queries, and the
  validation rules become assertion tests in dbt.

## Layout

```
src/meridian_inducements/
├── config.py        # schemas, category map, thresholds, file names
├── io_csv.py        # typed CSV loaders + schema enforcement
├── normalise.py     # adviser-id canonicalisation
├── validate.py      # data-quality rules → flag dataframe
├── transform.py     # joins, aggregations, lineage
├── pipeline.py      # run(input_dir, output_dir)
├── cli.py           # argparse entry point
└── __main__.py      # `python -m meridian_inducements`
tests/
├── test_normalise.py
├── test_validate.py
├── test_transform.py
└── test_pipeline_integration.py   # E2E against requirements/ fixtures
```

## Decisions explicitly out of scope

- Live Salesforce / Concur API integrations
- FX conversion (all amounts already in GBP)
- Persistent storage / database backend
- UI or report generation beyond CSV
