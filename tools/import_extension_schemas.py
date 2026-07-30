#!/usr/bin/env python3
"""Regenerate reviewed extension schemas from the current service bindings."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ROOT.parent
sys.path.insert(0, str(WORKSPACE / "engineering-memory" / "src"))

from engineering_memory.controlled_context import (  # noqa: E402
    ControlledFieldReleaseReceipt,
)
from engineering_memory.repository_context import (  # noqa: E402
    RepositoryEvidenceReleaseReceipt,
)
from engineering_memory.repository_verification_context import (  # noqa: E402
    RepositoryVerificationReleaseReceipt,
)

TARGETS = {
    "schemas/extensions/controlled-field-release/1.0/schema.json": (
        ControlledFieldReleaseReceipt
    ),
    "schemas/extensions/repository-structural-release/1.0/schema.json": (
        RepositoryEvidenceReleaseReceipt
    ),
    "schemas/extensions/repository-verification-release/1.0/schema.json": (
        RepositoryVerificationReleaseReceipt
    ),
}


def main() -> int:
    for relative, model in TARGETS.items():
        payload = model.model_json_schema(
            ref_template="#/$defs/{model}",
            mode="validation",
        )
        payload["$schema"] = "https://json-schema.org/draft/2020-12/schema"
        payload["$id"] = (
            "https://kajohnson6.github.io/engineering-context-contracts/"
            + relative
        )
        path = ROOT / relative
        path.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
