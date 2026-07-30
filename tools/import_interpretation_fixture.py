#!/usr/bin/env python3
"""Vendor the reviewed AMS PPS interpretation vector without rewriting it."""

from __future__ import annotations

import hashlib
from pathlib import Path

from engineering_context_contracts.interpretation import (
    EvidenceInterpretationReceipt,
)

ROOT = Path(__file__).resolve().parents[1]
SOURCE = (
    ROOT.parent
    / "component-lens"
    / "corpora"
    / "ams-gra-pps-chain"
    / "soft-interpretation-50-ohm-v1.json"
)
TARGET = ROOT / "fixtures" / "evidence-interpretation-ams-pps-50-ohm-v1.json"
EXPECTED_FILE_SHA256 = (
    "479c06b7ca86df3e4b7e884732e9939ce9f5f4465f873049de8130996455a0ae"
)
EXPECTED_CANONICAL_SHA256 = (
    "4c376fab0d2a4ccaf228313044200e4ed536fb4f58ea3e95cf4ece6ae63a9450"
)


def main() -> int:
    payload = SOURCE.read_bytes()
    if hashlib.sha256(payload).hexdigest() != EXPECTED_FILE_SHA256:
        raise ValueError("source interpretation fixture identity changed")
    receipt = EvidenceInterpretationReceipt.model_validate_json(payload)
    if receipt.sha256() != EXPECTED_CANONICAL_SHA256:
        raise ValueError("source interpretation semantic identity changed")
    TARGET.write_bytes(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
