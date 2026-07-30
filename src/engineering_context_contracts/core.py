"""Provider-neutral engineering evidence lifecycle and serving contracts."""

from __future__ import annotations

import hashlib
import re
from datetime import UTC, datetime
from enum import StrEnum
from typing import Annotated, Any, Literal
from uuid import UUID, uuid4

import rfc8785
from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

Sha256 = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
ContractVersion = Literal["1.0"]


def _aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timestamp must include a timezone")
    return value.astimezone(UTC)


AwareDatetime = Annotated[datetime, AfterValidator(_aware_utc)]


class LifecycleState(StrEnum):
    ACTIVE = "active"
    SUPERSEDED = "superseded"
    DEPRECATED = "deprecated"
    RETRACTED = "retracted"
    QUARANTINED = "quarantined"
    TOMBSTONED = "tombstoned"


class DispositionStatus(StrEnum):
    APPLIED = "applied"
    REJECTED = "rejected"
    NOT_APPLICABLE = "not_applicable"


class FeedbackReasonCode(StrEnum):
    USEFUL_APPLIED = "useful-applied"
    USEFUL_NOT_APPLICABLE = "useful-not-applicable"
    IRRELEVANT = "irrelevant"
    STALE_VERSION = "stale-version"
    INCORRECT = "incorrect"
    CONTRADICTED_BY_EXPERIMENT = "contradicted-by-experiment"
    DUPLICATE = "duplicate"
    OVERLY_BROAD = "overly-broad"
    UNSAFE = "unsafe"
    LICENSE_INCOMPATIBLE = "license-incompatible"


class LifecycleReasonCode(StrEnum):
    INITIAL_ACTIVATION = "initial-activation"
    AUTHORITATIVE_REVISION = "authoritative-revision"
    POLICY_CHANGE = "policy-change"
    MANUAL_REVIEW = "manual-review"
    SECRET_EXPOSURE = "secret-exposure"
    LEGAL_LICENSE_PURGE = "legal-license-purge"
    POISONED_CONTENT = "poisoned-content"
    STALE_VERSION = "stale-version"
    INCORRECT = "incorrect"
    CONTRADICTED_BY_EXPERIMENT = "contradicted-by-experiment"
    DUPLICATE = "duplicate"
    OVERLY_BROAD = "overly-broad"
    UNSAFE = "unsafe"
    LICENSE_INCOMPATIBLE = "license-incompatible"


class ApplicabilityDecision(StrEnum):
    APPLICABLE = "applicable"
    NOT_APPLICABLE = "not_applicable"
    REQUIRES_REVIEW = "requires_review"


class CorrectnessAssessment(StrEnum):
    CORRECT = "correct"
    INCORRECT = "incorrect"
    CONTRADICTED = "contradicted"
    REQUIRES_REVIEW = "requires_review"
    NOT_ASSESSED = "not_assessed"


class UtilityAssessment(StrEnum):
    USEFUL = "useful"
    NEUTRAL = "neutral"
    NOT_USEFUL = "not_useful"
    NOT_ASSESSED = "not_assessed"


class OutcomeStatus(StrEnum):
    PASS = "pass"
    FAIL = "fail"
    REVIEW = "review"


class MetricDirection(StrEnum):
    LOWER_IS_BETTER = "lower_is_better"
    HIGHER_IS_BETTER = "higher_is_better"
    NEUTRAL = "neutral"


class CacheLayer(StrEnum):
    EXACT_QUERY = "exact_query"
    STRUCTURED_OBLIGATION = "structured_obligation"
    HOT_EVIDENCE = "hot_evidence"


class CacheDisposition(StrEnum):
    HIT = "hit"
    MISS = "miss"
    BYPASS = "bypass"
    NEGATIVE_HIT = "negative_hit"


class SharedContract(BaseModel):
    """Fail closed when a producer adds semantics without a version change."""

    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    schema_version: ContractVersion = "1.0"


class ArtifactRef(SharedContract):
    """Provider-neutral locator plus content identity.

    ``uri`` may move or expire.  ``sha256`` is the artifact identity.
    """

    artifact_type: str = Field(min_length=1, max_length=100)
    uri: str = Field(min_length=1, max_length=2000)
    sha256: Sha256
    artifact_schema_version: str | None = Field(default=None, max_length=100)


