"""
Day 2: Upload the Day 1 cleaned Parquet file to GCS, load it into
BigQuery, and run validation queries to confirm everything landed
correctly.

SETUP:
    pip install google-cloud-storage google-cloud-bigquery pandas pyarrow

BEFORE RUNNING:
    1. Make sure Day 1 has been run and
       data/clean/partd_semaglutide_clean.parquet exists next to this script.
    2. Fill in PROJECT_ID, BUCKET_NAME, and SERVICE_ACCOUNT_KEY_PATH below
       to match what you created in the GCP setup step.
    3. Confirm the BigQuery dataset (partd_raw) already exists -- it was
       created in the GCP setup script. This script creates the TABLE
       inside it, not the dataset.
"""

import logging
from pathlib import Path

from google.cloud import bigquery, storage

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# CONFIG -- edit these to match your GCP setup
# ---------------------------------------------------------------------------
PROJECT_ID = "medicare-part-d-pipeline"
BUCKET_NAME = "part-d-pipeline-473821-data"
SERVICE_ACCOUNT_KEY_PATH = r"C:\Users\hem11\OneDrive\Desktop\Goals and Aspirition\DataEngineer\CMS\CMS_Data\Key\medicare-part-d-pipeline-8f8f4989a033.json"

BQ_DATASET = "partd_raw"
BQ_TABLE = "semaglutide_prescribers"

SCRIPT_DIR = Path(__file__).resolve().parent
CLEAN_PARQUET_PATH = SCRIPT_DIR / "data" / "clean" / "partd_semaglutide_clean.parquet"
GCS_BLOB_NAME = "clean/partd_semaglutide_clean.parquet"

EXPECTED_ROW_COUNT = 210_621  # from Day 1 -- used as a sanity check, not a hard assertion


# ---------------------------------------------------------------------------
# STEP 1: UPLOAD TO GCS
# ---------------------------------------------------------------------------
def upload_to_gcs(storage_client: storage.Client) -> str:
    if not CLEAN_PARQUET_PATH.exists():
        raise FileNotFoundError(
            f"Cleaned Parquet not found at {CLEAN_PARQUET_PATH}. Run Day 1's "
            "day1_extract_clean.py first."
        )

    bucket = storage_client.bucket(BUCKET_NAME)
    blob = bucket.blob(GCS_BLOB_NAME)

    log.info("Uploading %s -> gs://%s/%s", CLEAN_PARQUET_PATH, BUCKET_NAME, GCS_BLOB_NAME)
    blob.upload_from_filename(str(CLEAN_PARQUET_PATH))

    gcs_uri = f"gs://{BUCKET_NAME}/{GCS_BLOB_NAME}"
    log.info("Upload complete: %s", gcs_uri)
    return gcs_uri


# ---------------------------------------------------------------------------
# STEP 2: LOAD INTO BIGQUERY
# ---------------------------------------------------------------------------
def load_to_bigquery(bq_client: bigquery.Client, gcs_uri: str) -> str:
    table_ref = f"{PROJECT_ID}.{BQ_DATASET}.{BQ_TABLE}"

    job_config = bigquery.LoadJobConfig(
        source_format=bigquery.SourceFormat.PARQUET,
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,  # overwrite on re-run
        autodetect=True,  # infer schema from Parquet's own column types
    )

    log.info("Loading %s -> %s", gcs_uri, table_ref)
    load_job = bq_client.load_table_from_uri(gcs_uri, table_ref, job_config=job_config)
    load_job.result()  # blocks until the job finishes

    table = bq_client.get_table(table_ref)
    log.info("Load complete: %s rows, %s columns", table.num_rows, len(table.schema))
    return table_ref


# ---------------------------------------------------------------------------
# STEP 3: VALIDATE
# ---------------------------------------------------------------------------
def run_validation_queries(bq_client: bigquery.Client, table_ref: str) -> None:
    queries = {
        "row_count": f"SELECT COUNT(*) AS row_count FROM `{table_ref}`",
        "suppressed_pct": f"""
            SELECT
              ROUND(100 * COUNTIF(is_suppressed) / COUNT(*), 2) AS pct_suppressed
            FROM `{table_ref}`
        """,
        "total_cost_and_claims": f"""
            SELECT
              ROUND(SUM(Tot_Drug_Cst), 2) AS total_drug_cost,
              SUM(Tot_Clms) AS total_claims
            FROM `{table_ref}`
            WHERE NOT is_suppressed
        """,
        "top_5_prescriber_states_by_cost": f"""
            SELECT
              Prscrbr_State_Abrvtn,
              ROUND(SUM(Tot_Drug_Cst), 2) AS total_cost,
              COUNT(*) AS num_records
            FROM `{table_ref}`
            WHERE NOT is_suppressed
            GROUP BY Prscrbr_State_Abrvtn
            ORDER BY total_cost DESC
            LIMIT 5
        """,
        "top_5_prescriber_types_by_claims": f"""
            SELECT
              Prscrbr_Type,
              SUM(Tot_Clms) AS total_claims,
              COUNT(*) AS num_records
            FROM `{table_ref}`
            WHERE NOT is_suppressed
            GROUP BY Prscrbr_Type
            ORDER BY total_claims DESC
            LIMIT 5
        """,
    }

    for name, sql in queries.items():
        log.info("--- %s ---", name)
        result = bq_client.query(sql).result()
        for row in result:
            log.info(dict(row))

    # Sanity check against Day 1's known row count
    row_count_result = list(bq_client.query(queries["row_count"]).result())[0]
    actual = row_count_result["row_count"]
    if actual != EXPECTED_ROW_COUNT:
        log.warning(
            "Row count mismatch: BigQuery has %d rows, Day 1 extracted %d. "
            "Check for load errors or duplicate runs.",
            actual, EXPECTED_ROW_COUNT,
        )
    else:
        log.info("Row count matches Day 1 extraction exactly: %d rows.", actual)


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------
def main() -> None:
    if "REPLACE_ME" in (PROJECT_ID, BUCKET_NAME, SERVICE_ACCOUNT_KEY_PATH):
        raise SystemExit(
            "Set PROJECT_ID, BUCKET_NAME, and SERVICE_ACCOUNT_KEY_PATH at the "
            "top of this script before running."
        )

    storage_client = storage.Client.from_service_account_json(SERVICE_ACCOUNT_KEY_PATH)
    bq_client = bigquery.Client.from_service_account_json(SERVICE_ACCOUNT_KEY_PATH)

    gcs_uri = upload_to_gcs(storage_client)
    table_ref = load_to_bigquery(bq_client, gcs_uri)
    run_validation_queries(bq_client, table_ref)

    log.info("Day 2 complete. Ready for Day 3: Looker Studio dashboard.")


if __name__ == "__main__":
    main()