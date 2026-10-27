# Stage 2 — authorized once and verified complete

Stage 1 deployed configuration and manually staged sources only. The smallest
next step is to prove actual ADF managed-identity ingestion **before** considering
Databricks deployment or compute.

## Original authorization scope (consumed by one completed run)

- Trigger **exactly one manual run** of pl_tokyo_ingest in the existing
  adf-tokyo-olympics-hetram-2026 factory, subscription
  b52df7c6-044d-4326-92c8-496670def7c1, resource group rg-tokyo-olympics.
- Source: the five pinned files under
  staging/218c96338c6c3926d6a3910ceebcf2915e1097f9cccd024b1fa39a9458057685/.
- Destination: raw/adf/<the-new-pipeline-run-id>/ in the same container,
  tokyo-olympic-data. Do not reuse or overwrite any existing run path.
- Run the prepared sequential Binary Copy pipeline unchanged: five files,
  configured two DIUs/one parallel copy, zero retries, max pipeline concurrency one.
- Monitor run/activity state and allow cancellation if total wall-clock execution
  exceeds 10 minutes. No automatic second run even if propagation/access fails.
- Download the five ADF-created raw files into an isolated temporary directory;
  verify exact names/counts, byte lengths and SHA256 against the local pinned
  original data and the manually staged sources. Record sanitized run/activity
  IDs, source/destination paths, final status, durations and available billable
  duration/DIU metrics. Do not expose individual source records in evidence.
- Query costs read-only afterward, recognizing that Cost Management can lag.

## Estimated cost and controls

No Databricks/VM/cluster/NAT costs. Captured ADF rate: US$0.25 per DIU-hour,
US$1/1,000 orchestration activity runs. Illustrative five one-minute copies at
configured two DIUs cost about US$0.042 for data movement plus activity/transaction
charges. Plan **US$0.05–0.10** for the single small test; actual DIUs, minimum
rounding and startup differ by service and are not promised. Proposed operational
allowance **US$0.50** with the 10-minute cancel boundary; this is not an Azure
hard billing cap and cancellation/billing propagation can lag.

## Explicit exclusions

No new role grants, ACL/network/security changes, provider registrations,
Databricks workspace/Access Connector/VM/cluster, additional ADF definitions,
triggers/schedules, deletion, model retraining, dataset replacement, Git commit
or push. If the run fails, preserve evidence and stop; do not broaden access or
retry automatically. Existing project and cloud data remain intact.

Approval of this proposal would authorize the listed single billable ADF run and
its timeout cancellation only. It would **not** approve the earlier full Databricks
plan. Databricks and the remaining end-to-end demonstration need later explicit
approval after ingestion is evidenced.

Status: the one authorized run 1a11a954-8e6c-45e9-98b1-fc530f00a6e8 succeeded on 2026-10-25. Five Copy activities and five output hashes verified. No cancellation needed. No further run is authorized. See [verification evidence](stage2/README.md).
