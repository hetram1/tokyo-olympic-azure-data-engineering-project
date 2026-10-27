# Stage 3 deployment readiness and teardown detail

**PRE-DEPLOYMENT ONLY — NOT APPROVED.** Supporting technical detail for the
single [approval preview](approval-preview.md); this document is not a separate
approval request.
No Stage 3 resource, identity grant, compute or pipeline execution has occurred.

## Verified starting point — 2026-10-25

Azure for Students **b52df7c6-044d-4326-92c8-496670def7c1** is Enabled, spending
limit On; reported credit is US$100 with no pending eligible charges (billing can
lag; expiry unavailable). Only the existing ADF and storage resources are listed.
East Asia is policy-allowed; 6 regional vCPUs and 4 DDSv4-family vCPUs are unused.
Standard_D4ds_v4 has no returned SKU restriction. East Asia Premium workspace and
Access Connector ProviderNoRbac ARM validations succeeded; entitlement, live
capacity and Databricks runtime availability are not guaranteed by those checks.
Microsoft.Network is still NotRegistered. No budget exists; none is proposed here.

## Exact changes requested

| Item | Proposed change |
| --- | --- |
| Existing group | Reuse rg-tokyo-olympics; retain existing ADF, storage, roles and all data |
| Provider | Register only Microsoft.Network for the new workspace network; Compute and Databricks are already registered |
| Workspace | dbw-tokyo-olympics-hetram-2026, **eastasia**, Premium, existing workspace ARM template, secure connectivity / enableNoPublicIp=true; authenticated public workspace endpoint |
| Managed group | New rg-tokyo-olympics-databricks-managed, containing only service-managed workspace dependencies: storage, one VNet/two subnets, NSG(s), **one NAT gateway and its egress IPv4 public-IP resource**, plus the one job's VM/NIC/disks while running. Generated resource names/IDs and disk sizes are unavailable before provisioning; inventory them before compute and stop on unexpected footprint |
| Connector | ac-tokyo-olympics-hetram-2026, **eastasia**, SystemAssigned identity; inspect its newly generated principalId before binding any role |
| Azure roles | **Only that new connector principal:** Storage Blob Data Contributor at the existing container, plus Storage Blob Delegator at the existing storage account, as detailed below |
| Unity Catalog | New sc_tokyo_stage3 credential and three el_tokyo_stage3_* external locations; bind only to the new workspace. Raw is read-only; curated/analytics permit file read/write only at the proposed run prefixes. No file events, queues, Event Grid, metastore creation/reassignment or grants on existing UC objects |
| Code/job | Upload only the 27-file allowlisted bundle (55,885-byte ZIP; manifest retained) and import the exact pinned notebook. Create **one** tokyo-transform-verify job; invoke exactly once as the current authenticated operator, with no new service principal or ADF workspace role |

New resource IDs use this exact prefix:
`/subscriptions/b52df7c6-044d-4326-92c8-496670def7c1/resourceGroups/rg-tokyo-olympics/providers/Microsoft.Databricks/`,
followed by `workspaces/dbw-tokyo-olympics-hetram-2026` or
`accessConnectors/ac-tokyo-olympics-hetram-2026`. The connector principal GUID,
workspace ID/URL and job ID cannot be known until creation; resolve only from these
exact resources, record them, and stop if identity or scope differs. No existing
identity receives a new grant. Service-generated workspace storage identities or
assignments, if present, must be inventoried and confined to its new dependencies;
do not grant them access to existing project storage.

Storage account scope:
`/subscriptions/b52df7c6-044d-4326-92c8-496670def7c1/resourceGroups/rg-tokyo-olympics/providers/Microsoft.Storage/storageAccounts/tokyoolympicdatahetram`.
Container scope appends `/blobServices/default/containers/tokyo-olympic-data`.
Role IDs: Contributor **ba92f5b4-2d11-453d-a403-e96b0029c9fe**;
Delegator **db58b8e5-c6ad-4a2a-8342-4190687cbf4a**. Contributor permits data
read/write/delete throughout the container; UC prefixes and application rules
narrow use, not that Azure role. Delegator has only generateUserDelegationKey,
with no dataActions. **This storage-account-scoped Delegator grant is additional
to the old container-only plan and requires this approval.** No subscription/RG
role grant or existing ACL/firewall/private endpoint change is included.

