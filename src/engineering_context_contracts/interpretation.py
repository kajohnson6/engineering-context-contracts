"""Provider-neutral, provenance-linked evidence interpretation contract."""

from __future__ import annotations

import hashlib
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from engineering_context_contracts.core import canonical_json_bytes


class InterpretationModel(BaseModel):
    """Fail closed while preserving the interpretation v1.0 wire shape."""

    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class AssertionMode(StrEnum):
    NORMATIVE = "normative"
    DERIVED = "derived"
    PLAUSIBLE = "plausible"
    RECOMMENDATION = "recommendation"


class AuthorityEffect(StrEnum):
    SCOPED_AUTHORITATIVE = "scoped-authoritative"
    APPLICABILITY_BINDING = "applicability-binding"
    INFORMATIVE_ONLY = "informative-only"


class DependencySemantics(StrEnum):
    NORMATIVE_DELEGATION = "normative-delegation"
    PROJECT_SELECTION = "project-selection"
    SCHEMA_DEPENDENCY = "schema-dependency"
    INCORPORATION_BY_REFERENCE = "incorporation-by-reference"
    INFORMATIVE_REFERENCE = "informative-reference"


class InterpretationLifecycleState(StrEnum):
    ACTIVE = "active"
    SUPERSEDED = "superseded"
    QUARANTINED = "quarantined"


class InterpretationMaturity(StrEnum):
    DRAFT = "draft"
    EVIDENCE_REVIEWED = "evidence-reviewed"
    ENGINEERING_REVIEWED = "engineering-reviewed"
    SUPERSEDED = "superseded"
    QUARANTINED = "quarantined"


class ReviewState(StrEnum):
    UNREVIEWED = "unreviewed"
    ACCEPTED = "accepted"
    CHALLENGED = "challenged"
    REQUIRES_PROJECT_EVIDENCE = "requires-project-evidence"


class ConfidenceBasisKind(StrEnum):
    DIRECT_CLAUSE = "direct-clause"
    TABLE_STRUCTURE = "table-structure"
    CROSS_CLAUSE_CONSISTENCY = "cross-clause-consistency"
    ENGINEERING_PRINCIPLE = "engineering-principle"
    ABSENCE_OF_BINDING_SELECTION = "absence-of-binding-selection"
    VERIFIED_EXPERIMENT = "verified-experiment"


class InterpretationArtifactRef(InterpretationModel):
    artifact_type: Literal[
        "standards-source",
        "derived-retrieval-aid",
        "evidence-page",
        "staged-dependency-admission",
        "dependency-manifest",
        "dependency-correction",
        "interpretation-receipt",
    ]
    uri: str = Field(min_length=1)
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    artifact_schema_version: str | None = None


class InterpretationEvidenceRef(InterpretationModel):
    evidence_id: str = Field(min_length=1)
    authority_artifact_ref: InterpretationArtifactRef
    locator_artifact_ref: InterpretationArtifactRef | None = None
    clause: str = Field(min_length=1)
    locator: str = Field(min_length=1)
    authority_scope: list[str] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_locator(self) -> InterpretationEvidenceRef:
        if self.authority_artifact_ref.artifact_type == "derived-retrieval-aid":
            raise ValueError("authority must bind an original artifact")
        if self.locator_artifact_ref is not None and (
            self.locator_artifact_ref.artifact_type
            not in {"derived-retrieval-aid", "evidence-page"}
        ):
            raise ValueError("locator must be a retrieval aid or evidence page")
        return self


class InterpretationEdgeStep(InterpretationModel):
    edge_id: str = Field(min_length=1)
    source_artifact_id: str = Field(min_length=1)
    target_artifact_id: str = Field(min_length=1)
    semantics: DependencySemantics
    authority_effect: AuthorityEffect
    lifecycle_state: InterpretationLifecycleState = InterpretationLifecycleState.ACTIVE
    scope: list[str] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_edge_effect(self) -> InterpretationEdgeStep:
        expected = {
            DependencySemantics.NORMATIVE_DELEGATION: (
                AuthorityEffect.SCOPED_AUTHORITATIVE
            ),
            DependencySemantics.PROJECT_SELECTION: (
                AuthorityEffect.APPLICABILITY_BINDING
            ),
            DependencySemantics.SCHEMA_DEPENDENCY: (
                AuthorityEffect.SCOPED_AUTHORITATIVE
            ),
            DependencySemantics.INCORPORATION_BY_REFERENCE: (
                AuthorityEffect.SCOPED_AUTHORITATIVE
            ),
            DependencySemantics.INFORMATIVE_REFERENCE: (
                AuthorityEffect.INFORMATIVE_ONLY
            ),
        }[self.semantics]
        if self.authority_effect != expected:
            raise ValueError("edge semantics and authority effect disagree")
        return self


