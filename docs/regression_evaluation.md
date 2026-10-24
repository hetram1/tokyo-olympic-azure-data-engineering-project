# Regression selection and final evaluation

Run `python -B -m src.ml.train_model` from the repository root. It reads
`models/country_features.csv`, prints results and saves nothing. The reusable
`evaluate_regression(dataframe)` API returns the fitted training model, CV summary,
fold metrics, audited country partitions, final holdout metrics and country
predictions in memory. This default command neither reads nor overwrites joblib
artifacts. The explicit persistence command below reuses this same evaluator.

## Prespecified procedure

1. Validate one row per country and finite, non-negative numeric features/target.
   Sort by country so file row reordering does not alter partitions.
2. Use `train_test_split(test_size=0.20, random_state=42)` without outcome-based
   stratification. For the corrected 206-row dataset: 164 training countries and
   42 holdout countries. No holdout outcome is passed to model comparison.
3. Run shuffled five-fold KFold with seed 42 **within the training partition**.
   All three candidates use identical folds: four validation folds of 33 countries
   and one of 32, with 131 or 132 fit countries. Every training country is used
   once for validation and never overlaps its fold's fit countries.
4. Candidates are the mean DummyRegressor, Random Forest and XGBoost. The baseline
   learns a separate mean using each fold's fit outcomes. Existing forest/boosting
   hyperparameters are retained (300 estimators, forest depth 8/leaf minimum 2;
   XGBoost depth 4, learning rate 0.05, row/column sampling 0.8). Seeds are 42;
   one worker reduces parallel execution variability. No parameter search occurs.
5. Select lowest **mean fold validation MAE**, with alphabetical model-name tie
   breaking. Report mean fold MAE, RMSE and R² and sample standard deviations.
   These are unweighted fold averages, not pooled out-of-fold metrics; R² values
   from different folds/holdout have different target variance and are not directly
   interchangeable. RMSE/R² do not determine selection.
6. Clone the selected candidate, fit it on all 164 training countries, predict
   the 42 holdout countries once, then calculate final MAE, RMSE and R². Other
   candidates are never evaluated on holdout. Do not retune after inspecting it.

Features stay athlete_count, athlete_discipline_count, team_count,
team_discipline_count and team_event_count; the target remains Total. Country
names identify partitions and output rows, not predictors. Gold/Silver/Bronze,
medal-derived KPIs and performance classes are not inputs. No scaling, imputation
or feature selection is fitted outside folds. These constant/tree estimators
need no fitted preprocessing; future preprocessing must be inside a cloned
sklearn Pipeline so each fold fits it on its own training subset.

`cross_validate.py` uses the shared split and training-only comparison, printing
fold results without evaluating holdout. `analyze_model.py` uses the same full
procedure, reports the selected model's largest holdout errors and shows its
training-fit feature importances if supported. Each invocation is reproducible;
running analysis again does not provide a new independent holdout sample.

## Current run and interpretation

Using the corrected 206-country CSV and tested dependency versions:

| Training-only CV candidate | Mean MAE | Mean RMSE | Mean R² |
| --- | ---: | ---: | ---: |
| Mean baseline | 6.076116 | 11.242483 | -0.425056 |
| Random Forest | 2.246920 | 5.086712 | 0.704403 |
| XGBoost | 3.080584 | 7.493766 | 0.428577 |

Random Forest is selected by training CV. Its final holdout MAE is **4.563124**
medals, RMSE **11.691616** and R² **0.657687**. Baseline/XGBoost have no final
holdout scores in this procedure. MAE describes average absolute medal error;
RMSE emphasizes large errors. Holdout R² compares squared error with predicting
the holdout sample mean and is not a percentage of countries predicted correctly.
Large errors for medal-heavy countries remain despite useful average performance.

