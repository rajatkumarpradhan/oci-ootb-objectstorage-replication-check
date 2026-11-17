# oci-ootb-objectstorage-replication-check

**Category: built-in OCI services project (OOTB).** The custom portfolio project in this pair
is `oci-fss-snapshot-audit`.

## Which built-in OCI services this wires

- **OCI Object Storage replication policies** (`oci_objectstorage_replication_policy`): the
  built-in, asynchronous bucket-to-bucket copy. One policy per source bucket; the destination
  bucket must already exist (in another region for real DR), must NOT have versioning enabled
  or retention rules, and becomes read-only once the policy is created. Chained replication
  (a destination that is itself a source) is not supported.
- **OCI Object Storage buckets** (`oci_objectstorage_bucket`): the source and destination
  buckets the policy ties together, across two region aliases of the provider.

## Custom code vs native config

- **Native config**: `terraform/` declares a source bucket, a destination bucket in a second
  region (provider alias), and the replication policy - only built-in provider resources.
  **Template only - NOT plan/apply validated** (no live tenancy).
- **Custom code**: `repl_checker/` audits an offline JSON export of buckets and replication
  policies against four failure modes the service documents but does not warn about in
  advance.

## The rules

| Rule | Severity | Fires when |
| ---- | -------- | ---------- |
| REPL001 | HIGH | A bucket tagged `criticality=prod` has no replication policy - no asynchronous copy exists at all. |
| REPL002 | MEDIUM | A policy's destination bucket has versioning enabled or retention rules - OCI **rejects policy creation** in this state (it surfaces as a 403/authorization-style failure), so the plan would fail at apply time. |
| REPL003 | MEDIUM | A policy's destination bucket is itself configured as a replication source - chained replication is not supported by the service. |
| REPL004 | LOW | A policy's status is not ACTIVE (e.g. ERROR) - per the troubleshooting docs, the fix is to delete and recreate the policy; nothing self-heals. |

Exit code: `2` on any HIGH, `1` on MEDIUM/LOW only, `0` when clean.

## Run it

```bash
python -m repl_checker.cli samples/repl_messy.json   # exits 2, all 4 rules fire
python -m repl_checker.cli samples/repl_clean.json   # exits 0
python -m unittest discover -s tests -v              # 18 tests, stdlib only
```

## Honest limits

- **Offline audit**: the JSON export is synthetic; nothing calls the OCI Object Storage API.
- Rule semantics are grounded in the official docs as of Nov 2026
  (<https://docs.oracle.com/en-us/iaas/Content/Object/Tasks/usingreplication.htm> and its
  troubleshooting page): one policy per source, destination must pre-exist, destination cannot
  have versioning/retention rules, no chained replication, destination turns read-only,
  ERROR-state policies are deleted and recreated.
- Not modeled: objects uploaded to the source **before** policy creation are never replicated
  (docs call this out) - a one-time sync is a separate manual step this checker cannot verify.
- REPL001's `criticality=prod` tag is this tool's convention, not an OCI standard.
- Terraform template is illustrative and has **not** been plan/apply validated.

## Project status

Built as a daily OOTB project. 18 unit tests, green locally and in CI. Free tier only; no
live cloud calls, no spend.
