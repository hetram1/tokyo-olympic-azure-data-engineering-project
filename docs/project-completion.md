# Project completion audit — 2026-10-26

> Latest result — 2026-10-27: runtime/node readiness passed, but Unity Catalog
> rejected storage credential validation because the operator lacks a linked
> Entra object ID. Zero jobs were submitted. See the
> [identity prerequisite](azure/stage3/identity-prerequisite.md) and latest cleanup record.
> The verified local project has been pushed to `main`.


| Area | Verified status |
| --- | --- |
| Local quality, analytics and ML | Completed earlier; preserved, no retraining |
| ADF/ADLS Stage 1 and Stage 2 | Deployed; one successful ingestion, five SHA256 matches |
| Databricks PySpark execution | Incomplete: zero job submissions; Unity Catalog rejected the missing Entra identity association |
| Temporary Azure resources | All new resources removed; original resources/data/access preserved |
| Power BI Desktop | Four-page native PBIP saved; all 206 country rows and DAX aggregates reconciled |
| Power BI Service dashboard | Not published |
| GitHub | Verified release pushed to `main` on the default branch |

Open [Power BI instructions](../powerbi/TokyoOlympics/README.md) and
[actual overview capture](../powerbi/TokyoOlympics/previews/Overview.png).
The portable model embeds the pinned CSV, avoiding credentials and machine paths.
Live read-only DAX checks cover global totals, every country, India + USA combined
selection, empty selection and top-ten ranking/visibility. The final official
schema validator has no errors and one unavailable-schema warning for Desktop's
visual-container schema 2.14.0; real Desktop render and DAX checks passed.

The report uses **local analytics**, not a cloud transformation result. It must
not be presented as proof that the whole Azure pipeline ran end to end.
[Azure progress](azure/progress.md) records setup attempts, cleanup and delayed
costs. INR 15.35 is reported for Oct 25–26; Oct 27 and final charges are pending.

## Reproducible checks

```bash
.venv/bin/python -B -m unittest discover -s tests -v
.venv/bin/python -B -m src.azure.contracts
.venv/bin/python -B scripts/verify_powerbi_snapshot.py
.venv/bin/python -m pip check
git diff --check
```

The Power BI command checks saved evidence, not a fresh live connection. To
refresh the report in Desktop, open the PBIP, Refresh and Save. All Azure creation
and execution remain separate from these offline commands. Tests alone cannot
close the Databricks execution gap.

## Historical execution outcome — 2026-10-26

The fourth and final approved setup provisioned the workspace. A read-only
node-type readiness response used a different `UnknownWorkerEnvironmentException`
wording than the retry handler recognized. The controller stopped and completed
cleanup before job creation. This agent-side handling gap is recorded explicitly;
it does not prove that Azure for Students cannot run the job. No further attempt
was made after the final approval. Stage 3 remains incomplete.

Validation: 95 repository tests passed in 10.261 seconds, pinned contracts passed,
captured live Power BI DAX reconciliation passed, pip found no broken requirements,
and git diff --check passed. All 60 protected file hashes are unchanged. The
later readiness-handler correction passed four isolated fake-clock tests but has
not been exercised in Azure. [Validation journal](project-validation-20261026.json).

## Latest handover — 2026-10-27

The release is now pushed on `main` (including the prior
three local analytics/ML commits). All 95 tests passed again in 7.561 seconds;
contracts, Power BI snapshot reconciliation, dependency and staged diff checks
passed. The prepared readiness helper passed five tests. Power BI text files
were normalized to LF for Git without changing the embedded source CSV.

The fifth setup passed runtime/node readiness and applied only the two approved
connector roles, but Unity Catalog returned
`UC_STORAGE_CREDENTIAL_PRINCIPAL_MISSING_AZURE_OBJECT_ID`. No job was submitted.
All new resources and both roles were removed, with preservation checks passing.
The missing Entra identity association must be resolved through supported identity
management before cloud execution can be completed. [Prerequisite](azure/stage3/identity-prerequisite.md).

Reported historical setup cost is now INR 15.35 for Oct 25–26. New/final billing
is delayed; no hard-cap or final-spend claim is made. This release is suitable for
demonstrating verified work, but must not be described as a fully executed Azure
pipeline. See the [interview guide](interview-guide.md).
