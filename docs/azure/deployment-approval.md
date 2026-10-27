# Consolidated approval: one bounded Azure project demonstration

**Full-plan status: NOT APPROVED.** Stage 1 and the separately authorized single
Stage 2 ingestion run are complete. See [Stage 1 evidence](stage1/README.md) and
[Stage 2 verification](stage2/README.md). The Stage 2 authorization is consumed;
no further ingestion run or Databricks deployment/compute is authorized.
The broader proposal and starting-point inventory below are historical planning
context, not current resource inventory or permission to execute the remainder.
The next decision must reuse the verified raw run and exclude another ingestion.

**Current next decision:** [Stage 3 pre-deployment preview](stage3/approval-preview.md).
It supersedes the remaining proposal below: reuse the verified raw run, one
operator-invoked transformation job, explicitly revised connector permissions,
and teardown of only new Stage 3 resources. It is not yet approved.

## Historical decision requested

Approve one end-to-end educational demonstration in the existing **Azure for
Students** subscription, with an **estimated US$1–3 incremental cost and a proposed
US$5 operating ceiling**. This is a planning estimate, not an Azure-enforced billing
cap. Approve cleanup of the newly created paid resources after collecting evidence.
Do not upgrade the subscription or remove its existing spending limit.

## Verified starting point

- Subscription b52df7c6-044d-4326-92c8-496670def7c1 is Enabled, spendingLimit On.
- Its linked billing profile reports US$100 current credit, not an estimated
  balance, no expired credit and no pending eligible charges. Billing can lag;
  credit expiry was not returned. There is no configured Azure budget.
- Month-to-date actual-cost query returned INR 0.018355477 in storage and INR 0
  bandwidth. These are observed costs, not a forecast of this run.
- Existing ADF and HNS-enabled Standard_LRS storage are in indiasouthcentral.
  Resource group rg-tokyo-olympics has location centralindia.
- ADF has no pipelines/datasets/linked services/triggers and no returned inherited
  container storage assignments. Container tokyo-olympic-data has only directories
  and no listed data files; staging/ does not exist. Existing ACLs are preserved.
- Subscription policy permits indonesiacentral, eastasia, malaysiawest,
  polandcentral and indiasouthcentral. Central India workspace validation failed
  that policy. East Asia Databricks workspace **ProviderNoRbac validation passed**.
- East Asia has 6 total vCPUs available, with 4 in standardDDSv4Family.
  Standard_D4ds_v4 has no returned Azure SKU restriction. This does not reserve
  capacity or prove Databricks runtime/node-type availability.
- The ingestion template passed ARM Template-level validation. No resource was
  deployed and no pipeline was executed.

## Exact proposed changes

1. **Reuse existing ADF and storage**, without changing account/container names,
   public-access/firewall settings, shared-key settings, existing ACLs or old raw
   directories. No extra ADF, storage account, Key Vault, SQL warehouse, streaming
   service or scheduled trigger.
2. **Register Microsoft.Network**, which is still NotRegistered, solely for the
   approved new workspace's managed network. No policy exemption or location-policy
   modification. Microsoft.Compute and Microsoft.Databricks are already registered.
3. **Create one Premium Databricks workspace** dbw-tokyo-olympics-hetram-2026 in
   eastasia, in rg-tokyo-olympics. Managed resource group:
   rg-tokyo-olympics-databricks-managed. Permit only the normal workspace-managed
   storage, VNet/subnets, NSGs, secure outbound NAT/public-IP resources and temporary
   compute dependencies inside this new managed group. Enable secure cluster
   connectivity/no public IP on compute. Do not inject into or alter existing VNets.
   Workspace endpoint uses normal authenticated public access; no paid private
   endpoints or new networking add-ons. East Asia processing reads the India-region
   source, so this explicitly approves that cross-region transfer for these inputs.
4. **Create one Access Connector** ac-tokyo-olympics-hetram-2026, eastasia, with a
   system-assigned managed identity, for Unity Catalog storage access.
