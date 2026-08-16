"""De eigenlijke controles.

Vijf checks:
  C1 varianten  - schrijfwijzen die door elkaar gebruikt worden (Register/Registry)
  C2 weeskind   - begrip staat in de glossary maar wordt nergens gebruikt
  C3 ongedefinieerd - begrip wordt veel gebruikt maar staat niet in de glossary
  C4 conflict   - hetzelfde begrip heeft op twee plekken een andere definitie
  C5 mapping    - begrip heeft (nog) geen tegenhanger in DSSC / CTN / iSHARE / OIDC
"""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field

from .extract import Term, normalise
from .fetch import Page

SEVERITIES = ("blocker", "high", "medium", "low")


@dataclass
class Finding:
    check: str
    severity: str
    term: str
    evidence: str
    suggestion: str
    pages: list[str] = field(default_factory=list)

    def as_row(self) -> dict[str, str]:
        return {
            "check": self.check,
            "severity": self.severity,
            "term": self.term,
            "pages": "; ".join(sorted(set(self.pages))[:8]),
            "evidence": self.evidence,
            "suggestion": self.suggestion,
        }


def _count(pattern: str, text: str) -> int:
    return len(re.findall(rf"\b{re.escape(pattern)}\b", text, flags=re.IGNORECASE))


def count_occurrences(label: str, pages: list[Page]) -> dict[str, int]:
    """Aantal voorkomens van een label per pagina (glossarypagina's uitgezonderd)."""
    return {p.path: n for p in pages if (n := _count(label, p.text))}


# --------------------------------------------------------------------------- C1
def check_variants(variant_groups: list[dict], pages: list[Page]) -> list[Finding]:
    """Zoek varianten van hetzelfde begrip die naast elkaar in gebruik zijn."""
    findings: list[Finding] = []
    for group in variant_groups:
        preferred = group["preferred"]
        usage: dict[str, dict[str, int]] = {}
        for variant in group["variants"]:
            hits = count_occurrences(variant, pages)
            if hits:
                usage[variant] = hits
        if len(usage) < 2:
            continue
        totals = {v: sum(h.values()) for v, h in usage.items()}
        detail = ", ".join(f"{v} ({n}x)" for v, n in sorted(totals.items(), key=lambda kv: -kv[1]))
        touched = sorted({p for h in usage.values() for p in h})
        findings.append(
            Finding(
                check="C1-variant",
                severity=group.get("severity", "high"),
                term=preferred,
                evidence=f"Naast elkaar in gebruik: {detail}",
                suggestion=group.get(
                    "suggestion", f"Standaardiseer op '{preferred}'; neem de rest op als skos:altLabel."
                ),
                pages=touched,
            )
        )
    return findings


# --------------------------------------------------------------------------- C2
def check_orphans(glossary: list[Term], pages: list[Page], glossary_paths: set[str]) -> list[Finding]:
    """Begrippen die wel gedefinieerd zijn maar nergens in de architectuur staan."""
    body = [p for p in pages if p.path not in glossary_paths]
    findings = []
    for t in glossary:
        labels = [t.label, *t.aliases]
        hits = {p.path: n for lbl in labels for p, n in
                ((p, _count(lbl, p.text)) for p in body) if n}
        if not hits:
            findings.append(
                Finding(
                    check="C2-weeskind",
                    severity="medium",
                    term=t.label,
                    evidence="Staat in de glossary, komt op geen enkele architectuurpagina voor.",
                    suggestion="Bevestig dat het begrip nog geldig is, of markeer als "
                               "owl:deprecated met een skos:changeNote.",
                    pages=[t.source],
                )
            )
    return findings


# --------------------------------------------------------------------------- C3
CANDIDATE_RE = re.compile(r"\b(?:[A-Z][a-z]+)(?:[ -](?:[A-Z][a-z]+|of|and|the)){0,3}\b")
STOPWORDS = {
    "the", "this", "that", "these", "those", "each", "every", "when", "where",
    "which", "with", "within", "without", "from", "into", "for", "and", "but",
    "in", "on", "at", "by", "of", "to", "as", "it", "is", "are", "be", "an", "a",
    "however", "therefore", "instead", "note", "figure", "table", "example",
    "further", "reading", "purpose", "concepts", "risks", "introduction",
    "summary", "overview", "elements", "implementation", "considerations",
    "background", "rationale", "future", "topics", "core", "design", "decisions",
}