The operator already has effective wildcard management actions at the project RG;
recorded subscription permissions are in the preflight evidence. Minimum operations
are workspace/connector deployment, generated-group provisioning, and the two
specified role assignments/deletions. Databricks additionally requires workspace
access/compute entitlement, an available UC metastore, CREATE STORAGE CREDENTIAL
and CREATE EXTERNAL LOCATION privileges, and ownership/manage rights on only the
new objects/job. Do not elevate the operator, request account-wide admin, create a
metastore or broaden permissions automatically if these are missing. The job
owner and run_as must match the verified current operator; that operator gets
READ_FILES at raw and READ_FILES/WRITE_FILES at the two new output locations.

## Exactly one bounded transformation

Use [job.json](../../../infra/azure/stage3/job.json): **17.3.x-scala2.13** non-ML
runtime, STANDARD engine (no Photon), dedicated SINGLE_USER, explicit singleNode
profile/local Spark, **one Standard_D4ds_v4, zero worker nodes**, on-demand only.
No pool, autoscaling, init script, library installation, retries, schedule, queue,
SQL warehouse, serverless fallback, additional run or ADF pipeline invocation.
The current owner's job uses ephemeral compute, automatically terminated after
completion/failure. Set task/job timeout **1,800 seconds**; independently monitor
startup plus execution and request cancel/termination at **45 minutes**. These
are controls, not a guaranteed shutdown or billing cap. Job compute does not use
an all-purpose idle auto-termination setting.

Read only:
`abfss://tokyo-olympic-data@tokyoolympicdatahetram.dfs.core.windows.net/raw/adf/1a11a954-8e6c-45e9-98b1-fc530f00a6e8/`.
Write only new `curated/adf/c3c77b21-7385-4f93-91bd-e1d8ea1984d4/` and
`analytics/adf/c3c77b21-7385-4f93-91bd-e1d8ea1984d4/` in that same container.
The proposed output prefixes must still be absent immediately before the run.
Verify five original input hashes; shared quality gates; five cleaned Parquet
outputs; three country CSVs with 206 rows and pinned columns, keys and values;
Parquet schema/count/value round-trips; CSV hashes; and publish success manifest
last. Download outputs only to isolated verification storage; never replace local
references or ML artifacts. Preserve partial failure outputs without a success
manifest; do not repair/rerun automatically. Existing notebook collision wording
mentions a new ADF run; that wording is not authorization to repeat ingestion.

The storage account is HNS-enabled, publicNetworkAccess Enabled/defaultAction
Allow. Its existing HTTPS dfs/blob endpoints permit a cross-region network path
from East Asia without changing its firewall. This explicitly requests India ↔
East Asia processing/transfer of the five public datasets and derived outputs.
Access Connector is region-independent for this external storage use; creating it
in indiasouthcentral failed read-only validation (unsupported resource location),
so retain East Asia. **Actual network/MI/UC access is not yet proven.** After
approved provisioning, verify tenant, UC binding, runtime/node APIs and job schema
before starting compute; fail fast on imports/auth/input hashes inside the one
job before writing curated/analytics data. Do not enable serverless or weaken
security to work around failure. Raw location validation must remain read-only.

## Costs and uncertainty

| Evidence | Rate / interpretation |
| --- | --- |
| Previously captured East Asia retail meters | D4ds_v4 Linux **US$0.31/node-hour**; Premium Jobs **US$0.30/DBU-hour**; actual DBUs per node-hour unverified |
| Bounded current retail check | Standard IPv4 public IP **US$0.005/hour**; example P10 LRS disk **US$21.68/month**, P6 **US$11.2272/month**; actual disk count/SKU and proration must be observed |
| Managed networking | Microsoft confirms automatic, separately billable NAT with this managed-VNet design. Regional NAT hourly/processing price was **not returned**, so no verified NAT quote or zero-cost assumption |
| Transfer | East Asia inter-region meter **US$0.08/GB** observed; not a verified quote for both India/East Asia directions. Inputs are 0.000462 GB; bootstrap/network/control traffic and output transfer remain additional |
| Delayed actual billing | Current subscription MTD: INR0.04598372207 Storage, INR0 Bandwidth; no ADF row yet. This is not a Stage 3 quote or final Stage 2 cost |

