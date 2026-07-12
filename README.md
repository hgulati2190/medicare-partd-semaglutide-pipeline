# Medicare Part D Semaglutide Prescribing & Cost Pipeline

An end-to-end data pipeline analyzing national Medicare Part D prescribing
patterns and drug costs for **Semaglutide** (sold as Ozempic, Wegovy, and
Rybelsus) — built on Google Cloud Platform using CMS's public prescriber
data.

**[View the live dashboard →](https://datastudio.google.com/s/uAX4pzQhavQ)**

---

## Why this project

Medicare spends billions of dollars annually on GLP-1 medications like
Ozempic and Wegovy, and that spend has grown rapidly in recent years. This
project explores that trend using CMS's public Medicare Part D Prescribers
by Provider and Drug dataset — tracking prescription volume, total cost,
and which types of providers are driving that volume, nationwide.

It's built as a portfolio project to demonstrate practical, healthcare-domain
data engineering on GCP: pulling real data from a public API, handling
domain-specific data quality issues (see [Limitations](#limitations-and-honest-framing)
below), and moving it through a cloud pipeline into a usable dashboard.

## Architecture

```
CMS Public API (data.cms.gov)
        │  filtered extraction (Gnrc_Name = "Semaglutide")
        ▼
Python (pandas) — clean, standardize, flag suppressed records
        │  Parquet file
        ▼
Google Cloud Storage (raw file storage)
        │  BigQuery native load
        ▼
BigQuery (partd_raw.semaglutide_prescribers)
        │  SQL aggregation
        ▼
Looker Studio Dashboard
```

## Dataset

- **Source**: [CMS Medicare Part D Prescribers by Provider and Drug](https://data.cms.gov/provider-summary-by-type-of-service/medicare-part-d-prescribers/medicare-part-d-prescribers-by-provider-and-drug)
- **Slice used**: All records where `Gnrc_Name = "Semaglutide"` — **210,621 rows**
  nationwide, covering all three brand formulations (Ozempic, Wegovy, Rybelsus)
- **Grain**: one row per prescriber (NPI) per drug per year
- **Why this slice**: Semaglutide/GLP-1 drugs are one of the most
  discussed drug categories in healthcare today (cost, access, off-label use),
  making this a timely and explainable dataset choice. The slice size
  (~210K rows) was chosen after comparing several candidate filters
  (drug, specialty, state) for a size that's substantial enough to be a
  real dataset, while staying fast to process end-to-end.

## Pipeline

| Stage | What happens |
|---|---|
| **Extract & Clean** | Paginated pull from CMS's public API, filtered server-side to Semaglutide records only. Numeric fields cast properly, text standardized, duplicates dropped, CMS's privacy-suppressed values explicitly flagged (`is_suppressed`) rather than treated as zero. |
| **Load** | Cleaned Parquet file uploaded to Google Cloud Storage, then loaded directly into BigQuery with automatic schema detection. |
| **Validate** | Row counts and aggregate sums cross-checked between the local extraction and the loaded BigQuery table to confirm zero data loss. |
| **Visualize** | Looker Studio dashboard connected live to BigQuery, with charts covering cost by state, claims by prescriber type, and the brand-name split. |

## Key findings

- **~10.9M total claims** and **$13.8B in total drug cost** across all
  Semaglutide prescribing nationwide in the dataset period.
- **Texas and California** lead in total drug cost by state, followed
  closely by New York and Florida.
- **Family Practice physicians prescribe the most Semaglutide by claim
  volume** — ahead of Internal Medicine, Nurse Practitioners, and even
  Endocrinology, despite Semaglutide's strong association with
  specialist-driven diabetes/weight-management care.
- **Ozempic accounts for ~91% of claims**, with Rybelsus (~8%) and
  Wegovy making up the remainder.

## Limitations and honest framing

This project is a **credibility signal, not a production system**. To be
direct about its scope:

- No orchestration — this is a manually-run, one-time pipeline, not a
  scheduled job (no Airflow/Cloud Composer).
- No incremental loading — each run replaces the full table
  (`WRITE_TRUNCATE`), not designed for append-only updates.
- No CI/CD, no automated testing.
- The dataset is aggregated and public — no PII, no real-time constraints,
  no access-control complexity.

## Tech stack

- **Python** (pandas, requests, pyarrow) — extraction and cleaning
- **Google Cloud Storage** — raw file storage
- **BigQuery** — warehouse and SQL aggregation
- **Looker Studio** — dashboard/visualization
- **CMS Public API** (data.cms.gov) — data source

## Running this yourself

```bash
pip install -r requirements.txt

# 1. Extract and clean
python scripts/day1_extract_clean.py

# 2. Upload, load, and validate
python scripts/day2_upload_load_validate.py
```

Requires a GCP project with billing enabled, a GCS bucket, a BigQuery
dataset, and a service account key with Storage Object Admin +
BigQuery Data Editor + BigQuery Job User roles. See
[`docs/01_gcp_setup.md`](docs/01_gcp_setup.md) for setup steps, and
[`sql/explore_bigquery_queries.sql`](sql/explore_bigquery_queries.sql)
for the exploratory queries used to shape the dashboard.

---

*Built as part of a job search portfolio focused on Senior Data Engineer
roles in healthcare/pharmacy data.*
