# Crystal Ball — D&D 3.5 Reference App

App di consultazione del System Reference Document D&D 3.5 in italiano, basata sul fork di [olimot/srd-v3.5](https://github.com/olimot/srd-v3.5).

## Stack

- **Backend:** Python + FastAPI
- **Database:** SQLite (`dnd35.db`)
- **Data format:** JSON per categoria in `/data/`
- **Frontend:** HTML/CSS/JS statico su GitHub Pages
- **CI/CD:** GitHub Actions

## Quick start

```bash
# Installa dipendenze
pip install -r requirements.txt

# Parsing incantesimi → data/spells.json
python scripts/parse_srd.py spells

# Preview locale del sito SRD
python -m http.server 8000
# Apri http://localhost:8000
```

## Struttura repo

```
/data/              → JSON generati dal parser (spells.json, ...)
/scripts/           → parse_srd.py, import_to_db.py, import_translations.py
/backend/           → FastAPI app (TODO)
/frontend/          → HTML/CSS/JS app (TODO)
/spells/            → HTML sorgenti SRD (incantesimi)
/basic-rules-and-legal/ → HTML sorgenti SRD (regole, talenti, razze, classi, equipaggiamento)
dnd35.db            → SQLite database (gitignored)
```

Per la documentazione completa (schema DB, convenzioni, task) vedi [CLAUDE.md](CLAUDE.md).

## Stato attuale

- [x] Setup struttura cartelle e CLAUDE.md
- [x] Parser incantesimi (608 spell estratti)
- [ ] Parser talenti, razze, equipaggiamento, classi
- [ ] Schema SQLite e import_to_db.py
- [ ] Backend FastAPI
- [ ] Frontend consultazione
- [ ] Traduzioni IT

## Crediti

- SRD HTML originale: [olimot/srd-v3.5](https://github.com/olimot/srd-v3.5)
- Documenti originali: [Wizards of the Coast SRD](https://archive.org/details/dnd35srd)
