# Country-level team counting

Both country-table builders call `aggregate_team_counts` after the existing
verified Teams text corrections and country-key normalization.

- `team_count`: distinct `(Country, Discipline, Event, TeamName)` entries.
- `team_event_count`: distinct `(Country, Discipline, Event)` combinations.
- `team_discipline_count`: distinct disciplines per country, unchanged.

Inspection of the 743 raw rows and the corrected/normalized table found no exact
duplicates, no missing identity fields and no duplicate four-column identities.
There are 12 additional entries beyond the 731 country/discipline/event keys:
these are different beach volleyball pairs representing the same country/event.
They count as separate teams but a single event per country. The helper explicitly
deduplicates composite entries, so repeated records do not inflate counts.
Missing identity fields raise an error rather than silently undercounting.

Team names are reused across disciplines: 51 country/team-name groups span more
than one discipline. Generic event labels such as Men and Women also recur across
sports. Neither TeamName nor Event alone identifies an entry or sporting event.
These definitions count entries represented in this source, not unique rosters,
athletes, matches or the complete set of individual Olympic events.

| Country | Old teams | New teams | Old events | New events |
| --- | ---: | ---: | ---: | ---: |
| United States of America | 5 | 47 | 31 | 45 |
| Japan | 4 | 48 | 28 | 48 |
| People's Republic of China | 4 | 33 | 21 | 32 |
| Great Britain | 1 | 28 | 23 | 28 |
| Côte d'Ivoire | 1 | 1 | 1 | 1 |

Both country tables retain 206 rows and medal totals of 340 gold, 338 silver,
402 bronze and 1,080 total. Validation runs only in memory; saved artifacts remain
unchanged and therefore still contain older values.

Step 8 removes `medals_per_team_event` from newly built analytics and dashboard
exports. Total country medals include individual medals, whereas the denominator
contains only team-event participation. Their ratio cannot establish team-event
performance, and assigning zero to countries without team entries fabricates an
efficiency score. `team_event_count` remains a participation coverage feature.

None of the five source datasets provides team-event medal outcomes: Medals.csv
has country aggregates without discipline/event/team identifiers; Teams.csv has
entries without results; Athletes.csv and Coaches.csv have no medal outcomes;
EntriesGender.csv contains discipline-level entry counts. Joining these sources
cannot recover a team-specific medal numerator. No replacement ratio is invented.

The analytics schema decreases from 15 to 14 columns; the dashboard export schema
decreases from 17 to 16. All other columns and KPI formulas remain unchanged.
`prepare_powerbi_dataset` supports in-memory preparation; the existing file export
entry point still reads and writes the same paths when explicitly run. It accepts
the revised analytics schema and drops the retired column if given an older CSV.
It does not otherwise migrate stale country counts or team counts in that CSV.

Existing `models/country_analytics.csv` and
`dashboards/olympic_country_dashboard.csv` still contain the old KPI and older
country/team counts; they were deliberately not overwritten. Neither
`models/country_features.csv` nor the ML scripts consume this KPI. Future Power BI
reports should use the revised schema, remove references to the retired field,
and present `team_event_count` as coverage rather than medal efficiency. No Power
BI report files currently exist in the repository. Correct source-derived
analytics must be regenerated before producing a refreshed dashboard dataset.
