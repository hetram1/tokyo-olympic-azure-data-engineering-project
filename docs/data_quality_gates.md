# Automatic source gates

Both country builders call `load_validated_sources` before any aggregation or
derived output. Each invocation loads all five CSVs once, prepares copies with
the existing cleaning functions, and reuses those prepared tables. There is no
cache that can hide changed input. Nothing is written by validation. Output
directories are created only by explicit file-writing entry points, after a
successful build. Saved country/model/dashboard artifacts remain untouched.

Reusable interfaces in `src/quality/gates.py`:

- `validate_sources(sources)`: accepts a dictionary keyed by Athletes, Coaches,
  EntriesGender, Medals and Teams; returns prepared copies and a structured report.
  This diagnostic function collects errors without raising.
- `load_validated_sources(loader=None)`: loads the five files once using the
  existing encoding-aware loader, validates, and raises `DataQualityError` on any
  error. It returns prepared tables and the report on success.
- Both builders attach the report at `df.attrs['data_quality_report']`. Warnings
  remain available there without adding CSV columns or changing schemas. This
  metadata is not persisted by CSV export. Exceptions expose `.report` and include
  dataset, issue, remediation guidance and affected record samples. Samples use
  source dataframe indices (not CSV line numbers), capped at five per issue.

## Blocking errors

- Unreadable/missing datasets; missing required columns; duplicate column labels;
  missing, blank or non-text required identity/assignment fields. Coach Event is
  optional. No country-name mapping beyond the existing explicit normalization
  and verified Teams corrections is inferred.
- Unexpected U+FFFD characters in any text field after known corrections.
- Medal counts/ranks that are missing, nonnumeric, boolean, nonfinite or fractional;
  negative medal counts; nonpositive ranks; inconsistent medal arithmetic. Rank
  ties are allowed. Existing medal validators are reused after type checks.
- Gender schema/count/arithmetic/duplicate-discipline errors, using the existing
  gender validator. Duplicate discipline rows cannot safely be summed or removed.
- Duplicate normalized medal-country keys, even identical rows, because they
  multiply country joins. Athlete/team full-row duplicates follow established
  exact-dedup policies; conflicting extra fields on the same assignment/composite
  entry key are errors. Coach duplicates follow the existing coach validator:
  the documented redundant row is a warning; unexpected duplicates are errors.
- Medal countries without a participation-country match; team country keys absent
  from athlete data, which would create unexplained zero-athlete country rows;
  contradictory case-only country variants. These require source identity/coverage
  review, never guessed corrections. An unmatched team country might reflect
  incomplete source coverage rather than a typo; this gate blocks that ambiguity
  because silently generating its athlete-denominator KPIs would be unsafe.
- Both actual aggregation joins also enforce `validate='one_to_one'` as a final
  defense against accidental multiplication. Medal-country uniqueness is checked
  before these joins. Not every participating country must have medals or teams.

No universal country counts or medal totals are hardcoded into validation.

## Non-blocking observations

The known missing coach Event values remain unspecified assignments, not inferred
roles. Known exact duplicates are removed only under the established policies.
Repeated athlete names across disciplines remain distinct records. The gender
entry/athlete row difference, discipline-coverage differences and source-granularity
limitations are warnings. No source totals or individual gender labels are invented.

The current sources pass: 206 athlete/participating countries, 84 team countries,
93 medal countries, no unmatched medal keys or team-only country keys, and unique
medal country keys. There are 113 participating countries without medals and 122
athlete countries without team entries; both are valid. The outputs retain
340 gold, 338 silver, 402 bronze and 1,080 total medals. KPI formulas, output
column schemas and existing normalization/correction/counting definitions are
unchanged. Reports still flag 145 missing coach events, the known duplicates,
repeated names and the unresolved +231 raw gender-entry difference.

Limits: country names are not authoritative NOC IDs; aliases without detectable
key conflicts cannot always be identified. A valid arithmetic/schema check does
not verify real-world medal accuracy, coach assignments or unique human identities.
`run_quality_checks` remains a diagnostic raw-data profiler; production builders
use the enforcing gate rather than relying on that profiler to stop processing.
