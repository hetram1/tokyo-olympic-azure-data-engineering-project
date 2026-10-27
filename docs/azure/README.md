# Azure pipeline: verified ingestion; Stage 3 attempted and cleaned up

See [current progress](progress.md) for approvals, execution evidence, cleanup,
delayed costs and the remaining Databricks blocker. ADF Stage 2 succeeded; all
five raw hashes match. Four approved workspace setup attempts ended before any
Databricks job submission; all new resources were removed. The original plan
below describes architecture, not proof of a completed cloud transformation.

The [native Power BI report](../../powerbi/TokyoOlympics/README.md) is complete
locally using the validated local CSV. It has no successful cloud-output lineage
and has not been published to Power BI Service.

## Secure setup and read-only inventory

Azure CLI was missing on Ubuntu 26.04. The official Microsoft installer was
downloaded to `/tmp/tokyo-azure-cli-install.sh`, inspected, and approved; sudo
requires interactive authentication. In your own terminal only:

```bash
sudo bash /tmp/tokyo-azure-cli-install.sh
az version
az login --use-device-code --output none
```

Authenticate only on Microsoft's device-login page, confirming your own tenant and
account. Never send passwords, access tokens, device codes or CLI credential-cache
files through chat or commit them. The agent can start the device-code flow once
CLI is installed; no password is needed by the agent. Azure CLI stores its login
cache outside the repository. No credential from chat is used by this project.

The agent will list subscription names/IDs/state, resolve the explicitly selected
Azure for Students subscription, and pass its UUID to the read-only inventory:

```bash
.venv/bin/python -B -m src.azure.inventory --subscription-id SUBSCRIPTION_UUID --output /tmp/tokyo-azure-inventory.json
```

The output path must be new. This script disables automatic CLI extension installs,
uses Entra authentication for storage (never account keys), and queries resource
metadata, ADF definitions, inherited container-scope ADF roles, path ACLs, regional
compute quota, provider registration, existing workspaces, month-to-date actual
cost and budgets. The cost-management POST is a read-only query, not a deployment.
A denied/unsupported query is recorded as unavailable, never as zero cost or no
resources. Student credit balance/expiry must be established separately; budgets
and cost totals do not show remaining promotional credit. Provider listing and VM
quota do not alone prove Databricks offer eligibility. Actual workspace creation
is a separate approval-gated operation. An earlier inventory is recorded in inventory-2026-10-24.json; current execution
status is recorded in progress.md.

## Offline reproducible assets

- `infra/azure/environment.json`: target names and historical Stage 1 authorization snapshot;
  current execution and cleanup status is in progress.md.
- `infra/azure/data_contract.json`: five original-file SHA256s, exact headers,
  encodings, sizes/row counts, reference output schemas/hashes, code bundle hashes.
- `infra/azure/adf_ingestion.arm.json`: one managed-identity ADLS linked service,
  two binary datasets, one sequential five-file ingestion pipeline. No trigger,
  role assignment, storage account creation or compute creation.
- `infra/azure/adf_orchestration.arm.json`: separate optional managed-identity
  Databricks linked service and parent pipeline; invokes one approved Databricks job whose definition controls ephemeral
  compute. The linked service contains no compute provisioning settings. Running
  the job is billable; the job definition must be checked before invocation.
- `databricks/tokyo_transform.py`: parameterized notebook source using governed
  ADLS paths without DBFS mounts or embedded credentials.
- `src/azure/contracts.py`: offline source/quality checks and downloaded-output
  verification; never trains models or overwrites reference datasets.
- `src/azure/spark_transform.py`: Spark aggregations with shared Python quality
  gates for this bounded dataset, then small country CSVs for analytics/Power BI.
- `src/azure/inventory.py`: explicit read-only CLI inventory; no login/deployment.

Run local validations with the existing environment:

```bash
.venv/bin/python -B -m src.azure.contracts
.venv/bin/python -B -m unittest discover -s tests -v
git diff --check
```

`python -B -m src.azure.adf` deterministically renders the two local templates; it
never deploys. Contract repinning is deliberately not automatic: source/reference
or code changes require review. No cloud SDK or PySpark is installed in the local
environment. Notebook syntax, contracts and template invariants can be checked
locally; Spark execution remains unverified. ARM validation and workspace deployment results are recorded in progress.md.

## Source, ingestion and publication contract

Manual staging is explicitly labeled: an approved operator uploads only the five
unchanged files into `staging/<dataset_version>/`. These are **not ADF outputs**.
ADF `pl_tokyo_ingest` copies bytes into `raw/adf/<ingestion-pipeline-run-id>/` using
case-correct original filenames. A new run ID prevents overwrite of earlier raw
snapshots. Raw files must hash-identically to the pinned sources before any
transformation. Byte-preserving Binary Copy prevents source-encoding alteration.
ADF sequential copying uses a 10-minute per-file timeout, no automatic retries,
two configured DIUs and one parallel copy; actual runtime/billing must be measured.

The parent `pl_tokyo_end_to_end` waits for all copies, then passes the ingestion
child run ID and its own output run ID to the Databricks notebook. Notebook widgets
are repo_path, storage_account, container, raw_run_id and output_run_id. UUID/name
validation limits path misuse. The repo bundle must be deployed to an approved
workspace filesystem location with the pinned `src/`, notebook, contract and the
three small reference CSVs. Do not upload model binaries, `.git`, environments,
secrets or raw athlete records into the code bundle. Original raw records go only
to the approved restricted staging location.

