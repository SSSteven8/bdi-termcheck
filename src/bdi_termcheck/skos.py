"""Export van de BDI-begrippen als SKOS, conform NL-SBB.

NL-SBB (Nederlandse Standaard voor het Beschrijven van Begrippen) schrijft per
begrip minimaal voor: een term (skos:prefLabel), een definitie (skos:definition)
en een bron. Toelichting, synoniemen en relaties zijn optioneel maar aanbevolen.
SKOS is het serialisatieformaat; NL-SBB is het invulmodel daarbovenop.
"""

from __future__ import annotations

import datetime as dt
import re
from pathlib import Path

from .extract import Term

BASE = "https://begrippen.bdinetwork.org/id/begrip/"
SCHEME = "https://begrippen.bdinetwork.org/id/begrippenkader/bdi"

PREAMBLE = """@prefix skos:    <http://www.w3.org/2004/02/skos/core#> .
@prefix skosxl:  <http://www.w3.org/2008/05/skos-xl#> .
@prefix dct:     <http://purl.org/dc/terms/> .
@prefix owl:     <http://www.w3.org/2002/07/owl#> .
@prefix xsd:     <http://www.w3.org/2001/XMLSchema#> .
@prefix bdi:     <{base}> .

<{scheme}> a skos:ConceptScheme ;
    dct:title "BDI Begrippenkader"@nl , "BDI Glossary"@en ;
    dct:description "Begrippen uit de BDI Referentiearchitectuur, beschreven conform NL-SBB en geserialiseerd als SKOS."@nl ;
    dct:publisher "Basic Data Infrastructure" ;
    dct:modified "{today}"^^xsd:date .
"""


def slugify(label: str) -> str:
    s = re.sub(r"[^A-Za-z0-9]+", "-", label).strip("-").lower()
    return re.sub(r"-+", "-", s)


def _lit(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def concept_ttl(
    term: Term,
    lang: str = "en",
    mappings: dict[str, str] | None = None,
    deprecated: bool = False,
    source_url: str | None = None,
) -> str:
    """Eén skos:Concept in Turtle."""
    lines = [f"bdi:{slugify(term.label)} a skos:Concept ;"]
    lines.append(f"    skos:inScheme <{SCHEME}> ;")
    lines.append(f"    skos:prefLabel {_lit(term.label)}@{lang} ;")
    for alias in term.aliases:
        lines.append(f"    skos:altLabel {_lit(alias)}@{lang} ;")
    if term.definition:
        lines.append(f"    skos:definition {_lit(term.definition)}@{lang} ;")
    if source_url or term.source:
        lines.append(f"    dct:source {_lit(source_url or term.source)} ;")
    for predicate, target in (mappings or {}).items():
        lines.append(f"    skos:{predicate} <{target}> ;")
    if deprecated:
        lines.append("    owl:deprecated true ;")
        lines.append('    skos:changeNote "Vervallen; zie changeNote in de repository."@nl ;')
    lines[-1] = lines[-1].rstrip(" ;") + " ."
    return "\n".join(lines)


def write_vocabulary(
    terms: list[Term],
    out: Path,
    mappings: dict[str, dict[str, str]] | None = None,
    deprecated: set[str] | None = None,
) -> Path:
    """Schrijf het volledige begrippenkader weg als Turtle."""
    mappings = mappings or {}
    deprecated = deprecated or set()
    today = dt.date.today().isoformat()
    body = [PREAMBLE.format(base=BASE, scheme=SCHEME, today=today)]
    for t in sorted(terms, key=lambda x: x.label.lower()):
        body.append(
            concept_ttl(
                t,
                mappings=mappings.get(t.key),
                deprecated=t.key in deprecated,
            )
        )
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n\n".join(body) + "\n", encoding="utf-8")
    return out
