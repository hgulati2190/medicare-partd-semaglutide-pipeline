# GCP Setup — Part D Pipeline

Run these with `gcloud` CLI (install: https://cloud.google.com/sdk/docs/install) or do the equivalent in Console.

```bash
# 1. Auth
gcloud auth login

# 2. Create project (pick a unique ID)
export PROJECT_ID="part-d-pipeline-2026"
gcloud projects create $PROJECT_ID --name="CMS Part D Pipeline"
gcloud config set project $PROJECT_ID

# 3. Link billing (get billing account ID first)
gcloud billing accounts list
gcloud billing projects link $PROJECT_ID --billing-account=BILLING_ACCOUNT_ID

# 4. Enable required APIs
gcloud services enable \
  storage.googleapis.com \
  bigquery.googleapis.com \
  bigquerystorage.googleapis.com

# 5. Create GCS bucket (for raw/cleaned files, Day 2)
export BUCKET_NAME="${PROJECT_ID}-partd-data"
gcloud storage buckets create gs://$BUCKET_NAME --location=US

# 6. Create BigQuery dataset (Day 2)
bq mk --dataset --location=US ${PROJECT_ID}:partd_raw

# 7. Service account for the Python scripts (avoids using your personal creds)
gcloud iam service-accounts create partd-pipeline-sa \
  --display-name="Part D Pipeline SA"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:partd-pipeline-sa@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/storage.objectAdmin"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:partd-pipeline-sa@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/bigquery.dataEditor"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:partd-pipeline-sa@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/bigquery.jobUser"

# 8. Download a key for local dev (Day 1/2 scripts will use this)
gcloud iam service-accounts keys create ~/partd-sa-key.json \
  --iam-account=partd-pipeline-sa@${PROJECT_ID}.iam.gserviceaccount.com
```

**Cost note:** GCS + BigQuery are effectively free at this scale (BQ free tier: 1TB queries/mo,
10GB storage/mo; GCS: pennies for a filtered slice). Set a budget alert anyway:

```bash
gcloud billing budgets create \
  --billing-account=BILLING_ACCOUNT_ID \
  --display-name="Part D Pipeline Budget" \
  --budget-amount=10USD
```

**Do not commit `~/partd-sa-key.json` to GitHub.** Add it to `.gitignore` on Day 3.
