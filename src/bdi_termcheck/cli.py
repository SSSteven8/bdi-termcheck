"""Commandline-interface: `bdi-termcheck run`."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

from . import analyze, extract, fetch, report, skos

DEFAULT_INDEX = "https://bdi.gitbook.io/bdi-public-documentation/llms.txt"


def load_config(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="bdi-termcheck", description="Terminologiecontrole BDI")
    p.add_argument("command", choices=["fetch", "run", "vocab"], help="wat te doen")
    p.add_argument("--config", type=Path, default=Path("config/config.yaml"))
    p.add_argument("--cache", type=Path, default=Path("data/pages"))
    p.add_argument("--out", type=Path, default=Path("reports"))
    p.add_argument("--vocab-out", type=Path, default=Path("vocab/bdi.ttl"))
    p.add_argument("--offline", action="store_true", help="alleen de cache gebruiken")
    p.add_argument("--refresh", action="store_true", help="cache negeren en opnieuw ophalen")
    p.add_argument("--fail-on", default="", choices=["", *analyze.SEVERITIES],
                   help="exit-code 1 als er bevindingen van deze ernst of hoger zijn")
    return p


def get_pages(args, cfg) -> list[fetch.Page]:
    if args.offline:
        pages = fetch.load_cached(args.cache)
        if not pages:
            sys.exit(f"Cache {args.cache} is leeg. Draai eerst zonder --offline.")
        return pages
    return fetch.fetch_all(cfg.get("index_url", DEFAULT_INDEX), args.cache, refresh=args.refresh)


def collect_glossary(pages: list[fetch.Page], cfg: dict) -> tuple[list[extract.Term], set[str]]:
    configured = set(cfg.get("glossary_pages", []))
    slugs = {Path(g).stem for g in configured}
    terms: list[extract.Term] = []
    actual: set[str] = set()
    for p in pages:
        if p.path in configured or p.slug in slugs:
            terms += extract.parse_gitbook_glossary(p)
            actual.add(p.path)
    # Begrippenkaartjes staan ook op gewone bouwsteenpagina's; die tellen mee
    # voor conflictdetectie maar niet als canonieke glossary.
    return terms, actual


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    cfg = load_config(args.config)

    pages = get_pages(args, cfg)
    print(f"{len(pages)} pagina's geladen.")

    if args.command == "fetch":
        return 0

    glossary, glossary_paths = collect_glossary(pages, cfg)
    inline = [t for p in pages if p.path not in glossary_paths
              for t in extract.parse_card_table(p)]
    print(f"{len(glossary)} glossarybegrippen, {len(inline)} inline definities.")

    external: dict[str, dict[str, extract.Term]] = {}
    external_terms: list[list[extract.Term]] = []
    for name, rel in (cfg.get("external_glossaries") or {}).items():
        path = args.config.parent / rel
        if not path.exists():
            print(f"  overslaan: {path} bestaat niet")
            continue
        terms = extract.load_yaml_glossary(path, name)
        external[name] = extract.index_terms(terms)
        external_terms.append(terms)
        print(f"  {name}: {len(terms)} begrippen")

    if args.command == "vocab":
        out = skos.write_vocabulary(
            glossary,
            args.vocab_out,
            mappings=cfg.get("skos_mappings") or {},
            deprecated=set(cfg.get("deprecated") or []),
        )
        print(f"SKOS geschreven naar {out}")
        return 0

    keys = {t.key for t in glossary} | {extract.normalise(a) for t in glossary for a in t.aliases}

    findings: list[analyze.Finding] = []
    findings += analyze.check_variants(cfg.get("variant_groups") or [], pages)
    findings += analyze.check_orphans(glossary, pages, glossary_paths)
    findings += analyze.check_undefined(keys, pages, glossary_paths,
                                        **(cfg.get("undefined") or {}))
    findings += analyze.check_conflicts([glossary, inline, *external_terms])
    findings += analyze.check_mappings(glossary, external, cfg.get("skos_mappings") or {})
    findings = analyze.sort_findings(findings)

    paths = report.write_reports(findings, args.out, len(pages), len(glossary))
    print(f"{len(findings)} bevindingen. Geschreven: " + ", ".join(str(p) for p in paths))

    if args.fail_on:
        cutoff = analyze.SEVERITIES.index(args.fail_on)
        worst = [f for f in findings if analyze.SEVERITIES.index(f.severity) <= cutoff]
        if worst:
            print(f"{len(worst)} bevindingen op niveau '{args.fail_on}' of hoger.")
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
