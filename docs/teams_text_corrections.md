# Teams.csv verified text corrections

The raw `data/Teams.csv` is preserved. `load_csv` still returns raw values.
`src/quality/team_text.py` applies exact, column-specific replacements to a copy
before both country-table builders aggregate team data. The existing
`normalize_country_key` whitespace and country-alias handling remains intact.
No generic encoding repair or guessed character substitution is performed.

## Inventory and verified mappings

Verified on 2026-10-17. The raw file contains 37 U+FFFD replacement characters in
19 cells across 18 rows (743 total rows). Discipline has no affected values.
CSV line numbers below include the header; each record occupies one line.

| Column | Raw value | Corrected value | Cells | CSV lines | Evidence |
| --- | --- | --- | ---: | --- | --- |
| Country | `C�te d'Ivoire` | `Côte d'Ivoire` | 1 | 414 | FIFA squad list, p. 4; repository Athletes/Medals country spelling |
| TeamName | `C�te d�Ivoire` | `Côte d'Ivoire` | 1 | 414 | FIFA squad list, p. 4 |
| Event | `Men's �p�e Team` | `Men's Épée Team` | 9 | 356, 363, 375, 381, 387, 391, 397, 399, 400 | Olympic schedule, p. 12; FIE men's team event |
| Event | `Women's �p�e Team` | `Women's Épée Team` | 8 | 357, 362, 370, 378, 386, 389, 394, 403 | Olympic schedule, p. 12; FIE women's team event |

Affected men's fencing teams: China, France, Italy, Japan, Republic of Korea,
ROC, Switzerland, Ukraine, United States.
Affected women's fencing teams: China, Estonia, Hong Kong, China (one team
label containing a comma), Italy, Poland, Republic of Korea, ROC, United States.
The other affected row is the Côte d'Ivoire men's Football team.

## Evidence and canonical spelling

- [FIFA official Tokyo 2020 men's squad list](https://fdp.fifa.org/assetspublic/ce4/pdf/SquadLists-English.pdf),
  page 4: identifies CIV and its national football squad. The heading uses
  `Côte D'Ivoire`; this project retains `Côte d'Ivoire` to match its existing
  Athletes/Medals country keys. This verifies the team identity and apostrophe.
- [Tokyo 2020 competition schedule hosted by the Slovak Olympic committee](https://www.olympic.sk/sites/default/files/field_media_file/2019-09/OS_Tokio_2020_-_Competition_Schedule_Event_Line-up_for_Each_Session_April_2019.pdf),
  page 12: identifies both men's and women's Epée Team events. This is the
  April 2019 pre-postponement schedule, used for event names, not actual dates.
- [FIE men's Tokyo team event](https://fie.org/tournaments/2021/248/event/248/tableau)
  and [FIE women's Tokyo team event](https://fie.org/tournaments/2021/247/event/247/tableau)
  corroborate the event identities in the 2021 competition.
- [Olympic Council of Asia account](https://oca.asia/news/4542-korean-fencing-coach-chang-earns-ioc-coaches-lifetime-achievement-award-2023.html)
  uses the accented weapon spelling `épée` for the Korean women's Tokyo team.
  The correction layer uses `Épée` in title case and keeps the dataset's ASCII
  possessive apostrophe and event word order. This is canonical display
  formatting, not a claim that all sources use identical typography.

## Limits and invariants

All observed replacement-character values have verified mappings. Unknown
values, including future corruptions, remain unchanged for investigation.
Neither Discipline nor any unaffected text is edited. Repairs preserve row
order and count. Both generated country tables retain 206 countries and medal
totals of 340 gold, 338 silver, 402 bronze, 1,080 total. Existing model and
dashboard artifacts are not regenerated on disk.
