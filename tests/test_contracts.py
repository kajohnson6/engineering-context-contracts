import hashlib
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator
from pydantic import ValidationError

from engineering_context_contracts import (
    ArtifactRef,
    EvidenceInterpretationReceipt,
    admission_consideration_id,
    canonical_json_bytes,
    canonical_sha256,
    verify_packaged_contracts,
)

ROOT = Path(__file__).parents[1]


def test_manifest_verifies_every_normative_artifact():
    manifest = verify_packaged_contracts()
    assert manifest["core_contract_version"] == "1.0"
    assert manifest["canonicalization_profile"] == ("engineering-context-jcs-1.0")
    assert len(manifest["artifacts"]) == 10


@pytest.mark.parametrize(
    ("schema_path", "fixture_path"),
    [
        (
            "schemas/extensions/controlled-field-release/1.0/schema.json",
            "fixtures/controlled-field-release-rev-c-d-failure.json",
        ),
        (
            "schemas/extensions/repository-structural-release/1.0/schema.json",
            "fixtures/repository-structural-release-failure.json",
        ),
        (
            "schemas/extensions/repository-verification-release/1.0/schema.json",
            "fixtures/repository-verification-release-failure.json",
        ),
        (
            "schemas/evidence-interpretation/1.0/schema.json",
            "fixtures/evidence-interpretation-ams-pps-50-ohm-v1.json",
        ),
    ],
)
def test_extension_fixture_validates(schema_path: str, fixture_path: str):
    schema = json.loads((ROOT / schema_path).read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    fixture = json.loads((ROOT / fixture_path).read_text(encoding="utf-8"))
    Draft202012Validator(schema).validate(fixture)


def test_all_schemas_are_valid_draft_2020_12():
    for path in sorted((ROOT / "schemas").rglob("*.json")):
        schema = json.loads(path.read_text(encoding="utf-8"))
        assert schema["$schema"] == ("https://json-schema.org/draft/2020-12/schema")
        Draft202012Validator.check_schema(schema)


def test_canonicalization_vectors_are_exact():
    path = ROOT / "canonicalization" / "engineering-context-jcs-1.0" / "vectors.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["profile"] == "engineering-context-jcs-1.0"
    for vector in payload["vectors"]:
        actual = canonical_json_bytes(vector["normalized_json"])
        assert actual.decode() == vector["canonical_utf8"]
        assert canonical_sha256(vector["normalized_json"]) == vector["sha256"]


def test_core_version_and_artifact_version_are_independent():
    artifact = ArtifactRef(
        artifact_type="evidence-packet",
        artifact_schema_version="1.2",
        uri="component-lens://packets/example",
        sha256="a" * 64,
    )
    assert artifact.schema_version == "1.0"
    assert artifact.artifact_schema_version == "1.2"
    with pytest.raises(ValidationError):
        ArtifactRef.model_validate(
            {
                **artifact.model_dump(mode="json"),
                "schema_version": "99.0",
            }
        )


def test_consideration_identity_is_deterministic():
    actual = admission_consideration_id("a" * 64, "facet:kernel-source")
    expected = (
        "admission:"
        + hashlib.sha256(("a" * 64 + "\nfacet:kernel-source").encode()).hexdigest()
    )
    assert actual == expected


def test_interpretation_vector_preserves_wire_identity_and_soft_boundary():
    path = ROOT / "fixtures" / "evidence-interpretation-ams-pps-50-ohm-v1.json"
    receipt = EvidenceInterpretationReceipt.model_validate_json(path.read_bytes())
    assert receipt.sha256() == (
        "4c376fab0d2a4ccaf228313044200e4ed536fb4f58ea3e95cf4ece6ae63a9450"
    )
    assert receipt.hard_terminal_state == "project-evidence-required"
    assert (
        receipt.normative_coverage_assertions(
            "receiver-input-electrical-project-selection"
        )
        == []
    )
