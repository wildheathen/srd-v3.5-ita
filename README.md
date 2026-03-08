# Crystal Ball — D&D 3.5 Reference App

App di consultazione del System Reference Document D&D 3.5 in italiano, basata sul fork di [olimot/srd-v3.5](https://github.com/olimot/srd-v3.5).

Frontend statico (HTML/CSS/JS vanilla) su GitHub Pages, senza backend ne build system.

## Quick start

```bash
# Installa dipendenze (solo per test e backend opzionale)
pip install -r requirements.txt

# Esegui test
python -m pytest tests/ -v

# Apri direttamente nel browser
# oppure usa un server locale:
python -m http.server 8080
```

L'app carica i JSON da `data/` e non richiede backend.

## Dati

| Categoria | Entries | Fonti |
|-----------|---------|-------|
| Incantesimi | 4,155 | SRD + [dndtools.net](https://dndtools.net) + [5clone.com](https://5clone.com) |
| Talenti | 3,537 | SRD (111) + dndtools.net (3,426) |
| Abilita | 113 | dndtools.net (71 skills + 42 skill tricks) |
| Classi | 730 | SRD (31) + dndtools.net (699, di cui 610 prestigio) |
| Razze | 42 | SRD (7) + dndtools.net (35) |
| Mostri | 312 | SRD (289) + dndtools.net (23) |
| Equipaggiamento | 288 | SRD |
| Regole | 19 pagine | SRD |
| Manuali | 110 | Catalogo manuali EN/IT con abbreviazioni |

## Feature

- **Virtual scrolling** — con 4,155+ spell, renderizza solo ~30-40 nodi DOM visibili
- **Ricerca full-text** — toggle per cercare anche nelle descrizioni, con highlighting dei risultati
- **Multilingua (IT/EN)** — cambio lingua in tempo reale con persistenza dell'item selezionato
- **Preparazione incantesimi** — lista preparati con contatori uso/preparati, persistenza in localStorage
- **Filtri avanzati** — scuola, classe/dominio, livello, tipo, CR, manuale, edizione 3.0/3.5
- **Responsive** — layout adattivo con touch target 36x36px su mobile

## Struttura repo

```
/data/              → JSON per categoria (spells, feats, classes, monsters, races, equipment, rules, skills, sources)
/data/i18n/it/      → Overlay traduzioni italiane (per slug)
/frontend/          → style.css, app.js, i18n.js
/frontend/i18n/     → Stringhe UI per lingua (it.json, en.json)
/scripts/           → Parser SRD, scraper dndtools/5clone, PDF converter, import
/tests/             → Test pytest (schema JSON, overlay i18n)
/sources/           → Sorgenti HTML/PDF/CSV
index.html          → Entry point
```

## Fonti dati e crediti

| Fonte | Cosa fornisce |
|-------|---------------|
| [olimot/srd-v3.5](https://github.com/olimot/srd-v3.5) | HTML SRD inglese (base del progetto) |
| [Wizards of the Coast SRD](https://archive.org/details/dnd35srd) | Documenti originali OGL D&D 3.5 |
| [dndtools.net](https://dndtools.net) | Database esteso EN: incantesimi, talenti, classi, abilita, razze, mostri da 100+ manuali |
| [5clone.com](https://5clone.com) | Wiki italiana D&D 3.5: nomi italiani incantesimi e riferimenti manuali |
| [editorifolli.it](https://www.editorifolli.it/f/srd35/) | SRD italiano ufficiale in 249 PDF (regole, razze, classi, incantesimi, ecc.) |
| Manuale del Giocatore IT (OCR) | Descrizioni italiane di incantesimi e talenti |

Catalogo di 110 manuali D&D 3.5 con nomi EN/IT e abbreviazioni in `data/sources.json`.

## Deploy

GitHub Actions: push su `master` → test pytest → build con cache-busting → deploy GitHub Pages.

## Contribuire

Le traduzioni italiane sono il contributo piu utile. Vedi [CONTRIBUTING.md](CONTRIBUTING.md) per i dettagli.

Per la documentazione tecnica completa (schema DB, convenzioni, script, architettura i18n) vedi [CLAUDE.md](CLAUDE.md).

## Licenza

Contenuti SRD rilasciati sotto [Open Game License v1.0a](https://opengamingfoundation.org/ogl.html).
