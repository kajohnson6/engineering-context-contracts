"""Neutral release contracts for unverified bootstrap topology."""

from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import Field, model_validator

from engineering_context_contracts.core import (
    ArtifactRef,
    SharedContract,
    canonical_sha256,
)


class BootstrapTopologyNodeKind(StrEnum):
    DOCUMENT = "document"
    REPOSITORY = "repository"
    COMPONENT = "component"
    INTERFACE = "interface"


class BootstrapTopologyRelation(StrEnum):
    REFERENCES_DOCUMENT = "references-document"
    REFERENCES_REPOSITORY = "references-repository"
    CONNECTED_TO_INTERFACE = "connected-to-interface"


class BootstrapTopologyLocatorKind(StrEnum):
    ARTIFACT_ONLY = "artifact-only"
    DOCUMENT_PAGE_LINE = "document-page-line"
    REPOSITORY_PATH_LINE = "repository-path-line"
    KICAD_NET_PIN = "kicad-net-pin"


class BootstrapTopologyLocator(SharedContract):
    locator_kind: BootstrapTopologyLocatorKind
    artifact: ArtifactRef
    page_number: int | None = Field(default=None, ge=1)
    path: str | None = Field(default=None, min_length=1, max_length=1024)
    line_number: int | None = Field(default=None, ge=1)
    element_id: str | None = Field(default=None, min_length=1, max_length=500)
    component_ref: str | None = Field(default=None, min_length=1, max_length=100)
    pin: str | None = Field(default=None, min_length=1, max_length=100)

    @model_validator(mode="after")
    def fields_match_kind(self) -> BootstrapTopologyLocator:
        detailed = (
            self.page_number,
            self.path,
            self.line_number,
            self.element_id,
            self.component_ref,
            self.pin,
        )
        if self.locator_kind == BootstrapTopologyLocatorKind.ARTIFACT_ONLY:
            if any(value is not None for value in detailed):
                raise ValueError("artifact-only locator cannot release details")
        elif (
            self.locator_kind
            == BootstrapTopologyLocatorKind.DOCUMENT_PAGE_LINE
        ):
            if self.page_number is None or self.line_number is None:
                raise ValueError("document locator requires page and line")
            if any(
                value is not None
                for value in (self.path, self.element_id, self.component_ref, self.pin)
            ):
                raise ValueError("document locator contains unrelated fields")
        elif (
            self.locator_kind
            == BootstrapTopologyLocatorKind.REPOSITORY_PATH_LINE
        ):
            if self.path is None or self.line_number is None:
                raise ValueError("repository locator requires path and line")
            if any(
                value is not None
                for value in (
                    self.page_number,
                    self.element_id,
                    self.component_ref,
                    self.pin,
                )
            ):
                raise ValueError("repository locator contains unrelated fields")
        else:
            if self.element_id is None or self.component_ref is None:
                raise ValueError("KiCad locator requires element and component")
            if any(
                value is not None
                for value in (self.page_number, self.path, self.line_number)
            ):
                raise ValueError("KiCad locator contains unrelated fields")
        return self


class BootstrapTopologyNode(SharedContract):
    node_id: str = Field(pattern=r"^[a-zA-Z0-9][a-zA-Z0-9._:/-]{0,299}$")
    node_kind: BootstrapTopologyNodeKind
    label: str = Field(min_length=1, max_length=300)
    attributes: dict[str, str] = Field(default_factory=dict)
    evidence: list[ArtifactRef] = Field(min_length=1, max_length=16)
    knowledge_state: Literal["extracted-unverified"] = "extracted-unverified"


class BootstrapTopologyEdge(SharedContract):
    source_edge_id: str = Field(min_length=1, max_length=500)
    source_node_id: str = Field(
        pattern=r"^[a-zA-Z0-9][a-zA-Z0-9._:/-]{0,299}$"
    )
    relation: BootstrapTopologyRelation
    target_node_id: str = Field(
        pattern=r"^[a-zA-Z0-9][a-zA-Z0-9._:/-]{0,299}$"
    )
    locators: list[BootstrapTopologyLocator] = Field(min_length=1, max_length=8)
    knowledge_state: Literal["extracted-unverified"] = "extracted-unverified"


class TopologyBootstrapReleasePolicy(SharedContract):
    artifact_type: Literal["topology-bootstrap-release-policy"] = (
        "topology-bootstrap-release-policy"
    )
    policy_id: str = Field(min_length=1, max_length=200)
    scope_id: str = Field(min_length=1, max_length=300)
    access_policy: ArtifactRef
    recipient: Literal["engineering-memory"] = "engineering-memory"
    permitted_node_kinds: list[BootstrapTopologyNodeKind] = Field(min_length=1)
    permitted_relations: list[BootstrapTopologyRelation] = Field(min_length=1)
    max_nodes: int = Field(ge=1, le=100_000)
    max_edges: int = Field(ge=0, le=500_000)
    allow_labels: bool = False
    allow_attributes: bool = False
    allow_detailed_locators: bool = False
    no_raw_content: Literal[True] = True
    enabled: bool = False
    revoked: bool = False

    @model_validator(mode="after")
    def policy_is_bounded(self) -> TopologyBootstrapReleasePolicy:
        if self.access_policy.artifact_type not in {
            "public-access-policy",
            "controlled-access-policy",
        }:
            raise ValueError("topology release requires an access policy")
        if len(self.permitted_node_kinds) != len(set(self.permitted_node_kinds)):
            raise ValueError("permitted node kinds must be unique")
        if len(self.permitted_relations) != len(set(self.permitted_relations)):
            raise ValueError("permitted relations must be unique")
        return self


