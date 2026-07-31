import pytest
from pydantic import ValidationError

from engineering_context_contracts import (
    ArtifactRef,
    SoftwareCoverageObligation,
    SoftwareCoverageObligationReleaseReceipt,
    SoftwareCoverageObligationReleaseRecord,
    SoftwareCoverageObligationSet,
    canonical_sha256,
)


def _ref(kind: str, marker: str) -> ArtifactRef:
    return ArtifactRef(
        artifact_type=kind,
        artifact_schema_version="1.0",
        uri=f"controlled-project://synthetic/{kind}/{marker}",
        sha256=marker * 64,
    )


def _obligation_set() -> SoftwareCoverageObligationSet:
    source = _ref("authoritative-standard-document", "a")
    return SoftwareCoverageObligationSet(
        set_id="ams-gra-software-coverage-2026.01",
        project_id="synthetic-radio",
        standard="AMS-GRA",
        standard_revision="2026.01",
        standard_source=source,
        admission_receipt=_ref("evidence-admission-receipt", "b"),
        obligations=[
            SoftwareCoverageObligation(
                obligation_id="GRA-MPU-046",
                source_locator="Digital Payload Processor MPU, GRA-MPU-046",
                requirement_statement=(
                    "Provide automated tests of non-COTS microprocessor "
                    "software with at least 50% source-code structural "
                    "coverage, excluding named third-party library classes."
                ),
                tier=1,
                threshold_percent=50,
                subject="non-cots-microprocessor-software",
                metric_label="source-code-structural-coverage",
                verification_method="demonstration",
                excluded_source_kinds=[
                    "third-party-cots",
                    "third-party-open-source",
                ],
                source=source,
            )
        ],
    )


def _receipt() -> SoftwareCoverageObligationReleaseReceipt:
    obligations = _obligation_set()
    return SoftwareCoverageObligationReleaseReceipt(
        project_id=obligations.project_id,
        recipient="engineering-memory",
        access_policy=_ref("controlled-access-policy", "c"),
        release_policy=_ref(
            "software-coverage-obligation-release-policy", "d"
        ),
        obligation_set=ArtifactRef(
            artifact_type=obligations.artifact_type,
            artifact_schema_version=obligations.schema_version,
            uri=(
                "component-lens://software-coverage-obligation-sets/"
                f"{canonical_sha256(obligations)}"
            ),
            sha256=canonical_sha256(obligations),
        ),
        released_obligations=obligations,
    )


def test_release_record_closes_all_content_identities() -> None:
    receipt = _receipt()
    digest = canonical_sha256(receipt)
    record = SoftwareCoverageObligationReleaseRecord(
        reference=ArtifactRef(
            artifact_type=receipt.artifact_type,
            artifact_schema_version=receipt.schema_version,
            uri=(
                "controlled-project://synthetic-radio/"
                f"software-coverage-obligation-releases/{digest}"
            ),
            sha256=digest,
        ),
        receipt=receipt,
    )

    assert record.reference.sha256 == digest
    assert record.receipt.released_obligations.whole_standard_coverage_claimed is False


def test_receipt_rejects_tampered_obligation_set_reference() -> None:
    receipt = _receipt()
    with pytest.raises(ValidationError, match="obligation_set reference mismatch"):
        SoftwareCoverageObligationReleaseReceipt.model_validate(
            {
                **receipt.model_dump(mode="json"),
                "obligation_set": {
                    **receipt.obligation_set.model_dump(mode="json"),
                    "sha256": "f" * 64,
                },
            }
        )


def test_requirement_source_must_match_admitted_standard() -> None:
    obligations = _obligation_set()
    changed = obligations.obligations[0].model_copy(
        update={"source": _ref("authoritative-standard-document", "e")}
    )
    with pytest.raises(
        ValidationError,
        match="source must equal standard source",
    ):
        SoftwareCoverageObligationSet.model_validate(
            {
                **obligations.model_dump(mode="json"),
                "obligations": [changed.model_dump(mode="json")],
            }
        )
