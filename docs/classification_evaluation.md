# Medal-performance classification evaluation (Step 20)

Run from the repository root in the existing environment:

```bash
source .venv/bin/activate
python -B -m unittest discover -s tests -v
python -B -m src.ml.classify_medal_performance
git diff --check
```

The classification command reads `models/country_features.csv`, prints JSON to
standard output, and saves nothing. It never loads or replaces regression models
or reports. `evaluate_classification(dataframe)` returns a
`ClassificationEvaluation` containing class order/distribution, country-level
train/validation memberships, pooled model/baseline metrics, fold metrics and a
country-sorted DataFrame of OOF labels/probabilities. No fitted full-data model is
returned. The optional estimator argument is a testing seam, not a tuning workflow.

## Validation and fixed procedure

Input must have unique column labels and country, Total and the five participation
features. Extra columns are ignored, never predictors. Counts must have real
numeric dtypes and finite, nonnegative integer-valued values. Integer-valued floats
and pandas nullable numeric dtypes without missing values are accepted; booleans,
complex numbers, strings, missing values, fractions and infinities are rejected.
Countries must be nonblank strings. The existing country helper trims surrounding
whitespace and applies its one documented alias correction. Duplicate normalized
keys and unresolved replacement characters are errors. Rows sort by normalized
country key, so file row order and index do not determine folds. Inputs are copied.

Validated Total maps to exactly No Medal = 0, Medal = 1–9, High Medal = 10+.
Every class must have at least five countries; 206 rows is not a universal rule.
The explicit class order is **No Medal, Medal, High Medal** for distribution,
confusion-matrix axes and probability columns. Estimator probability columns are
remapped from each fitted estimator's `classes_`; display order is never assumed.
Invalid estimator labels or probability matrices fail clearly.

One shuffled StratifiedKFold loop uses five folds and seed 42. Each fold fits one
RandomForestClassifier with the unchanged 300 trees, depth 8, minimum leaf size 2,
balanced class weights, seed 42 and n_jobs=-1. Class weights are learned from that
fold's training labels. Both validation labels and probabilities come from this
same fitted estimator. There is no full-data fit or model selection. A separately
fitted most-frequent DummyClassifier uses the identical training/validation split.
Majority ties use sklearn's lexical class ordering. Disjoint memberships and
exactly one validation prediction per country are verified.

The predictors remain athlete_count, athlete_discipline_count, team_count,
team_discipline_count and team_event_count. Country, medal totals/components,
classes and medal-derived KPIs are excluded. No fitted preprocessing happens
outside folds. Future preprocessing must be fitted within each training fold.

## Metrics and undefined values

The primary results pool all OOF predictions once. Fold metrics are also returned;
nonlinear pooled F1 is not the mean of fold F1. Confusion-matrix rows are actual
classes, columns predicted classes. Accuracy, macro/weighted precision, recall and
F1, per-class metrics, one-vs-rest ROC-AUC and average precision (AP) are included.
Weighted recall equals accuracy in this single-label task. AP is explicitly named;
it is not trapezoidal PR-curve area. ROC-AUC/AP evaluate ranking, not calibration.
Balanced forest probability outputs are not established as calibrated probabilities.

Undefined per-class precision (no predictions), recall (no actual examples), or
F1 (neither actual nor predicted examples) is represented by None/JSON null and
listed under undefined_metrics. Macro/weighted precision/recall/F1 assign these
undefined components zero contribution, preserving the baseline comparison and
avoiding an inflated score from silently dropping classes. F1 is defined as zero
when a class has actual examples but no predictions. ROC-AUC requires positives
and negatives; AP requires positives. Undefined ranking metrics are null, and
macro/weighted ranking aggregates are null if any constituent is undefined.
The required five-per-class gate makes ranking metrics defined for normal pooled
and fold evaluations, including the constant majority baseline.

## Corrected-data result and interpretation

The corrected input has 113 No Medal, 68 Medal and 25 High Medal countries. Five
folds each validate on five High Medal countries, 13–14 Medal and 22–23 No Medal.
This is feasible stratification, but minority-class estimates remain variable.

Step 20 reproduces Step 19: forest accuracy 0.762136, macro F1 0.728887,
weighted F1 0.763420; baseline accuracy 0.548544 and weighted F1 0.388623.
The source was already sorted by country and its keys already normalized, so
sorting and probability-column remapping change no scores. The semantic matrix
order changes presentation only. The historical approximately 0.7944 weighted F1
used older data and is not a comparable benchmark or a score to recover.

This is exploratory country estimation within the same Olympics, not future-Games
forecasting or independent external validation. The data and CV results were
already inspected. Any future model comparison/tuning needs a prespecified nested
procedure or genuinely new external data, not optimization against these scores.
Athlete names are imperfect person identifiers; team/event participation features
reflect source coverage. Missing medal rows are interpreted as zero by the builder,
which depends on source completeness. Pre-event feature availability is unverified;
shared country/resource factors and small, skewed classes limit generalization.
Class boundaries are fixed operational categories, not an optimized or causal scale.
Parallel/native-library differences may affect numerical reproducibility; source,
code, environment and split identities matter as well as seeds.

