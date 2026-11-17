"""REPL001-REPL004 rules, grounded in the OCI Object Storage replication docs."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Finding:
    rule: str
    severity: str  # HIGH | MEDIUM | LOW
    bucket: str
    detail: str


def _by_name(buckets: tuple) -> dict:
    return {b.name: b for b in buckets}


def rule_prod_without_policy(buckets: tuple) -> list:
    """REPL001 HIGH: prod-criticality bucket with no replication policy."""
    return [
        Finding("REPL001", "HIGH", b.name,
                "tagged criticality=prod but has no replication policy; no asynchronous copy exists")
        for b in buckets if b.is_prod() and b.replication is None
    ]


def rule_bad_destination(buckets: tuple) -> list:
    """REPL002 MEDIUM: destination bucket has versioning or retention rules (policy creation fails)."""
    idx = _by_name(buckets)
    out = []
    for b in buckets:
        if b.replication is None:
            continue
        dest = idx.get(b.replication.destination_bucket)
        if dest is None:
            continue  # destination outside this export; cannot evaluate
        problems = []
        if dest.versioning.lower() == "enabled":
            problems.append("versioning enabled")
        if dest.has_retention_rules:
            problems.append("retention rules")
        if problems:
            out.append(
                Finding("REPL002", "MEDIUM", b.name,
                        f"destination bucket '{dest.name}' has {' and '.join(problems)}; "
                        f"OCI rejects replication policy creation in this state")
            )
    return out


def rule_chained_replication(buckets: tuple) -> list:
    """REPL003 MEDIUM: destination bucket is itself a replication source (chaining unsupported)."""
    idx = _by_name(buckets)
    out = []
    for b in buckets:
        if b.replication is None:
            continue
        dest = idx.get(b.replication.destination_bucket)
        if dest is not None and dest.replication is not None:
            out.append(
                Finding("REPL003", "MEDIUM", b.name,
                        f"destination bucket '{dest.name}' is itself a replication source; "
                        f"chained replication is not supported")
            )
    return out


def rule_policy_not_active(buckets: tuple) -> list:
    """REPL004 LOW: replication policy status is not ACTIVE."""
    return [
        Finding("REPL004", "LOW", b.name,
                f"replication policy status is {b.replication.status}, not ACTIVE; "
                f"docs prescribe deleting and recreating the policy - nothing self-heals")
        for b in buckets if b.replication is not None and b.replication.status != "ACTIVE"
    ]


ALL_RULES = (
    rule_prod_without_policy,
    rule_bad_destination,
    rule_chained_replication,
    rule_policy_not_active,
)

_SEVERITY_RANK = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}


def run_all(buckets: tuple) -> list:
    findings = []
    for rule in ALL_RULES:
        findings.extend(rule(buckets))
    findings.sort(key=lambda x: (_SEVERITY_RANK[x.severity], x.rule, x.bucket))
    return findings


def exit_code(findings: list) -> int:
    if any(f.severity == "HIGH" for f in findings):
        return 2
    if findings:
        return 1
    return 0