class ApplicabilityEnvelope(SharedContract):
    tool_identity: str | None = Field(default=None, max_length=300)
    tool_version: str | None = Field(default=None, max_length=100)
    tool_version_min_inclusive: str | None = Field(default=None, max_length=100)
    tool_version_max_exclusive: str | None = Field(default=None, max_length=100)
    architectures: list[str] = Field(default_factory=list)
    device_families: list[str] = Field(default_factory=list)
    exact_devices: list[str] = Field(default_factory=list)
    silicon_steppings: list[str] = Field(default_factory=list)
    repository_uri: str | None = Field(default=None, max_length=2000)
    repository_tag: str | None = Field(default=None, max_length=300)
    repository_commit: str | None = Field(default=None, max_length=200)
    repository_revision: str | None = Field(default=None, max_length=200)
    repository_revision_min: str | None = Field(default=None, max_length=200)
    repository_revision_max: str | None = Field(default=None, max_length=200)
    document_id: str | None = Field(default=None, max_length=500)
    corpus_snapshot_sha256: Sha256 | None = None
    document_revision: str | None = Field(default=None, max_length=200)
    corpus_revision: str | None = Field(default=None, max_length=200)
    project_configuration_sha256: Sha256 | None = None
    configuration_selectors: dict[str, str] = Field(default_factory=dict)
    consumer_models: list[str] = Field(default_factory=list)
    agent_profiles: list[str] = Field(default_factory=list)
    valid_from: AwareDatetime | None = None
    valid_until: AwareDatetime | None = None
    access_policy_sha256: Sha256 | None = None
    policy_domain: str | None = Field(default=None, max_length=300)

    @model_validator(mode="after")
    def validity_interval_is_ordered(self) -> ApplicabilityEnvelope:
        if (
            self.valid_from is not None
            and self.valid_until is not None
            and self.valid_from >= self.valid_until
        ):
            raise ValueError("valid_from must be earlier than valid_until")
        return self


class RequiredConsideration(SharedContract):
    consideration_id: str = Field(pattern=r"^[a-zA-Z0-9][a-zA-Z0-9._:-]{0,199}$")
    text: str = Field(min_length=1, max_length=4000)
    source: ArtifactRef
    basis: Literal["admitted_obligation", "verified_fact"]
    source_obligation_id: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def admitted_obligation_has_deterministic_identity(
        self,
    ) -> RequiredConsideration:
        if self.basis == "admitted_obligation":
            if not self.source_obligation_id:
                raise ValueError(
                    "admitted_obligation requires source_obligation_id"
                )
            expected = admission_consideration_id(
                self.source.sha256,
                self.source_obligation_id,
            )
            if self.consideration_id != expected:
                raise ValueError(
                    "admitted obligation consideration_id must equal "
                    f"{expected}"
                )
        elif self.source_obligation_id is not None:
            raise ValueError(
                "source_obligation_id is only valid for admitted_obligation"
            )
        return self


class LifecycleEvent(SharedContract):
    event_id: UUID = Field(default_factory=uuid4)
    occurred_at: AwareDatetime = Field(default_factory=lambda: datetime.now(UTC))
    target: ArtifactRef
    previous_state: LifecycleState | None = None
    next_state: LifecycleState
    reason_code: LifecycleReasonCode
    actor_class: str = Field(min_length=1, max_length=100)
    actor_identity: str = Field(min_length=1, max_length=300)
    supporting_artifacts: list[ArtifactRef] = Field(default_factory=list)
    supersedes: list[ArtifactRef] = Field(default_factory=list)
    replacements: list[ArtifactRef] = Field(default_factory=list)
    applicability: ApplicabilityEnvelope = Field(
        default_factory=ApplicabilityEnvelope
    )
    required_considerations: list[RequiredConsideration] = Field(
        default_factory=list
    )
    predecessor_event_sha256: Sha256 | None = None
    transition_id: UUID | None = None
    purge_authorization: ArtifactRef | None = None
    tombstone_metadata: dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="after")
    def destructive_states_have_required_provenance(self) -> LifecycleEvent:
        if self.next_state is LifecycleState.TOMBSTONED:
            if self.purge_authorization is None:
                raise ValueError("tombstoning requires purge_authorization")
            if not self.tombstone_metadata:
                raise ValueError("tombstoning requires tombstone_metadata")
        is_supersession = bool(self.supersedes or self.replacements) or (
            self.next_state is LifecycleState.SUPERSEDED
        )
        if is_supersession and self.transition_id is None:
            raise ValueError("supersession requires transition_id")
        if self.next_state is LifecycleState.SUPERSEDED and (
            not self.replacements or self.supersedes
        ):
            raise ValueError(
                "superseded target requires replacements and no supersedes"
            )
        if self.supersedes:
            if self.next_state is not LifecycleState.ACTIVE:
                raise ValueError("replacement target must transition to active")
            if self.replacements:
                raise ValueError(
                    "replacement target cannot also list replacements"
                )
        return self


