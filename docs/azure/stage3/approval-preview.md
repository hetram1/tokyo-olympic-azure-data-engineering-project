# Stage 3 — single final approval preview

**NOT APPROVED. No Stage 3 cloud changes or runs performed.** This supersedes the
remaining older proposal. [Technical checks and complete teardown detail](deployment-readiness.md).

**Verified:** Azure for Students b52df7c6-044d-4326-92c8-496670def7c1 is Enabled,
spending limit On, reported credit US$100 (billing/expiry uncertainty). East Asia
is allowed; 6 regional/4 DDSv4 vCPUs free, D4ds_v4 listing unrestricted. Both East
Asia ARM templates pass ProviderNoRbac validation, which does not guarantee live
capacity, entitlement or Databricks runtime/UC availability. **95 tests pass**;
pinned contracts, Python3.12 grammar, dependencies, preservation and diff checks pass.

## Exact changes for approval

| Change | Exact boundary |
| --- | --- |
| Register provider | Microsoft.Network only; Microsoft.Compute/Databricks already registered |
| Premium workspace | dbw-tokyo-olympics-hetram-2026, eastasia, in existing rg-tokyo-olympics; enableNoPublicIp=true; authenticated public workspace endpoint |
| New managed infrastructure | rg-tokyo-olympics-databricks-managed only: workspace storage, VNet/two subnets, NSG(s), one billable NAT gateway/egress IPv4 public-IP resource; one job VM/NIC/disks during execution. Generated names/disk SKUs are not yet knowable; record and stop on unexpected footprint |
| Access Connector | ac-tokyo-olympics-hetram-2026, eastasia, SystemAssigned. Read its exact newly generated principalId before assigning roles; no other existing identity receives new access |
| Two new roles, only that connector | Storage Blob Data Contributor **ba92f5b4-2d11-453d-a403-e96b0029c9fe** at existing container; Storage Blob Delegator **db58b8e5-c6ad-4a2a-8342-4190687cbf4a** at existing storage account |
| Unity Catalog | New sc_tokyo_stage3 credential and el_tokyo_stage3_raw/curated/analytics external locations, bound only to the new workspace; raw READ_FILES/read-only, outputs READ_FILES/WRITE_FILES. No file events, queues, Event Grid or metastore creation/reassignment |
| Code and one job | Allowlisted 27-file code/contract/reference bundle (55,885-byte ZIP), exact pinned notebook, one tokyo-transform-verify job invoked once as current operator. No new service principal or ADF workspace grant |

Resource prefix:
`/subscriptions/b52df7c6-044d-4326-92c8-496670def7c1/resourceGroups/rg-tokyo-olympics/providers/`.
Workspace/connector IDs append `Microsoft.Databricks/workspaces/dbw-tokyo-olympics-hetram-2026`
and `Microsoft.Databricks/accessConnectors/ac-tokyo-olympics-hetram-2026`.
Storage account scope appends `Microsoft.Storage/storageAccounts/tokyoolympicdatahetram`;
container scope appends `/blobServices/default/containers/tokyo-olympic-data`.

**Permission difference from the old plan:** account-scoped Blob Delegator is
needed alongside container-scoped Contributor. Delegator only generates user
delegation keys, with no dataActions; Contributor permits read/write/delete
throughout the container despite narrower UC/application use. No subscription/RG
data role, ACL, existing firewall or network change is proposed. Connector GUID,
workspace URL/ID and job ID must be resolved from these exact newly created
resources. Service-generated storage identities must remain confined to new
workspace dependencies, with no existing-project-storage grant.

## One job, existing input, new outputs

[Prepared job](../../../infra/azure/stage3/job.json): runtime **17.3.x-scala2.13**,
STANDARD engine/no Photon, dedicated SINGLE_USER, explicit singleNode/local
Spark, **one Standard_D4ds_v4, zero workers**, on-demand, no pool/autoscale/library
installation/schedule/queue/retry/serverless fallback. Job owner/run_as must be
current operator. Ephemeral job compute terminates on completion/failure;
**1,800-second task/job timeout**, independent **45-minute startup-plus-run cancel/
termination boundary**. Controls and cancellation do not guarantee a billing cap.

