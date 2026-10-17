# Athlete-name cleaning and duplicate handling

`clean_athlete_names` in `src/quality/data_quality.py` strips surrounding Unicode
whitespace from PersonName on a deep copy. It preserves internal whitespace,
case, spelling, accents, missing values, other columns and the source index.
Both builders apply this function, normalize country keys, then remove only
exact full-row duplicates. Names matching across disciplines or countries do not
justify record deletion. The raw CSV and raw quality profiling remain unchanged.

Actual findings in `data/Athletes.csv` (CSV lines include the header):

- Lines 255 and 256 both contain `ALI Mohamed`, Bahrain, Handball. One redundant
  row is removed in memory. Without source IDs, identical rows cannot prove
  that two records describe the same real person; this is exact-record deduplication.
- Line 3313 contains `GIRAUD Aurelien `, France, Skateboarding, with one trailing
  ASCII space. Its derived name becomes `GIRAUD Aurelien`. No other names have
  surrounding whitespace. Trimming creates no additional exact duplicates.

There are 11,085 raw rows and 11,084 distinct full records, before and after
trimming. Thirteen country/name groups span multiple disciplines (26 retained
records); they are preserved rather than resolved into assumed identities.
The existing `athlete_count` remains a distinct normalized-name count per country,
a proxy rather than a verified count of unique people. Its sum is 11,071 before
and after cleaning. This step does not redesign that feature or its KPI uses.

In-memory feature/analytics tables retain 206 country rows and 340 gold,
338 silver, 402 bronze and 1,080 total medals. Saved country/model/dashboard
artifacts remain untouched. Name collisions, coach issues and the difference
between athlete rows and gender entry totals remain outside this step.
