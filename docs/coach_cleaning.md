# Coach cleaning and validation policy

The source has 394 rows and four text columns: Name, Country, Discipline, Event.
Name/Country/Discipline are required identity/assignment fields; Event is optional.
The feature and analytics builders do not use coach records in aggregation.
Step 12 validates Coaches.csv through their shared source gate before generation.

| Discipline | Raw rows | Missing Event |
| --- | ---: | ---: |
| Artistic Swimming | 69 | 28 |
| Baseball/Softball | 26 | 0 |
| Basketball | 74 | 50 |
| Football | 59 | 31 |
| Handball | 29 | 5 |
| Hockey | 45 | 9 |
| Rugby Sevens | 25 | 1 |
| Volleyball | 45 | 21 |
| Water Polo | 22 | 0 |
| Total | 394 | 145 |

There are no missing identity fields or surrounding whitespace in the current
source. The exact duplicate at CSV lines 145 and 146 is GUERRERO Rolando,
Mexico, Baseball/Softball, Softball. Removing its redundant occurrence leaves
393 rows (Baseball/Softball decreases from 26 to 25); missing Event stays at 145.
Thirteen names recur in the raw file; twelve have different event assignments
and remain separate records (for example CHEPAK Anastasiya: Duet and Team).

The source supports records at country/discipline level even when Event is absent.
Discipline-wide coaching is a plausible interpretation, but the CSV has no role
or assignment metadata to prove it for each missing value. Missing Event therefore
means **unspecified**, not a verified discipline-wide role or an invalid record.
It is permitted and reported as a warning, never inferred from another coach,
country, discipline or event. This policy does not assert that all blanks are
factually correct; verification would require source assignment records.

`clean_and_validate_coaches` returns a cleaned deep copy and a structured report:

- Strip surrounding whitespace in the four schema text fields; preserve accents,
  case and internal whitespace. Whitespace-only Event becomes missing. Existing
  missing events remain missing. Extra columns are retained without modification.
- Require the four columns and unique column labels. Schema failures return an
  unchanged copy plus an `invalid_schema` error, avoiding unsafe cleaning.
- Report null/blank Name, Country or Discipline as `missing_identity` errors and
  non-string non-missing schema values as `invalid_text_type` errors. Do not
  invent or drop incomplete identities. Consumers must inspect errors.
- Deduplicate only exact full rows after whitespace normalization. Names alone
  are not coach identifiers; different assignments/countries/disciplines remain.
  Identical rows are redundant records, not proof of unique real-world identity.
- The one documented GUERRERO redundant row is `known_exact_duplicate` warning.
  Other duplicate rows, including additional copies of that known record, produce
  `unexpected_exact_duplicates` errors even though the exact-row cleaner removes
  them. This keeps previously unknown source defects visible.
- Remaining missing Event values produce `unspecified_event` warnings with a
  distribution by discipline. Reports describe each invocation; cleaning is
  idempotent, so rerunning on cleaned data reports no removed duplicates.

`run_quality_checks` retains its existing raw Coaches profile and adds the report
as `Coaches.cleaning_validation`. It does not replace raw inputs, write a cleaned
CSV or affect the other four dataset profiles. Current results have no coach
validation errors; the duplicate and missing assignments are documented warnings.
Country-level athlete/team features, KPIs, medal totals and saved artifacts are
unaffected. Coach assignment uncertainty and the lack of reliable coach IDs remain.
