# Come contribuire

Grazie per il tuo interesse nel progetto Crystal Ball! Il modo principale per contribuire e aiutare con le **traduzioni italiane** dei contenuti del D&D 3.5 SRD.

## Cosa manca

I nomi e i metadati sono quasi tutti tradotti. Il lavoro grosso che resta sono le **descrizioni** (`desc_html`):

| Categoria | Entries | Descrizioni tradotte | Priorita |
|-----------|---------|---------------------|----------|
| Mostri | 289 | 2% | Alta |
| Regole | 19 | 0% | Alta |
| Classi | 31 | 23% | Media |
| Incantesimi | 608 | 100% (32 da rivedere) | Bassa |
| Talenti | 111 | 100% | -- |
| Razze | 7 | 100% | -- |

## Come contribuire (3 modi)

### 1. GitHub Issue (il piu semplice)

Non serve installare nulla. Apri un issue usando il template **"Traduzione"**:

1. Vai su **Issues > New issue**
2. Scegli il template **Traduzione**
3. Seleziona la categoria (es. mostri) e scrivi lo slug (es. `aboleth`)
4. Incolla la tua traduzione
5. Il maintainer la integrera nel JSON

### 2. Foglio di calcolo (per tradurre tante entry)

Nella cartella `contrib/` ci sono dei CSV pronti da compilare:

- `contrib/monsters_desc_html.csv` — 288 mostri
- `contrib/rules_desc_html.csv` — 19 pagine di regole
- `contrib/classes_desc_html.csv` — 31 classi

Scarica il CSV, aprilo in Excel/Google Sheets, compila la colonna `desc_html_it`, e poi:
- Condividi il file compilato in un issue, oppure
- Se hai clonato il repo, importalo con: `python scripts/import_from_csv.py contrib/monsters_desc_html.csv monsters --apply`

### 3. Modifica diretta su GitHub (senza clonare)

1. Naviga al file overlay, es. [`data/i18n/it/monsters.json`](data/i18n/it/monsters.json)
2. Clicca l'icona matita (Edit this file)
3. Usa Ctrl+F per trovare lo slug del mostro
4. Aggiungi il campo `desc_html` con la traduzione
5. Clicca **"Propose changes"** — GitHub crea automaticamente fork + branch + PR

## Regole per le traduzioni

- **Usa la terminologia ufficiale** della traduzione italiana di D&D 3.5 (Twenty Five Edition / Wizards of the Coast Italia)
- **Mantieni i tag HTML** (`<p>`, `<strong>`, `<table>`, ecc.) — traduci solo il testo al loro interno
- **Non tradurre:** nomi propri del setting, abbreviazioni universali (HP, AC, DC), formule matematiche
- **Coerenza:** usa sempre gli stessi termini (es. "Tiro salvezza", non "TS" o "Tiro di salvezza" alternati)

### Esempio pratico

Nel file `data/i18n/it/monsters.json`, un mostro ha gia il nome tradotto:

```json
{
  "slug": "aboleth",
  "name": "Aboleth",
  "type": "Aberrazione Enorme (Acquatica)"
}
```

Per aggiungere la descrizione, aggiungi il campo `desc_html`:

```json
{
  "slug": "aboleth",
  "name": "Aboleth",
  "type": "Aberrazione Enorme (Acquatica)",
  "desc_html": "<p>Gli aboleth sono creature acquatiche...</p>"
}
```

Il campo `slug` deve corrispondere esattamente a quello nei dati base inglesi (`data/monsters.json`).

## Come funziona il sistema

I dati base in `/data/*.json` sono in inglese e **non vanno modificati**. Le traduzioni sono in file separati (overlay) in `data/i18n/it/`. Ogni overlay e un array JSON di oggetti con `slug` + i campi tradotti. I campi non presenti restano in inglese automaticamente.

Per dettagli tecnici, struttura dei file e tutti i campi traducibili per categoria, vedi [CONTRIBUTING-TRANSLATIONS.md](CONTRIBUTING-TRANSLATIONS.md).

## Validazione

Prima di proporre modifiche, verifica che il JSON sia valido:

```bash
python -m json.tool data/i18n/it/monsters.json > /dev/null && echo "OK"
```

Oppure usa un validatore JSON online se non hai Python installato.

## Domande?

Apri un issue con la label **"domanda"** e ti rispondiamo.
