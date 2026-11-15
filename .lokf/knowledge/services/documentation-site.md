---
type: Service
id: https://w3id.org/lmodel/fluxnova-bpm-platform/knowledge/services/documentation-site
genre: reference
title: Documentation site
description: The knowledge website at `https://lmodel.github.io/fluxnova-bpm-platform`, built from the bundle, the sidecar README, the docs pages, the changelog and the schema's pages.
resource: website/site.toml
sources:
  - id: site.toml
    resource: website/site.toml
    title: the site's address, title and redirects
generated:
  by: process:ktl-librarian
  at: "2026-11-15T03:29:18Z"
status: draft
---

# Documentation site

The site is served at `https://lmodel.github.io/fluxnova-bpm-platform`.[^site.toml] Its home page is `.linkml/README.md` and its docs pages come from `.linkml/docs`. It shows no changelog until `.linkml/CHANGELOG.md` holds a release.[^site.toml] The site leaves out FINOS's own `docs/`.[^site.toml]

[^site.toml]: website/site.toml, the site's address, title and redirects