class InterpretationAssumption(InterpretationModel):
    assumption_id: str = Field(min_length=1)
    statement: str = Field(min_length=1)
    state: Literal["explicit", "verified", "unverified"]
    consequence_if_false: str = Field(min_length=1)


class InterpretationAmbiguity(InterpretationModel):
    ambiguity_id: str = Field(min_length=1)
    statement: str = Field(min_length=1)
    evidence_ids: list[str] = Field(min_length=1)
    impact: str = Field(min_length=1)


class ConfidenceBasis(InterpretationModel):
    kind: ConfidenceBasisKind
    statement: str = Field(min_length=1)
    evidence_ids: list[str] = Field(default_factory=list)
    effect: Literal["supports", "limits"]


class InterpretationAlternative(InterpretationModel):
    alternative_id: str = Field(min_length=1)
    statement: str = Field(min_length=1)
    disposition: Literal["open", "less-plausible", "conditionally-applicable"]
    rationale: str = Field(min_length=1)
    evidence_ids: list[str] = Field(default_factory=list)


class ClosureAction(InterpretationModel):
    action_id: str = Field(min_length=1)
    action: str = Field(min_length=1)
    required_artifact_kinds: list[str] = Field(default_factory=list)
    completion_criterion: str = Field(min_length=1)


class ApplicabilityContext(InterpretationModel):
    project_baseline: str = Field(min_length=1)
    configuration: str = Field(min_length=1)
    standard_versions: list[str] = Field(min_length=1)
    access_policy: str = Field(min_length=1)


class EvidenceInterpretationAssertion(InterpretationModel):
    assertion_id: str = Field(min_length=1)
    mode: AssertionMode
    statement: str = Field(min_length=1)
    normalized_assertion: str = Field(min_length=1)
    evidence_ids: list[str] = Field(min_length=1)
    edge_path: list[InterpretationEdgeStep] = Field(default_factory=list)
    authority_scope: list[str] = Field(min_length=1)
    authority_effect: AuthorityEffect
    assumptions: list[InterpretationAssumption] = Field(default_factory=list)
    ambiguities_and_counterevidence: list[InterpretationAmbiguity] = Field(
        default_factory=list
    )
    confidence_level: Literal["low", "moderate", "high"]
    confidence_basis: list[ConfidenceBasis] = Field(min_length=1)
    alternatives_considered: list[InterpretationAlternative] = Field(min_length=1)
    engineering_consequence_if_wrong: str = Field(min_length=1)
    closure_actions: list[ClosureAction] = Field(min_length=1)
    applicability: ApplicabilityContext
    maturity: InterpretationMaturity
    review_state: ReviewState
    normative_coverage_allowed: bool = False
    eligible_obligation_ids: list[str] = Field(default_factory=list)
    authority_promotion_prohibited: bool = True

    @model_validator(mode="after")
    def prohibit_soft_authority(self) -> EvidenceInterpretationAssertion:
        if self.mode != AssertionMode.NORMATIVE and (
            self.normative_coverage_allowed or self.eligible_obligation_ids
        ):
            raise ValueError("non-normative assertions cannot satisfy obligations")
        if self.mode in {
            AssertionMode.PLAUSIBLE,
            AssertionMode.RECOMMENDATION,
        }:
            if self.authority_effect != AuthorityEffect.INFORMATIVE_ONLY:
                raise ValueError(
                    "plausible/recommendation authority is informative only"
                )
            if not self.authority_promotion_prohibited:
                raise ValueError("soft assertions cannot be promoted")
        if self.normative_coverage_allowed:
            if not self.eligible_obligation_ids:
                raise ValueError("normative coverage requires exact obligation IDs")
            if self.authority_effect == AuthorityEffect.INFORMATIVE_ONLY:
                raise ValueError("informative evidence cannot satisfy obligations")
            if not any(
                basis.kind == ConfidenceBasisKind.DIRECT_CLAUSE
                and basis.effect == "supports"
                for basis in self.confidence_basis
            ):
                raise ValueError("normative coverage requires direct-clause support")
        return self