The notebook verifies code and raw-byte hashes, parses explicit encodings/schema
contracts on the bounded driver input, and calls the existing enforcing gates.
This reuses name trimming, exact duplicates, verified Teams repairs, country keys,
coach policy and gender/medal/join checks without inventing new cleaning rules.
Spark then performs distinct-athlete counts, composite team counts, medal joins,
KPIs and fixed medal classes. This is deliberately a small-data demonstration;
it is not a claim that collecting these inputs onto the driver scales arbitrarily.

Cleaned five-dataset Parquet outputs go under `curated/adf/<output-run-id>/`. Three
small country-level CSVs go under `analytics/adf/<output-run-id>/` with stable filenames:
country_features.csv, country_analytics.csv and olympic_country_dashboard.csv.
The dashboard exporter is the existing shared local function. Output columns,
country keys and numeric values must match the pinned local references (float
rtol/atol 1e-12). All exports are reread for checksum/value verification; only then
is manifest.json published with status=validated. No existing output run can be
overwritten. Failed partial run directories have no success manifest and must not
be consumed; any cleanup requires separate authorization. Curated Parquet rows
are the already validated prepared frames; the notebook rereads them and checks
schemas, counts and bidirectional row differences before publishing success.

Download an approved successful run into a NEW local temporary directory, then:

```bash
.venv/bin/python -B -m src.azure.contracts --verify-export /tmp/tokyo-downloaded-run
```

This verifies manifest, file checksums and key/value parity without replacing local
models/, data/, dashboards/ or reports/. Power BI can consume the validated CSV
through an authenticated approved connection/download. The supplied PBIP currently embeds the verified local CSV; it is not a Databricks export or published Service dashboard. ML artifacts are not regenerated by any cloud command.

## Least-privilege permissions to resolve after inventory

Preferred ADF access is path ACLs: traverse-only on the container root, read/execute
on staging/<dataset_version> and its files, traverse-only on raw/, and write/execute plus appropriate default
ACLs only on a new raw/adf/ directory. Existing raw/athletes, raw/coaches and other
legacy raw directories do not need writable ACLs. No write access to curated/ or analytics/ is needed by ADF. Snapshot
existing ACLs/defaults/masks before any edits. Existing inherited RBAC/deny entries
must be checked because they can alter effective rights; do not grant blanket
subscription or storage-account Contributor just to make a copy work.

Databricks uses an Access Connector managed identity and Unity Catalog external
locations with raw read access and curated/analytics write access. Precise cloud
roles/ACLs depend on verified workspace setup. Credential validation may require
additional scope; evaluate narrow separate containers or conditional access before
requesting broad existing-container rights. ADF-to-Databricks execution also needs
the factory identity registered/authorized in that workspace with only the notebook
and approved compute permissions. It is not the same identity as the storage
Access Connector. Stage 1 granted the recorded container-scoped ADF role; Stage 3 stopped before its new connector grants. No ACL changes were made.

## Cost and deployment approval

Lowest-cost candidate: reuse this ADF/storage, manually trigger exactly one batch,
avoid Mapping Data Flows, schedules, streaming, SQL warehouses and always-on
clusters. Prefer suitable already-owned Databricks compute only if its continued
use and cost are explicitly approved; otherwise price the smallest eligible job
compute/workspace offering after inventory. Student availability is not assumed.
Timeouts do not by themselves stop an existing cluster or cap Azure spend.

Before any deployment/run, prepare one consolidated approval containing:

1. Verified subscription/region and all affected resource IDs.
2. Exactly which linked services, datasets and pipelines will be added; export
   backups first if any names already exist, and do not replace unrelated objects.
3. Exact named-principal role/ACL changes and original ACLs/masks for rollback.
4. Exact source staging/upload paths and notebook/code bundle paths.
5. Whether a workspace/Access Connector/compute needs creation, approved SKU,
   quota, runtime, worker count and termination policy.
6. Region-specific prices, estimated ADF activity/DIU time, Databricks VM/DBU or
   serverless charges, storage/transactions, logging and egress. Define a monetary
   approval ceiling and maximum one-run allowance; no fabricated zero-cost promise.
7. Rollback: stop/cancel only approved runs, terminate only newly approved compute,
   restore changed ACLs/definitions, remove only exact new role assignments after
   authorization, and retain run-specific data/evidence unless deletion is approved.

These approval requirements describe future changes. Completed Stage 1/2 actions and the approved Stage 3 setup attempts are recorded in progress.md. ARM template syntax
and local tests are not proof of service acceptance. Later non-billable ARM
validation/what-if should precede any approved deployment. No actual cloud feature
is to be described as verified until ADF activity and Databricks job evidence,
source/output manifests, parity and billed-cost checks have been collected.

## Official references

- [Azure CLI Ubuntu installation](https://learn.microsoft.com/en-us/cli/azure/install-azure-cli-linux?pivots=apt)
- [ADF ADLS Gen2 connector and managed identity](https://learn.microsoft.com/en-us/azure/data-factory/connector-azure-data-lake-storage)
- [ADF Binary Copy](https://learn.microsoft.com/en-us/azure/data-factory/format-binary)
- [ADF Databricks linked services](https://learn.microsoft.com/en-us/azure/data-factory/compute-linked-services)
- [Databricks managed identities and Unity Catalog](https://learn.microsoft.com/en-us/azure/databricks/getting-started/connect-to-azure-storage)
- [Cost Management read-only query API](https://learn.microsoft.com/en-us/rest/api/cost-management/query/usage?view=rest-cost-management-2025-03-01)

## Current deployment decision

The saved Stage 3 scope was approved and attempted; it is no longer awaiting its
original approval. All allowed setup attempts have ended and cleanup is verified.
A new billable setup is outside that exhausted attempt allowance. See
[progress](progress.md) for the exact failure and next-step boundary. Do not run
the optional parent pipeline: it would ingest again, contrary to the user's scope.
