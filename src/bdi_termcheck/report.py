"""Rapportage: één Markdown-rapport en één CSV om in Excel te openen."""

from __future__ import annotations

import csv
import datetime as dt
from pathlib import Path

from .analyze import Finding, SEVERITIES

HEADERS = ["#", "Check", "Ernst", "Term", "Bevinding", "Voorstel", "Pagina's"]


def _escape(cell: str) -> str:
    return cell.replace("|", "\\|").replace("\n", " ")


def to_markdown(findings: list[Finding], n_pages: int, n_terms: int) -> str:
    counts = {s: sum(1 for f in findings if f.severity == s) for s in SEVERITIES}
    lines = [
        "# BDI terminologie-rapport",
        "",
        f"Gegenereerd op {dt.date.today().isoformat()} — "
        f"{n_pages} pagina's, {n_terms} gedefinieerde begrippen, {len(findings)} bevindingen.",
        "",
        "| Ernst | Aantal |",
        "| --- | ---: |",
    ]
    lines += [f"| {s} | {counts[s]} |" for s in SEVERITIES]
    lines += ["", "## Bevindingen", "", "| " + " | ".join(HEADERS) + " |",
              "|" + "|".join([" --- "] * len(HEADERS)) + "|"]
    for i, f in enumerate(findings, 1):
        lines.append(
            "| " + " | ".join(
                _escape(c) for c in (
                    str(i), f.check, f.severity, f.term, f.evidence,
                    f.suggestion, "; ".join(sorted(set(f.pages))[:4]),
                )
            ) + " |"
        )
    return "\n".join(lines) + "\n"


def write_reports(findings: list[Finding], out_dir: Path, n_pages: int, n_terms: int) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    md = out_dir / "report.md"
    md.write_text(to_markdown(findings, n_pages, n_terms), encoding="utf-8")

    csv_path = out_dir / "findings.csv"
    with csv_path.open("w", newline="", encoding="utf-8-sig") as fh:
        writer = csv.DictWriter(
            fh, fieldnames=["check", "severity", "term", "pages", "evidence", "suggestion"]
        )
        writer.writeheader()
        for f in findings:
            writer.writerow(f.as_row())
    return [md, csv_path]