class InterpretationLifecycleEvent(InterpretationModel):
    event_id: str = Field(min_length=1)
    assertion_id: str = Field(min_length=1)
    state: InterpretationLifecycleState
    replacements: list[str] = Field(default_factory=list)
    reason: str = Field(min_length=1)
    evidence_ids: list[str] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_replacement(self) -> InterpretationLifecycleEvent:
        if (self.state == InterpretationLifecycleState.SUPERSEDED) != bool(
            self.replacements
        ):
            raise ValueError("only superseded events require replacements")
        return self


class EvidenceInterpretationReceipt(InterpretationModel):
    schema_version: Literal["1.0"] = "1.0"
    receipt_id: str = Field(min_length=1)
    question: str = Field(min_length=1)
    source_admission_ref: InterpretationArtifactRef
    effective_manifest_ref: InterpretationArtifactRef
    correction_ref: InterpretationArtifactRef
    hard_terminal_state: Literal[
        "ready",
        "unsatisfied",
        "project-evidence-required",
    ]
    evidence_catalog: list[InterpretationEvidenceRef] = Field(min_length=1)
    assertions: list[EvidenceInterpretationAssertion] = Field(min_length=1)
    lifecycle_events: list[InterpretationLifecycleEvent] = Field(default_factory=list)
    content_contract: Literal[
        "normalized-assertions-and-provenance-only;"
        "no-raw-content;no-hidden-controller-frontier"
    ] = (
        "normalized-assertions-and-provenance-only;"
        "no-raw-content;no-hidden-controller-frontier"
    )

    @model_validator(mode="after")
    def validate_graph(self) -> EvidenceInterpretationReceipt:
        evidence_ids = [item.evidence_id for item in self.evidence_catalog]
        if len(evidence_ids) != len(set(evidence_ids)):
            raise ValueError("evidence IDs must be unique")
        assertion_ids = [item.assertion_id for item in self.assertions]
        if len(assertion_ids) != len(set(assertion_ids)):
            raise ValueError("assertion IDs must be unique")
        known_evidence = set(evidence_ids)
        for assertion in self.assertions:
            referenced = set(assertion.evidence_ids)
            referenced.update(
                evidence_id
                for item in assertion.ambiguities_and_counterevidence
                for evidence_id in item.evidence_ids
            )
            referenced.update(
                evidence_id
                for basis in assertion.confidence_basis
                for evidence_id in basis.evidence_ids
            )
            referenced.update(
                evidence_id
                for alternative in assertion.alternatives_considered
                for evidence_id in alternative.evidence_ids
            )
            if referenced - known_evidence:
                raise ValueError("assertion references unknown evidence")
        for event in self.lifecycle_events:
            if event.assertion_id not in assertion_ids:
                raise ValueError("lifecycle event references unknown assertion")
            if set(event.replacements) - set(assertion_ids):
                raise ValueError("lifecycle replacement is unknown")
            if set(event.evidence_ids) - known_evidence:
                raise ValueError("lifecycle event references unknown evidence")
        return self

    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self)

    def sha256(self) -> str:
        return hashlib.sha256(self.canonical_bytes()).hexdigest()

    def normative_coverage_assertions(
        self,
        obligation_id: str,
    ) -> list[EvidenceInterpretationAssertion]:
        """Return only assertions structurally eligible for exact coverage."""

        superseded = {
            event.assertion_id
            for event in self.lifecycle_events
            if event.state != InterpretationLifecycleState.ACTIVE
        }
        return [
            assertion
            for assertion in self.assertions
            if assertion.assertion_id not in superseded
            and assertion.mode == AssertionMode.NORMATIVE
            and assertion.normative_coverage_allowed
            and obligation_id in assertion.eligible_obligation_ids
        ]
