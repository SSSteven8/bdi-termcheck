# bdi-termcheck

Controleert de terminologie in de [BDI Referentiearchitectuur](https://bdi.gitbook.io/bdi-public-documentation)
en exporteert het begrippenkader als SKOS conform NL-SBB.

Het leest de GitBook-documentatie via `llms.txt`, haalt van elke pagina de
Markdown-versie op, en vergelijkt die met de glossary, met het CTN-document, met
DSSC, met iSHARE en met OpenID Connect.

## Wat het oplevert

| Bestand | Inhoud |
| --- | --- |
| `reports/report.md` | Rapport met alle bevindingen, gesorteerd op ernst |
| `reports/findings.csv` | Zelfde lijst, te openen in Excel |
| `vocab/bdi.ttl` | Het begrippenkader als SKOS/Turtle |

## De vijf controles

| Code | Wat het zoekt | Voorbeeld dat het vindt |
| --- | --- | --- |
| C1-variant | Schrijfwijzen die door elkaar gebruikt worden | `Association Register` naast `Association Registry` |
| C2-weeskind | Begrip staat in de glossary maar wordt nergens gebruikt | `Data Sovereignty` |
| C3-ongedefinieerd | Begrip wordt veel gebruikt maar is nergens gedefinieerd | `BDI Connector`, `Local Policy Engine` |
| C4-conflict | Zelfde begrip, twee onverenigbare definities | `Outsider` |
| C5-mapping | Begrip heeft geen koppeling naar DSSC / iSHARE / OIDC | `Root Association` |

C1 en C5 werken op basis van `config/config.yaml`. Dat is bewust: welke varianten
bij elkaar horen en welke term de voorkeur heeft, is een redactionele keuze, geen
codekeuze. Jij vult die tabel, het programma doet het telwerk.

---

# Stap voor stap: van niets naar draaiend

Deze uitleg gaat ervan uit dat je nog nooit met Git of Python hebt gewerkt.
Elke regel die begint met `$` typ je in een terminal (zonder de `$`).

## Stap 1 — Wat je nodig hebt

Installeer twee dingen op je laptop:

1. **Python 3.10 of hoger** — <https://www.python.org/downloads/>
   Vink bij het installeren op Windows *"Add Python to PATH"* aan.
2. **Git** — <https://git-scm.com/downloads>

Terminal openen: Windows → *PowerShell*. macOS → *Terminal*.

Controleer of het gelukt is:

```
$ python --version
$ git --version
```

Zie je bij allebei een versienummer, dan ben je klaar. Zegt Windows
"python is not recognized", dan is de PATH-optie niet aangevinkt; installeer
Python opnieuw met die vink aan.

## Stap 2 — Een repository op GitHub

1. Log in op <https://github.com> en ga naar de organisatie `Basic-Data-Infrastructure`.
2. Klik **New repository**.
3. Naam: `bdi-termcheck`. Zichtbaarheid: **Public**. Zet **Add a README** *uit*
   (die zit al in deze map).
4. Klik **Create repository**. GitHub toont nu een pagina met commando's — die
   heb je zo nodig.

## Stap 3 — De code naar GitHub zetten

Pak deze map uit op je laptop en ga er in de terminal naartoe:

```
$ cd pad/naar/bdi-termcheck
$ git init
$ git add .
$ git commit -m "Eerste versie van de terminologiecontrole"
$ git branch -M main
$ git remote add origin https://github.com/Basic-Data-Infrastructure/bdi-termcheck.git
$ git push -u origin main
```

Ververs de GitHub-pagina; je code staat er.

> Wat gebeurde hier? `git init` maakt van de map een repository. `git add .`
> selecteert alle bestanden. `git commit` legt een momentopname vast met een
> omschrijving. `git remote add origin` vertelt Git waar de kopie op GitHub staat.
> `git push` stuurt hem daarheen. Bij elke volgende wijziging herhaal je alleen
> `git add .`, `git commit -m "..."` en `git push`.

## Stap 4 — Lokaal draaien

Maak een *virtual environment*: een afgeschermde Python-installatie per project,
zodat pakketten van dit project niet botsen met andere projecten.

macOS / Linux:

```
$ python3 -m venv .venv
$ source .venv/bin/activate
$ pip install -e ".[dev]"
```

Windows PowerShell:

```
$ python -m venv .venv
$ .venv\Scripts\Activate.ps1
$ pip install -e ".[dev]"
```

Weigert PowerShell het activeren, draai dan eerst eenmalig:
`Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`.

Draai nu de controle:

```
$ bdi-termcheck run
```

De eerste keer haalt hij alle 45 pagina's op (ongeveer een halve minuut) en zet
ze in `data/pages/`. Daarna:

```
$ bdi-termcheck run --offline      # gebruik de cache, geen internet nodig
$ bdi-termcheck run --refresh      # haal alles opnieuw op
$ bdi-termcheck vocab              # schrijf vocab/bdi.ttl
$ pytest -q                        # draai de tests
```

Open `reports/report.md` in je editor, of `reports/findings.csv` in Excel.

Klaar met werken? `deactivate` sluit de virtual environment.

## Stap 5 — Automatisch laten draaien op GitHub

In `.github/workflows/termcheck.yml` staat al een *GitHub Action*: een script dat
GitHub op hun servers voor je uitvoert. Hij draait elke maandagochtend, én bij
elke pull request, én wanneer je zelf op de knop drukt.

Zetten:

1. Ga in je repository naar **Settings → Actions → General**.
2. Onder *Workflow permissions*: kies **Read and write permissions**, en klik **Save**.
   Zonder dit mag de action het bijgewerkte rapport niet terugcommitten.
3. Ga naar het tabblad **Actions**, kies *Terminologiecontrole*, klik **Run workflow**.

Na een minuut staat het verse rapport in de repository, en kun je het als
*artifact* downloaden.

## Stap 6 — Zichtbaar maken in GitBook

GitBook ondersteunt geen eigen plugins meer op de manier die je waarschijnlijk
in gedachten hebt; wat wél werkt is de **GitHub Sync** die GitBook aanbiedt.
De volgorde:

1. Koppel de gitbook-space aan de repository
   `Basic-Data-Infrastructure/BDI-Reference-Architecture` (GitBook → *Integrations*
   → *GitHub* → *Configure*).
2. Laat deze tool het gegenereerde `reports/report.md` en een leesbare versie van
   het begrippenkader in die repository schrijven, bijvoorbeeld als
   `readme/glossary/terminologie-rapport.md`.
3. GitBook publiceert dat bestand automatisch als pagina.

Zo hoef je in GitBook zelf niets te programmeren: de repository is de bron, en de
action houdt de pagina bij.

## Stap 7 — Bevindingen als change requests

De volgende stap in volwassenheid is dat elke bevinding van ernst `blocker` of
`high` automatisch een issue wordt in
[BDI-change-requests](https://github.com/Basic-Data-Infrastructure/BDI-change-requests/issues).
Voeg daarvoor een stap toe aan de workflow met de GitHub CLI:

```yaml
      - name: Issues aanmaken voor blockers
        env:
          GH_TOKEN: ${{ secrets.CHANGE_REQUEST_TOKEN }}
        run: |
          python -c "
          import csv
          rows = list(csv.DictReader(open('reports/findings.csv', encoding='utf-8-sig')))
          for r in rows:
              if r['severity'] == 'blocker':
                  print(r['term'], '|', r['suggestion'])
          " > blockers.txt
          # daarna per regel: gh issue create --repo ... --title ... --body ...
```

Bouw dit pas als de lijst met blockers stabiel is; anders overspoel je de
issuelijst met ruis.

---

## Configuratie aanpassen

Alles wat een redactionele keuze is, staat in `config/config.yaml`.

Een nieuwe variantgroep toevoegen:

```yaml
variant_groups:
  - preferred: Data Custodian
    variants: [Data Custodian, Data Owner, Data Holder]
    severity: blocker
    suggestion: Kies één rolnaam en leg de rest vast als altLabel.
```

Een nieuw extern glossary toevoegen: maak `config/glossaries/gaiax.yaml` in
hetzelfde formaat als de bestaande bestanden, en verwijs ernaar onder
`external_glossaries`.

Het CTN-document is leidend. Als er een nieuwe versie van het Word-document komt,
werk je `config/glossaries/ctn.yaml` bij; dat is de machineleesbare kopie ervan.

## Projectindeling

```
src/bdi_termcheck/
  fetch.py     ophalen en cachen van de GitBook-pagina's
  extract.py   begrippen uit gitbook-HTML en uit YAML halen
  analyze.py   de vijf controles
  skos.py      export naar SKOS/Turtle
  report.py    Markdown- en CSV-rapport
  cli.py       commandline
config/        instellingen en externe glossaries
tests/         tests met vaste voorbeeldpagina's
```

## Licentie

Voorstel: EUPL-1.2, in lijn met de rest van het BDI-ecosysteem.
