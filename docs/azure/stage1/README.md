# Stage 1 authorization and evidence

The user explicitly authorized only: inspect exact IDs, assign Storage Blob Data
Contributor to the existing ADF system identity at the existing container scope
if missing, non-overwriting staging of the five pinned datasets, deploy/validate
ingestion-only ADF definitions, local tests and sanitized evidence collection.
This supersedes the consolidated plan only for those Stage 1 operations.

No Databricks/Access Connector/VM/NAT/cluster creation, other identity grants,
subscription/resource-group data roles, ACL/network changes, deletion, pipeline
triggering, billable compute, Git push or Stage 2 is authorized.

Exact read-only preview was displayed before applying changes. Existing identity,
role GUID and scope matched the reviewed plan; ADF definitions and source prefix
were empty. The CLI runner rechecks these boundaries before any mutation.

Commands:

```bash
# Read-only, fails on unexpected identity/scope/role/ADF objects or staged files:
.venv/bin/python -B -m scripts.azure_stage1
# Mutating: requires explicit user approval, not authorization merely by this flag:
.venv/bin/python -B -m scripts.azure_stage1 --apply-stage1
```

The runner records each completed change. Uploads use Entra authentication,
overwrite=false and If-None-Match=*. Each file is downloaded with its returned
ETag and compared by length/SHA256 to the pinned source. No account keys are read.
The ARM deployment is Incremental and contains only four ADF child resources.
Read-back checks compare deployed properties with the prepared template. The
runner never calls createRun, debug, pipeline execution or linked-service test
connection (which might allocate an integration runtime). On error it records
partial progress and stops without deleting resources or granting other access.

Deployment evidence files include the created role-assignment ID, upload ETags and
verified hashes, ARM deployment state, deployed resource IDs and comparison
results. They contain no login tokens, passwords or account keys. Manually staged
sources remain distinct from future ADF-created raw/adf/<run-id>/ outputs.

Cloud configuration success does not prove ADF managed-identity data-plane access
or actual ingestion. Those require a separately authorized pipeline run. Role
propagation can take time. No successful end-to-end resume claim is made here.