class FeedbackEvent(SharedContract):
    event_id: UUID = Field(default_factory=uuid4)
    occurred_at: AwareDatetime = Field(default_factory=lambda: datetime.now(UTC))
    target: ArtifactRef
    reason_code: FeedbackReasonCode
    correctness: CorrectnessAssessment
    applicability: ApplicabilityDecision
    utility: UtilityAssessment
    delivery_disposition: DispositionStatus | None = None
    actor_class: str = Field(min_length=1, max_length=100)
    actor_identity: str = Field(min_length=1, max_length=300)
    request_context: ApplicabilityEnvelope = Field(
        default_factory=ApplicabilityEnvelope
    )
    supporting_artifacts: list[ArtifactRef] = Field(default_factory=list)
    outcome_references: list[ArtifactRef] = Field(default_factory=list)
    requested_lifecycle_transition: LifecycleState | None = None
    explanation: str = Field(default="", max_length=4000)


class EvidenceDeliveryReceipt(SharedContract):
    receipt_id: UUID = Field(default_factory=uuid4)
    delivered_at: AwareDatetime = Field(default_factory=lambda: datetime.now(UTC))
    task_id: str = Field(min_length=1, max_length=500)
    consumer_identity: str = Field(min_length=1, max_length=300)
    consumer_profile: str | None = Field(default=None, max_length=300)
    packet: ArtifactRef
    admission_receipt: ArtifactRef
    resolver_receipt: ArtifactRef
    cache_receipt: ArtifactRef | None = None
    policy: ArtifactRef
    applicability_result: ApplicabilityDecision
    evidence_applicability: ApplicabilityEnvelope = Field(
        default_factory=ApplicabilityEnvelope
    )
    request_context: ApplicabilityEnvelope = Field(
        default_factory=ApplicabilityEnvelope
    )
    required_considerations: list[RequiredConsideration] = Field(
        default_factory=list
    )

    @field_validator("required_considerations")
    @classmethod
    def consideration_ids_are_unique(
        cls, values: list[RequiredConsideration]
    ) -> list[RequiredConsideration]:
        ids = [value.consideration_id for value in values]
        if len(ids) != len(set(ids)):
            raise ValueError("required consideration IDs must be unique")
        return values

    @model_validator(mode="after")
    def admitted_obligations_reference_admission_receipt(
        self,
    ) -> EvidenceDeliveryReceipt:
        if (
            self.request_context.access_policy_sha256 is not None
            and self.request_context.access_policy_sha256
            != self.policy.sha256
        ):
            raise ValueError(
                "delivery policy must match request access policy"
            )
        for consideration in self.required_considerations:
            if (
                consideration.basis == "admitted_obligation"
                and consideration.source.sha256
                != self.admission_receipt.sha256
            ):
                raise ValueError(
                    "admitted obligation source must be admission_receipt"
                )
        return self


