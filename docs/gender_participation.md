# Gender participation validation

EntriesGender.csv has one aggregate row per discipline: Female, Male and Total
entries, without country, athlete, event, date, roster status or source-definition
identifiers. Athletes.csv has name/country/discipline records, without gender or
stable athlete IDs. Neither dataset establishes that its records count precisely
the same population. Summed discipline entries are not verified unique people.

## Findings

- All 46 gender records have distinct nonblank discipline labels, no missing
  fields or exact duplicates, valid non-negative integer counts and
  Female + Male = Total. Female totals 5,432, Male 5,884, combined 11,316.
- Both sources cover exactly the same 46 discipline labels, with no spelling or
  coverage discrepancies. Only Cycling BMX Freestyle has matching row totals.
- Athletes has 11,085 raw rows, including one redundant ALI Mohamed / Bahrain /
  Handball row. Existing name cleaning and exact deduplication retain 11,084
  records. The gender-minus-athlete gap is 231 raw or 232 after deduplication;
  the known duplicate therefore does not explain the gap.
- Athlete names contain 11,062 distinct strings globally and 11,071 distinct
  country/name pairs, before and after existing whitespace cleaning. Nine names
  occur in multiple countries. Thirteen country/name groups have records in
  multiple disciplines. Neither name-only deduplication nor country/name matching
  can establish unique people; different disciplines can represent legitimate
  multi-discipline participation or different people with the same name.
- The discrepancies have both signs: 38 disciplines have more gender entries,
  seven have more raw athlete rows, and one matches. Missing disciplines cannot
  explain the difference. Different roster/entry definitions, extraction coverage
  or snapshots are possible explanations, not verified facts. The repository has
  no metadata sufficient to identify the cause. The difference remains unresolved.

The exact comparison below is gender Total minus raw athlete rows. Handball's
cleaned athlete count is 342 instead of 343, changing its difference to -6;
all other discipline counts are unchanged by existing athlete cleaning.

| Discipline | Gender Total | Raw athlete rows | Difference |
| --- | ---: | ---: | ---: |
| 3x3 Basketball | 64 | 62 | +2 |
| Archery | 128 | 122 | +6 |
| Artistic Gymnastics | 196 | 187 | +9 |
| Artistic Swimming | 105 | 98 | +7 |
| Athletics | 2041 | 2068 | -27 |
| Badminton | 173 | 164 | +9 |
| Baseball/Softball | 234 | 220 | +14 |
| Basketball | 288 | 280 | +8 |
| Beach Volleyball | 96 | 90 | +6 |
| Boxing | 289 | 270 | +19 |
| Canoe Slalom | 82 | 78 | +4 |
| Canoe Sprint | 249 | 236 | +13 |
| Cycling BMX Freestyle | 19 | 19 | 0 |
| Cycling BMX Racing | 48 | 43 | +5 |
| Cycling Mountain Bike | 76 | 74 | +2 |
| Cycling Road | 201 | 190 | +11 |
| Cycling Track | 189 | 208 | -19 |
| Diving | 143 | 133 | +10 |
| Equestrian | 198 | 237 | -39 |
| Fencing | 215 | 249 | -34 |
| Football | 608 | 567 | +41 |
| Golf | 120 | 115 | +5 |
| Handball | 336 | 343 | -7 |
| Hockey | 384 | 406 | -22 |
| Judo | 393 | 373 | +20 |
| Karate | 82 | 77 | +5 |
| Marathon Swimming | 50 | 49 | +1 |
| Modern Pentathlon | 72 | 69 | +3 |
| Rhythmic Gymnastics | 96 | 95 | +1 |
| Rowing | 522 | 496 | +26 |
| Rugby Sevens | 297 | 283 | +14 |
| Sailing | 350 | 336 | +14 |
| Shooting | 356 | 342 | +14 |
| Skateboarding | 80 | 77 | +3 |
| Sport Climbing | 40 | 37 | +3 |
| Surfing | 40 | 38 | +2 |
| Swimming | 779 | 743 | +36 |
| Table Tennis | 172 | 164 | +8 |
| Taekwondo | 130 | 123 | +7 |
| Tennis | 191 | 178 | +13 |
| Trampoline Gymnastics | 32 | 31 | +1 |
| Triathlon | 110 | 106 | +4 |
| Volleyball | 288 | 274 | +14 |
| Water Polo | 268 | 269 | -1 |
| Weightlifting | 197 | 187 | +10 |
| Wrestling | 289 | 279 | +10 |
| Total | 11316 | 11085 | +231 |

## Validation and valid comparisons

`validate_gender_data` returns a report without mutating, trimming or removing any
source records. Missing required columns, repeated column labels, missing/blank
or non-text disciplines, repeated discipline records (including conflicting
aggregates), missing counts, nonnumeric/nonfinite/fractional/boolean counts,
negative counts and invalid arithmetic are errors. Numeric integer-valued floats
are accepted; numeric strings are not silently coerced. Arithmetic is checked
only on otherwise valid counts. Invalid schemas return errors rather than crash.

The optional athlete comparison checks exact discipline-label sets and reports
per-discipline and overall raw-row differences as warnings. Comparison-schema
problems are errors; no attempt is made to derive gender labels from names.
`run_quality_checks` includes the report in EntriesGender.validation while
retaining its raw profile and legacy arithmetic/negative-value summary fields.
Consumers should inspect validation.errors; a zero arithmetic-error count alone
does not imply the schema or count values are valid.

Gender proportions within a discipline and the distribution of recorded entries
across disciplines can be described using this aggregate source. Country-level
gender comparisons, gender labels for individual athletes, unique-person totals
and causal explanations for the mismatch cannot be derived from these files.
No totals are forced to match, no gender assignments are invented, and no gender
rows are deduplicated. All raw data and saved project artifacts remain unchanged.