5. **Storage RBAC: exactly two container-scoped grants**, no account/subscription
   data roles:
   - ADF MI 2b14c4a6-9415-4738-b6a6-a8b671d97d6f: Storage Blob Data Contributor.
   - The newly created Access Connector MI: Storage Blob Data Contributor.
   Scope for both:
   `/subscriptions/b52df7c6-044d-4326-92c8-496670def7c1/resourceGroups/rg-tokyo-olympics/providers/Microsoft.Storage/storageAccounts/tokyoolympicdatahetram/blobServices/default/containers/tokyo-olympic-data`.
   Role definition: ba92f5b4-2d11-453d-a403-e96b0029c9fe.
   **Tradeoff:** this standard role permits read/write/delete throughout this
   project's container; it is broader than prefix-only ACLs. The implementation
   writes only new version/run paths and never deletes existing data. Container
   scope is chosen for documented managed-identity interoperability and simple
   reversible setup, not presented as path-level isolation. No ACL edits included.
6. **Workspace authorization:** register the ADF MI as a Databricks workspace
   service principal; grant only the approved job's run and required compute
   permissions. Grant Azure Contributor (role b24988ac-6180-42a0-ab88-20f7382dd24c)
   to that MI **only on the newly created workspace resource** for the ADF MSI
   integration. No subscription/resource-group Contributor grant. Use the Access
   Connector storage credential and narrowly scoped Unity Catalog external
   locations for raw/adf read and curated/adf plus analytics/adf write. Do not
   create a metastore or request tenant-wide admin permissions automatically;
   stop if the workspace lacks the required existing/automatically supplied setup.
7. **Source staging:** upload exactly the five original, hash-pinned CSVs
   (461,896 bytes total) using Entra authentication into
   staging/218c96338c6c3926d6a3910ceebcf2915e1097f9cccd024b1fa39a9458057685/.
   Use the current authenticated operator's existing permissions. If upload is
   denied, stop; do not fall back to keys or add an unapproved third storage grant.
   Manually staged files are labeled as such and are never claimed as ADF outputs.
8. **ADF definitions:** add only ls_tokyo_adls_mi, ds_tokyo_staged_binary,
   ds_tokyo_raw_binary and pl_tokyo_ingest; then ls_tokyo_databricks_mi and
   pl_tokyo_end_to_end. Export any existing same-name definitions first; stop if
   unexpected user-owned objects appeared. No trigger creation. Ingestion copies
   only those five files as binary into raw/adf/<ingestion-run-id>/.
9. **Deploy the pinned code bundle and one job**, named tokyo-transform-verify.
   Use Databricks Runtime 17.3 LTS (`17.3.x-scala2.13`, subject to the workspace API
   confirming that exact ID), non-ML runtime, no Photon, no package installation,
   no spot fallback and no autoscaling. Use **one Standard_D4ds_v4 node, four
   vCPUs, zero additional workers, explicit single-node mode**. It must run Spark
   locally; zero workers without single-node configuration is not acceptable.
   Prefer ephemeral job compute rather than a retained all-purpose cluster.
   ADF's DatabricksJob activity invokes this fixed job and does not choose compute.
   Confirm runtime/node type/DBU estimate and Unity Catalog access before starting.
   If unsupported, stop without substituting a larger SKU or increasing quota.
10. **Authorize exactly one manual parent pipeline run**, with no automatic
    retries and max concurrency one. Verify original-byte hashes, five cleaned
    datasets, country analytics and Power BI-ready CSV parity; publish a success
    manifest only after re-reading the outputs. Results go to new run paths; no
    existing datasets, analytics or ML artifacts are replaced or retrained.
11. **Collect evidence and shut down/clean up** as described below. No push,
    merge, branch change or subscription upgrade is included.

## Costs: observed prices versus estimates

Public Azure Retail Prices API responses were captured on 2026-10-24 in
retail-price-reference-2026-10-24.json. They are list meters, not an offer-specific
quote. Exchange rates/taxes and applicable billing rules may differ.