class ConsiderationDisposition(SharedContract):
    disposition_id: UUID = Field(default_factory=uuid4)
    recorded_at: AwareDatetime = Field(default_factory=lambda: datetime.now(UTC))
    delivery_receipt_sha256: Sha256
    consideration_id: str = Field(
        pattern=r"^[a-zA-Z0-9][a-zA-Z0-9._:-]{0,199}$"
    )
    disposition: DispositionStatus
    reason_code: FeedbackReasonCode | None = None
    explanation: str = Field(default="", max_length=4000)
    implementation_reference: ArtifactRef | None = None
    citation_reference: ArtifactRef | None = None
    outcome_reference: ArtifactRef | None = None

    @model_validator(mode="after")
    def non_application_has_a_reason(self) -> ConsiderationDisposition:
        if self.disposition is not DispositionStatus.APPLIED:
            if self.reason_code is None:
                raise ValueError("rejected/not_applicable requires reason_code")
            if not self.explanation.strip():
                raise ValueError("rejected/not_applicable requires explanation")
        return self


class OutcomeMetric(SharedContract):
    name: str = Field(min_length=1, max_length=300)
    value: int | float | str | bool
    unit: str = Field(min_length=1, max_length=100)
    direction: MetricDirection


class EvidenceOutcomeReceipt(SharedContract):
    receipt_id: UUID = Field(default_factory=uuid4)
    recorded_at: AwareDatetime = Field(default_factory=lambda: datetime.now(UTC))
    delivery_receipt_sha256: Sha256
    disposition_references: list[ArtifactRef] = Field(default_factory=list)
    execution_environment: dict[str, Any] = Field(default_factory=dict)
    version_pins: dict[str, str] = Field(default_factory=dict)
    result_artifacts: list[ArtifactRef] = Field(default_factory=list)
    metrics: list[OutcomeMetric] = Field(default_factory=list)
    outcome: OutcomeStatus
    producer: str = Field(min_length=1, max_length=300)


