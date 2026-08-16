"""Termen uit bronnen halen.

Twee soorten bronnen:
  1. De BDI-gitbook glossarypagina ("BDI Terms"), waar elk begrip in een
     <details><summary>Term</summary>definitie</details>-blok staat.
  2. Externe glossaries (CTN-document, DSSC, iSHARE, OIDC) uit YAML.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from .fetch import Page

DETAILS_RE = re.compile(
    r"<details>\s*<summary>(?P<term>.*?)</summary>(?P<body>.*?)</details>",
    re.DOTALL,
)
CARD_ROW_RE = re.compile(r"<td><strong>(?P<term>[^<]+)</strong></td><td>(?P<body>.*?)</td>", re.DOTALL)
TAG_RE = re.compile(r"<[^>]+>")


def _clean(s: str) -> str:
    s = TAG_RE.sub(" ", s)
    s = s.replace("&#x26;", "&").replace("&amp;", "&").replace("&quot;", '"')
    s = re.sub(r"[*_`\\]", "", s)
    return re.sub(r"\s+", " ", s).strip()


@dataclass
class Term:
    """Eén begrip met zijn definitie en herkomst."""

    label: str
    definition: str
    source: str
    aliases: list[str] = field(default_factory=list)

    @property
    def key(self) -> str:
        return normalise(self.label)


def normalise(label: str) -> str:
    """Vergelijkingssleutel: kleine letters, geen leestekens, enkele spaties."""
    s = _clean(label).lower()
    s = re.sub(r"[^a-z0-9 ]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def split_labels(summary: str) -> list[str]:
    """'Association Administrator, Association Authority' -> twee labels.

    Ook '(Branch Register)' wordt als alias behandeld.
    """
    text = _clean(summary)
    alt = re.findall(r"\(([^)]+)\)", text)
    text = re.sub(r"\([^)]*\)", "", text)
    labels = [p.strip() for p in text.split(",") if p.strip()]
    labels += [a.strip() for a in alt if a.strip()]
    return labels or [text.strip()]


def parse_gitbook_glossary(page: Page) -> list[Term]:
    """Haal begrippen uit een gitbook-pagina met <details>-blokken."""
    terms: list[Term] = []
    for m in DETAILS_RE.finditer(page.text):
        labels = split_labels(m.group("term"))
        definition = _clean(m.group("body"))
        primary, *aliases = labels
        terms.append(
            Term(label=primary, definition=definition, source=page.path, aliases=aliases)
        )
    return terms


def parse_card_table(page: Page) -> list[Term]:
    """Haal begrippen uit een GitBook 'cards'-tabel (zoals op Association Register)."""
    return [
        Term(label=_clean(m.group("term")), definition=_clean(m.group("body")), source=page.path)
        for m in CARD_ROW_RE.finditer(page.text)
    ]


def load_yaml_glossary(path: Path, source_label: str) -> list[Term]:
    """Lees een extern glossary uit YAML.

    Verwacht formaat:
        terms:
          - label: Association Register
            aliases: [ASR]
            definition: ...
    """
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return [
        Term(
            label=t["label"],
            definition=t.get("definition", "").strip(),
            source=source_label,
            aliases=list(t.get("aliases", [])),
        )
        for t in data.get("terms", [])
    ]


def index_terms(terms: list[Term]) -> dict[str, Term]:
    """Sleutel -> Term, inclusief aliassen."""
    out: dict[str, Term] = {}
    for t in terms:
        out.setdefault(t.key, t)
        for a in t.aliases:
            out.setdefault(normalise(a), t)
    return out
