# Azure completion progress

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

## Stage 3 pre-deployment prepared — 2026-10-25

**No Stage 3 deployment or execution is approved.** The single current decision
is [the Stage 3 exact-change/cost preview](stage3/approval-preview.md); it replaces
the remaining steps in the older consolidated proposal and reuses the existing
verified raw run. It proposes no ADF ingestion or new ADF definitions/permissions.

- Current read-only checks reconfirmed the Students subscription, allowed East
  Asia region, 6 free regional/4 DDSv4-family vCPUs, unrestricted D4ds_v4 listing,
  two existing top-level resources, US$100 reported credit, no budget, and delayed
  MTD Storage INR0.04598372207/Bandwidth INR0. Live eligibility/capacity is unproven.
- Both East Asia ARM templates passed ProviderNoRbac validation. The optional
  storage-region Access Connector check failed LocationNotAvailableForResourceType;
  retain the original East Asia connector. Microsoft.Network remains NotRegistered.
- The new connector needs the documented Storage Blob Delegator action at the
  existing storage account in addition to container-scoped Blob Data Contributor.
  This is an explicit proposed permission difference; neither role was granted.
  The new connector principal GUID cannot exist before approved creation.
- Prepared one unsubmitted, single-node/zero-worker dedicated Jobs configuration,
  no retry/schedule/queue or new ingestion. Current-operator invocation avoids
  additional ADF workspace grants. Proposed output UUID is
  c3c77b21-7385-4f93-91bd-e1d8ea1984d4; both output prefixes were empty when checked.
- Pinned source/reference/code checks, shared quality gates and Python3.12 grammar
  parsing passed. All five existing raw file ETags/sizes still match Stage 2.
  A temporary 27-file code/contract/reference bundle (55885 bytes) was allowlisted
  and hashed; it contains no raw copies, model binaries or credentials.
- No PySpark is installed locally, and no Spark/Databricks execution or runtime
  compatibility pass is claimed. Documented 17.3 LTS baseline has Python3.12.3,
  pandas2.2.3 and Spark4.0.0, differing from local Python3.14/pandas3.0.6. Cloud
  built-ins and UC access must pass fail-fast validation in the one approved job.
- Full suite **95 passed in 7.371 seconds**; dependency/contract/diff checks passed.
  Source, tests, datasets, model bytes and all Stage 1/2 evidence remain unchanged.
- One bounded pricing batch confirmed public-IP/disk/example bandwidth meters;
  NAT tariff and actual node DBUs remain unverified. Estimate US$1–3; proposed
  US$5 allowance is not a cap. The new managed NAT/IP/storage/disks require
  same-session teardown even when compute is stopped. No further pricing search
  is planned. Exact rate qualifications and rollback are in the approval preview.

## Stop boundary and next blocker

**Stage 2 is complete; no further run is authorized.** No Databricks workspace,
Access Connector, NAT, VM or cluster was created. No RBAC/ACL/network/security
change, dataset replacement, commit or push occurred in Stage 2. Cancellation and
billing limits are not guaranteed; the successful run ended before the timeout.

The remaining blocker is a separately approved Databricks transformation phase:
East Asia workspace and required managed infrastructure, Access Connector,
explicit narrow identity/Unity Catalog permissions, then a separately bounded
single-node job and cloud/local parity verification. Reuse this verified raw run;
**do not rerun ingestion**. The [Stage 3 preview](stage3/approval-preview.md) is the current unapproved
decision; the older broader plan is retained only as historical context. Workspace eligibility/capacity, runtime/Unity Catalog access
and networking/DBU costs remain unresolved until that approved phase. Prepared
Spark code has not been cloud-executed; no curated/analytics cloud parity or full
end-to-end resume claim is asserted.

## Verified subscription context retained

Azure CLI 2.91.0, device-code authenticated. Azure for Students subscription
b52df7c6-044d-4326-92c8-496670def7c1 is Enabled, spending limit On. The linked
billing profile reported USD 100 current credit; expiry/billing lag unresolved.
No Azure budget is configured. Existing ADF/storage are in indiasouthcentral;
resource group metadata is centralindia. Central India Databricks validation was
policy-denied; East Asia validation passed. East Asia has 6 total vCPUs, 4 DDSv4
family vCPUs, and no returned Standard_D4ds_v4 SKU restriction. Actual Databricks
runtime/node availability, live capacity and Unity Catalog are still unverified.
Only Microsoft.Compute and Microsoft.Databricks provider registration was approved
in the earlier phase; both were registered. No further registration in Stage 1.

## Preserved local work

Branch feature/olympic-ai-platform; committed checkpoint
eb30e6fbf31afe59d74b67973fd230df43a59c23. Existing Azure preparation is uncommitted.
The source snapshot version remains
218c96338c6c3926d6a3910ceebcf2915e1097f9cccd024b1fa39a9458057685.
Local datasets, verified analytics/dashboard exports, ML source, model binaries
and regression/classification reports are protected; no retraining or regeneration.
Prepared Spark/job code is not claimed cloud-executed. No credential from chat
was used, stored or passed to a command. No further pricing/web investigation.

## Evidence

- [Stage 3 single approval preview](stage3/approval-preview.md)
- [Stage 3 read-only inventory and ARM validation](stage3/predeployment-inventory.json)
- [Stage 3 local readiness checks](stage3/local-predeployment-validation.json)

- [Stage 2 verification and limitations](stage2/README.md)
- [Stage 2 final run journal](stage2/run.json)
- [Stage 2 file hashes, activity results and cost query](stage2/verification.json)
- [Stage 2 local validation](stage2/local-validation.json)

- [Stage 1 authorization and verification method](stage1/README.md)
- [Stage 1 deployment journal](stage1/deployment-20261024T140732Z.json)
- [Stage 1 post-deployment verification](stage1/post-deployment-verification.json)
- [ARM validation](stage1/arm-validation.json)
- [Earlier read-only inventory](inventory-2026-10-24.json)
- [Captured public list rates and gaps](retail-price-reference-2026-10-24.json)
- [Unapproved broader Databricks plan](deployment-approval.md)
