#!/usr/bin/env python3
"""Build the content manifest for normative contract artifacts."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INCLUDED_ROOTS = ("canonicalization", "fixtures", "schemas")


def main() -> int:
    artifacts = []
    for root_name in INCLUDED_ROOTS:
        for path in sorted((ROOT / root_name).rglob("*")):
            if not path.is_file():
                continue
            data = path.read_bytes()
            artifacts.append(
                {
                    "path": path.relative_to(ROOT).as_posix(),
                    "sha256": hashlib.sha256(data).hexdigest(),
                    "byte_count": len(data),
                }
            )
    payload = {
        "manifest_version": "1.0",
        "package_version": "0.3.0",
        "core_contract_version": "1.0",
        "canonicalization_profile": "engineering-context-jcs-1.0",
        "artifacts": artifacts,
    }
    (ROOT / "CONTRACT-MANIFEST.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
