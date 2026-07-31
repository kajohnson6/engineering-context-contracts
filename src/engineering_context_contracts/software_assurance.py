"""Neutral release contracts for admitted software-coverage obligations."""

from __future__ import annotations

from typing import Literal

from pydantic import Field, model_validator

from engineering_context_contracts.core import (
    ArtifactRef,
    SharedContract,
    canonical_sha256,
)


class SoftwareCoverageObligation(SharedContract):
    obligation_id: str = Field(min_length=1, max_length=200)
    source_locator: str = Field(min_length=1, max_length=1000)
    requirement_statement: str = Field(min_length=1, max_length=4000)
    tier: Literal[1, 2, 3]
    threshold_percent: float = Field(ge=0, le=100)
    subject: Literal["non-cots-microprocessor-software"]
    metric_label: Literal["source-code-structural-coverage"]
    verification_method: Literal["demonstration"]
    excluded_source_kinds: list[
        Literal["third-party-cots", "third-party-open-source"]
    ] = Field(min_length=1)
    source: ArtifactRef

    @model_validator(mode="after")
    def exclusions_are_unique(self) -> SoftwareCoverageObligation:
        if len(self.excluded_source_kinds) != len(
            set(self.excluded_source_kinds)
        ):
            raise ValueError("excluded source kinds must be unique")
        return self


class SoftwareCoverageObligationSet(SharedContract):
    artifact_type: Literal["software-coverage-obligation-set"] = (
        "software-coverage-obligation-set"
    )
    set_id: str = Field(min_length=1, max_length=300)
    project_id: str = Field(min_length=1, max_length=300)
    standard: str = Field(min_length=1, max_length=300)
    standard_revision: str = Field(min_length=1, max_length=200)
    standard_source: ArtifactRef
    admission_receipt: ArtifactRef
    authority_class: Literal["normative"] = "normative"
    obligations: list[SoftwareCoverageObligation] = Field(min_length=1)
    lower_tiers_are_cumulative: Literal[True] = True
    coverage_scope: Literal["enumerated-obligations-only"] = (
        "enumerated-obligations-only"
    )
    whole_standard_coverage_claimed: Literal[False] = False
    synthetic_fixture: bool = False

    @model_validator(mode="after")
    def obligations_are_unique_and_consistent(
        self,
    ) -> SoftwareCoverageObligationSet:
        identities = [item.obligation_id for item in self.obligations]
        if len(identities) != len(set(identities)):
            raise ValueError("software coverage obligation IDs must be unique")
        if any(item.source != self.standard_source for item in self.obligations):
            raise ValueError(
                "software coverage obligation source must equal standard source"
            )
        return self


class SoftwareCoverageObligationReleaseReceipt(SharedContract):
    artifact_type: Literal["software-coverage-obligation-release-receipt"] = (
        "software-coverage-obligation-release-receipt"
    )
    project_id: str = Field(min_length=1, max_length=300)
    recipient: Literal["engineering-memory"]
    access_policy: ArtifactRef
    release_policy: ArtifactRef
    obligation_set: ArtifactRef
    released_obligations: SoftwareCoverageObligationSet
    no_raw_content: Literal[True] = True
    content_contract: Literal[
        "normalized-admitted-software-coverage-obligations-and-references-only"
    ] = (
        "normalized-admitted-software-coverage-obligations-and-references-only"
    )

    @model_validator(mode="after")
    def references_are_closed(
        self,
    ) -> SoftwareCoverageObligationReleaseReceipt:
        if self.access_policy.artifact_type != "controlled-access-policy":
            raise ValueError("access_policy must identify a controlled policy")
        if (
            self.release_policy.artifact_type
            != "software-coverage-obligation-release-policy"
        ):
            raise ValueError("release_policy has the wrong artifact type")
        if (
            self.obligation_set.artifact_type
            != self.released_obligations.artifact_type
            or self.obligation_set.sha256
            != canonical_sha256(self.released_obligations)
        ):
            raise ValueError("obligation_set reference mismatch")
        if self.project_id != self.released_obligations.project_id:
            raise ValueError("released obligation project mismatch")
        return self


class SoftwareCoverageObligationReleaseRecord(SharedContract):
    reference: ArtifactRef
    receipt: SoftwareCoverageObligationReleaseReceipt

    @model_validator(mode="after")
    def reference_matches_receipt(
        self,
    ) -> SoftwareCoverageObligationReleaseRecord:
        digest = canonical_sha256(self.receipt)
        if (
            self.reference.artifact_type != self.receipt.artifact_type
            or self.reference.sha256 != digest
            or self.reference.uri
            != (
                f"controlled-project://{self.receipt.project_id}/"
                f"software-coverage-obligation-releases/{digest}"
            )
        ):
            raise ValueError(
                "software coverage obligation release reference mismatch"
            )
        return self

