"""Ophalen en cachen van de BDI GitBook-documentatie.

GitBook publiceert een machine-leesbare index op /llms.txt en van elke pagina
een Markdown-variant door '.md' aan de URL te plakken. Dat maakt scrapen
onnodig: we lezen de index en halen per pagina de Markdown op.
"""

from __future__ import annotations

import hashlib
import re
import time
from dataclasses import dataclass
from pathlib import Path

import requests

USER_AGENT = "bdi-termcheck/0.1 (+https://github.com/Basic-Data-Infrastructure)"
LINK_RE = re.compile(r"^\s*-\s*\[(?P<title>[^\]]+)\]\((?P<url>https?://[^)\s]+\.md)\)")


@dataclass(frozen=True)
class Page:
    """Eén documentatiepagina."""

    title: str
    url: str
    slug: str
    text: str

    @property
    def path(self) -> str:
        """Pad binnen de gitbook, handig als korte verwijzing in rapporten."""
        return self.url.split("/bdi-public-documentation/", 1)[-1]


def _cache_name(url: str) -> str:
    digest = hashlib.sha1(url.encode("utf-8")).hexdigest()[:10]
    tail = url.rstrip("/").split("/")[-1].replace(".md", "")
    return f"{tail}-{digest}.md"


def _get(url: str, session: requests.Session, timeout: int = 30) -> str:
    resp = session.get(url, timeout=timeout, headers={"User-Agent": USER_AGENT})
    resp.raise_for_status()
    return resp.text


def read_index(index_url: str, session: requests.Session) -> list[tuple[str, str]]:
    """Lees llms.txt en geef (titel, url) terug voor elke .md-pagina."""
    body = _get(index_url, session)
    out: list[tuple[str, str]] = []
    seen: set[str] = set()
    for line in body.splitlines():
        m = LINK_RE.match(line)
        if not m:
            continue
        url = m.group("url")
        if url in seen:
            continue
        seen.add(url)
        out.append((m.group("title").strip(), url))
    if not out:
        raise RuntimeError(f"Geen pagina-links gevonden in {index_url}")
    return out


def strip_boilerplate(text: str) -> str:
    """Verwijder de GitBook-header en de 'Agent Instructions'-voettekst.

    Die staan op elke pagina en zouden anders elke woordtelling vervuilen.
    """
    text = re.sub(r"^>.*?\n", "", text, count=1)
    text = re.split(r"\n---\n\s*# Agent Instructions", text)[0]
    return text.strip()


def fetch_all(
    index_url: str,
    cache_dir: Path,
    refresh: bool = False,
    delay: float = 0.3,
) -> list[Page]:
    """Haal alle pagina's op (of lees ze uit de cache) en geef ze terug."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    session = requests.Session()
    pages: list[Page] = []

    for title, url in read_index(index_url, session):
        cached = cache_dir / _cache_name(url)
        if cached.exists() and not refresh:
            raw = cached.read_text(encoding="utf-8")
        else:
            raw = _get(url, session)
            cached.write_text(raw, encoding="utf-8")
            time.sleep(delay)
        slug = url.rstrip("/").split("/")[-1].removesuffix(".md")
        pages.append(Page(title=title, url=url, slug=slug, text=strip_boilerplate(raw)))

    return pages


def load_cached(cache_dir: Path) -> list[Page]:
    """Lees uitsluitend uit de cache. Handig offline en in tests."""
    pages = []
    for f in sorted(cache_dir.glob("*.md")):
        raw = f.read_text(encoding="utf-8")
        text = strip_boilerplate(raw)
        title = next((ln[2:].strip() for ln in text.splitlines() if ln.startswith("# ")), f.stem)
        pages.append(Page(title=title, url=f"file://{f}", slug=f.stem, text=text))
    return pages
