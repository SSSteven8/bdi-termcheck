# bdi-termcheck

Controleert de terminologie in de [BDI Referentiearchitectuur](https://bdi.gitbook.io/bdi-public-documentation)
en exporteert het begrippenkader als SKOS conform NL-SBB.

De tool leest de GitBook-documentatie via `llms.txt`, haalt van elke pagina de
Markdown-versie op en vergelijkt die met de BDI-glossary, het CTN-glossary, DSSC,
iSHARE en OpenID Connect. Het resultaat is een rapport met bevindingen en een
machineleesbaar begrippenkader, beide reproduceerbaar in CI.

## Output

| Bestand | Inhoud |
| --- | --- |
| `reports/report.md` | Bevindingen, gesorteerd op ernst |
| `reports/findings.csv` | Zelfde lijst, geschikt voor spreadsheets |
| `vocab/bdi.ttl` | Begrippenkader als SKOS/Turtle |

## Controles

| Code | Detecteert | Voorbeeld |
| --- | --- | --- |
| C1-variant | Schrijfwijzen die door elkaar gebruikt worden | `Association Register` vs `Association Registry` |
| C2-weeskind | Gedefinieerd begrip dat nergens gebruikt wordt | `Data Sovereignty` |
| C3-ongedefinieerd | Veelgebruikt begrip zonder definitie | `BDI Connector`, `Local Policy Engine` |
| C4-conflict | Eén begrip, twee onverenigbare definities | `Outsider` |
| C5-mapping | Begrip zonder koppeling naar DSSC / iSHARE / OIDC | `Root Association` |

C1 en C5 zijn configuratiegestuurd: welke varianten bij elkaar horen, welke term
de voorkeur heeft en welke externe mappings gelden, staat in `config/config.yaml`.
Dat is een redactionele keuze, geen codekeuze — de code doet uitsluitend het
telwerk.

## Vereisten

- Python 3.10 of hoger
- Git

## Installatie

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
```

Op macOS/Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Gebruik

```bash
bdi-termcheck run              # documentatie ophalen en analyseren
bdi-termcheck run --offline    # analyseren op basis van de cache
bdi-termcheck run --refresh    # cache negeren en opnieuw ophalen
bdi-termcheck vocab            # vocab/bdi.ttl genereren
pytest -q                      # tests draaien
```

De eerste `run` haalt alle documentatiepagina's op en cachet ze in `data/pages/`.
Met `--fail-on high` (of `blocker`/`medium`/`low`) geeft de tool exitcode 1 bij
bevindingen van die ernst of hoger, geschikt voor gebruik als CI-gate.

## Configuratie

Alles wat menselijk oordeel vraagt staat in `config/config.yaml`.

Variantgroep toevoegen:

```yaml
variant_groups:
  - preferred: Data Custodian
    variants: [Data Custodian, Data Owner, Data Holder]
    severity: blocker
    suggestion: Kies één rolnaam en leg de rest vast als altLabel.
```

Extern glossary toevoegen: plaats een YAML-bestand in `config/glossaries/` in het
formaat van de bestaande bestanden en verwijs ernaar onder `external_glossaries`.

Het CTN-document is leidend. `config/glossaries/ctn.yaml` is de machineleesbare
kopie ervan en wordt bijgewerkt zodra er een nieuwe versie van het document is.

## Continuous integration

`.github/workflows/termcheck.yml` draait de controle wekelijks, bij elke pull
request en on demand. De workflow vereist *Read and write permissions* onder
**Settings → Actions → General → Workflow permissions** om het bijgewerkte rapport
terug te committen. Het rapport en het SKOS-bestand worden daarnaast als artifact
bewaard.

## Publicatie in GitBook

GitBook publiceert via GitHub Sync. Koppel de space aan de repository die de
architectuur bevat en laat de workflow `reports/report.md` en een leesbare versie
van het begrippenkader naar die repository schrijven; GitBook publiceert die
bestanden vervolgens als pagina.

## Begrippenkader als SKOS/NL-SBB

Het gegenereerde `vocab/bdi.ttl` volgt NL-SBB, geserialiseerd als SKOS:

| NL-SBB | SKOS |
| --- | --- |
| Term | `skos:prefLabel` |
| Synoniem | `skos:altLabel` |
| Definitie | `skos:definition` |
| Toelichting | `skos:scopeNote` |
| Bron | `dct:source` |
| Hiërarchie | `skos:broader` / `skos:narrower` |
| Externe gelijkstelling | `skos:exactMatch` / `closeMatch` / `relatedMatch` |
| Vervallen | `owl:deprecated` + `skos:changeNote` |

Voorgestelde namespace: `https://begrippen.bdinetwork.org/id/begrip/{slug}`.
Het Turtle-bestand is de bron; de glossarypagina in GitBook wordt eruit
gegenereerd.

## Structuur

```
src/bdi_termcheck/
  fetch.py     ophalen en cachen van GitBook-pagina's
  extract.py   begrippen uit GitBook-HTML en YAML
  analyze.py   de vijf controles
  skos.py      export naar SKOS/Turtle
  report.py    Markdown- en CSV-rapport
  cli.py       commandline
config/        instellingen en externe glossaries
tests/         tests met vaste voorbeeldpagina's
```

## Licentie

EUPL-1.2.