class TopologyBootstrapHandoffReceipt(SharedContract):
    artifact_type: Literal["topology-bootstrap-handoff-receipt"] = (
        "topology-bootstrap-handoff-receipt"
    )
    source_bootstrap: ArtifactRef
    source_scope_id: str = Field(min_length=1, max_length=300)
    project_id: str = Field(min_length=1, max_length=128)
    configuration: str = Field(min_length=1, max_length=300)
    recipient: Literal["engineering-memory"] = "engineering-memory"
    access_policy: ArtifactRef
    release_policy: ArtifactRef
    nodes: list[BootstrapTopologyNode] = Field(min_length=1)
    edges: list[BootstrapTopologyEdge] = Field(default_factory=list)
    completeness: Literal["bounded-partial"] = "bounded-partial"
    relation_semantics_unverified: Literal[True] = True
    usable_as_evidence: Literal[False] = False
    promotion_required: Literal[True] = True
    no_raw_content: Literal[True] = True
    content_contract: Literal[
        "unverified-topology-nodes-edges-and-immutable-provenance-only"
    ] = "unverified-topology-nodes-edges-and-immutable-provenance-only"

    @model_validator(mode="after")
    def graph_is_closed_and_unique(self) -> TopologyBootstrapHandoffReceipt:
        if self.source_bootstrap.artifact_type != "topology-bootstrap-draft":
            raise ValueError("source_bootstrap has the wrong artifact type")
        if self.release_policy.artifact_type != "topology-bootstrap-release-policy":
            raise ValueError("release_policy has the wrong artifact type")
        node_ids = [item.node_id for item in self.nodes]
        edge_ids = [item.source_edge_id for item in self.edges]
        if len(node_ids) != len(set(node_ids)):
            raise ValueError("handoff node IDs must be unique")
        if len(edge_ids) != len(set(edge_ids)):
            raise ValueError("handoff source edge IDs must be unique")
        known = set(node_ids)
        relationships = []
        for edge in self.edges:
            if edge.source_node_id == edge.target_node_id:
                raise ValueError("handoff self-edge is not permitted")
            if {edge.source_node_id, edge.target_node_id} - known:
                raise ValueError("handoff edge endpoint is unknown")
            relationships.append(
                (edge.source_node_id, edge.relation, edge.target_node_id)
            )
        if len(relationships) != len(set(relationships)):
            raise ValueError("handoff relationships must be unique")
        return self


class TopologyBootstrapHandoffRecord(SharedContract):
    reference: ArtifactRef
    policy: TopologyBootstrapReleasePolicy
    receipt: TopologyBootstrapHandoffReceipt

    @model_validator(mode="after")
    def record_is_content_addressed_and_policy_closed(
        self,
    ) -> TopologyBootstrapHandoffRecord:
        policy_digest = canonical_sha256(self.policy)
        if (
            self.receipt.release_policy.artifact_type != self.policy.artifact_type
            or self.receipt.release_policy.sha256 != policy_digest
        ):
            raise ValueError("handoff release policy reference mismatch")
        if self.receipt.source_scope_id != self.policy.scope_id:
            raise ValueError("handoff scope does not match release policy")
        if self.receipt.access_policy != self.policy.access_policy:
            raise ValueError("handoff access policy does not match release policy")
        if self.receipt.recipient != self.policy.recipient:
            raise ValueError("handoff recipient does not match release policy")
        if not self.policy.enabled or self.policy.revoked:
            raise ValueError("handoff release policy is not active")
        if len(self.receipt.nodes) > self.policy.max_nodes:
            raise ValueError("handoff node count exceeds release policy")
        if len(self.receipt.edges) > self.policy.max_edges:
            raise ValueError("handoff edge count exceeds release policy")
        if any(
            item.node_kind not in self.policy.permitted_node_kinds
            for item in self.receipt.nodes
        ):
            raise ValueError("handoff node kind is not permitted")
        if any(
            item.relation not in self.policy.permitted_relations
            for item in self.receipt.edges
        ):
            raise ValueError("handoff relation is not permitted")
        if not self.policy.allow_labels and any(
            item.label != item.node_id for item in self.receipt.nodes
        ):
            raise ValueError("handoff labels are not permitted")
        if not self.policy.allow_attributes and any(
            item.attributes for item in self.receipt.nodes
        ):
            raise ValueError("handoff attributes are not permitted")
        if not self.policy.allow_detailed_locators and any(
            locator.locator_kind != BootstrapTopologyLocatorKind.ARTIFACT_ONLY
            for edge in self.receipt.edges
            for locator in edge.locators
        ):
            raise ValueError("detailed handoff locators are not permitted")
        receipt_digest = canonical_sha256(self.receipt)
        if (
            self.reference.artifact_type != self.receipt.artifact_type
            or self.reference.sha256 != receipt_digest
            or not self.reference.uri.endswith(f"/{receipt_digest}")
        ):
            raise ValueError("handoff record reference mismatch")
        return self
