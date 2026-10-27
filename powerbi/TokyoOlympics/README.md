# Tokyo Olympics — Power BI report

Open **TokyoOlympics.pbip** in Power BI Desktop. Keep the `.Report` and
`.SemanticModel` folders beside it. The report contains four pages: Overview,
Participation, Country detail and Methodology.

The import model embeds the pinned UTF-8 CSV, so no Azure credentials or absolute
file paths are needed. If opening a source-only checkout, click **Refresh** once
to load the embedded snapshot, then Save. Refresh deliberately reloads this same
snapshot; this is not a live Azure connection. If Desktop offers a TMDL format
upgrade, choosing **Don't upgrade** retains the supplied model format.

Use country and performance-band dropdowns to filter a page. Slicers are local to
each page. Clear both selections to restore all delegations. The country table
supports sorting by column headers. The medal chart keeps the top ten ranks within
the current selection, including ties; the efficiency chart requires at least
20 listed athletes per country.

## Verified data

Desktop was refreshed and the saved model queried with read-only DAX. All 206
country rows reconcile to the source CSV: medal colors and totals, athlete and
team counts, medal efficiency, gold share, medal ranks and top-ten visibility.
Global and India + United States combined totals/ratios also reconcile. Empty
selections return blanks. See `source-validation.json` and `live-dax-evidence.json`.

| Measure | Full snapshot |
| --- | ---: |
| Countries/delegations | 206 |
| Medal countries | 93 |
| Medal awards | 1,080 |
| Listed athletes (distinct-name proxy within country) | 11,071 |
| Composite team entries | 743 |
| Medals per 100 athletes | 9.755216330954747 |
| Gold share | 31.48148148148148% |

Source SHA256: `37495ff232f8aa5140e6f194d851f41c053aa4cf4390f65faaf45e6283956bcb`.
The embedded dataset matches the project's validated local analytics export.
It is **not a Databricks-produced export**: Stage 3 stopped before job submission.
The source's historical coverage and medal accounting are retained, rather than
represented as current official Olympic records. Athlete names are not person IDs;
team medal counts and athlete counts have different grains.

## Release boundary

This is a local Desktop report, not a published Power BI Service dashboard.
Publishing requires a chosen workspace and its authentication/licensing. No
Service publication has been performed. `previews/` contains actual Desktop
captures, not illustrative mockups. `.pbi/` holds a local cache and is ignored by
Git; the embedded source allows a fresh checkout to refresh without it.

The official report-author CLI reports no structural errors. Desktop's saved
visual schema 2.14.0 was unavailable from the public schema endpoint during final
validation, leaving one schema-fetch warning; actual Desktop loading, DAX and
render checks are recorded separately.
