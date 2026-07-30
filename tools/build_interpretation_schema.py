#!/usr/bin/env python3
"""Generate the normative EvidenceInterpretationReceipt JSON Schema."""

from __future__ import annotations

import json
from pathlib import Path

from engineering_context_contracts.interpretation import (
    EvidenceInterpretationReceipt,
)

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "schemas" / "evidence-interpretation" / "1.0" / "schema.json"


def main() -> int:
    schema = EvidenceInterpretationReceipt.model_json_schema(
        ref_template="#/$defs/{model}"
    )
    schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
    schema["$id"] = (
        "https://engineering-context-contracts.invalid/"
        "schemas/evidence-interpretation/1.0/schema.json"
    )
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        json.dumps(schema, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
