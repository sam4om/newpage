# IFA Inducements Consolidation — Meridian Capital Management EMEA Regulatory Disclosure

## Client context

> Meridian Capital Management is a mid-size UCITS fund manager operating
> across the UK, Germany, France, and Italy. Meridian distributes its
> funds through a network of independent financial advisers (IFAs) and
> wealth management firms — running product roadshows, advisory panels,
> due diligence sessions, and investment conferences throughout the year.
> Each engagement generates a payment or reimbursement to the participating
> adviser that must be disclosed under MiFID II inducements rules and
> equivalent national regulations.
>
> Three separate systems hold pieces of the picture. The **Salesforce CRM**
> logs planned engagements and records agreed advisory fees. The **SAP
> Concur expense system** captures actual reimbursement claims submitted
> by distribution managers after each engagement. An internal **adviser
> master registry** holds validated adviser identity and firm affiliation
> data.
>
> Nobody has joined these three systems together. Every quarter, a
> compliance analyst reconciles them manually in a spreadsheet — a process
> that takes two weeks and produces a finding at every external audit.
>
> The **Head of Distribution Compliance** is frustrated: "I need one
> defensible number per adviser. Last quarter we had six advisers where
> the CRM said one amount and the expense claims said another. I cannot
> submit an inducements report I cannot reconcile — the FCA will come
> back to us."
>
> The **Finance Controller** pushed back: "Concur is the system of record
> for actual payments. Salesforce has planned spend. I've been burned
> before by people using the planned figure in reporting. The number has
> to come from actual expense claims."
>
> The **Head of Distribution** added: "My distribution managers submit
> expenses weeks after an engagement — especially when there's a hotel
> involved. Whatever you build needs to handle late submissions without
> re-running everything from scratch."
>
> The **CTO** sent a note: "We have CSV exports from all three systems
> for the current reporting period. Use those for the prototype — don't
> worry about a live integration. But I'd love to hear how you'd architect
> this properly for quarterly production use."

---

## The ask

Build a data pipeline prototype that consolidates the three CSV exports
into a single adviser-level inducements summary ready for MiFID II
regulatory disclosure. The pipeline should load the source data, validate
it, resolve the joins between systems, compute the correct aggregated
spend per adviser per disclosure category, and flag any records it cannot
confidently resolve.

Three files are provided alongside this document:

| File | Source system | Contents |
|---|---|---|
| `adviser_registry.csv` | Internal adviser master data | One row per registered adviser |
| `engagements.csv` | Salesforce CRM export | One row per distribution engagement |
| `claims.csv` | SAP Concur export | One row per expense claim or payment |

---

## Source schemas

### `adviser_registry.csv`

| Column | Description |
|---|---|
| `adviser_id` | Unique adviser identifier (e.g. `ADV-001`) |
| `full_name` | Adviser full name |
| `specialisation` | Financial planning specialisation |
| `firm_name` | Affiliated IFA firm or wealth management practice |
| `city` | City |
| `country` | ISO country code |
| `inducement_disclosure_required` | Whether this adviser requires regulatory disclosure (TRUE/FALSE) |

### `engagements.csv`

| Column | Description |
|---|---|
| `engagement_id` | Unique engagement identifier (e.g. `ENG-001`) |
| `engagement_date` | Date of the engagement |
| `engagement_type` | Product Roadshow, Advisory Panel, Due Diligence Session, or Investment Conference |
| `venue_city` | City where the engagement took place |
| `venue_country` | ISO country code |
| `adviser_id` | Adviser identifier — references `adviser_registry.adviser_id` |
| `adviser_name` | Adviser name as recorded in Salesforce at time of engagement |
| `role` | Adviser role at the engagement (Presenter, Panellist, Reviewer, Chair) |
| `agreed_fee_gbp` | Agreed advisory or speaking fee in GBP |
| `crm_recorded_total_gbp` | Total inducement value as recorded in Salesforce at engagement close (GBP) |
| `hospitality_provided` | Whether hospitality was provided (TRUE/FALSE) |
| `status` | Engagement status (Completed, Cancelled) |

### `claims.csv`

| Column | Description |
|---|---|
| `claim_id` | Unique claim identifier |
| `engagement_ref` | Reference to the associated engagement |
| `adviser_ref` | Adviser identifier as used in Concur (format: `A-XXXXX`) |
| `claim_date` | Date the expense was incurred |
| `claim_category` | HOSPITALITY, TRAVEL, ACCOMMODATION, TRAINING_CPD, or QUARTERLY_SETTLEMENT |
| `amount_gbp` | Claim amount in GBP |
| `row_type` | LINE_ITEM or QUARTERLY_SETTLEMENT |
| `submitted_by` | Distribution manager who submitted the claim |

