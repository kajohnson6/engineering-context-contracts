"""Access and verify packaged normative contract artifacts."""

from __future__ import annotations

import hashlib
import json
from importlib import resources
from pathlib import Path
from typing import Any


def _resource_root():
    packaged = resources.files("engineering_context_contracts")
    if packaged.joinpath("CONTRACT-MANIFEST.json").is_file():
        return packaged
    return Path(__file__).resolve().parents[2]


def contract_manifest() -> dict[str, Any]:
    path = _resource_root().joinpath("CONTRACT-MANIFEST.json")
    return json.loads(path.read_text(encoding="utf-8"))


def verify_packaged_contracts() -> dict[str, Any]:
    root = _resource_root()
    manifest = contract_manifest()
    for artifact in manifest["artifacts"]:
        data = root.joinpath(artifact["path"]).read_bytes()
        if len(data) != artifact["byte_count"]:
            raise ValueError(
                f"contract byte count mismatch: {artifact['path']}"
            )
        if hashlib.sha256(data).hexdigest() != artifact["sha256"]:
            raise ValueError(f"contract digest mismatch: {artifact['path']}")
    return manifest
