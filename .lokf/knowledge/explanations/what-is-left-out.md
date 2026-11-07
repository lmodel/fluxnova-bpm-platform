---
type: Explanation
id: https://w3id.org/lmodel/fluxnova-bpm-platform/knowledge/explanations/what-is-left-out
genre: explanation
title: What the schema leaves out
description: "What the schema does not model: the engine's computed columns and the columns' lengths, the CMMN and DMN models, what the BPMN model API does not register, the rest of Fluxnova, and what the first release removed from the old sidecar."
resource: .linkml/docs/about.md
about:
  - https://w3id.org/lmodel/fluxnova-bpm-platform/knowledge/datasets/fluxnova-linkml-schema
sources:
  - id: about.md
    resource: .linkml/docs/about.md
    title: What is left out
  - id: changelog.md
    resource: .linkml/CHANGELOG.md
    title: Removed
generated:
  by: process:ktl-librarian
  at: "2026-11-07T11:20:19Z"
  revision: 5ed3c6a8c1320d688a6f21040b5678fc5cbc4fdc
status: draft
---

# What the schema leaves out

The schema leaves out the engine's computed columns, the columns' lengths, the CMMN and DMN models, and the rest of Fluxnova, such as the REST API and the web applications.[^about.md] It also leaves out what the BPMN model API does not register, such as `camunda:async` on an intermediate event, which the engine reads, and content in other namespaces.[^about.md] The first release removed the old provenance overlay, the sixteen SSSOM sets and their overlay, and a MyBatis cross-check that counted no discrepancies by construction.[^changelog.md]

[^about.md]: .linkml/docs/about.md, What is left out
[^changelog.md]: .linkml/CHANGELOG.md, Removed
