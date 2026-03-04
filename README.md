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

# Parsing di tutti i contenuti SRD → JSON in /data/
python scripts/parse_srd.py

# Import JSON → SQLite
python scripts/import_to_db.py

# Avvio backend API
uvicorn backend.app:app --reload --port 8000

# Frontend (in un altro terminale, o aprire frontend/index.html)
# L'API di default è http://localhost:8000/api
```

## Struttura repo

```
/data/              → JSON generati dal parser (spells.json, ...)
/scripts/           → parse_srd.py, import_to_db.py, import_translations.py
/backend/           → FastAPI app (app.py)
/frontend/          → HTML/CSS/JS app di consultazione
/spells/            → HTML sorgenti SRD (incantesimi)
/basic-rules-and-legal/ → HTML sorgenti SRD (regole, talenti, razze, classi, equipaggiamento)
dnd35.db            → SQLite database (gitignored)
```

Per la documentazione completa (schema DB, convenzioni, task) vedi [CLAUDE.md](CLAUDE.md).

## Dati estratti

| Categoria | Conteggio |
|-----------|-----------|
| Incantesimi | 608 |
| Talenti | 111 |
| Razze | 7 |
| Equipaggiamento | 288 |
| Classi | 31 |

## Stato attuale

- [x] Setup struttura cartelle e CLAUDE.md
- [x] Parser completo (incantesimi, talenti, razze, equipaggiamento, classi)
- [x] Schema SQLite e import_to_db.py
- [x] Backend FastAPI con API REST
- [x] Frontend consultazione (dark theme)
- [x] GitHub Actions deploy
- [ ] Traduzioni IT

## Crediti

- SRD HTML originale: [olimot/srd-v3.5](https://github.com/olimot/srd-v3.5)
- Documenti originali: [Wizards of the Coast SRD](https://archive.org/details/dnd35srd)