No classification artifacts are persisted in Step 20. A later authorized persistence
step should retain country-keyed OOF evidence, fold memberships, class order,
baseline, full metrics/undefined-value policy, source/code hashes, model settings,
versions and limitations, with reload/metric reproduction checks. Any later
full-data classification fit must be clearly distinguished from evaluation models.

## Persist and validate classification artifacts (Step 21)

Step 21 adds an explicit persistence command while leaving the Step 20 evaluator
unchanged. Run from the repository root in the existing pinned environment:

```bash
source .venv/bin/activate
python -B -m unittest discover -s tests -v
python -B -m src.ml.persist_classification
sha256sum models/country_features.csv reports/classification_evaluation.json reports/classification_oof_predictions.csv models/medal_classification_model.joblib
git diff --check
```

This command deliberately replaces only these three classification outputs:

| Path | Purpose |
| --- | --- |
| `reports/classification_evaluation.json` | Pooled/fold model and baseline metrics, class definitions/order, full country memberships, source/code hashes, model settings, versions, limitations and separate final-model provenance |
| `reports/classification_oof_predictions.csv` | One sorted row per normalized country with actual class/Total, fold, OOF prediction and explicit named class probabilities, plus baseline prediction/probabilities |
| `models/medal_classification_model.joblib` | Separately trained full-data classifier for demonstration/inference; ignored by Git |

The command calls the existing Step 20 evaluator once: five training-only forest
fits and five independently fold-trained majority baselines. It retains the live
OOF result without replacing it with any final-model output. It then fits exactly
one separate Random Forest on all validated countries (206 for this source), with
the frozen settings. There is no parameter search or score-based selection.
The final model has lexical native class order High Medal / Medal / No Medal;
the report and named OOF CSV columns use semantic order No Medal / Medal / High
Medal. This mapping is checked explicitly.

Before replacement, staging verification compares the serialized CSV with the live
OOF result, reconstructs pooled/fold metrics from round-trip float64 values, checks
actual classes/totals, exact sorted country coverage, probability ranges/sums,
predicted-class maxima, deterministic fold memberships and training-fold majority
predictions. The report records per-class nulls and the existing aggregate policy.
ROC-AUC is one-vs-rest and precision-recall ranking uses average precision (AP).
CSV floats use 17 significant digits; JSON preserves full values and disallows NaN.
There are no generated timestamps. Report keys are sorted.

The freshly generated final model is loaded only after checking its known digest.
Verification checks features/dtypes, model class/parameters, native/semantic class
orders, training-country provenance and forest bootstrap sample lengths. Its
`inference_replay` labels/probabilities on the sorted input are retained only for
reload consistency checks: no in-sample performance scores are reported. These
predictions are separate from the OOF CSV. A checksum proves identity, not trust:
never use this helper to deserialize an arbitrary existing or third-party joblib.
The previous classification model, if any, is backed up without loading it.

All three existing targets and their checksums are copied to an external
`/tmp/tokyo-classification-*` recovery directory before generation. It contains a
`backup_manifest.json`, any `backup/` files, `staged/` outputs and, on success,
`completed_sha256.json`. The command prints this path. Source and destination
checksums are checked again before replacement to detect concurrent edits. Each
replacement is atomic, and synchronous write/final-validation failures restore
existing targets or remove only outputs newly created by that failed transaction.
Validation failure before publication leaves destination artifacts untouched.
A process/machine crash between three replacements cannot be transactionally
atomic; recover using the retained backups/manifest. `/tmp` is temporary storage,
so copy backups elsewhere for durable retention. Concurrent writers should still
be avoided; checksum checks are not a filesystem-wide lock.

With identical source path, code and environment, synthetic tests confirm byte
reproducibility of all three artifacts. Absolute source paths and code digests are
part of the report, so moving a checkout or changing code changes report bytes.
Native-library/threading differences can affect numeric/model bytes; numeric
verification uses 1e-12 tolerance. Offline verification reconstructs evidence from
CSV and membership records; it does not retrain fold models or turn saved
provenance into independent proof of historical fitting. During publication,
comparison with the live evaluator provides that additional linkage.

The corrected-data metrics agree with Step 20 within floating-point tolerance:
accuracy 0.762136, weighted F1 0.763420, macro F1 0.728887; majority accuracy
0.548544. Persisting these already inspected results does not make them independent
validation. The final full-data model is an inference demonstration, not a source
of cross-validation scores or evidence of future-Olympics forecasting accuracy.
No raw/derived data, dashboard exports or regression artifacts are modified.