The historical Random Forest MAE of approximately 3.675 came from 207 rows with
the corrupted extra country, old team/event features and test-based selection.
It is not an apples-to-apples benchmark. Corrected features and removal of the
extra row change both fitted data and country memberships under the same seed.
The higher new MAE is reported without trying to recover the old score. The new
code fixes the selection procedure; it does not prove that the historically
examined source dataset has become independent evidence.

This is country-level estimation within one Olympics, not future-Games
forecasting. Sample size is small, medal outcomes are skewed, CV variability is
substantial, names are imperfect athlete IDs and participation coverage is a
proxy. Participation data has no verified pre-event availability timestamp.
Country records may share unmodelled regional/resource factors, so random country
splits do not prove temporal or out-of-distribution generalization. No causal
interpretation is supported. Historical data inspection and any future retuning
after holdout exposure can introduce analyst selection bias; use new external
data for a fresh final assessment. Step 16 saved no prediction/model artifacts;
Step 17 adds the explicit persistence workflow below without changing selection.

## Persist and verify the evaluation artifacts (Step 17)

From the repository root, in the tested environment:

```bash
source .venv/bin/activate
python -B -m unittest discover -s tests -v
python -B -m src.ml.persist_regression
sha256sum models/country_features.csv models/medal_prediction_model.joblib reports/regression_evaluation.json reports/regression_holdout_predictions.csv
git diff --check
```

`persist_regression_evaluation` backs up all existing target artifacts and their
SHA256 values outside the repository before generation. It creates a recoverable
`/tmp/tokyo-step17-*` directory containing `backup/`, `backup_manifest.json`,
`staged/` and, after success, `completed_sha256.json`. It never loads the old
model. Backups are retained, but `/tmp` is temporary storage rather than a durable
archive. If a target changes concurrently, replacement stops. Each target is
replaced atomically; synchronous replacement/verification exceptions roll back
the set using backups. A process/machine crash between replacements cannot be
made transactionally atomic across three files; use retained backups to recover.

The evaluator is called once with the prespecified candidates/splits. Its selected
model remains fitted on 164 training countries, not the full 206-country dataset.
No second training pass is introduced by saving or verification. The persisted
model receives a provenance attribute containing the source SHA256, ordered
training country keys, training count and a fingerprint of the ordered training
country/features/target CSV representation. Forest bootstrap sample lengths also
confirm the fitted training population size.

| Artifact | Contents |
| --- | --- |
| `models/medal_prediction_model.joblib` | Selected training-only fitted estimator and training provenance; ignored by Git |
| `reports/regression_evaluation.json` | Model name/class/parameters, feature names/dtypes and target; seed and split procedure; train/holdout counts and country lists; all candidate CV metrics/fold partitions; selection criterion; holdout metrics; source/model/prediction hashes; training fingerprint; Python/library versions; limitations |
| `reports/regression_holdout_predictions.csv` | 42 country-sorted rows: country, actual_total, predicted_total, absolute_error |

CSV predictions use 17 significant digits and JSON keeps full floating-point
values, with deterministic key ordering and no generated timestamps. Metrics are
computed before any serialization; report metrics are then checked against saved
predictions. With the same source path, code and environment, the synthetic tests
verify byte-reproducible artifacts. Relocating the source changes its absolute
path in the report; native-library changes can alter fitted bytes/numerics.

Verification checks source/model/prediction hashes, the exact input schema and
dtypes, train/holdout and CV memberships, CV aggregation and winner, model class
and parameters, training provenance and count, actual holdout targets, reloaded
predictions, absolute errors and final metrics. Only the newly created model with
an already-known digest is deserialized; a checksum alone cannot make an unknown
pickle safe. Prediction replay checks artifact integrity, not a new assessment
or a chance to retune the model.

The holdout was **already inspected in Step 16**. Persisting it does not make it
independent external validation. It supports same-Olympics estimation evidence,
not prospective medal-prediction performance. No raw/country/dashboard CSV is
modified by this command and classification remains unchanged.
