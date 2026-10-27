# Azure completion progress — 2026-10-26

> Latest result — 2026-10-27: runtime/node readiness passed, but Unity Catalog
> rejected storage credential validation because the operator lacks a linked
> Entra object ID. Zero jobs were submitted. See the
> [identity prerequisite](stage3/identity-prerequisite.md) and latest cleanup record.
> The verified local project has been pushed to `feature/olympic-ai-platform`.


**ADF Stage 2 is complete. Databricks Stage 3 is not complete. All newly created
Stage 3 resources have been removed and preservation checks passed.** The local
Power BI report is built, saved and reconciled; no Service publication is claimed.
See [project completion audit](../project-completion.md).

## Stage 1 completed — 2026-10-24

Explicit Stage 1 authorization was received and an exact identity/role/scope/source/
ADF-object preview was displayed before changes. No identity or scope differed
from the reviewed plan.

- Existing ADF MI 2b14c4a6-9415-4738-b6a6-a8b671d97d6f received exactly one
  Storage Blob Data Contributor assignment, only at the existing
  tokyoolympicdatahetram / tokyo-olympic-data container scope.
- Five original source files (461,896 bytes) were created without overwrite under
  staging/218c96338c6c3926d6a3910ceebcf2915e1097f9cccd024b1fa39a9458057685/.
  Each was downloaded again using its ETag and verified by byte length and SHA256.
  These are explicitly manually staged sources, not ADF-ingested outputs.
- Incremental ARM deployment succeeded for ls_tokyo_adls_mi,
  ds_tokyo_staged_binary, ds_tokyo_raw_binary and pl_tokyo_ingest. All four
  definitions were read back and matched the prepared properties.
- ARM ProviderNoRbac validation passed before deployment. Final full local suite:
  **95 tests passed** in 7.528 seconds, including four Stage 1 boundary tests.
  Pinned contracts, dependency consistency and git diff --check passed.
- Post-checks confirmed one exact grant, unchanged existing directory ACLs and
  storage security/network settings, only five staged source files, no output
  files in raw/curated/analytics, no pipeline runs in the checked 24-hour window,
  and no subscription resources beyond the existing storage account and factory.
- Current MTD cost query still reports INR 0.018355477 storage and INR 0 bandwidth.
  Reporting can lag; an isolated Stage 1 bill is not yet available. No pipeline
  execution, data-movement or Databricks/VM compute charges were initiated.

## Stage 2 verified — 2026-10-25

Exactly one authorized manual run of pl_tokyo_ingest completed successfully:
**1a11a954-8e6c-45e9-98b1-fc530f00a6e8**. Azure reports start
2026-10-25T13:51:51.3786548Z, end 2026-10-25T13:53:36.8537534Z,
duration **105.475 seconds**. All five Copy activities and their sequential ForEach
succeeded. No cancellation was necessary. The subsequent resume/verification
performed read-only Azure queries and downloaded only these five output files;
it did not start another run. The execution-window query returned this one run.

- Preflight matched all four deployed definitions, the exact ADF principal and
  existing container-only role, no active runs, no existing raw/adf files, and all
  five staged source hashes. Run parameters were empty. The output dataset uses
  the Azure-generated pipeline RunId, not a caller-supplied reusable destination.
- Five ADF-created files exist under
  raw/adf/1a11a954-8e6c-45e9-98b1-fc530f00a6e8/ in tokyo-olympic-data.
  Exact filenames, sizes and SHA256 match the pinned originals and staged-source
  preflight: Athletes.csv 407406 bytes; Coaches.csv 16494; EntriesGender.csv 1076;
  Medals.csv 2320; Teams.csv 34600. Total **461896 bytes**; no discrepancy found.
- Downloads used ETag conditions into temporary storage. Original staged-file
  ETags, ADF container role and storage network/security settings remain unchanged.
  The Binary sink has no conditional no-overwrite lock against an external writer;
  a unique service-generated run path, unique filenames and zero configured retries
  provided isolation for this run.
- Secure activity input/output settings hide payloads and detailed DIU/billing
  fields. All five Copy statuses/timestamps/IDs are directly observed. File-to-Copy
  attribution is inferred from the verified sequential ForEach order, while each
  file hash is independently verified from storage; payload attribution is not
  claimed as directly observed. Null retryAttempt values are not proof of zero
  internal service retries; the deployed activity policy has retry=0.
- Post-run full suite: **95 tests passed in 7.449 seconds**; dependency check
  found no broken requirements; git diff --check passed. Protected tracked
  implementation, datasets/reports and saved model hashes remain unchanged.
- Post-run subscription MTD cost query: **INR 0.04598372207 Storage; INR 0 Bandwidth**.
  No ADF charge has appeared in that response yet. It is delayed subscription data,
  not a zero-cost run or final isolated bill. The prior **US$0.05–0.10 estimate** and
  **US$0.50 operating allowance** remain estimates/controls, not a hard billing cap.
  Secure activity output prevents reconstructing exact metered DIUs here.

## Stage 3 approved attempts and verified cleanup

The user approved the saved narrow scope: East Asia Premium workspace, one
4-vCPU single-node job, existing ADF raw input, two scoped connector roles,
India–East Asia processing, US$5 total allowance (not a hard cap), and deletion
of only newly created Databricks dependencies. They subsequently approved a
replacement setup, a corrected-identity-check setup, and one final readiness-recovery attempt. These approvals
did not authorize repeated ingestion, subscription upgrades, serverless compute,
manual metastore creation, broader storage grants, job retries or GitHub push.

