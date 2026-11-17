"""python -m repl_checker.cli EXPORT"""

from __future__ import annotations

import argparse
import sys

from .model import ExportError, load_export
from .rules import exit_code, run_all


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="objectstorage-replication-check",
        description="Audit an offline export of OCI Object Storage buckets for replication coverage and config errors.",
    )
    p.add_argument("export", help="path to the JSON export")
    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    try:
        buckets = load_export(args.export)
    except ExportError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    findings = run_all(buckets)
    with_pol = sum(1 for b in buckets if b.replication is not None)
    print(
        f"Replication audit - {len(buckets)} bucket(s), {with_pol} with a replication policy, "
        f"{len(findings)} finding(s)"
    )
    for x in findings:
        print(f"[{x.severity:6s}] {x.rule} bucket={x.bucket}")
        print(f"         {x.detail}")
    code = exit_code(findings)
    print({0: "RESULT: clean", 1: "RESULT: warnings only", 2: "RESULT: HIGH findings present"}[code])
    return code


if __name__ == "__main__":
    raise SystemExit(main())
