# Engineering Context Contracts

Provider-neutral, contract-first records for exchanging engineering evidence
between retrieval systems, project corpora, repositories, verification
runners, mutable memory, and agent clients.

The normative artifacts are:

- JSON Schema Draft 2020-12 schemas under `schemas/`;
- the `engineering-context-jcs-1.0` RFC 8785 canonicalization profile and
  byte/digest vectors under `canonicalization/`;
- synthetic, non-proprietary interoperability fixtures under `fixtures/`;
- the content hashes in `CONTRACT-MANIFEST.json`.

The Python package is the first convenience binding. It is not a replacement
for the normative schemas and vectors.

## Ownership boundary

This repository defines wire contracts, canonical identity, shared enums, and
cross-record invariants. It does not implement retrieval, storage, access
control, lifecycle persistence, model calls, source inspection, test
execution, or policy decisions.

Provider extensions currently cover:

- controlled field-level release;
- exact-Git structural evidence release;
- commit-bound verified-execution release.

The core package also publishes the provider-neutral
`EvidenceInterpretationReceipt` wire contract. It separates normative,
derived, plausible, and recommendation assertions while structurally
prohibiting non-normative assertions from satisfying compliance obligations.
Its reviewed AMS/OMS 1 PPS fixture preserves the hard
`project-evidence-required` state alongside a provenance-linked plausible
interpretation and design-safe recommendation.

Raw controlled content, source snippets, commands, logs, credentials, and
project-specific data are prohibited from the included fixtures.

## Versioning

Package version and wire `schema_version` are independent:

- package `0.2.0` adds the evidence-interpretation wire contract;
- wire contract `1.0` rejects unknown versions;
- compatible additions require a new explicitly supported schema version;
- consumers must fail closed on unknown required semantics.

## Development

```bash
python -m venv .venv
.venv/bin/pip install -e '.[test]'
.venv/bin/pytest
```
