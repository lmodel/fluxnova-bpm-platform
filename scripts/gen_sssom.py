#!/usr/bin/env python3
"""Generate SSSOM mapping files from ecosystem LinkML schemas.

Reads every ``*.yaml`` in *ecosystem_dir*, extracts ``*_mappings`` entries from
elements that are **native** to each schema (where ``from_schema`` is absent or
equals the schema's own ``id`` URI), then writes one
``fluxnova-{prefix}.sssom.tsv`` per distinct subject prefix into *mappings_dir*.

This replaces any previous SSSOM files that were incorrectly generated using the
container file's ``default_prefix`` for imported (non-native) classes.

Design:
  - Native-only filter: ``from_schema`` absent  OR  ``from_schema == schema.id``
  - Multiple schema files sharing the same ``default_prefix`` are merged.
  - All object prefixes from injected rows are collected into ``curie_map``.
  - Rows are sorted and deduplicated for determinism.
  - Existing ``fluxnova-*.sssom.tsv`` files that no longer have any rows are
    deleted (stale files from incorrect earlier generation).

Usage::

    python scripts/gen_sssom.py
    python scripts/gen_sssom.py --dry-run
    python scripts/gen_sssom.py --ecosystem-dir path/to/ecosystem \\
                                --mappings-dir  path/to/mappings
"""

import argparse
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

import yaml

# ── Constants ─────────────────────────────────────────────────────────────────

DEFAULT_ECOSYSTEM_DIR = Path("ecosystem")
DEFAULT_MAPPINGS_DIR  = Path("src/fluxnova_bpm_platform/mappings")

NAMESPACE      = "https://w3id.org/lmodel/"
MAPPING_DATE   = date.today().isoformat()
LICENSE_URI    = "https://www.apache.org/licenses/LICENSE-2.0"
AUTHOR_ID      = "https://w3id.org/lmodel"

LINKML_TO_SKOS: dict[str, str] = {
    "exact_mappings":   "skos:exactMatch",
    "close_mappings":   "skos:closeMatch",
    "broad_mappings":   "skos:broadMatch",
    "narrow_mappings":  "skos:narrowMatch",
    "related_mappings": "skos:relatedMatch",
}

# Override: map subject_prefix → canonical filename stem when they differ
PREFIX_TO_STEM: dict[str, str] = {
    "d3f":  "d3fend",
    "core": "vulnerability-core",
}