| Component | Verified list meter | Estimate/qualification |
| --- | --- | --- |
| East Asia Standard_D4ds_v4 Linux VM | US$0.31/node-hour | US$0.155 for 30 minutes, before disks and provisioning time |
| East Asia Premium Jobs Compute | US$0.30/DBU-hour | Exact DBU consumption must be confirmed from workspace/node metadata; NOT US$0.30 per cluster-hour |
| East Asia Premium All-purpose Compute | US$0.55/DBU-hour | Reference only; ephemeral Jobs Compute is preferred |
| ADF Cloud Data Movement, existing region | US$0.25 per metered hour/DIU-hour billing basis | Five one-minute, two-DIU copies illustrate about US$0.042; actual DIUs/minimum rounding may differ |
| ADF orchestration | US$1 per 1,000 activity runs | Several activities; a few cents planning allowance |
| Inactive ADF pipeline meter | US$0.80/pipeline-month | Applicability/retention rules need care; avoid leaving unused demo definitions indefinitely |
| Managed NAT, public IP, disks, workspace storage and cross-region traffic | Full regional quote not verified | Must not be treated as free; workspace-managed networking can charge even with compute stopped |

Illustration only: if the one node consumes 1 DBU/hour, 30 minutes of VM plus Jobs
DBU usage is about US$0.305, before networking, disks, transfer and setup. This is
not a verified DBU consumption value. A conservative **US$1–3 one-time allowance**
includes brief setup and ancillary usage; it is an estimate, not a guarantee.
Proposed **US$5 operating ceiling**: stop launching work if known/estimated spend
would exceed it; do not keep a workspace running to wait for user input. Azure
Cost Management can lag and budgets are alerts, not a real-time hard cap. No
technical guarantee of an exact US$5 final bill is implied.

## Shutdown and ongoing cost controls

- No schedules, retries, autoscale, SQL warehouses or serverless fallback.
- One job; max concurrent runs one; task/job timeout 1,800 seconds. Monitor wall
  clock and cancel/terminate the job if startup plus execution exceeds 45 minutes.
- Stop if rate/capacity/permissions differ materially from this plan. Do not create
  replacement compute or broaden permissions to work around failures.
- Export sanitized evidence and ADF/job definitions locally, retaining validated
  output CSVs and manifests in the existing storage account.
- **Default cost-preserving choice:** delete only the new Databricks workspace and
  its service-managed resource group after evidence collection (or failed setup),
  and remove the new Access Connector and the role assignments created here.
  Complete teardown in the same work session; four hours is a stop/cleanup deadline,
  not permission for four hours of compute. Do not modify the managed network
  directly. Confirm the workspace deletion removed its billable dependencies;
  report any orphaned/locked resources immediately.
- After exporting their definitions and evidence, delete only the six new demo ADF
  child objects to avoid inactive-pipeline retention costs. Keep the existing ADF
  factory, storage account, container, all pre-existing directories and all data.
- Therefore expected **new ongoing compute/network charges after verified teardown
  are zero**; small existing-account storage/transaction costs remain and are not
  promised zero. Until teardown completes, NAT/IP/storage costs can continue even
  when the job is stopped. Keeping a live workspace instead requires a separate
  explicit retention budget; it is not the default.
- This is an executed, evidenced and reproducibly redeployable demo, not a claim
  of a permanently running production service after teardown.

## Rollback and unresolved risks

Record all created resource IDs and role-assignment GUIDs. On failure, cancel only
the authorized job/run, terminate its compute, export available diagnostics, remove
only the newly created role assignments and workspace/connector/ADF child objects,
and verify costs/resources afterward. Restore any same-name definitions from the
pre-change export if replacement was explicitly allowed. Never delete existing
raw/curated/analytics data or local artifacts. Retain failed run directories without
a success marker; deleting cloud data requires a separate explicit request.

ProviderNoRbac validation does not prove all authorization, live capacity or
Databricks entitlements. Unity Catalog availability, exact node/runtime support,
operator upload permission and DBU consumption still need workspace-level checks.
If those checks fail, stop and clean up the new paid workspace rather than
upgrading the subscription, changing allowed regions, requesting quotas or adding
unapproved roles. No further open-ended web/pricing searches are planned.

**Approval needed:** explicitly approve this one bounded demonstration, the exact
RBAC/new-network/resource changes above, India-to-East-Asia processing, the US$5
operating ceiling with its billing-lag limitation, and teardown of only new demo
resources. Until then, all deployment and billable execution remain stopped.
