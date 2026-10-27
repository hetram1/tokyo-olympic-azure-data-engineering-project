# Pending approval: provider registration only

Subscription: Azure for Students (`b52df7c6-044d-4326-92c8-496670def7c1`).
Both namespaces were confirmed NotRegistered on 2026-10-24.

## Exact proposed changes

```bash
az provider register --namespace Microsoft.Compute --subscription b52df7c6-044d-4326-92c8-496670def7c1
az provider register --namespace Microsoft.Databricks --subscription b52df7c6-044d-4326-92c8-496670def7c1
```

Poll registration using read-only provider metadata. Then repeat read-only quota,
SKU and workspace-availability checks. Do not create a workspace to test eligibility.
Registration alone does not prove student-offer eligibility.

## Cost and scope

Provider registration does not create a billable Azure resource. No VM, workspace,
cluster, pipeline execution, upload, deployment, role assignment, path ACL, firewall,
spending-limit or subscription-offer change is authorized by this request.
No subscription upgrade or spending-limit removal is proposed.

## Rollback

If cancelled and still unused, unregister only these two newly registered providers
after confirming there are no dependent resources. Never unregister a provider
that was already registered or acquired resources through other work.

## Following approval boundary

After eligibility is understood, prepare one consolidated deployment/run approval
with exact roles/ACLs, resource names, runtime/SKU, cost estimate and a project
spending ceiling. No paid execution is included here.

Status: user explicitly approved provider registration only on 2026-10-24.
Registration of exactly these two providers completed and was verified Registered.
No other cloud mutation is authorized by this provider-only approval. Further
provisioning requires the separate consolidated deployment approval.
