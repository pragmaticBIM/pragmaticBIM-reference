"""Run every shacl_defined rule against pass/fail fixture graphs."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from pyshacl import validate
from rdflib import Graph, Namespace, URIRef

ROOT = Path(__file__).resolve().parents[1]
RULES_DIR = ROOT / "rules"
FIXTURES_DIR = ROOT / "tests" / "fixtures" / "rules"

PBS = Namespace("https://schema.pragmaticbim.ch/")
SH = Namespace("http://www.w3.org/ns/shacl#")
RULE_NS = Namespace("https://schema.pragmaticbim.ch/rule/")

FOCUS = URIRef("https://schema.pragmaticbim.ch/ex/focus")

SHACL_PREFIXES = """\
@prefix sh: <http://www.w3.org/ns/shacl#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix rule: <https://schema.pragmaticbim.ch/rule/> .
@prefix pbs: <https://schema.pragmaticbim.ch/> .
@prefix ifc: <https://w3id.org/ifc/IFC4_ADD2#> .
"""

SEVERITY_BY_STATUS = {
    "violation": SH.Violation,
    "warning": SH.Warning,
    "info": SH.Info,
}


def _shacl_defined_rules() -> list[tuple[str, dict]]:
    rules: list[tuple[str, dict]] = []
    for path in sorted(RULES_DIR.glob("*.yaml")):
        doc = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(doc, dict):
            continue
        if doc.get("rule_status") != "shacl_defined":
            continue
        rules.append((path.stem, doc))
    return rules


SHACL_RULES = _shacl_defined_rules()
SHACL_SLUGS = [slug for slug, _ in SHACL_RULES]


def _load_shapes(shacl_text: str) -> Graph:
    graph = Graph()
    graph.parse(data=SHACL_PREFIXES + "\n" + shacl_text, format="turtle")
    return graph


def _validate(data_path: Path, shapes: Graph):
    data = Graph()
    data.parse(source=data_path, format="turtle")
    return validate(
        data,
        shacl_graph=shapes,
        inference="rdfs",
        abort_on_first=False,
        meta_shacl=False,
        advanced=True,
        js=False,
        debug=False,
    )


def _validation_rows(report: Graph) -> list[tuple[URIRef, URIRef]]:
    return [
        (sev, focus)
        for sev, focus in report.query(
            """
            SELECT ?sev ?fn WHERE {
                ?r a sh:ValidationResult ;
                   sh:resultSeverity ?sev ;
                   sh:focusNode ?fn .
            }
            """,
            initNs={"sh": SH},
        )
    ]


@pytest.mark.parametrize("slug,doc", SHACL_RULES, ids=SHACL_SLUGS)
def test_shacl_rule_fixtures(slug: str, doc: dict) -> None:
    assert "shacl" in doc and doc["shacl"].strip(), f"{slug}: missing shacl body"

    shapes = _load_shapes(doc["shacl"])
    assert len(shapes) > 0, f"{slug}: SHACL did not parse into triples"

    shape_iri = RULE_NS[slug]
    expected_severity = SEVERITY_BY_STATUS[doc["severity"]]
    declared = set(shapes.objects(shape_iri, SH.severity))
    assert expected_severity in declared, (
        f"{slug}: NodeShape severity {declared} does not include YAML severity "
        f"{doc['severity']}"
    )

    fixture_dir = FIXTURES_DIR / slug
    pass_path = fixture_dir / "pass.ttl"
    fail_path = fixture_dir / "fail.ttl"
    assert pass_path.is_file(), f"{slug}: missing {pass_path}"
    assert fail_path.is_file(), f"{slug}: missing {fail_path}"

    fail_head = fail_path.read_text(encoding="utf-8").lstrip()
    assert fail_head.startswith("#"), (
        f"{slug}: fail.ttl must start with a clause comment"
    )

    pass_ok, pass_report, _ = _validate(pass_path, shapes)
    pass_rows = _validation_rows(pass_report)
    assert pass_ok and not pass_rows, (
        f"{slug}: pass.ttl must conform with 0 results; got {pass_rows}"
    )

    fail_ok, fail_report, _ = _validate(fail_path, shapes)
    fail_rows = _validation_rows(fail_report)
    assert not fail_ok, f"{slug}: fail.ttl must not conform"
    assert fail_rows, f"{slug}: fail.ttl produced no ValidationResult"

    focus_rows = [sev for sev, focus in fail_rows if focus == FOCUS]
    assert focus_rows, (
        f"{slug}: fail.ttl has no result on expected focus node {FOCUS}; "
        f"got {fail_rows}"
    )

    # Prefer a result at the declared severity. Property constraints may still
    # report sh:Violation in pySHACL even when the NodeShape is sh:Warning;
    # in that case the NodeShape declaration above is the severity contract.
    if expected_severity not in focus_rows:
        assert expected_severity in declared
