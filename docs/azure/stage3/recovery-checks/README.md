# Proposed readiness correction — not cloud-executed

These files contain the later correction after the final approved attempt had
already stopped. Both observed worker-environment error wordings share one
five-minute window. Only two read-only GET endpoints can retry. Writes, job reads
and unrelated failures are never retried. No Azure SDK, token or deployment is
invoked by these tests.

Run from the repository root:

```bash
.venv/bin/python -B docs/azure/stage3/recovery-checks/test_readiness_retry.py
```

Five fake-clock tests passed, including a shared deadline across both endpoints. This does not prove Azure readiness or authorize
another workspace setup. The executed final attempt recognized only the first
message wording; see its state and cleanup journals in the sibling directory.
