"""Data model + export loading for the replication audit."""

from __future__ import annotations

import json
from dataclasses import dataclass, field


class ExportError(ValueError):
    """Raised when an export file is malformed."""


@dataclass(frozen=True)
class ReplicationPolicy:
    name: str
    destination_bucket: str
    destination_region: str
    status: str  # ACTIVE | ERROR | ...


@dataclass(frozen=True)
class Bucket:
    name: str
    region: str
    versioning: str  # Enabled | Disabled | Suspended
    has_retention_rules: bool
    tags: dict = field(default_factory=dict)
    replication: ReplicationPolicy | None = None

    def is_prod(self) -> bool:
        return str(self.tags.get("criticality", "")).strip().lower() == "prod"


def load_export(path: str) -> tuple:
    with open(path, "r", encoding="utf-8") as fh:
        try:
            raw = json.load(fh)
        except json.JSONDecodeError as exc:
            raise ExportError(f"{path}: not valid JSON: {exc}") from exc
    if not isinstance(raw, dict) or not isinstance(raw.get("buckets"), list):
        raise ExportError(f"{path}: top level must be an object with a 'buckets' list")
    out = []
    for i, b in enumerate(raw["buckets"]):
        where = f"buckets[{i}]"
        for req in ("name", "region"):
            if req not in b:
                raise ExportError(f"{where}: missing required field {req!r}")
        policy = None
        p = b.get("replication")
        if p is not None:
            for req in ("destination_bucket", "destination_region", "status"):
                if req not in p:
                    raise ExportError(f"{where}.replication: missing required field {req!r}")
            policy = ReplicationPolicy(
                name=p.get("name", "") or "",
                destination_bucket=p["destination_bucket"],
                destination_region=p["destination_region"],
                status=str(p["status"]).upper(),
            )
        out.append(
            Bucket(
                name=b["name"],
                region=b["region"],
                versioning=b.get("versioning", "Disabled"),
                has_retention_rules=bool(b.get("has_retention_rules", False)),
                tags=b.get("tags", {}) or {},
                replication=policy,
            )
        )
    return tuple(out)
