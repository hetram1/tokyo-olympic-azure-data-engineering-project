# Suggested change title

Add verified Azure ingestion and a portable Tokyo Olympics Power BI report

# Review description

The project now includes pinned Azure data contracts and ADF deployment/run
evidence, plus a native four-page Power BI report backed by the validated local
country snapshot. The single ADF ingestion run produced five CSVs whose names,
byte lengths and SHA256 hashes match the pinned originals. Power BI imports its
embedded CSV without Azure credentials or machine-specific paths; live Desktop
DAX reconciled every country, totals, filtered aggregates and medal rankings.

Databricks preparation and failed setup evidence are included with explicit
limits: no job was submitted, no cloud analytics output is verified, and all
temporary infrastructure was removed. Documentation distinguishes local and ADF
success from the unfinished cloud transformation. Existing data and ML artifacts
were preserved.

Validation: 95 tests passed; pinned contracts, Power BI evidence reconciliation,
dependency consistency and diff checks passed. All 60 protected local hashes
remain unchanged. Actual Desktop renders were inspected. The report-author CLI
reported zero errors and one unavailable-schema warning for Desktop's saved
visualContainer 2.14.0 schema.

The Power BI report has not been published to Service. Azure billing is delayed;
the reported setup charges are not a final bill. The project must not be described
as a successfully executed end-to-end Azure pipeline until Stage 3 completes.

# Local handover

- Branch: `main`
- Native report: `powerbi/TokyoOlympics/TokyoOlympics.pbip`
- Report instructions and validation: `powerbi/TokyoOlympics/README.md`
- Completion audit: `docs/project-completion.md`
- Azure attempts and cleanup: `docs/azure/progress.md`
- Validation journal: `docs/project-validation-20261027.json`

The verified release is committed and pushed to `main`.
The latest execution evidence records successful
runtime readiness, blocked credential validation due to missing Entra identity
association, zero job submissions and verified cleanup. No Service publication.