Estimate **US$1–3 incremental** for short provisioning, one job, collection and
same-session cleanup. Illustration: 30 minutes of the VM plus an *assumed* 1–2
DBU/hour is US$0.305–0.455, before disks/network/storage. Reserve a planning
US$0.10–0.30 per workspace-hour for ancillary usage until teardown (not a verified
NAT tariff). Keep job compute to at most the 45-minute monitor boundary and new
workspace/network lifetime under **4 hours**, preferably much shorter. Actual DBU,
NAT, disk, transfer, tax, billing rounding and offer restrictions remain uncertain.
**US$5 is an operating allowance, NOT an Azure-enforced hard spending cap.** Do
not upgrade Students, remove its spending limit or launch work after a known
estimate exceeds the allowance. Recheck service-generated footprint and rates
before the sole job; stop and clean up on a material mismatch. No repeated open-ended
pricing investigation is proposed.

## Teardown included in this requested approval

1. On success or failure, cancel any active authorized job, verify its cluster
   TERMINATED and VM deallocation/removal; export sanitized job/resource/run
   evidence, validated country outputs and manifests locally without replacing
   existing datasets. Do not wait on idle paid resources for more user input.
2. Delete only the newly created job/notebook/bundle and three UC locations plus
   credential, after confirming object ownership and absence of other consumers.
   This removes UC registrations, not the ADLS files. Remove only the two new
   connector role-assignment IDs, then delete only the new Access Connector.
3. Delete only dbw-tokyo-olympics-hetram-2026 through its supported workspace
   deletion operation. Allow service-managed cleanup of only the newly created
   rg-tokyo-olympics-databricks-managed. Do not directly edit its protected network.
4. Verify disappearance of **all new VMs, NICs, managed disks, NAT gateway,
   public IP/prefix, VNet/subnets, NSGs and workspace storage**. NAT/public-IP/disks
   and storage may keep billing after compute stops. If orphaned/locked resources
   remain, record their exact IDs and charges; remove only manifest-listed new
   resources through supported deletion, or report a blocker. Never claim teardown
   complete while billable dependencies remain. Unexpected resources outside the
   new managed group require review, not blanket deletion.
5. Retain Stage 1/2 ADF definitions, the original ADF role, storage/container and
   **all existing/new ADLS data/evidence**. Do not delete the existing factory or
   rg-tokyo-olympics. Unregister Microsoft.Network only if this stage newly
   registered it, no resources depend on it and Azure permits; otherwise record
   registration retained (registration itself is not a billable resource).

Target new ongoing compute/network charges after **verified complete teardown**:
none. Existing storage, retained output bytes/transactions and possible retained
ADF-definition charges remain; no zero-total-bill promise. On any failed setup,
collect evidence and perform the same new-resource-only teardown; no retry,
larger SKU, quota request, second region or new identity/permission workaround.

## Validation and evidence

**95 tests passed (7.371 seconds)**; source/reference/code contract and shared
quality gates passed; dependency check and git diff --check passed. Pinned code
parses as Python 3.12; local Python/pandas differ from the documented DBR baseline
(Python3.12.3/pandas2.2.3/Spark4.0.0). No local PySpark/DBR execution or cloud
compatibility pass is claimed. No packages were installed. All Stage 1/2 evidence,
datasets, existing source and saved model files are preserved.

[Inventory/ARM validation](predeployment-inventory.json) ·
[Bounded price check](bounded-price-check.json) ·
[Local compatibility checks](local-predeployment-validation.json) ·
[Bundle manifest](bundle-manifest.json) ·
[Output/permission preflight](output-and-permission-preflight.json) ·
[UC plan](../../../infra/azure/stage3/unity-catalog-plan.json).

Technical references: [managed NAT behavior](https://learn.microsoft.com/en-us/azure/databricks/security/network/classic/secure-cluster-connectivity),
[managed identity roles](https://learn.microsoft.com/en-us/azure/databricks/connect/unity-catalog/cloud-storage/azure-managed-identities),
[UC privileges](https://learn.microsoft.com/en-us/azure/databricks/connect/unity-catalog/cloud-storage/external-locations-adls),
[single-node compute](https://learn.microsoft.com/en-us/azure/databricks/compute/configure#single-node-compute),
[17.3 LTS baseline](https://learn.microsoft.com/en-us/azure/databricks/release-notes/runtime/17.3lts).