class CacheReceipt(SharedContract):
    receipt_id: UUID = Field(default_factory=uuid4)
    recorded_at: AwareDatetime = Field(default_factory=lambda: datetime.now(UTC))
    cache_layer: CacheLayer
    canonical_key_sha256: Sha256
    key_components: dict[str, Any]
    disposition: CacheDisposition
    reused_artifacts: list[ArtifactRef] = Field(default_factory=list)
    lifecycle_check_performed: bool
    applicability_check_performed: bool
    policy_check_performed: bool
    producer_version: str = Field(min_length=1, max_length=200)
    unsatisfied_obligations: list[str] = Field(default_factory=list)
    review_after: AwareDatetime | None = None
    negative_failure_class: Literal["semantic_unsatisfied"] | None = None

    @model_validator(mode="after")
    def negative_hits_are_semantic_and_bounded(self) -> CacheReceipt:
        exact_required = {
            "normalized_query",
            "corpus_snapshot_sha256",
            "model_revisions",
            "index_revisions",
            "snapshot_digests",
            "retrieval_route",
            "retrieval_parameters",
            "required_code_paths",
            "code_evidence_policy",
            "access_policy_sha256",
            "applicability_context_sha256",
            "admission_policy_version",
        }
        obligation_required = exact_required | {
            "subject_anchor",
            "vendor_anchor",
            "authority_anchor",
            "product_anchor",
            "facets",
            "required_source_paths",
            "complete_file_policy",
            "evidence_diversity_policy_version",
        }
        hot_required = {
            "artifact_sha256",
            "access_policy_sha256",
            "applicability_context_sha256",
            "serving_policy_version",
            "model_revisions",
            "index_revisions",
            "snapshot_digests",
        }
        required = (
            obligation_required
            if self.cache_layer is CacheLayer.STRUCTURED_OBLIGATION
            else exact_required
            if self.cache_layer is CacheLayer.EXACT_QUERY
            else hot_required
        )
        missing = sorted(required - self.key_components.keys())
        if missing:
            raise ValueError(
                "cache key is missing required components: "
                + ", ".join(missing)
            )
        required_lanes = {
            "dense_page_text",
            "dense_code",
            "colpali_visual",
            "reranker",
            "selector",
            "query_expansion",
            "policy",
        }
        required_indexes = {"page", "text", "code", "visual"}
        required_snapshots = {"page", "text", "code", "visual"}
        self._require_named_lanes(
            "model_revisions",
            required_lanes,
            allow_not_applicable=True,
        )
        self._require_named_lanes(
            "index_revisions",
            required_indexes,
            allow_not_applicable=True,
        )
        self._require_named_lanes(
            "snapshot_digests",
            required_snapshots,
            allow_not_applicable=True,
            require_digests=True,
        )
        self._require_canonical_string_set("required_code_paths")
        if self.cache_layer is CacheLayer.STRUCTURED_OBLIGATION:
            self._require_canonical_string_set("facets")
            self._require_canonical_string_set("required_source_paths")
        expected_key_sha256 = canonical_sha256(self.key_components)
        if self.canonical_key_sha256 != expected_key_sha256:
            raise ValueError(
                "canonical_key_sha256 does not match key_components"
            )
        if self.disposition is CacheDisposition.NEGATIVE_HIT:
            if not self.unsatisfied_obligations:
                raise ValueError(
                    "negative cache hit requires unsatisfied_obligations"
                )
            if self.review_after is None:
                raise ValueError("negative cache hit requires review_after")
            if self.negative_failure_class != "semantic_unsatisfied":
                raise ValueError(
                    "negative cache hit must be semantic_unsatisfied"
                )
        elif self.negative_failure_class is not None:
            raise ValueError(
                "negative_failure_class is only valid for a negative hit"
            )
        return self

    def _require_named_lanes(
        self,
        field_name: str,
        required: set[str],
        *,
        allow_not_applicable: bool,
        require_digests: bool = False,
    ) -> None:
        value = self.key_components.get(field_name)
        if not isinstance(value, dict):
            raise ValueError(f"{field_name} must be an object")
        missing = sorted(required - value.keys())
        if missing:
            raise ValueError(
                f"{field_name} is missing required lanes: "
                + ", ".join(missing)
            )
        for lane in required:
            revision = value[lane]
            if allow_not_applicable and revision == "not-applicable":
                continue
            if not isinstance(revision, str) or not revision:
                raise ValueError(
                    f"{field_name}.{lane} must be a revision or "
                    "not-applicable"
                )
            if require_digests and not re.fullmatch(
                r"[0-9a-f]{64}",
                revision,
            ):
                raise ValueError(
                    f"{field_name}.{lane} must be SHA-256 or not-applicable"
                )

    def _require_canonical_string_set(self, field_name: str) -> None:
        value = self.key_components.get(field_name)
        if (
            not isinstance(value, list)
            or not all(isinstance(item, str) and item for item in value)
            or value != sorted(set(value))
        ):
            raise ValueError(
                f"{field_name} must be a sorted unique string array"
            )


class ResolveEvidenceRequest(SharedContract):
    request_id: UUID = Field(default_factory=uuid4)
    requested_at: AwareDatetime = Field(default_factory=lambda: datetime.now(UTC))
    task_id: str = Field(min_length=1, max_length=500)
    request_context: ApplicabilityEnvelope = Field(
        default_factory=ApplicabilityEnvelope
    )
    candidate_artifacts: list[ArtifactRef] = Field(default_factory=list)
    include_deprecated: bool = False


class EligibilityExplanation(SharedContract):
    target: ArtifactRef
    lifecycle_state: LifecycleState | None
    applicability_result: ApplicabilityDecision
    applicability_constraint: ApplicabilityEnvelope = Field(
        default_factory=ApplicabilityEnvelope
    )
    request_context: ApplicabilityEnvelope = Field(
        default_factory=ApplicabilityEnvelope
    )
    eligible: bool
    reasons: list[str] = Field(default_factory=list)
    required_considerations: list[RequiredConsideration] = Field(
        default_factory=list
    )
    lifecycle_event_sha256: Sha256 | None = None


class ResolveEvidenceResponse(SharedContract):
    request_id: UUID
    resolved_at: AwareDatetime = Field(default_factory=lambda: datetime.now(UTC))
    eligible: list[EligibilityExplanation] = Field(default_factory=list)
    excluded: list[EligibilityExplanation] = Field(default_factory=list)
    resolver_receipt: ArtifactRef