---

## MiFID II inducements disclosure categories

Under MiFID II (Article 24), all inducements paid to or received from
third parties in connection with investment services must be disclosed to
clients. The required output must categorise inducements into the
following buckets:

| Category | What it covers |
|---|---|
| Advisory & speaking fees | Fees paid for advisory panels, roadshow presentations, due diligence reviews |
| Hospitality & entertainment | Meals, refreshments, hospitality at engagements |
| Travel & accommodation | Travel reimbursements, hotel costs |
| Training & CPD | Conference registrations, continuing professional development costs |

---

## Required output

The pipeline should produce a single consolidated CSV with one row per
adviser, containing:

| Column | Description |
|---|---|
| `adviser_id` | Resolved adviser identifier |
| `full_name` | From registry |
| `firm_name` | From registry |
| `country` | From registry |
| `advisory_fees_gbp` | Sum of agreed fees across all engagements |
| `hospitality_gbp` | Sum of HOSPITALITY claims |
| `travel_accommodation_gbp` | Sum of TRAVEL + ACCOMMODATION claims |
| `training_cpd_gbp` | Sum of TRAINING_CPD claims |
| `total_disclosed_inducement_gbp` | Sum of all categories |
| `inducement_disclosure_required` | From registry |
| `data_quality_flags` | Any issues found (pipe-separated list, or blank) |

---

## Constraints and notes

- Use whatever language or tooling you are most productive with (Python,
  SQL, dbt, Pandas — all acceptable)
- The CSVs represent real exports from production systems — **they are
  not clean**
- A pipeline that produces a correct, well-documented output for 80% of
  records with clear flags on the remaining 20% is better than one that
  silently produces wrong totals for 100%
- The expected deliverable is a working pipeline script and the output
  CSV — not a front-end

---

## What "done" looks like is up to you

There is no prescribed output format beyond the schema above. Part of the
assessment is your judgment about what to handle first and what to defer.

---

## Architectural considerations

The prototype is a script against static files, but you should be prepared
to discuss:

- **Idempotency** — if the pipeline runs twice against the same source
  data, does the output change? How would you guarantee it does not?
- **Late-arriving data** — distribution managers submit expenses weeks
  after engagements. How would you design an incremental load that handles
  late submissions without reprocessing everything?
- **Schema evolution** — if Concur adds a column or renames one, what
  breaks and what does not? How would you isolate the pipeline from
  upstream schema changes?
- **Data lineage** — if the compliance team challenges a specific
  adviser's total, can you trace every pound in the output back to its
  source row? What would the data model need to support this?
- **Scale** — 35 engagements today. If Meridian runs 2,000 engagements
  per quarter across 30 countries, what changes architecturally?

> You are not expected to implement these — but your pipeline design
> should reflect awareness of them, and you should be ready to discuss
> them.

---

## Business goals

- **Reporting accuracy** — eliminate the reconciliation gap between
  Salesforce and Concur that generates a finding at every audit
- **Timeliness** — produce the quarterly inducements report in hours,
  not two weeks
- **Auditability** — every figure in the output should be traceable to a
  source row; no black-box aggregations
- **Completeness** — flag any adviser engagement that cannot be fully
  resolved, rather than silently dropping or under-reporting it

---

## Regulatory reference

> This section provides context. No prior knowledge of MiFID II or
> financial services inducements reporting is expected.

### MiFID II Inducements Rules

The Markets in Financial Instruments Directive II (MiFID II) requires
investment firms to disclose all inducements — monetary and non-monetary
benefits — paid to or received from third parties in connection with
the provision of investment services. This includes advisory fees,
hospitality, travel, accommodation, and training or CPD contributions.

Firms must disclose inducements at the individual adviser level and
demonstrate that each payment is designed to enhance the quality of the
service provided to the end client. Reports are submitted to national
regulators (FCA in the UK, BaFin in Germany, AMF in France, CONSOB in
Italy) and must be available for audit upon request.

The core principle is **completeness**: every transfer of value above a
de minimis threshold must appear in the report. An undisclosed payment —
even an accidental omission — is a compliance breach that can result in
regulatory sanction and reputational damage. Similarly, a double-counted
or inflated figure damages credibility with regulators and adviser
networks alike.

A compliant pipeline must therefore handle three failure modes with equal
care: missing records, duplicated records, and incorrect amounts.
