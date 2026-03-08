# Crystal Ball — D&D 3.5 Reference App

App di consultazione del System Reference Document D&D 3.5, basata sul fork di [olimot/srd-v3.5](https://github.com/olimot/srd-v3.5).

## Stack

- **Frontend:** HTML/CSS/JS vanilla su GitHub Pages (legge i JSON direttamente, nessun build system)
- **Data format:** JSON per categoria in `/data/`
- **Backend:** Python + FastAPI (opzionale, per API REST locale)
- **Database:** SQLite (`dnd35.db`, opzionale, generato dagli script)
- **CI/CD:** GitHub Actions (test + deploy)

## Fonti dati

I dati del progetto provengono da diverse fonti, tutte relative al contenuto Open Game License (OGL) di D&D 3.5:

| Fonte | Tipo | Contenuto |
|-------|------|-----------|
| [olimot/srd-v3.5](https://github.com/olimot/srd-v3.5) | HTML EN | SRD inglese completo: spell, feat, classi, razze, equipaggiamento, mostri, regole, psionics, epic, divine, magic items |
| [dndtools.net](https://dndtools.net) | HTML EN | Database esteso D&D 3.5: 4155 incantesimi, 3537 talenti, 730 classi, 113 abilita/trucchi, 42 razze, 312 mostri. Include source book, pagina, edizione (3.0/3.5) |
| [5clone.com](https://5clone.com) | HTML IT/EN | Wiki italiana D&D 3.5: nomi italiani degli incantesimi, riferimenti ai manuali, descrizioni brevi (~1368 spell) |
| [editorifolli.it](https://www.editorifolli.it/f/srd35/) | PDF IT | SRD italiano ufficiale: 249 PDF organizzati in 10 capitoli (regole, razze, classi, abilita, talenti, equipaggiamento, avventura, combattimento, magia, incantesimi) |
| Testo manuale OCR | TXT IT | Manuale del Giocatore italiano (OCR da PDF), usato per estrarre descrizioni IT di spell e talenti |
| `data/sources.json` | JSON | Catalogo di 110 manuali D&D 3.5 con nomi EN/IT e abbreviazioni (es. PHB→MdG, DMG→GdDM) |

## Dati estratti

| Categoria | JSON | Entries | Fonti |
|-----------|------|---------|-------|
| Incantesimi | `spells.json` | 4,155 | SRD + dndtools.net + 5clone.com |
| Talenti | `feats.json` | 3,537 | SRD (111) + dndtools.net (3,426) |
| Abilita | `skills.json` | 113 | dndtools.net (71 skills + 42 skill tricks) |
| Classi | `classes.json` | 730 | SRD (31) + dndtools.net (699, di cui 610 prestigio) |
| Razze | `races.json` | 42 | SRD (7) + dndtools.net (35) |
| Mostri | `monsters.json` | 312 | SRD (289) + dndtools.net (23) |
| Equipaggiamento | `equipment.json` | 288 | SRD |
| Regole | `rules.json` | 19 pagine | SRD |
| Manuali | `sources.json` | 110 | Catalogo manuali EN/IT |

### Campi comuni dndtools.net

Ogni entry proveniente da dndtools.net ha questi campi aggiuntivi:
- `source_book`: nome completo del manuale EN (es. "Player's Handbook v.3.5")
- `source_page`: numero pagina
- `source_url`: URL dndtools.net della pagina dettaglio
- `edition`: "3.0" o "3.5"
- `source_site`: "dndtools.net"

### Schema skills.json

Skills (`category: "skill"`):
- `key_ability`: STR/DEX/CON/INT/WIS/CHA
- `trained_only`: boolean
- `armor_check_penalty`: boolean
- `check`, `action`, `try_again`, `special`, `synergy`, `restriction`, `untrained`: sezioni HTML

Skill Tricks (`category: "skill_trick"`):
- `prerequisites`: testo requisiti
- `benefit`: testo beneficio HTML

## Struttura repo

```
/data/              → JSON generati dal parser (spells, feats, races, equipment, classes, monsters, rules, skills, sources)
/data/i18n/{lang}/  → Data overlay files per lingua (solo campi tradotti, keyed by slug)
/scripts/           → Parser, scraper, import, PDF converter
/backend/           → FastAPI app (opzionale, non necessario per GitHub Pages)
/frontend/          → style.css, app.js, i18n.js (caricati da index.html nella root)
/frontend/i18n/     → UI string files per lingua (it.json, en.json)
/tests/             → Test suite pytest (schema JSON, overlay i18n)
/sources/           → Sorgenti HTML/PDF/CSV (vedi sotto)
index.html          → Entry point Crystal Ball (root, servito da GitHub Pages)
```

**Sorgenti e risorse** (sotto `/sources/`):
```
/sources/srd/                   → HTML SRD inglese da olimot/srd-v3.5 (spells, monsters, regole, ecc.)
/sources/testo-manuale/         → Testo manuale italiano (OCR da PDF) + HTML per capitoli
/sources/contrib/               → CSV e HTML di supporto per traduzioni e import (5clone, classi, mostri)
/sources/pdf-ita/               → HTML estratti dai PDF SRD italiano (249 file, 10 capitoli)
```

## Schema DB

### Tabelle principali

**spells:** name, slug, school, subschool, descriptor, level, components, casting_time, range, target_area_effect, duration, saving_throw, spell_resistance, desc_html

**feats:** name, slug, type, prerequisites, benefit, normal, special, desc_html

**races:** name, slug, traits_json, desc_html

**equipment:** name, slug, category, data_json, desc_html

**classes:** name, slug, hit_die, alignment, table_html, desc_html

### Tabella traduzioni

**translations:** id, entity_type, entity_id, lang, field, value

Serve per le traduzioni IT incrementali senza toccare le tabelle principali.

## Convenzioni

- Campi EN sempre presenti, IT opzionali via tabella `translations`
- `desc_html`: testo formattato in HTML, **non strippare i tag** — la formattazione serve
- Fallback lingua: se traduzione IT non esiste, mostra EN
- ID numerici auto-increment, slug testuale per riferimenti esterni
- Il parser legge i file HTML dalla root del repo (non da una sottocartella separata)
- Il frontend legge i JSON statici da `data/` (non richiede backend)
- Gli incantesimi preparati sono salvati in `localStorage` (chiave `crystalball_prepared`)

## Frontend

Tab disponibili: **Incantesimi**, **Preparati**, **Talenti**, **Appresi**, **Abilita**, **Classi**, **Razze**, **Equipaggiamento**, **Mostri**, **Regole**, **Stato Traduzioni**

### Feature principali

- **Virtual scrolling**: con 4,155+ spell, il DOM renderizza solo ~30-40 nodi visibili (altezza fissa 52px per riga, buffer ±15 righe). Riduce drasticamente il consumo di memoria.
- **Ricerca full-text**: toggle "Cerca nella descrizione" accanto alla barra di ricerca. Quando attivo, cerca anche in `desc_html` e `benefit` (con strip dei tag HTML). Preferenza salvata in localStorage.
- **Highlighting**: i termini cercati vengono evidenziati con `<mark>` sia nella lista risultati che nel pannello dettaglio.
- **Persistenza selezione al cambio lingua**: quando si cambia lingua (IT/EN), l'item aperto nel dettaglio resta selezionato e viene aggiornato nella nuova lingua.
- **Touch target mobile**: bottoni min 36x36px per usabilita su dispositivi touch.

### Incantesimi
- Filtro scuola (dropdown), filtro classe/dominio (dropdown), filtro manuale
- Multi-select livello 0–9 (checkbox), con bottoni Tutti/Nessuno
- Checkbox "Includi edizione 3.0"
- Ordinamento per livello crescente
- Badge verde con contatore `usato/preparato` per incantesimi gia preparati
- Bottone **+** per aggiungere alla lista preparati

### Preparati
- Lista incantesimi preparati con contatori uso/preparati (+/- per entrambi)
- Persistenza in localStorage
- Click sul nome per vedere il dettaglio dell'incantesimo
- Indicatore visivo rosso quando tutti gli usi sono esauriti

### Abilita
- Filtro per categoria (Abilita / Trucchi / Entrambi)
- Filtro per caratteristica chiave (STR/DEX/CON/INT/WIS/CHA)
- Checkbox "Solo addestrate"
- Dettaglio con sezioni Check, Azione, Speciale, Sinergia, ecc.

### Classi
- Filtro per tipo (Base / Prestigio / Tutti)
- Dettaglio con hit die, skill points, class skills, source book

### Razze
- Dettaglio con taglia, velocita, modificatori caratteristiche, livello aggiustamento

### Mostri
- Filtro per CR (Challenge Rating) e tipo creatura
- Stat block completo nel pannello dettaglio

## Script

```bash
# ── Parsing sorgenti SRD (HTML → JSON) ──
python scripts/parse_srd.py              # parse tutto
python scripts/parse_srd.py spells       # parse solo incantesimi
python scripts/parse_srd.py monsters     # parse solo mostri

# ── Import JSON → SQLite ──
python scripts/import_to_db.py

# ── Import traduzioni IT (formato JSON) ──
python scripts/import_translations.py translations_it.json

# ── Estrazione PDF → HTML strutturato ──
python scripts/pdf_to_html.py <pdf_path> <output_html>                    # modo spells (default)
python scripts/pdf_to_html.py --mode generic <pdf_path> <output_html>     # modo generico

# ── Download e conversione batch PDF SRD italiano ──
python scripts/download_srd_pdfs.py --output-dir /tmp/srd-pdf-ita         # download 249 PDF
python scripts/convert_all_pdfs.py --pdf-dir /tmp/srd-pdf-ita --output-dir sources/pdf-ita
python scripts/convert_all_pdfs.py --force                                # ri-converte anche se HTML esiste

# ── Scraping dndtools.net (EN) ──
python scripts/dndtools_download.py --category feats      # 3588 talenti
python scripts/dndtools_download.py --category skills     # 71 abilita
python scripts/dndtools_download.py --category skill-tricks # 42 trucchi abilita
python scripts/dndtools_download.py --category classes    # 743 classi
python scripts/dndtools_download.py --category races      # 42 razze
python scripts/dndtools_download.py --category monsters   # 29 mostri

# Parse HTML → JSON intermedio
python scripts/dndtools_parse_feats.py     # → data/dndtools/feats_en_parsed.json
python scripts/dndtools_parse_skills.py    # → data/skills.json
python scripts/dndtools_parse_classes.py   # → data/dndtools/classes_en_parsed.json
python scripts/dndtools_parse_races.py     # → data/dndtools/races_en_parsed.json
python scripts/dndtools_parse_monsters.py  # → data/dndtools/monsters_en_parsed.json

# Merge parsed data → data/*.json
python scripts/dndtools_merge_feats.py     # feats.json: 111 → 3537
python scripts/dndtools_merge_classes.py   # classes.json: 31 → 730
python scripts/dndtools_merge_races.py     # races.json: 7 → 42
python scripts/dndtools_merge_monsters.py  # monsters.json: 289 → 312

# ── Scraping 5clone.com (IT) ──
python scripts/parse_5clone_index.py       # estrai URL spell da indice salvato
python scripts/scrape_5clone.py            # scrape pagine dettaglio (~1368 spell)
python scripts/merge_5clone_spells.py      # merge nomi IT in spells.json

# ── Backend locale (opzionale) ──
uvicorn backend.app:app --reload --port 8000
```

## Estrazione PDF SRD

Lo script `scripts/pdf_to_html.py` converte i PDF del SRD italiano (da editorifolli.it) in HTML strutturato.

**Due modalita:**
- `--mode spells` (default): parsing strutturato per incantesimi con campi separati (Scuola, Livello, Componenti, ecc.)
- `--mode generic`: parsing generico per tutti gli altri contenuti (heading detection, paragrafi, bold/italic, tabelle)

**Approccio ibrido:**
1. `pdftotext` per il testo completo (zero perdite)
2. Parsing raw PDF streams per identificare font Bold/Italic
3. Merge: applica `<b>`/`<i>` al testo usando i frammenti formattati (con word-boundary check per bold)
4. Struttura: split in blocchi con campi separati dalla descrizione (spells) o heading detection (generic)
5. Leggibilita: `<br>` dopo ogni frase e prima di elenchi
6. Tabelle: rilevamento automatico di pattern tabulari (colonne separate da 3+ spazi), generazione `<table>` HTML

**Pipeline batch:**
- `download_srd_pdfs.py`: manifesto hardcoded di tutti i 249 PDF, download con curl, resume-safe
- `convert_all_pdfs.py`: routing automatico cap.10 → spells, resto → generic, skip existing

**Requisiti:** `pdftotext` e `curl` nel PATH (inclusi in Git for Windows). Nessuna dipendenza Python esterna.

**Sorgenti PDF:** `https://www.editorifolli.it/f/srd35/` (249 file, ~100MB totali)

## Test

Test suite con pytest, eseguiti automaticamente in CI prima del deploy.

```bash
python -m pytest tests/ -v
```

**Test disponibili:**
- `test_json_schema.py` — Validazione schema JSON per tutte le categorie (campi obbligatori, no duplicati, no nomi vuoti, conteggi minimi)
- `test_i18n_overlay.py` — Integrita overlay traduzioni (slug validi, no orfani, merge corretto, fallback EN)

## API Endpoints (backend opzionale)

```
GET /api/spells?q=&school=&level=&limit=50&offset=0
GET /api/spells/{slug}
GET /api/feats?q=&type=&limit=50&offset=0
GET /api/feats/{slug}
GET /api/races
GET /api/races/{slug}
GET /api/equipment?q=&category=&limit=50&offset=0
GET /api/equipment/{id}
GET /api/classes
GET /api/classes/{slug}
```

Tutti gli endpoint accettano `?lang=it` per le traduzioni.

## Deploy

GitHub Actions workflow (`.github/workflows/deploy.yml`):
- Trigger: push su `master` o manual dispatch
- Step: test pytest → genera report traduzioni → build con cache-busting → deploy GitHub Pages
- Copia `index.html`, `frontend/`, `data/*.json`, `data/i18n/` in `_site/`

## Sistema i18n (multi-lingua)

L'app supporta il cambio lingua in tempo reale tramite un selettore nell'header.

### Architettura

Due livelli di traduzione:

1. **UI strings** (`frontend/i18n/{lang}.json`): labels, bottoni, filtri, messaggi (~80 chiavi)
2. **Data overlay** (`data/i18n/{lang}/{category}.json`): traduzioni dei contenuti SRD (nomi, scuole, tipi)

### Come funziona

- Lingua di default: italiano (`it`)
- Preferenza salvata in `localStorage` (chiave `crystalball_lang`)
- I dati base in `/data/` sono sempre in inglese (EN)
- Per ogni lingua diversa da EN, il frontend carica un overlay da `data/i18n/{lang}/` e fa il merge per slug
- Se un campo non ha traduzione nell'overlay, resta in inglese (fallback automatico)
- La funzione `t(key)` traduce le stringhe UI; `loadDataOverlay()` e `applyOverlay()` gestiscono i dati
- Cambio lingua preserva l'item selezionato nel pannello dettaglio

### Aggiungere una nuova lingua

1. Creare `frontend/i18n/{lang}.json` copiando `en.json` e traducendo i valori
2. Creare `data/i18n/{lang}/` con file overlay per categoria (formato: array di oggetti con `slug` + campi tradotti)
3. Aggiungere il codice lingua a `SUPPORTED_LANGS` in `frontend/i18n.js`
4. Aggiungere `<option value="{lang}">` nel selettore in `index.html`

### Formato overlay dati

```json
[
  {"slug": "fireball", "name": "Palla di Fuoco", "school": "Invocazione"},
  {"slug": "magic-missile", "name": "Dardo Incantato"}
]
```

Solo i campi presenti vengono sovrascritti; il resto resta in inglese.

## Task correnti

- [x] Setup struttura cartelle
- [x] Scrivere parse_srd.py (incantesimi, talenti, razze, equipaggiamento, classi, mostri, regole)
- [x] Definire schema SQLite
- [x] Scrivere import_to_db.py
- [x] Setup backend FastAPI
- [x] Setup frontend (HTML/CSS/JS) con filtri avanzati
- [x] Scrivere import_translations.py
- [x] GitHub Actions deploy workflow
- [x] Sistema preparazione incantesimi con contatori uso/preparati
- [x] Sezione mostri (312 entries con stat block)
- [x] Sezione regole (19 pagine descrittive)
- [x] Sistema i18n multi-lingua (UI strings + data overlay)
- [x] Traduzioni IT termini chiave (nomi spell, mostri, talenti, classi, razze)
- [x] Scraping dndtools.net EN (feats, skills, skill tricks, classes, races, monsters)
- [x] Scraping 5clone.com IT (nomi italiani incantesimi)
- [x] Tab Abilita (skills + skill tricks) con filtri
- [x] Dettagli estesi per tutte le categorie (source book, prestige, size, ecc.)
- [x] Virtual scrolling per performance con 4000+ entries
- [x] Ricerca full-text con toggle e highlighting
- [x] Test suite pytest (schema JSON + overlay i18n)
- [x] Touch target mobile
- [x] Table parsing nel PDF converter
- [x] Persistenza selezione al cambio lingua
- [ ] Traduzioni IT descrizioni complete (desc_html, benefit, ecc.)
