# Crystal Ball — D&D 3.5 Reference App

App di consultazione del System Reference Document D&D 3.5, basata sul fork di [olimot/srd-v3.5](https://github.com/olimot/srd-v3.5).

## Stack

- **Backend:** Python + FastAPI (opzionale, per API REST)
- **Database:** SQLite (`dnd35.db`, opzionale)
- **Data format:** JSON per categoria in `/data/`
- **Frontend:** HTML/CSS/JS statico su GitHub Pages (legge i JSON direttamente)
- **CI/CD:** GitHub Actions

## Struttura repo

```
/data/              → JSON generati dal parser (spells, feats, races, equipment, classes, monsters, rules)
/scripts/           → parse_srd.py, import_to_db.py, import_translations.py
/backend/           → FastAPI app (opzionale, non necessario per GitHub Pages)
/frontend/          → style.css, app.js, i18n.js (caricati da index.html nella root)
/frontend/i18n/     → UI string files per lingua (it.json, en.json, ...)
/data/i18n/{lang}/  → Data overlay files per lingua (solo campi tradotti, keyed by slug)
index.html          → Entry point Crystal Ball (root, servito da GitHub Pages)
dnd35.db            → SQLite database (gitignored, generato dagli script)
```

**Sorgenti e risorse** (sotto `/sources/`):
```
/sources/srd/spells/            → 9 file HTML con tutti gli incantesimi (spells-a-b.html ... spells-t-z.html)
/sources/srd/basic-rules-and-legal/ → regole base, talenti, razze, classi, equipaggiamento, combattimento, abilità
/sources/srd/divine/            → abilità divine, domini, ranghi
/sources/srd/epic/              → contenuti di livello epico
/sources/srd/magic-items/       → oggetti magici
/sources/srd/monsters/          → mostri (18 file HTML)
/sources/srd/psionics/          → contenuti psionici
/sources/testo-manuale/         → testo manuale italiano (OCR da PDF) + HTML per capitoli
/sources/contrib/               → CSV e HTML di supporto per traduzioni e import
/sources/pdf-ita/               → HTML estratti dai PDF SRD italiano (249 file, 10 capitoli)
```

**Sorgenti PDF italiano** (sotto `/sources/pdf-ita/`, 249 file totali):
```
/sources/pdf-ita/01-regole-base/       → 6 file (basi, caratteristiche, allineamento, ecc.)
/sources/pdf-ita/02-razze/             → 128 file (razze base + varianti ambientali + mostri come razze)
/sources/pdf-ita/03-classi/            → 70 file (classi base + varianti + classi di prestigio)
/sources/pdf-ita/04-abilita/           → 3 file (intro, elenco, gradi massimi)
/sources/pdf-ita/05-talenti/           → 6 file (generali, combattimento, creazione, metamagia, mostri)
/sources/pdf-ita/06-equipaggiamento/   → 4 file (armi, armature, avventura, merci/servizi)
/sources/pdf-ita/07-avventura/         → 4 file (esplorazione, movimento, condizioni, trasporto)
/sources/pdf-ita/08-combattimento/     → 7 file (basi, azioni, attacco, difesa, iniziativa, speciali)
/sources/pdf-ita/09-magia/            → 5 file (intro, arcana, divina, descrizioni, capacita speciali)
/sources/pdf-ita/10-incantesimi/       → 16 file (A-UVWXYZ, 601 incantesimi con campi strutturati)
```

## Dati estratti

| Categoria | JSON | Entries |
|-----------|------|---------|
| Incantesimi | `spells.json` | 608 |
| Talenti | `feats.json` | 111 |
| Razze | `races.json` | 7 |
| Equipaggiamento | `equipment.json` | 288 |
| Classi | `classes.json` | 31 |
| Mostri | `monsters.json` | 289 |
| Regole | `rules.json` | 19 pagine |

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

Tab disponibili: **Incantesimi**, **Preparati**, **Talenti**, **Classi**, **Razze**, **Equipaggiamento**, **Mostri**, **Regole**

### Incantesimi
- Filtro scuola (dropdown), filtro classe/dominio (dropdown)
- Multi-select livello 0–9 (checkbox), con bottoni Tutti/Nessuno
- Ordinamento per livello crescente
- Badge verde con contatore `usato/preparato` per incantesimi già preparati
- Bottone **+** per aggiungere alla lista preparati

### Preparati
- Lista incantesimi preparati con contatori uso/preparati (+/- per entrambi)
- Persistenza in localStorage
- Click sul nome per vedere il dettaglio dell'incantesimo
- Indicatore visivo rosso quando tutti gli usi sono esauriti

### Mostri
- Filtro per CR (Challenge Rating) e tipo creatura
- Stat block completo nel pannello dettaglio

## Script

```bash
# Parsing dei sorgenti HTML → JSON
python scripts/parse_srd.py              # parse tutto
python scripts/parse_srd.py spells       # parse solo incantesimi
python scripts/parse_srd.py monsters     # parse solo mostri

# Import JSON → SQLite
python scripts/import_to_db.py

# Import traduzioni IT (formato JSON)
python scripts/import_translations.py translations_it.json

# Estrazione PDF → HTML strutturato (con grassetto/corsivo)
python scripts/pdf_to_html.py <pdf_path> <output_html>                    # modo spells (default)
python scripts/pdf_to_html.py --mode generic <pdf_path> <output_html>     # modo generico

# Download tutti i 249 PDF SRD italiano
python scripts/download_srd_pdfs.py --output-dir /tmp/srd-pdf-ita

# Conversione batch di tutti i PDF in HTML
python scripts/convert_all_pdfs.py --pdf-dir /tmp/srd-pdf-ita --output-dir sources/pdf-ita
python scripts/convert_all_pdfs.py --force   # ri-converte anche se HTML esiste

# Avvio backend locale (opzionale)
uvicorn backend.app:app --reload --port 8000
```

## Estrazione PDF SRD

Lo script `scripts/pdf_to_html.py` converte i PDF del SRD italiano (da editorifolli.it) in HTML strutturato.

**Due modalità:**
- `--mode spells` (default): parsing strutturato per incantesimi con campi separati (Scuola, Livello, Componenti, ecc.)
- `--mode generic`: parsing generico per tutti gli altri contenuti (heading detection, paragrafi, bold/italic)

**Approccio ibrido:**
1. `pdftotext` per il testo completo (zero perdite)
2. Parsing raw PDF streams per identificare font Bold/Italic
3. Merge: applica `<b>`/`<i>` al testo usando i frammenti formattati (con word-boundary check per bold)
4. Struttura: split in blocchi con campi separati dalla descrizione (spells) o heading detection (generic)
5. Leggibilità: `<br>` dopo ogni frase e prima di elenchi

**Pipeline batch:**
- `download_srd_pdfs.py`: manifesto hardcoded di tutti i 249 PDF, download con curl, resume-safe
- `convert_all_pdfs.py`: routing automatico cap.10 → spells, resto → generic, skip existing

**Requisiti:** `pdftotext` e `curl` nel PATH (inclusi in Git for Windows). Nessuna dipendenza Python esterna.

**Limiti:** Non gestisce tabelle (da estendere). I PDF di classi/equipaggiamento hanno tabelle che vengono preservate come testo ma perdono la struttura.

**Sorgenti PDF:** `https://www.editorifolli.it/f/srd35/` (249 file, ~100MB totali)

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
- Copia `index.html`, `frontend/`, `data/*.json` in `_site/`
- Deploy su GitHub Pages

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
- [x] Sezione mostri (289 entries con stat block)
- [x] Sezione regole (19 pagine descrittive)
- [x] Sistema i18n multi-lingua (UI strings + data overlay)
- [x] Traduzioni IT termini chiave (nomi spell, mostri, talenti, classi, razze)
- [ ] Traduzioni IT descrizioni complete (desc_html, benefit, ecc.)