| Attempt | Actual result | Evidence |
| --- | --- | --- |
| Initial, Oct 25 | Canceled before compute; new resources removed | [cleanup](stage3/execution/cleanup.json) |
| Replacement, Oct 26 | Agent's resource whitelist omitted the service-created managed identity; stopped before compute | [state](stage3/execution-20261026/state.json), [cleanup](stage3/execution-20261026/cleanup.json) |
| Corrected setup, Oct 26 | Workspace ARM deployment succeeded; a Databricks API returned HTTP 400: no associated worker environments; zero job submissions | [state](stage3/execution-20261026-corrected/state.json), [cleanup](stage3/execution-20261026-corrected/cleanup.json) |
| Final readiness-recovery, Oct 26 | Workspace provisioned; one bounded readiness retry occurred, then a second worker-environment error wording escaped the narrow handler; zero job submissions | [state](stage3/execution-20261026-readiness/state.json), [cleanup](stage3/execution-20261026-readiness/cleanup.json) |

The last response is not proof of subscription ineligibility or a permanent
service outage. The corrected-setup controller did not retry this readiness response before its
finally-block teardown. The final recovery attempt retried the first wording,
then stopped on `UnknownWorkerEnvironmentException: Unknown worker environment`
from the node-type API. This second wording was omitted from the agent
controller's retry predicate; it is a controller gap, not an established permanent
entitlement failure. No successful Spark/runtime/storage-access execution,
curated Parquet or analytics manifest exists. No Stage 3 connector role was
applied in the first four attempts because setup stopped before that step. Existing Stage 1 ADF access is
preserved.

Final independent read-only audit at 2026-10-26T15:08:55Z found no new resources,
no Stage 3 outputs, and identical original blob metadata, ADF definitions,
storage settings and inherited container roles. Earlier teardown also verified
all protected local hashes. The new managed group and its NAT/IP/default catalog
storage/connector/identity were removed. The auto-created empty East Asia
Network Watcher was removed; its empty resource-group shell and provider
registration are retained. Existing ADF/ADLS were never deleted.

Actual-cost query at 2026-10-26T15:09:01Z returned INR 4.819334579710466 for
Oct 25: NAT Gateway 4.33512127750002, public IP/Virtual Network 0.481680141944446,
and managed storage 0.00253316026600001. No Oct 26 rows had arrived. This is delayed
reported cost, **not a final bill or proof that total spend stayed under US$5**.

- [Final preservation audit](stage3/final-audit-20261026/verification.json)
- [Final resource inventory](stage3/final-audit-20261026/inventory.json)
- [Delayed actual-cost response](stage3/final-audit-20261026/cost.json)
- [Original Stage 3 scope](stage3/approval-preview.md), now historical proposal
- [Pre-Stage 3 progress snapshot](progress-before-stage3-20261025.md)

## Earlier completion boundary — before the 2026-10-27 attempt

The approved setup attempts are consumed; no background job or workspace remains.
No further attempt was started after the final approval. The remaining readiness
handler has been extended locally and four fake-clock tests now cover the observed
message transition, timeout and non-retry behavior for writes/unrelated errors.
That later fix has NOT been cloud-executed. Service readiness, actual node access
and runtime execution still require verification; repeated workspace creation
is not a completed transformation.
Reuse raw run `1a11a954-8e6c-45e9-98b1-fc530f00a6e8`; never repeat ingestion.
Only an actually successful job, validated output manifest and local/cloud parity
can close Stage 3. No full Azure end-to-end success is claimed.

## Final-attempt cleanup confirmation

At 2026-10-26T15:31:13.622761+00:00, cleanup again verified no new resources and unchanged original blobs, ADF, storage settings, roles and all protected local hashes. The final attempt created no job, connector grants or Stage 3 outputs. All four attempts are retained as evidence; no successful run is inferred from workspace creation.

## Latest attempt and cleanup — 2026-10-27

The user's instruction to continue, finish and push authorized the next prepared
bounded attempt. Four read-only readiness waits resolved the worker-environment
startup responses; the exact 17.3 runtime and four-core D4ds_v4 node were found.
The new Access Connector and exactly two approved scoped role assignments were
created. Unity Catalog rejected credential creation because the validating
operator was not linked to an Entra object ID. The job was never created or run;
no new data output exists. No broader grants or validation bypass were attempted.

Cleanup at **2026-10-27T09:33:14.264425+00:00** passed: no new resources remained; original
blobs, ADF definitions, storage settings, roles and all 60 protected local files
were unchanged. Both new role assignments and the connector were removed along
with the workspace and managed dependencies.

- [Final state and exact service error](stage3/execution-20261027-worker-ready/state.json)
- [Verified runtime/node](stage3/execution-20261027-worker-ready/runtime-node-check.json)
- [Cleanup and preservation](stage3/execution-20261027-worker-ready/cleanup.json)
- [Identity prerequisite and official guidance](stage3/identity-prerequisite.md)
- [Current delayed cost query](stage3/budget-check-20261027.json): **INR 15.346172113043849**
  for Oct 25–26 as reported at 09:18:23 UTC Oct 27. Oct 27/final charges are pending;
  the US$5 allowance is not a guaranteed billing cap.

The verified local release is pushed to `feature/olympic-ai-platform`. Databricks
cloud transformation/parity and Power BI Service publication remain incomplete.