class EvidenceResolverReceipt(SharedContract):
    receipt_id: UUID = Field(default_factory=uuid4)
    resolved_at: AwareDatetime = Field(default_factory=lambda: datetime.now(UTC))
    request: ResolveEvidenceRequest
    eligible: list[EligibilityExplanation] = Field(default_factory=list)
    excluded: list[EligibilityExplanation] = Field(default_factory=list)


class SupersessionRequest(SharedContract):
    transition_id: UUID = Field(default_factory=uuid4)
    old_event_id: UUID = Field(default_factory=uuid4)
    new_event_id: UUID = Field(default_factory=uuid4)
    occurred_at: AwareDatetime = Field(default_factory=lambda: datetime.now(UTC))
    old_target: ArtifactRef
    new_target: ArtifactRef
    old_predecessor_event_sha256: Sha256
    reason_code: LifecycleReasonCode = (
        LifecycleReasonCode.AUTHORITATIVE_REVISION
    )
    actor_class: str = Field(min_length=1, max_length=100)
    actor_identity: str = Field(min_length=1, max_length=300)
    supporting_artifacts: list[ArtifactRef] = Field(default_factory=list)
    new_applicability: ApplicabilityEnvelope = Field(
        default_factory=ApplicabilityEnvelope
    )
    new_required_considerations: list[RequiredConsideration] = Field(
        default_factory=list
    )

    @model_validator(mode="after")
    def targets_differ(self) -> SupersessionRequest:
        if self.old_target.sha256 == self.new_target.sha256:
            raise ValueError("supersession targets must differ")
        return self


class SupersessionReceipt(SharedContract):
    transition_id: UUID
    old_event: ArtifactRef
    new_event: ArtifactRef


def admission_consideration_id(
    admission_receipt_sha256: str,
    obligation_id: str,
) -> str:
    """Map an admitted obligation to a deterministic consideration ID."""

    digest = hashlib.sha256(
        f"{admission_receipt_sha256}\n{obligation_id}".encode()
    ).hexdigest()
    return f"admission:{digest}"


