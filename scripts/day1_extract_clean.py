"""
Day 1: Download a filtered slice of CMS Medicare Part D Prescribers by
Provider and Drug, inspect it, and clean/transform it into a Parquet
file ready for GCS upload on Day 2.

Filters at the API level (not after download) to keep this fast on a
2hr/day budget -- the full national file is 25M+ rows / several GB.

SETUP:
    pip install requests pandas pyarrow

BEFORE RUNNING:
    1. Go to the dataset page on data.cms.gov, click "API" / "Export",
       and copy the dataset UUID from the shown URL
       (data.cms.gov/data-api/v1/dataset/<UUID>/data).
    2. Paste it into DATASET_UUID below.
    3. Pick a filter that gives you a portfolio-sized slice -- one state
       is usually a few hundred thousand rows, which is plenty.
"""

import io
import logging
import sys
from pathlib import Path

import pandas as pd
import requests

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# CONFIG -- edit these
# ---------------------------------------------------------------------------
DATASET_UUID = "9552739e-3d05-4c1b-8eff-ecabf391e2e5"  # Medicare Part D Prescribers by Provider and Drug
API_BASE = f"https://data.cms.gov/data-api/v1/dataset/{DATASET_UUID}/data"

# Filter to keep the slice manageable. Confirmed via 00_explore_dataset.py:
# Gnrc_Name = "Semaglutide" -> 210,621 rows (GLP-1/diabetes drug).
FILTER_FIELD = "Gnrc_Name"
FILTER_VALUE = "Semaglutide"

PAGE_SIZE = 5000  # CMS API max page size

# Anchor all paths to this script's own folder, not whatever directory you
# happen to run it from -- avoids files landing in unexpected places
# (e.g. your OS user folder) depending on how you launched the script.
SCRIPT_DIR = Path(__file__).resolve().parent
RAW_DIR = SCRIPT_DIR / "data" / "raw"
CLEAN_DIR = SCRIPT_DIR / "data" / "clean"
RAW_DIR.mkdir(parents=True, exist_ok=True)
CLEAN_DIR.mkdir(parents=True, exist_ok=True)

RAW_CSV_PATH = RAW_DIR / f"partd_{FILTER_VALUE.lower()}_raw.csv"
CLEAN_PARQUET_PATH = CLEAN_DIR / f"partd_{FILTER_VALUE.lower()}_clean.parquet"


# ---------------------------------------------------------------------------
# STEP 1: DOWNLOAD (paginated, filtered)
# ---------------------------------------------------------------------------
def fetch_filtered_dataset() -> pd.DataFrame:
    """Pull all pages matching FILTER_FIELD == FILTER_VALUE into one DataFrame."""
    rows = []
    offset = 0

    while True:
        params = {
            f"filter[{FILTER_FIELD}]": FILTER_VALUE,
            "size": PAGE_SIZE,
            "offset": offset,
        }
        resp = requests.get(API_BASE, params=params, timeout=60)
        resp.raise_for_status()
        page = resp.json()

        if not page:
            break

        rows.extend(page)
        log.info("Fetched %d rows (offset=%d)", len(page), offset)

        if len(page) < PAGE_SIZE:
            break  # last page
        offset += PAGE_SIZE

    if not rows:
        log.error("No rows returned. Check DATASET_UUID and FILTER_FIELD/VALUE.")
        sys.exit(1)

    df = pd.DataFrame(rows)
    log.info("Total rows fetched: %d", len(df))
    return df


# ---------------------------------------------------------------------------
# STEP 2: INSPECT
# ---------------------------------------------------------------------------
def inspect(df: pd.DataFrame) -> None:
    log.info("Shape: %s", df.shape)
    log.info("Columns:\n%s", df.columns.tolist())
    log.info("Dtypes:\n%s", df.dtypes)
    log.info("Nulls per column:\n%s", df.isna().sum()[df.isna().sum() > 0])
    log.info("Sample rows:\n%s", df.head(3).to_string())

    # CMS suppresses small counts (<11) as blanks for privacy -- confirm
    # how much of that you have, since it affects Day 2 validation queries.
    suppression_cols = [c for c in df.columns if "Sprsn_Flag" in c]
    if suppression_cols:
        log.info("Suppression flag columns present: %s", suppression_cols)


# ---------------------------------------------------------------------------
# STEP 3: CLEAN / TRANSFORM
# ---------------------------------------------------------------------------
def clean(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    # Every value comes back from the API as a string -- cast numeric columns.
    numeric_cols = [
        "Tot_Clms", "Tot_30day_Fills", "Tot_Day_Suply", "Tot_Drug_Cst",
        "Tot_Benes", "GE65_Tot_Clms", "GE65_Tot_30day_Fills",
        "GE65_Tot_Drug_Cst", "GE65_Tot_Day_Suply", "GE65_Tot_Benes",
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Standardize text fields
    text_cols = ["Prscrbr_Last_Org_Name", "Prscrbr_First_Name", "Brnd_Name", "Gnrc_Name"]
    for col in text_cols:
        if col in df.columns:
            df[col] = df[col].str.strip().str.upper()

    # Drop exact duplicate rows if any slipped in from pagination overlap
    before = len(df)
    df = df.drop_duplicates()
    if len(df) != before:
        log.info("Dropped %d duplicate rows", before - len(df))

    # Flag suppressed records rather than silently treating NaN as zero --
    # this distinction matters for anyone reviewing the dashboard.
    if "Tot_Clms" in df.columns:
        df["is_suppressed"] = df["Tot_Clms"].isna()

    return df


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------
def main() -> None:
    if DATASET_UUID == "REPLACE_ME":
        log.error("Set DATASET_UUID at the top of this script before running.")
        sys.exit(1)

    log.info("Fetching filtered dataset: %s = %s", FILTER_FIELD, FILTER_VALUE)
    log.info("Raw output path:   %s", RAW_CSV_PATH.resolve())
    log.info("Clean output path: %s", CLEAN_PARQUET_PATH.resolve())
    df_raw = fetch_filtered_dataset()
    df_raw.to_csv(RAW_CSV_PATH, index=False)
    log.info("Saved raw data -> %s", RAW_CSV_PATH)

    inspect(df_raw)

    df_clean = clean(df_raw)
    df_clean.to_parquet(CLEAN_PARQUET_PATH, index=False)
    log.info("Saved cleaned data -> %s", CLEAN_PARQUET_PATH)
    log.info("Ready for Day 2: GCS upload + BigQuery load.")


if __name__ == "__main__":
    main()