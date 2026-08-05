import pytest
from pydantic import ValidationError

from engineering_context_contracts import (
    ArtifactRef,
    BootstrapTopologyEdge,
    BootstrapTopologyLocator,
    BootstrapTopologyNode,
    TopologyBootstrapHandoffReceipt,
    TopologyBootstrapHandoffRecord,
    TopologyBootstrapReleasePolicy,
    canonical_sha256,
)


def _ref(kind: str, marker: str) -> ArtifactRef:
    return ArtifactRef(
        artifact_type=kind,
        artifact_schema_version="1.0",
        uri=f"component-lens://synthetic/{kind}/{marker}",
        sha256=marker * 64,
    )


def _record() -> TopologyBootstrapHandoffRecord:
    access_policy = _ref("public-access-policy", "a")
    policy = TopologyBootstrapReleasePolicy(
        policy_id="synthetic-public-topology-release",
        scope_id="synthetic-system",
        project_id="synthetic-project",
        configuration="baseline",
        access_policy=access_policy,
        permitted_node_kinds=["repository"],
        permitted_relations=["references-repository"],
        max_nodes=8,
        max_edges=16,
        allow_labels=True,
        allow_attributes=True,
        allow_detailed_locators=True,
        enabled=True,
    )
    policy_ref = ArtifactRef(
        artifact_type=policy.artifact_type,
        artifact_schema_version=policy.schema_version,
        uri=(
            "component-lens://topology-bootstrap-release-policies/"
            f"{canonical_sha256(policy)}"
        ),
        sha256=canonical_sha256(policy),
    )
    source = _ref("topology-bootstrap-draft", "b")
    file_ref = _ref("code-file", "c")
    receipt = TopologyBootstrapHandoffReceipt(
        source_bootstrap=source,
        source_scope_id="synthetic-system",
        project_id="synthetic-project",
        configuration="baseline",
        access_policy=access_policy,
        release_policy=policy_ref,
        nodes=[
            BootstrapTopologyNode(
                node_id="repository:flight-app",
                node_kind="repository",
                label="Flight application",
                attributes={"source_revision": "1" * 40},
                evidence=[source],
            ),
            BootstrapTopologyNode(
                node_id="repository:sensor-driver",
                node_kind="repository",
                label="Sensor driver",
                attributes={"source_revision": "2" * 40},
                evidence=[source],
            ),
        ],
        edges=[
            BootstrapTopologyEdge(
                source_edge_id="bootstrap-edge:" + "d" * 64,
                source_node_id="repository:flight-app",
                relation="references-repository",
                target_node_id="repository:sensor-driver",
                locators=[
                    BootstrapTopologyLocator(
                        locator_kind="repository-path-line",
                        artifact=file_ref,
                        path="compose.yaml",
                        line_number=12,
                    )
                ],
            )
        ],
    )
    digest = canonical_sha256(receipt)
    return TopologyBootstrapHandoffRecord(
        reference=ArtifactRef(
            artifact_type=receipt.artifact_type,
            artifact_schema_version=receipt.schema_version,
            uri=f"component-lens://topology-bootstrap-handoffs/{digest}",
            sha256=digest,
        ),
        policy=policy,
        receipt=receipt,
    )


def test_handoff_record_is_content_addressed_and_unverified() -> None:
    record = _record()

    assert record.reference.sha256 == canonical_sha256(record.receipt)
    assert record.receipt.usable_as_evidence is False
    assert record.receipt.promotion_required is True
    assert record.receipt.relation_semantics_unverified is True
    assert record.receipt.no_raw_content is True


def test_handoff_rejects_unknown_edge_endpoint() -> None:
    record = _record()
    edge = record.receipt.edges[0].model_copy(
        update={"target_node_id": "repository:missing"}
    )

    with pytest.raises(ValidationError, match="endpoint is unknown"):
        TopologyBootstrapHandoffReceipt.model_validate(
            {
                **record.receipt.model_dump(mode="json"),
                "edges": [edge.model_dump(mode="json")],
            }
        )


@pytest.mark.parametrize(
    ("update", "message"),
    [
        ({"enabled": False}, "not active"),
        ({"revoked": True}, "not active"),
        ({"allow_attributes": False}, "attributes are not permitted"),
        ({"allow_detailed_locators": False}, "locators are not permitted"),
    ],
)
def test_handoff_policy_fails_closed(update: dict, message: str) -> None:
    record = _record()
    policy = record.policy.model_copy(update=update)
    policy_ref = record.receipt.release_policy.model_copy(
        update={"sha256": canonical_sha256(policy)}
    )
    receipt = record.receipt.model_copy(update={"release_policy": policy_ref})
    reference = record.reference.model_copy(
        update={"sha256": canonical_sha256(receipt)}
    )

    with pytest.raises(ValidationError, match=message):
        TopologyBootstrapHandoffRecord(
            reference=reference,
            policy=policy,
            receipt=receipt,
        )


def topology_bootstrap_fixture() -> TopologyBootstrapHandoffRecord:
    return _record()