def canonical_json_data(value: Any) -> Any:
    """Normalize Python contract values to the JCS/I-JSON data model."""

    if isinstance(value, BaseModel):
        return canonical_json_data(value.model_dump(mode="python"))
    if isinstance(value, datetime):
        normalized = _aware_utc(value)
        return normalized.isoformat(timespec="microseconds").replace(
            "+00:00",
            "Z",
        )
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, dict):
        if not all(isinstance(key, str) for key in value):
            raise TypeError("canonical JSON object keys must be strings")
        return {
            key: canonical_json_data(item)
            for key, item in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [canonical_json_data(item) for item in value]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise TypeError(
        f"value of type {type(value).__name__} is not canonical JSON"
    )


def canonical_json_bytes(value: Any) -> bytes:
    """Serialize with RFC 8785 JCS after contract profile normalization."""

    return rfc8785.dumps(canonical_json_data(value))


def canonical_sha256(value: Any) -> str:
    """Return SHA-256 over the shared RFC 8785 canonical representation."""

    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def evaluate_applicability(
    constraint: ApplicabilityEnvelope,
    context: ApplicabilityEnvelope,
    *,
    at: datetime | None = None,
) -> tuple[ApplicabilityDecision, list[str]]:
    """Evaluate an applicability constraint without treating unknown as a match."""

    now = at or datetime.now(UTC)
    reasons: list[str] = []
    unknown: list[str] = []

    scalar_fields = (
        "tool_identity",
        "repository_uri",
        "repository_tag",
        "repository_commit",
        "repository_revision",
        "document_id",
        "corpus_snapshot_sha256",
        "document_revision",
        "corpus_revision",
        "project_configuration_sha256",
        "access_policy_sha256",
        "policy_domain",
    )
    for name in scalar_fields:
        expected = getattr(constraint, name)
        if expected is None:
            continue
        actual = getattr(context, name)
        if actual is None:
            unknown.append(name)
        elif actual != expected:
            reasons.append(f"{name} mismatch")

    list_fields = (
        "architectures",
        "device_families",
        "exact_devices",
        "silicon_steppings",
        "consumer_models",
        "agent_profiles",
    )
    for name in list_fields:
        expected_values = set(getattr(constraint, name))
        if not expected_values:
            continue
        actual_values = set(getattr(context, name))
        if not actual_values:
            unknown.append(name)
        elif expected_values.isdisjoint(actual_values):
            reasons.append(f"{name} has no compatible value")

    for key, expected in constraint.configuration_selectors.items():
        actual = context.configuration_selectors.get(key)
        if actual is None:
            unknown.append(f"configuration_selectors.{key}")
        elif actual != expected:
            reasons.append(f"configuration selector {key} mismatch")

    if constraint.valid_from is not None and now < constraint.valid_from:
        reasons.append("validity interval has not started")
    if constraint.valid_until is not None and now >= constraint.valid_until:
        reasons.append("validity interval has expired")

    version_result, version_reason = _match_tool_version(constraint, context)
    if version_result is False:
        reasons.append(version_reason)
    elif version_result is None:
        unknown.append("tool_version")

    revision_result, revision_reason = _match_repository_revision(
        constraint,
        context,
    )
    if revision_result is False:
        reasons.append(revision_reason)
    elif revision_result is None:
        unknown.append("repository_revision")

    if reasons:
        return ApplicabilityDecision.NOT_APPLICABLE, reasons
    if unknown:
        return (
            ApplicabilityDecision.REQUIRES_REVIEW,
            [f"missing applicability context: {name}" for name in sorted(set(unknown))],
        )
    return ApplicabilityDecision.APPLICABLE, []


def _match_tool_version(
    constraint: ApplicabilityEnvelope,
    context: ApplicabilityEnvelope,
) -> tuple[bool | None, str]:
    constrained = any(
        (
            constraint.tool_version,
            constraint.tool_version_min_inclusive,
            constraint.tool_version_max_exclusive,
        )
    )
    if not constrained:
        return True, ""
    actual = context.tool_version
    if actual is None:
        return None, "tool version is unknown"
    if constraint.tool_version is not None and actual != constraint.tool_version:
        return False, "tool_version mismatch"
    actual_parts = _semantic_version(actual)
    if actual_parts is None and (
        constraint.tool_version_min_inclusive
        or constraint.tool_version_max_exclusive
    ):
        return None, "tool version is not semantically comparable"
    if constraint.tool_version_min_inclusive:
        lower = _semantic_version(constraint.tool_version_min_inclusive)
        if lower is None or actual_parts is None:
            return None, "minimum tool version is not semantically comparable"
        if actual_parts < lower:
            return False, "tool version is below minimum"
    if constraint.tool_version_max_exclusive:
        upper = _semantic_version(constraint.tool_version_max_exclusive)
        if upper is None or actual_parts is None:
            return None, "maximum tool version is not semantically comparable"
        if actual_parts >= upper:
            return False, "tool version is at or above exclusive maximum"
    return True, ""


def _semantic_version(value: str) -> tuple[int, int, int] | None:
    match = re.fullmatch(r"v?(\d+)(?:\.(\d+))?(?:\.(\d+))?(?:[-+].*)?", value)
    if match is None:
        return None
    return tuple(int(part or 0) for part in match.groups())


def _match_repository_revision(
    constraint: ApplicabilityEnvelope,
    context: ApplicabilityEnvelope,
) -> tuple[bool | None, str]:
    constrained = any(
        (
            constraint.repository_revision_min,
            constraint.repository_revision_max,
        )
    )
    if not constrained:
        return True, ""
    actual = context.repository_revision
    if actual is None:
        return None, "repository revision is unknown"
    actual_parts = _semantic_version(actual)
    if actual_parts is None:
        return None, "repository revision requires an external resolver"
    if constraint.repository_revision_min:
        lower = _semantic_version(constraint.repository_revision_min)
        if lower is None:
            return None, "minimum repository revision is not comparable"
        if actual_parts < lower:
            return False, "repository revision is below minimum"
    if constraint.repository_revision_max:
        upper = _semantic_version(constraint.repository_revision_max)
        if upper is None:
            return None, "maximum repository revision is not comparable"
        if actual_parts > upper:
            return False, "repository revision is above maximum"
    return True, ""
