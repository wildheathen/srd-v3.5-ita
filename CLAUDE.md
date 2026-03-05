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
/frontend/          → style.css, app.js (caricati da index.html nella root)
index.html          → Entry point Crystal Ball (root, servito da GitHub Pages)
dnd35.db            → SQLite database (gitignored, generato dagli script)
```

**Sorgenti HTML SRD** (nella root del repo, dal fork originale):
```
/spells/            → 9 file HTML con tutti gli incantesimi (spells-a-b.html ... spells-t-z.html)
/basic-rules-and-legal/ → regole base, talenti, razze, classi, equipaggiamento, combattimento, abilità
/divine/            → abilità divine, domini, ranghi
/epic/              → contenuti di livello epico
/magic-items/       → oggetti magici
/monsters/          → mostri (18 file HTML)
/psionics/          → contenuti psionici
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

# Avvio backend locale (opzionale)
uvicorn backend.app:app --reload --port 8000
```

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
- [ ] Aggiungere traduzioni IT
