"""Build the topology-bootstrap handoff extension schema and fixture."""

import json
import runpy
from pathlib import Path

from engineering_context_contracts import TopologyBootstrapHandoffRecord

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = Path(
    "schemas/extensions/topology-bootstrap-handoff/1.0/schema.json"
)
FIXTURE = Path("fixtures/topology-bootstrap-handoff-v1.json")


def main() -> None:
    schema = TopologyBootstrapHandoffRecord.model_json_schema(
        mode="validation",
        ref_template="#/$defs/{model}",
    )
    schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
    schema["$id"] = (
        "https://engineering-context-contracts.invalid/schemas/extensions/"
        "topology-bootstrap-handoff/1.0/schema.json"
    )
    SCHEMA.parent.mkdir(parents=True, exist_ok=True)
    SCHEMA.write_text(
        json.dumps(schema, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    fixture_builder = runpy.run_path(
        str(ROOT / "tests/test_topology_bootstrap_contracts.py")
    )["topology_bootstrap_fixture"]
    fixture = fixture_builder()
    FIXTURE.write_text(
        fixture.model_dump_json(indent=2) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
