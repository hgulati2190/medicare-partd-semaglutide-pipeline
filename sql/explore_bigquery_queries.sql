-- Run these directly in the BigQuery Console's Query Editor
-- (BigQuery > Query > paste > Run). Each is free/cheap at this table size.

-- 1. Overall shape check
SELECT
  COUNT(*) AS total_rows,
  COUNT(DISTINCT Prscrbr_NPI) AS unique_prescribers,
  COUNT(DISTINCT Prscrbr_State_Abrvtn) AS states_represented,
  COUNTIF(is_suppressed) AS suppressed_rows,
  ROUND(100 * COUNTIF(is_suppressed) / COUNT(*), 2) AS pct_suppressed
FROM `medicare-part-d-pipeline.partd_raw.semaglutide_prescribers`;

-- 2. Brand name breakdown -- Semaglutide is sold as Ozempic, Wegovy, Rybelsus.
-- This tells you the split, which could become its own dashboard chart.
SELECT
  Brnd_Name,
  COUNT(*) AS num_records,
  SUM(Tot_Clms) AS total_claims,
  ROUND(SUM(Tot_Drug_Cst), 2) AS total_cost
FROM `medicare-part-d-pipeline.partd_raw.semaglutide_prescribers`
WHERE NOT is_suppressed
GROUP BY Brnd_Name
ORDER BY total_cost DESC;

-- 3. Average cost per claim -- a normalized metric, useful since raw totals
-- are skewed by prescriber volume.
SELECT
  ROUND(SUM(Tot_Drug_Cst) / SUM(Tot_Clms), 2) AS avg_cost_per_claim
FROM `medicare-part-d-pipeline.partd_raw.semaglutide_prescribers`
WHERE NOT is_suppressed;

-- 4. Distribution check -- are a small number of prescribers driving most
-- of the volume, or is it evenly spread? (Useful framing for "who prescribes
-- this most" style charts.)
SELECT
  Prscrbr_NPI,
  Prscrbr_Last_Org_Name,
  Prscrbr_State_Abrvtn,
  Tot_Clms,
  Tot_Drug_Cst
FROM `medicare-part-d-pipeline.partd_raw.semaglutide_prescribers`
WHERE NOT is_suppressed
ORDER BY Tot_Clms DESC
LIMIT 10;
