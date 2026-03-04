# Crystal Ball — D&D 3.5 Reference App

App di consultazione del System Reference Document D&D 3.5, basata sul fork di [olimot/srd-v3.5](https://github.com/olimot/srd-v3.5).

## Stack

- **Backend:** Python + FastAPI
- **Database:** SQLite (`dnd35.db`)
- **Data format:** JSON per categoria in `/data/`
- **Frontend:** HTML/CSS/JS statico su GitHub Pages
- **CI/CD:** GitHub Actions

## Struttura repo

```
/data/              → JSON generati dal parser (spells.json, feats.json, races.json, equipment.json, classes.json)
/scripts/           → parse_srd.py, import_to_db.py, import_translations.py
/backend/           → FastAPI app
/frontend/          → HTML/CSS/JS app
dnd35.db            → SQLite database (gitignored, generato dagli script)
```

**Sorgenti HTML SRD** (nella root del repo, dal fork originale):
```
/spells/            → 9 file HTML con tutti gli incantesimi (spells-a-b.html ... spells-t-z.html)
/basic-rules-and-legal/ → regole base, talenti (feats.html), razze, classi, equipaggiamento
/divine/            → abilità divine, domini, ranghi
/epic/              → contenuti di livello epico
/magic-items/       → oggetti magici
/monsters/          → mostri
/psionics/          → contenuti psionici
```

## Schema DB

### Tabelle principali

**spells:** name, slug, school, subschool, descriptor, level, components, casting_time, range, target_area_effect, duration, saving_throw, spell_resistance, desc_html

**feats:** name, slug, type, prerequisites, benefit, normal, special, desc_html

**races:** name, slug + tutti i campi strutturati dagli HTML, desc_html

**equipment:** name, slug + tutti i campi strutturati dagli HTML, desc_html

**classes:** name, slug + tutti i campi strutturati dagli HTML, desc_html

### Tabella traduzioni

**translations:** id, entity_type, entity_id, lang, field, value

Serve per le traduzioni IT incrementali senza toccare le tabelle principali.

## Convenzioni

- Campi EN sempre presenti, IT opzionali via tabella `translations`
- `desc_html`: testo formattato in HTML, **non strippare i tag** — la formattazione serve
- Fallback lingua: se traduzione IT non esiste, mostra EN
- ID numerici auto-increment, slug testuale per riferimenti esterni
- Il parser legge i file HTML dalla root del repo (non da una sottocartella separata)

## Script

```bash
# Parsing dei sorgenti HTML → JSON
python scripts/parse_srd.py              # parse tutto
python scripts/parse_srd.py spells       # parse solo incantesimi

# Import JSON → SQLite (TODO)
python scripts/import_to_db.py

# Import traduzioni IT (TODO)
python scripts/import_translations.py
```

## Task correnti

- [ ] Setup struttura cartelle
- [ ] Scrivere parse_srd.py (incantesimi come primo test)
- [ ] Definire schema SQLite
- [ ] Scrivere import_to_db.py
- [ ] Parsing talenti, razze, equipaggiamento, classi
- [ ] Setup backend FastAPI
- [ ] Setup frontend
