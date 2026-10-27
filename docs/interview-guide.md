# Tokyo Olympics project: interview guide

## A 60–90 second explanation

“This project turns five Tokyo Olympics CSV datasets into validated country-level
analytics and a Power BI report. Azure Data Factory copies the pinned source
bytes into a run-specific ADLS directory using managed identity. I verify every
output by filename, length and SHA256, so a successful pipeline status is not the
only integrity check.

The transformation layer standardizes known country aliases, removes exact
duplicates, validates medal arithmetic and joins, and computes country features.
The Power BI model has four pages and explicit DAX measures. I reconciled all
206 countries against the source, including filtered aggregate ratios and ranks.

The ML work compares medal-count regression models using training-only cross
validation and evaluates a fixed classifier through out-of-fold predictions.
These are exploratory estimates within one Games, not forecasts of a future
Olympics. Cloud execution status is documented separately from implemented code.”

Before saying that Databricks ran successfully, check the current
[completion audit](project-completion.md). The historical attempts stopped before
job submission; a notebook or workspace alone is not execution evidence.

## Show these in a five-minute demo

1. Open the [Power BI overview](../powerbi/TokyoOlympics/previews/Overview.png):
   1,080 medal awards, 11,071 listed athletes, 206 delegations and 93 medal countries.
2. Open `powerbi/TokyoOlympics/TokyoOlympics.pbip` in Desktop. Use the country
   dropdown, then the Country detail page. Explain that slicers are page-local.
3. Show [the source/DAX reconciliation](../powerbi/TokyoOlympics/source-validation.json)
   and explain ratio-of-sums: aggregate gold divided by aggregate medals, rather
   than averaging country percentages.
4. Show [ADF run evidence](azure/stage2/README.md): the single run
   `1a11a954-8e6c-45e9-98b1-fc530f00a6e8`, five successful copies,
   461,896 verified bytes, 105.475 seconds.
5. Show the test suite and one ML report. Use saved evidence for cloud components;
   do not redeploy or repeat ingestion merely to demonstrate the project.

## Questions you can answer concretely

| Question | Answer grounded in the implementation |
| --- | --- |
| Why Binary Copy in ADF? | Preserve the original encodings and bytes; parse explicitly during transformation. |
| How do you avoid duplicate ingestion? | Reuse the verified ingestion run; outputs are addressed by service-generated run IDs. No scheduled ingestion trigger is deployed. |
| Why a success manifest? | The notebook publishes it only after CSV and Parquet read-back checks, so partial output directories are not treated as complete. |
| How is access controlled? | ADF uses managed identity with a container-scoped grant. The prepared Databricks design uses an Access Connector, scoped roles and workspace-bound Unity Catalog locations. |
| What is an athlete count? | A distinct-name proxy within country, not a reliable count of uniquely identified people. |
| What is a team count? | Distinct country/discipline/event/team-name entries, not globally distinct team names. |
| Why are efficiency ratios qualified? | A team medal counts once in the medal table; athlete and medal grains differ. The ratio is descriptive, not an individual win probability. |
| How is leakage addressed? | Regression model selection uses training-only CV; the holdout is reserved for final evaluation. Classifier scores use OOF predictions, separate from the full-data demonstration model. |
| What would change at production scale? | Replace bounded driver-side parsing with distributed ingestion/schema enforcement, add orchestration/recovery, monitored SLAs and access reviews, and validate new data/version drift. |

## Measured ML results

- Regression selected **Random Forest**: holdout MAE **4.563** medals,
  RMSE **11.692**, R² **0.658**. [Saved evaluation](../reports/regression_evaluation.json).
- Classification pooled OOF accuracy **76.21%**, macro F1 **0.729**,
  macro ROC AUC **0.904**. Majority baseline accuracy **54.85%**.
  [Saved evaluation](../reports/classification_evaluation.json).

The data are small, skewed and from one Olympics. Historical inspection limits
independent validation claims. Pre-event availability of all participation
features is not established; these numbers do not validate future forecasting.

## Verification commands

```bash
.venv/bin/python -B -m unittest discover -s tests -v
.venv/bin/python -B -m src.azure.contracts
.venv/bin/python -B scripts/verify_powerbi_snapshot.py
```

The last command checks captured Desktop evidence against the pinned CSV; it does
not start Power BI or Azure. A source-only PBIP checkout needs a Desktop Refresh
to load the embedded snapshot, which requires no Azure credentials.