# Well-known base URIs for common namespaces (supplement schema-declared prefixes)
WELL_KNOWN_URIS: dict[str, str] = {
    "semapv":                   "https://w3id.org/semapv/vocab/",
    "skos":                     "http://www.w3.org/2004/02/skos/core#",
    "linkml":                   "https://w3id.org/linkml/",
    "schema":                   "http://schema.org/",
    "owl":                      "http://www.w3.org/2002/07/owl#",
    "rdf":                      "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    "rdfs":                     "http://www.w3.org/2000/01/rdf-schema#",
    "xsd":                      "http://www.w3.org/2001/XMLSchema#",
    "PATO":                     "http://purl.obolibrary.org/obo/PATO_",
    "WIKIDATA":                 "https://www.wikidata.org/wiki/",
    "WIKIDATA_PROPERTY":        "https://www.wikidata.org/prop/",
    "BFO":                      "http://purl.obolibrary.org/obo/BFO_",
    "IAO":                      "http://purl.obolibrary.org/obo/IAO_",
    "RO":                       "http://purl.obolibrary.org/obo/RO_",
    "dpv":                      "https://www.w3.org/ns/dpv#",
    "dct":                      "http://purl.org/dc/terms/",
    "foaf":                     "http://xmlns.com/foaf/0.1/",
    "prov":                     "http://www.w3.org/ns/prov#",
    "unified_cyber_ontology":   "https://w3id.org/lmodel/uco-master/",
    "attack":                   "https://w3id.org/lmodel/attack/",
    "capec":                    "https://lmodel.github.io/capec/",
    "stix":                     "https://w3id.org/lmodel/stix/",
    "d3f":                      "https://lmodel.github.io/d3fend/",
    "core":                     "https://w3id.org/lmodel/vulnerability-core/",
    "cve":                      "https://w3id.org/lmodel/cve/",
    "cwe":                      "https://w3id.org/lmodel/cwe/",
    "oscal":                    "https://lmodel.github.io/oscal/",
    "slsa":                     "https://lmodel.github.io/slsa/",
    "spdx":                     "https://lmodel.github.io/spdx/",
    "gist":                     "https://ontologies.semanticarts.com/gist/",
    "ocsf":                     "https://schema.ocsf.io/",
    "iso27001":                 "https://lmodel.github.io/iso27001/",
    "iso29100":                 "https://lmodel.github.io/iso29100/",
    "nist_csf_v2":              "https://lmodel.github.io/nist-csf-v2/",
    "nvd":                      "https://nvd.nist.gov/",
    "kev_catalog":              "https://www.cisa.gov/known-exploited-vulnerabilities-catalog/",
    "cis_controls":             "https://lmodel.github.io/cis-controls/",
    "mcp":                      "https://modelcontextprotocol.io/",
    "nist_sp_800_53":           "https://lmodel.github.io/nist-sp-800-53/",
    "nist_sp_800_171":          "https://lmodel.github.io/nist-sp-800-171/",
    "nist_sp_800_218":          "https://lmodel.github.io/nist-sp-800-218/",
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _prefix_to_stem(prefix: str) -> str:
    return PREFIX_TO_STEM.get(prefix, prefix.replace("_", "-"))


def _curie_map_from_schema(data: dict) -> dict[str, str]:
    """Extract prefix → URI from the schema's ``prefixes`` block."""
    result: dict[str, str] = {}
    for k, v in (data.get("prefixes") or {}).items():
        if isinstance(v, dict):
            uri = v.get("prefix_reference", "")
        else:
            uri = str(v)
        if uri:
            result[k] = uri
    return result


# ── Extraction ────────────────────────────────────────────────────────────────

# Row = (subject_id, subject_label, predicate_id, object_id, element_type)
Row = tuple[str, str, str, str, str]


def extract_rows(schema_path: Path) -> tuple[str, str, str, list[Row], dict[str, str]]:
    """Extract native *_mappings from a schema file.

    Returns ``(schema_id, default_prefix, schema_name, rows, curie_map)``.
    Only elements whose ``from_schema`` is absent or equals *schema_id* are
    included (native-only filter).
    """
    with open(schema_path, encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    if not isinstance(data, dict):
        return "", "", "", [], {}

    schema_id: str = data.get("id", "")
    dp: str        = data.get("default_prefix", "")
    schema_name    = data.get("name", schema_path.stem)
    if not dp:
        return schema_id, dp, schema_name, [], {}

    curie_map = _curie_map_from_schema(data)
    rows: list[Row] = []

    sections = [
        ("classes", "class"),
        ("slots",   "slot"),
        ("types",   "type"),
        ("enums",   "enum"),
    ]
    for section, elem_type in sections:
        for elem_name, defn in (data.get(section) or {}).items():
            if not isinstance(defn, dict):
                continue
            from_schema = defn.get("from_schema")
            # Native-only filter
            if from_schema and from_schema != schema_id:
                continue
            for linkml_key, skos_pred in LINKML_TO_SKOS.items():
                for obj_id in (defn.get(linkml_key) or []):
                    obj_id = str(obj_id).strip()
                    if not obj_id:
                        continue
                    rows.append((
                        f"{dp}:{elem_name}",
                        elem_name,
                        skos_pred,
                        obj_id,
                        elem_type,
                    ))

    return schema_id, dp, schema_name, rows, curie_map


# ── SSSOM rendering ───────────────────────────────────────────────────────────

def _collect_object_prefixes(rows: list[Row]) -> set[str]:
    prefixes: set[str] = set()
    for _, _, _, obj_id, _ in rows:
        if ":" in obj_id and not obj_id.startswith("http"):
            prefixes.add(obj_id.split(":")[0])
    return prefixes


def _render_sssom(
    subject_prefix: str,
    schema_name: str,
    rows: list[Row],
    curie_map: dict[str, str],
) -> str:
    """Render SSSOM TSV content as a string."""
    # Ensure subject prefix is in curie_map
    if subject_prefix not in curie_map:
        uri = WELL_KNOWN_URIS.get(subject_prefix, f"{NAMESPACE}{subject_prefix}/")
        curie_map[subject_prefix] = uri

    # Add well-known URIs for any object prefixes missing from curie_map
    for pfx in _collect_object_prefixes(rows):
        if pfx not in curie_map and pfx in WELL_KNOWN_URIS:
            curie_map[pfx] = WELL_KNOWN_URIS[pfx]

    schema_uri = curie_map.get(subject_prefix, f"{NAMESPACE}{subject_prefix}")

    lines: list[str] = [
        f'# mapping_set_id: "{NAMESPACE}mappings/{subject_prefix}.sssom.tsv"',
        '# mapping_set_version: "1.0.0"',
        f'# mapping_set_description: "SSSOM mappings extracted from the lmodel {schema_name} LinkML schema"',
        f'# license: "{LICENSE_URI}"',
        f'# creator_id: ["{AUTHOR_ID}"]',
        f'# mapping_date: "{MAPPING_DATE}"',
        f'# subject_source: "{schema_uri}"',
        "# curie_map:",
    ]
    for pfx in sorted(curie_map):
        uri = curie_map[pfx]
        if uri:
            lines.append(f'#   {pfx}: "{uri}"')

    lines.append("")
    lines.append("\t".join([
        "subject_id", "subject_label", "predicate_id", "object_id", "object_label",
        "mapping_justification", "mapping_date", "author_id", "comment",
    ]))
    for subj_id, subj_label, pred, obj_id, comment in rows:
        lines.append("\t".join([
            subj_id, subj_label, pred, obj_id, "",
            "semapv:ManualMappingCuration", MAPPING_DATE,
            AUTHOR_ID, comment,
        ]))

    return "\n".join(lines) + "\n"


# ── Main generation ───────────────────────────────────────────────────────────

def gen_sssom(
    ecosystem_dir: Path,
    mappings_dir: Path,
    dry_run: bool = False,
    verbose: bool = False,
) -> int:
    """Generate SSSOM files from ecosystem schemas. Returns exit code."""

    # prefix → (schema_name, [rows], merged_curie_map)
    prefix_data: dict[str, tuple[str, list[Row], dict[str, str]]] = {}

    for schema_path in sorted(ecosystem_dir.glob("*.yaml")):
        if schema_path.name.startswith("."):
            continue
        schema_id, dp, schema_name, rows, curie_map = extract_rows(schema_path)
        if not dp:
            if verbose:
                print(f"  skip (no default_prefix): {schema_path.name}")
            continue

        if rows or verbose:
            print(f"  read: {schema_path.name}  prefix={dp}  native_rows={len(rows)}")

        if dp not in prefix_data:
            prefix_data[dp] = (schema_name, [], {})
        existing_name, existing_rows, existing_cmap = prefix_data[dp]
        existing_rows.extend(rows)
        existing_cmap.update(curie_map)

    # Determine which SSSOM stems will be written
    generated_stems: set[str] = set()
    total_rows = 0

    for prefix in sorted(prefix_data.keys()):
        schema_name, rows, curie_map = prefix_data[prefix]
        # Deduplicate and sort
        rows = sorted(set(rows))
        if not rows:
            if verbose:
                print(f"  skip (no native mappings): prefix={prefix}")
            continue

        stem      = _prefix_to_stem(prefix)
        out_path  = mappings_dir / f"fluxnova-{stem}.sssom.tsv"
        content   = _render_sssom(prefix, schema_name, rows, curie_map)
        total_rows += len(rows)
        generated_stems.add(f"fluxnova-{stem}.sssom.tsv")

        if dry_run:
            print(f"  [dry-run] would write: {out_path.name}  ({len(rows)} rows)")
        else:
            out_path.write_text(content, encoding="utf-8")
            print(f"  wrote: {out_path.name}  ({len(rows)} rows)")

    # Remove stale files that are no longer valid
    stale = [
        p for p in sorted(mappings_dir.glob("fluxnova-*.sssom.tsv"))
        if p.name not in generated_stems
    ]
    for stale_path in stale:
        if dry_run:
            print(f"  [dry-run] would delete stale: {stale_path.name}")
        else:
            stale_path.unlink()
            print(f"  deleted stale: {stale_path.name}")

    print(
        f"\ngen-sssom: {'[dry-run] ' if dry_run else ''}"
        f"wrote {len(generated_stems)} file(s) / {total_rows} total rows; "
        f"deleted {len(stale)} stale file(s)."
    )
    return 0


# ── CLI ───────────────────────────────────────────────────────────────────────

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate SSSOM TSV files from ecosystem LinkML schemas."
    )
    parser.add_argument(
        "--ecosystem-dir",
        type=Path,
        default=DEFAULT_ECOSYSTEM_DIR,
        help=f"Directory containing ecosystem schema YAML files (default: {DEFAULT_ECOSYSTEM_DIR})",
    )
    parser.add_argument(
        "--mappings-dir",
        type=Path,
        default=DEFAULT_MAPPINGS_DIR,
        help=f"Output directory for SSSOM TSV files (default: {DEFAULT_MAPPINGS_DIR})",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report changes without writing any files.",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Print per-file detail including schemas with zero native rows.",
    )
    args = parser.parse_args(argv)

    if not args.ecosystem_dir.is_dir():
        print(f"ERROR: ecosystem directory not found: {args.ecosystem_dir}", file=sys.stderr)
        return 1

    args.mappings_dir.mkdir(parents=True, exist_ok=True)
    print(f"gen-sssom: reading ecosystem schemas from {args.ecosystem_dir} …")
    return gen_sssom(args.ecosystem_dir, args.mappings_dir, args.dry_run, args.verbose)


if __name__ == "__main__":
    sys.exit(main())