Read existing `raw/adf/1a11a954-8e6c-45e9-98b1-fc530f00a6e8/` only. Write new
`curated/adf/c3c77b21-7385-4f93-91bd-e1d8ea1984d4/` and
`analytics/adf/c3c77b21-7385-4f93-91bd-e1d8ea1984d4/`, all under
`abfss://tokyo-olympic-data@tokyoolympicdatahetram.dfs.core.windows.net/`.
Recheck empty output paths. Verify five input hashes, shared quality gates, five
cleaned Parquet outputs/round-trips, three 206-country CSVs against pinned local
schemas/keys/values, and success manifest last. Never overwrite local references.

Existing storage HNS/public endpoints/defaultAction Allow permit the planned
India ↔ East Asia HTTPS path without firewall changes; actual MI/UC connectivity
is unproven. Connector cannot deploy in indiasouthcentral (validation failed), so
retain East Asia. Approve this cross-region public-data processing explicitly.
Before compute, verify runtime/node APIs, tenant, current-user/job identity and UC
metastore/privileges/bindings. Operator needs CREATE STORAGE CREDENTIAL and CREATE
EXTERNAL LOCATION; existing Azure management permission checks show wildcard
actions. Stop and clean up on missing access; no elevation or new metastore.
Inside the single job, imports/access/hashes must pass before output writes.
DBR's documented Python3.12.3/pandas2.2.3/Spark4.0.0 differ from local versions;
no local PySpark/DBR execution or cloud compatibility pass is claimed.

## Cost, lifetime and teardown

- **Observed list meters:** VM US$0.31/node-hour; Jobs US$0.30/DBU-hour (actual
  DBUs/node-hour unverified); Standard public IP US$0.005/hour. Example disks:
  P10 US$21.68/month, P6 US$11.2272/month; actual disk footprint/proration unknown.
- **Unresolved:** regional NAT hourly/processing quote, actual DBUs, disk count,
  bootstrap traffic, both-direction transfer and taxes. An East Asia US$0.08/GB
  inter-region meter is indicative, not a verified India-direction quote.
- **Estimate US$1–3 incremental; US$5 allowance is NOT a hard spending cap.**
  Illustrative 30-minute VM plus assumed 1–2 DBU/hour: US$0.305–0.455 before
  ancillary charges. Planning reserve US$0.10–0.30/workspace-hour is an estimate,
  not a verified NAT rate. Current delayed MTD bill: INR0.0459837 Storage/0 Bandwidth;
  it does not establish a final run cost. No subscription upgrade/spending-limit removal.
- Immediately after success/failure, cancel active job, verify compute terminated,
  export sanitized evidence, then delete only the new job/notebook/bundle, three
  UC locations/credential, two new role assignments and connector. Preserve all ADLS data.
- Delete only the new workspace through supported deletion and verify cleanup of
  its new managed group: **VMs, NICs, disks, NAT, IP/prefix, VNet/subnets, NSGs and
  storage**. NAT/IP/disks/storage can bill after compute stops. Report any orphaned
  or locked resource and never claim cleanup complete prematurely. No edits to
  protected managed networking; no blanket deletion outside the new group.
- Same-session teardown, **under four hours**, preferably immediately after the
  one job; four hours is not compute authorization. After verified teardown,
  expect no new ongoing compute/network charge; retained storage/ADF charges remain.
  Remove newly registered provider only if unused/supported; registration alone
  is not billable. Full supported rollback procedure is in the linked readiness detail.

**Next approval:** explicitly authorize this scope, the two specified roles,
cross-region processing, one bounded job, US$5 allowance with uncertainty, and
new-resource-only teardown. **No ingestion, ADF changes, new ML training, retry,
existing-data deletion, commit, push or branch change is included.**

[Inventory/ARM evidence](predeployment-inventory.json) ·
[Bounded price capture](bounded-price-check.json) ·
[Local checks and preservation](final-local-validation.json).
