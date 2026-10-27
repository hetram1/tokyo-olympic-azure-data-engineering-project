# Remaining Databricks execution decision

The native Power BI report is saved and live DAX reconciles all 206 countries.
The three approved Azure setup attempts have ended. No Databricks job has run;
all newly created resources are deleted and the original ADF/ADLS/data/roles remain.
Azure reports ₹4.82 so far for Oct 25; Oct 26 and final billing are still delayed.

The last setup failed on a read-only classic-compute readiness API with HTTP 400,
“does not have any associated worker environments.” The Databricks Go SDK lists
this message among transient errors:
https://pkg.go.dev/github.com/databricks/databricks-sdk-go/openapi
This does not prove that waiting will resolve it. The earlier controller stopped
and tore down immediately, so it did not establish a permanent entitlement issue.

A separate prepared controller permits at most five minutes of ten-second waits
for this exact HTTP 400 on the runtime/node-type GET checks. It never retries
mutations, jobs or unrelated errors. Fake-clock tests cover recovery, hard timeout,
and non-retry behavior for writes/job reads/permission failures. It requires prior
cleanup to be verified and uses a new evidence folder; previous journals stay intact.

Any newly approved attempt retains the exact original scope: East Asia Premium,
one Standard_D4ds_v4 node, zero workers, existing raw run only, container-level
Blob Data Contributor and account-level Blob Delegator for the new connector,
India–East Asia processing, one 30-minute maximum job with zero retries, and full
cleanup of only new resources. The original US$5 allowance covers all attempts
and remains an allowance rather than a hard cap. No serverless substitution,
subscription upgrade, manual metastore, broader permissions or ingestion rerun.

**Approved and attempted on 2026-10-26.** The workspace provisioned, but the
node-type API changed to a second worker-environment error wording not covered
by the executed retry handler. It stopped before any job submission; cleanup is
verified. A later handler correction covers both observed messages and passes
four tests, but has not been cloud-executed. No further setup was started. No
GitHub push or Power BI Service publication was performed.
