# Stage 2 — verified ADF ingestion

Verified on 2026-10-25. Pipeline **pl_tokyo_ingest** succeeded. Exactly one
authorized run was started: **1a11a954-8e6c-45e9-98b1-fc530f00a6e8**.
It ran from 13:51:51.3786548Z to 13:53:36.8537534Z (105.475 seconds).
All five Copy activities and the sequential ForEach succeeded; no cancellation
was required. Later verification did not start another run.

## Evidence

- [Preflight](preflight.json): identity, container-only role, deployed definitions, staged hashes and empty raw destination inventory.
- [Run journal](run.json): sole createRun attempt, run ID, terminal status and activity timestamps.
- [Independent read-only verification](verification.json): fresh Azure run/activity reads, exactly one run in the execution window, five downloaded output hashes and delayed cost response.
- [Local validation](local-validation.json): 95 passing tests, dependency check, protected model hashes and Git checkpoint.

Only the five raw output CSVs were downloaded during final verification, to an
isolated temporary directory with ETag conditions. No project dataset was replaced.
The pinned source contract and earlier staged-source readback provide the reference.

## Five file-integrity checks

Container: tokyo-olympic-data. Destination prefix:
`raw/adf/1a11a954-8e6c-45e9-98b1-fc530f00a6e8/`.
Sources were manually staged under the dataset-version prefix recorded in preflight.

| File | Bytes | SHA256 | Result |
| --- | ---: | --- | --- |
| Athletes.csv | 407406 | `689e808c9c4dc46c041977ac2ca3e90aa592e235bbfca6cfd0ae50545fabcdfa` | Match |
| Coaches.csv | 16494 | `7f0fd82d59be93ef1fe53c9ca7617f5c8541169413e2bc5142dd186e0b93c4dd` | Match |
| EntriesGender.csv | 1076 | `2c0d18cfe475341d29098e559cc24e6511155938392a78a0db357fe55f4c6821` | Match |
| Medals.csv | 2320 | `453b4753dd7ee174e3e7056fa37ef4b5aaaab3885add9001d7998e60c66152e8` | Match |
| Teams.csv | 34600 | `41403e201a4b209ad5042ecd685a99c40edafb83d50dbfdcd822824650505ee3` | Match |

Exactly five files; total **461896 bytes**. No filename, size or hash discrepancy.

## Limits of the evidence

- secureInput/secureOutput hide activity payloads and detailed billing/DIU metrics. Copy-to-file attribution in verification.json is explicitly inferred from the verified sequential item order. File hashes are independently observed.
- The pipeline uses a new service-generated RunId; Binary Copy itself does not supply an atomic no-overwrite condition against an external concurrent writer.
- All original staged-file ETags, storage settings and the ADF role matched preflight. No role, ACL, security or network mutation was issued in Stage 2.
- Null retryAttempt is an unavailable field, not evidence about internal service retries. Authored retry policy is zero; exactly one createRun request was issued.
- A read-only MTD cost query returned INR0.04598372207 Storage and INR0 Bandwidth. No ADF row was present yet. Billing is delayed and these are subscription totals, not this run's final charge.
- US$0.05–0.10 remains the planning estimate. US$0.50 is an operating allowance, not an enforced cap; cancellation and billing propagation are not guaranteed.

## Stop boundary

Stage 2 authorization is consumed. No second run, Databricks deployment, paid
compute, RBAC change, commit or push is authorized. The next deployment blocker
is explicit approval for the East Asia Databricks workspace/access/compute phase
with bounded costs and rollback, using this existing raw run. The prepared Spark
transformation has not yet been executed or verified in cloud; curated/analytics
parity and a full end-to-end resume claim remain outstanding.

## Local checks after cloud execution

```bash
.venv/bin/python -B -m unittest discover -s tests -v
.venv/bin/python -m pip check
git diff --check
```

Result: **95 tests passed in 7.449 seconds**; no broken dependencies; diff check
passed. Pip reported only an unwritable cache warning and disabled its cache.
No existing source code, model or dataset was modified during verification.
