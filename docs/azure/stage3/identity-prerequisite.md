# Databricks identity prerequisite — observed 2026-10-27

The latest approved setup passed workspace deployment, operator verification,
automatic metastore discovery, and Databricks 17.3 / Standard_D4ds_v4 readiness.
The Access Connector was created and the two approved scoped roles applied.
Unity Catalog then rejected storage credential creation with:

`UC_STORAGE_CREDENTIAL_PRINCIPAL_MISSING_AZURE_OBJECT_ID`

Databricks could not associate the validating workspace user with an Entra object
ID, so it could not verify that user's access to the Azure connector. This is
separate from the connector's storage roles. Broadening storage permissions or
disabling credential validation is not an appropriate fix.

No job, cluster run, curated dataset or cloud analytics manifest was created.
The controller proceeded to remove its two exact role assignments, connector,
workspace and new managed dependencies. The adjacent cleanup journal is the
authority for the final resource/preservation result.

## Resolve before another billable setup

1. Have the Databricks account administrator inspect the operator's identity
   mapping and automatic identity management/readiness status in the correct
   Microsoft Entra tenant.
2. Use the supported Microsoft Entra sign-in and identity-sync flow so the user's
   real object ID is associated with the Databricks identity. Do not invent or
   manually spoof an external identity value.
3. Verify the association and connector authorization before another credential
   validation or compute request. Keep the original storage scopes unchanged.

Microsoft documents that Entra SSO tokens carry the object ID used for identity
matching, and provides an account-admin readiness report for identity-link
divergences. These are relevant next checks; they have not been verified as a
successful remedy for this account:

- [Automatic identity management](https://learn.microsoft.com/en-us/azure/databricks/admin/users-groups/automatic-identity-management/)
- [Identity management readiness report](https://learn.microsoft.com/en-us/azure/databricks/admin/users-groups/automatic-identity-management/readiness-report)

For an interview, present ADF ingestion, local transformations, tested ML and the
validated Power BI report as completed. Describe the PySpark notebook and
governed cloud design as implemented but not successfully executed. Do not call
the entire Azure pipeline end-to-end verified.
