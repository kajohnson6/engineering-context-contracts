"""Build the software-assurance extension JSON Schema."""

import json
from pathlib import Path

from engineering_context_contracts import (
    SoftwareCoverageObligationReleaseRecord,
)

TARGET = Path(
    "schemas/extensions/software-coverage-obligation-release/1.0/schema.json"
)


def main() -> None:
    schema = SoftwareCoverageObligationReleaseRecord.model_json_schema(
        mode="validation",
        ref_template="#/$defs/{model}",
    )
    schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
    schema["$id"] = (
        "https://engineering-context-contracts.invalid/schemas/extensions/"
        "software-coverage-obligation-release/1.0/schema.json"
    )
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    TARGET.write_text(
        json.dumps(schema, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
