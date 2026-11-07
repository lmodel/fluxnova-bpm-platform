---
type: Dataset
id: https://w3id.org/lmodel/fluxnova-bpm-platform/knowledge/datasets/example-data
genre: reference
title: Example data
description: "The examples under `.linkml/tests/data/`: a valid example of each engine table's class, a BPMN definitions document, and counter-examples, some derived from FINOS's MockProvider test fixtures."
resource: .linkml/tests/data
about:
  - https://w3id.org/lmodel/fluxnova-bpm-platform/knowledge/datasets/fluxnova-linkml-schema
sources:
  - id: test_data.py
    resource: .linkml/tests/test_data.py
  - id: fluxnovatask-vendor.yaml
    resource: .linkml/tests/data/valid/FluxnovaTask-vendor.yaml
generated:
  by: process:ktl-librarian
  at: "2026-11-07T03:39:33Z"
  revision: 1797b282710e663bc55b039da4111f93e86ef90f
status: draft
---

# Example data

`tests/data/valid/<Class>-<anything>.yaml` must validate against the class and load as its dataclass, and `tests/data/invalid/` must fail.[^test_data.py] The examples named `-vendor` use the values of FINOS's `MockProvider.java` test fixtures.[^fluxnovatask-vendor.yaml]

[^test_data.py]: .linkml/tests/test_data.py
[^fluxnovatask-vendor.yaml]: .linkml/tests/data/valid/FluxnovaTask-vendor.yaml