def check_undefined(
    glossary_keys: set[str], pages: list[Page], glossary_paths: set[str], min_pages: int = 2,
    min_hits: int = 4,
) -> list[Finding]:
    """Kandidaat-begrippen die vaak voorkomen maar niet gedefinieerd zijn."""
    hits: Counter[str] = Counter()
    where: dict[str, set[str]] = defaultdict(set)

    for p in pages:
        if p.path in glossary_paths:
            continue
        text = re.sub(r"```.*?```", " ", p.text, flags=re.DOTALL)
        text = re.sub(r"https?://\S+", " ", text)
        for m in CANDIDATE_RE.finditer(text):
            phrase = m.group(0).strip()
            words = phrase.split()
            if len(words) == 1 and words[0].lower() in STOPWORDS:
                continue
            if all(w.lower() in STOPWORDS for w in words):
                continue
            key = normalise(phrase)
            if not key or key in glossary_keys:
                continue
            hits[phrase] += 1
            where[phrase].add(p.path)

    findings = []
    for phrase, n in hits.most_common():
        if n < min_hits or len(where[phrase]) < min_pages:
            continue
        findings.append(
            Finding(
                check="C3-ongedefinieerd",
                severity="medium",
                term=phrase,
                evidence=f"{n}x gebruikt op {len(where[phrase])} pagina's, staat niet in de glossary.",
                suggestion="Definieer het begrip, of vervang het door een bestaand begrip.",
                pages=sorted(where[phrase]),
            )
        )
    return findings


# --------------------------------------------------------------------------- C4
def _similarity(a: str, b: str) -> float:
    """Jaccard op woordniveau. Ruw maar voldoende om afwijkingen op te merken."""
    wa, wb = set(normalise(a).split()), set(normalise(b).split())
    if not wa or not wb:
        return 0.0
    return len(wa & wb) / len(wa | wb)


def check_conflicts(term_sets: list[list[Term]], threshold: float = 0.45) -> list[Finding]:
    """Zelfde label, wezenlijk andere definitie in twee bronnen."""
    by_key: dict[str, list[Term]] = defaultdict(list)
    for terms in term_sets:
        for t in terms:
            if t.definition:
                by_key[t.key].append(t)

    findings = []
    for key, terms in by_key.items():
        for i, a in enumerate(terms):
            for b in terms[i + 1:]:
                if a.source == b.source:
                    continue
                sim = _similarity(a.definition, b.definition)
                if sim >= threshold:
                    continue
                findings.append(
                    Finding(
                        check="C4-conflict",
                        severity="blocker" if sim < 0.2 else "high",
                        term=a.label,
                        evidence=(
                            f"[{a.source}] {a.definition[:180]} || "
                            f"[{b.source}] {b.definition[:180]} (overlap {sim:.0%})"
                        ),
                        suggestion="Kies één definitie. Als beide nodig zijn, splits in twee "
                                   "begrippen met eigen prefLabel.",
                        pages=[a.source, b.source],
                    )
                )
    return findings


# --------------------------------------------------------------------------- C5
def check_mappings(
    glossary: list[Term], external: dict[str, dict[str, Term]], mapping_hints: dict[str, dict]
) -> list[Finding]:
    """Begrippen zonder expliciete koppeling naar een externe standaard."""
    findings = []
    for t in glossary:
        declared = mapping_hints.get(t.key, {})
        auto = {name: idx[t.key].label for name, idx in external.items() if t.key in idx}
        covered = set(declared) | set(auto)
        missing = [n for n in external if n not in covered]
        if not missing:
            continue
        findings.append(
            Finding(
                check="C5-mapping",
                severity="low",
                term=t.label,
                evidence=f"Geen koppeling naar: {', '.join(missing)}."
                         + (f" Wel naar: {', '.join(sorted(covered))}." if covered else ""),
                suggestion="Leg een skos:exactMatch / closeMatch / relatedMatch vast, of noteer "
                           "expliciet 'geen equivalent'.",
                pages=[t.source],
            )
        )
    return findings


def sort_findings(findings: list[Finding]) -> list[Finding]:
    order = {s: i for i, s in enumerate(SEVERITIES)}
    return sorted(findings, key=lambda f: (order.get(f.severity, 9), f.check, f.term.lower()))
