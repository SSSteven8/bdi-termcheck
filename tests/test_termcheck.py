"""Tests. Draaien met: pytest"""
from pathlib import Path

from bdi_termcheck import analyze, extract, fetch, skos

FIXTURES = Path(__file__).parent / "fixtures"


def pages():
    return fetch.load_cached(FIXTURES)


def glossary():
    page = next(p for p in pages() if p.slug == "bdi-terms")
    return extract.parse_gitbook_glossary(page)


def test_boilerplate_is_stripped():
    for p in pages():
        assert "Agent Instructions" not in p.text
        assert not p.text.startswith(">")


def test_glossary_parsing_finds_terms_and_aliases():
    terms = {t.label: t for t in glossary()}
    assert "Association" in terms
    assert "Trigger" in terms["Pulse"].aliases
    assert "Branch Register" in terms["Association Register"].aliases


def test_empty_definition_is_kept_visible():
    terms = {t.label: t for t in glossary()}
    assert terms["Data Sovereignty"].definition == ""


def test_variant_check_flags_register_vs_registry():
    group = [{"preferred": "Association Register",
              "variants": ["Association Register", "Association Registry"]}]
    found = analyze.check_variants(group, pages())
    assert len(found) == 1
    assert "Registry" in found[0].evidence


def test_conflict_check_flags_contradicting_outsider():
    inline = [t for p in pages() if p.slug != "bdi-terms"
              for t in extract.parse_card_table(p)]
    found = analyze.check_conflicts([glossary(), inline])
    assert any(f.term == "Outsider" for f in found)


def test_orphan_check_flags_unused_term():
    gp = {p.path for p in pages() if p.slug == "bdi-terms"}
    found = analyze.check_orphans(glossary(), pages(), gp)
    assert "Data Sovereignty" in {f.term for f in found}


def test_skos_slug_and_turtle_shape():
    assert skos.slugify("Association Register (ASR)") == "association-register-asr"
    ttl = skos.concept_ttl(extract.Term("Data Owner", "A legal entity.", "x.md"))
    assert ttl.startswith("bdi:data-owner a skos:Concept ;")
    assert ttl.rstrip().endswith(".")
