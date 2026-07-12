"""
Explore the CMS Part D Prescribers by Provider and Drug dataset WITHOUT
downloading the full file. Uses tiny API requests to understand structure,
row counts, and candidate filter values before committing to a slice.

SETUP:
    pip install requests pandas

BEFORE RUNNING:
    Set DATASET_UUID (see day1_extract_clean.py for how to find it).
"""

import logging

import pandas as pd
import requests

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
log = logging.getLogger(__name__)

DATASET_UUID = "9552739e-3d05-4c1b-8eff-ecabf391e2e5"
API_BASE = f"https://data.cms.gov/data-api/v1/dataset/{DATASET_UUID}/data"
STATS_URL = f"{API_BASE}/stats"


def get_total_row_count():
    """Full dataset row count -- costs nothing, no data transferred."""
    resp = requests.get(STATS_URL, timeout=30)
    resp.raise_for_status()
    stats = resp.json()
    log.info("Dataset stats: %s", stats)
    return stats


def peek_sample(n=10):
    """Grab just N rows to see columns and real values."""
    resp = requests.get(API_BASE, params={"size": n, "offset": 0}, timeout=30)
    resp.raise_for_status()
    df = pd.DataFrame(resp.json())
    log.info("Columns (%d): %s", len(df.columns), df.columns.tolist())
    log.info("Sample:\n%s", df.head(n).to_string())
    return df


def count_rows_for_filter(field: str, value: str) -> int:
    """
    Get an exact row count for a candidate filter by paginating through
    the filtered result set. Note: this CMS API does not support a
    column-selection parameter (tested -- "properties" is ignored and
    all columns come back regardless), so each page is the full row
    width. Still cheap: a few hundred thousand rows at 5000/page is a
    handful of requests.
    """
    total = 0
    offset = 0
    page_size = 5000

    while True:
        resp = requests.get(
            API_BASE,
            params={
                f"filter[{field}]": value,
                "size": page_size,
                "offset": offset,
            },
            timeout=60,
        )
        resp.raise_for_status()
        page = resp.json()
        total += len(page)

        if len(page) < page_size:
            break
        offset += page_size

    log.info("%s=%s: %d exact rows", field, value, total)
    return total


def compare_candidate_filters():
    """
    Check row counts for a few candidate slices side by side so you can
    pick one without guessing. Edit the candidates dict to whatever
    you're weighing.
    """
    # Confirmed real values from a live API sample (case-sensitive, title case)
    candidates = {
        ("Gnrc_Name", "Semaglutide"): None,          # GLP-1 / diabetes example
        ("Gnrc_Name", "Oxycodone Hcl"): None,         # opioid example
        ("Gnrc_Name", "Insulin Glargine,hum.Rec.Anlog"): None,  # insulin example
        ("Prscrbr_Type", "Internal Medicine"): None,  # broad primary care specialty
        ("Prscrbr_Type", "Endocrinology"): None,      # check if this specialty exists/has volume
        ("Prscrbr_State_Abrvtn", "MD"): None,
    }
    for (field, value) in candidates:
        candidates[(field, value)] = count_rows_for_filter(field, value)

    log.info("\n--- Candidate slice sizes ---")
    for (field, value), count in candidates.items():
        log.info("%s = %s -> %s rows", field, value, count)


if __name__ == "__main__":
    if DATASET_UUID == "REPLACE_ME":
        raise SystemExit("Set DATASET_UUID first.")

    get_total_row_count()
    peek_sample(10)
    compare_candidate_filters()