# Guida alle Traduzioni — Crystal Ball D&D 3.5 SRD

Questa guida spiega come contribuire alle traduzioni italiane (o in altre lingue) dell'app Crystal Ball.

## Panoramica del sistema

L'app ha **due livelli di traduzione**:

| Livello | Cosa traduce | Dove si trova | Formato |
|---------|-------------|---------------|---------|
| **UI strings** | Labels, bottoni, filtri, messaggi dell'interfaccia | `frontend/i18n/{lang}.json` | Oggetto JSON chiave-valore |
| **Data overlay** | Contenuti SRD (nomi, scuole, descrizioni) | `data/i18n/{lang}/{categoria}.json` | Array JSON di oggetti con `slug` |

I dati base in `/data/` sono **sempre in inglese**. Le traduzioni sono file separati (overlay) che sovrascrivono solo i campi tradotti. Se un campo non è presente nell'overlay, resta in inglese (fallback automatico).

## Struttura file

```
frontend/
  i18n/
    en.json              ← UI strings inglese
    it.json              ← UI strings italiano

data/
  spells.json            ← dati base EN (non modificare)
  feats.json
  classes.json
  races.json
  monsters.json
  equipment.json
  rules.json
  i18n/
    it/
      spells.json        ← overlay IT incantesimi
      feats.json         ← overlay IT talenti
      classes.json       ← overlay IT classi
      races.json         ← overlay IT razze
      monsters.json      ← overlay IT mostri
      equipment.json     ← overlay IT equipaggiamento
      rules.json         ← overlay IT regole
```

## Formato overlay dati

Ogni file overlay è un **array JSON** di oggetti. Ogni oggetto deve avere il campo `slug` (per il match con i dati base) più i campi tradotti:

```json
[
  {
    "slug": "fireball",
    "name": "Palla di Fuoco",
    "school": "Invocazione"
  },
  {
    "slug": "magic-missile",
    "name": "Dardo Incantato",
    "school": "Invocazione",
    "desc_html": "<p>Un dardo di energia magica...</p>"
  }
]
```

**Regole importanti:**
- Il campo `slug` è **obbligatorio** e deve corrispondere esattamente allo slug nei dati base
- Includi **solo i campi che hai tradotto** — quelli assenti restano in inglese
- Il campo `desc_html` contiene HTML: **non rimuovere i tag HTML**, traduci solo il testo al loro interno
- L'ordine degli oggetti nell'array non conta

## Campi traducibili per categoria

### Incantesimi (`spells.json`) — 608 entries

| Campo | Tipo | Esempio EN | Esempio IT | Stato |
|-------|------|-----------|-----------|-------|
| `name` | stringa | "Fireball" | "Palla di Fuoco" | ✅ 100% |
| `school` | stringa | "Evocation" | "Invocazione" | ✅ 100% |
| `subschool` | stringa/null | "Creation" | "Creazione" | ✅ 100% |
| `descriptor` | stringa/null | "Fire" | "Fuoco" | ✅ 100% |
| `level` | stringa | "Sor/Wiz 3" | "Str/Mag 3" | ✅ 100% |
| `components` | stringa | "V, S, M" | "V, S, M" | ✅ 100% |
| `casting_time` | stringa | "1 standard action" | "1 azione standard" | ✅ 100% |
| `range` | stringa | "Long (400 ft. + 40 ft./level)" | "Lungo (120 m + 12 m/livello)" | ✅ 100% |
| `target_area_effect` | stringa | "One creature" | "Una creatura" | ✅ 100% |
| `duration` | stringa | "1 round/level" | "1 round/livello" | ✅ 100% |
| `saving_throw` | stringa | "Reflex half" | "Riflessi dimezza" | ✅ 100% |
| `spell_resistance` | stringa | "Yes" | "Sì" | ✅ 100% |
| `desc_html` | HTML | (descrizione completa) | — | ✅ 100% (⚠️ 32 troncati) |

### Talenti (`feats.json`) — 111 entries

| Campo | Tipo | Esempio EN | Esempio IT | Stato |
|-------|------|-----------|-----------|-------|
| `name` | stringa | "Power Attack" | "Attacco Poderoso" | ✅ 98% |
| `type` | stringa | "General" | "Generale" | ✅ 99% |
| `prerequisites` | stringa/null | "Str 13" | "For 13" | ✅ 100% |
| `benefit` | stringa | "On your action..." | "Nel tuo turno..." | ✅ 100% |
| `normal` | stringa/null | "Without this feat..." | "Senza questo talento..." | ✅ 100% |
| `special` | stringa/null | "A fighter may..." | "Un guerriero può..." | ✅ 100% |
| `desc_html` | HTML | (descrizione completa) | — | ✅ 100% |

### Classi (`classes.json`) — 31 entries

| Campo | Tipo | Esempio EN | Esempio IT | Stato |
|-------|------|-----------|-----------|-------|
| `name` | stringa | "Wizard" | "Mago" | ✅ 97% |
| `hit_die` | stringa | "d4." | — | ⚠️ Dato numerico |
| `alignment` | stringa | "Any" | "Qualsiasi" | ✅ 100% |
| `table_html` | HTML | (tabella progressione) | — | ⚠️ 70% (9 simili EN) |
| `desc_html` | HTML | (descrizione classe) | — | ⚠️ 23% (solo strutturale) |

### Razze (`races.json`) — 7 entries

| Campo | Tipo | Esempio EN | Esempio IT | Stato |
|-------|------|-----------|-----------|-------|
| `name` | stringa | "Elves" | "Elfi" | ✅ Fatto |
| `traits` | array | ["Medium size", ...] | ["Taglia media", ...] | ✅ 100% |
| `desc_html` | HTML | (descrizione razza) | — | ✅ 100% |

### Mostri (`monsters.json`) — 289 entries

| Campo | Tipo | Esempio EN | Esempio IT | Stato |
|-------|------|-----------|-----------|-------|
| `name` | stringa | "Aboleth" | "Aboleth" | ✅ 73% (79 simili EN) |
| `type` | stringa | "Huge Aberration (Aquatic)" | "Aberrazione Enorme (Acquatica)" | ✅ 93% |
| `environment` | stringa | "Underground" | "Sotterraneo" | ✅ 100% |
| `organization` | stringa | "Solitary, brood (2–4)" | "Solitario, nidiata (2–4)" | ✅ 99% |
| `alignment` | stringa | "Usually lawful evil" | "Solitamente legale malvagio" | ✅ 100% |
| `desc_html` | HTML | (descrizione completa) | — | ⚠️ 2% (solo label strutturali) |

> **Nota:** I campi numerici dello stat block (`hit_dice`, `initiative`, `speed`, `armor_class`, `saves`, `abilities`, `challenge_rating`, ecc.) generalmente non necessitano di traduzione.

### Equipaggiamento (`equipment.json`) — 288 entries

| Campo | Tipo | Esempio EN | Esempio IT | Stato |
|-------|------|-----------|-----------|-------|
| `name` | stringa | "Longsword" | "Spada Lunga" | ✅ 93% |
| `category` | stringa | "weapon" | "arma" | ⚠️ Non nel overlay |
| `desc_html` | HTML | (descrizione) | — | ⚠️ Non nel base EN |

> **Nota:** L'overlay equipaggiamento ha 276 entry (nomi tradotti). Il base EN non ha campo `desc_html`.

### Regole (`rules.json`) — 19 pagine

| Campo | Tipo | Esempio EN | Esempio IT | Stato |
|-------|------|-----------|-----------|-------|
| `name` | stringa | "Basic Rules and Ability Scores" | "Regole Base e Punteggi Abilità" | ⚠️ 21% (15 simili EN) |
| `desc_html` | HTML | (contenuto pagina intero) | — | ❌ 0% (da fare) |

## Controllare lo stato delle traduzioni

Usa lo script di confronto per vedere cosa manca:

```bash
# Report completo di tutte le categorie
python scripts/translation_status.py

# Report per una singola categoria
python scripts/translation_status.py spells

# Report per una lingua specifica (default: it)
python scripts/translation_status.py --lang it
```

Output esempio:
```
=== SPELLS (608 entries) ===
  name         608/608  ████████████████████ 100%
  school       608/608  ████████████████████ 100%
  subschool    213/213  ████████████████████ 100%
  descriptor     0/352  ░░░░░░░░░░░░░░░░░░░░   0%
  casting_time   0/608  ░░░░░░░░░░░░░░░░░░░░   0%
  desc_html      0/608  ░░░░░░░░░░░░░░░░░░░░   0%
```

## Come contribuire

Ci sono **tre modi** per contribuire, dal piu semplice al piu completo:

### Metodo 1: GitHub Issue (nessun setup richiesto)

Il modo piu semplice. Non serve clonare il repo ne installare nulla.

1. Vai su **Issues > New issue > Traduzione**
2. Scegli la categoria e lo slug dell'entry
3. Incolla la tua traduzione nel campo di testo
4. Il maintainer integrera la traduzione nel JSON

### Metodo 2: Foglio di calcolo (CSV)

Per tradurre tante entry alla volta, lavora in Excel/Google Sheets:

```bash
# Esporta le entry da tradurre in CSV
python scripts/export_for_translation.py monsters desc_html
# -> genera contrib/monsters_desc_html.csv

# Apri il CSV in un foglio di calcolo, compila la colonna *_it
# Poi importa le traduzioni:
python scripts/import_from_csv.py contrib/monsters_desc_html.csv monsters --apply
```

### Metodo 3: Modifica diretta del JSON

#### 3a. Su GitHub (senza clonare)

1. Naviga a `data/i18n/it/monsters.json` su GitHub
2. Clicca l'icona matita (Edit this file)
3. Usa Ctrl+F per trovare lo slug
4. Aggiungi/modifica i campi tradotti
5. Clicca "Propose changes" — GitHub crea automaticamente fork + branch + PR

#### 3b. In locale (workflow completo)

1. **Identifica cosa tradurre** — Esegui `python scripts/translation_status.py` per vedere i campi mancanti
2. **Apri il file overlay** — Es. `data/i18n/it/spells.json`
3. **Trova l'entry per slug** — Cerca lo slug dell'entry che vuoi tradurre
4. **Aggiungi i campi tradotti** — Se l'entry esiste gia, aggiungi i nuovi campi. Se non esiste, aggiungi un nuovo oggetto con lo `slug`

**Esempio — aggiungere la descrizione a un incantesimo:**

Prima (solo nome e scuola tradotti):
```json
{
  "slug": "fireball",
  "name": "Palla di Fuoco",
  "school": "Invocazione"
}
```

Dopo (con descrizione aggiunta):
```json
{
  "slug": "fireball",
  "name": "Palla di Fuoco",
  "school": "Invocazione",
  "saving_throw": "Riflessi dimezza",
  "spell_resistance": "Sì",
  "desc_html": "<p>Una palla di fuoco brilla dalla punta del tuo dito...</p>"
}
```

### 2. Tradurre stringhe UI

1. Apri `frontend/i18n/it.json`
2. Trova la chiave da tradurre (es. `"filter.all_schools"`)
3. Modifica il valore

Per aggiungere nuove chiavi (se l'app viene aggiornata):
1. Controlla `frontend/i18n/en.json` per le chiavi mancanti in `it.json`
2. Aggiungi la traduzione in `it.json`

### 3. Aggiungere una nuova lingua

1. Crea `frontend/i18n/{lang}.json` copiando `en.json` e traducendo i valori
2. Crea la cartella `data/i18n/{lang}/` con file overlay per ogni categoria (inizialmente `[]`)
3. Aggiungi il codice lingua a `SUPPORTED_LANGS` in `frontend/i18n.js`
4. Aggiungi `<option value="{lang}">` nel selettore lingua in `index.html`

## Consigli per i traduttori

- **Consulta le fonti ufficiali:** Le traduzioni italiane di D&D 3.5 sono state pubblicate da Twenty Five Edition/Wizards of the Coast Italia. Usa la terminologia ufficiale quando possibile
- **Mantieni la coerenza:** Usa gli stessi termini in tutto il progetto (es. "Tiro salvezza" non "Tiro di salvezza" una volta e "TS" un'altra)
- **HTML:** Quando traduci `desc_html`, mantieni tutti i tag HTML (`<p>`, `<strong>`, `<em>`, `<table>`, ecc.) e traduci solo il testo al loro interno
- **Non tradurre:** Nomi propri specifici del setting, abbreviazioni universali (HP, AC, DC), formule matematiche
- **Priorità suggerita:**
  1. Nomi (massimo impatto visivo, poco sforzo)
  2. Campi brevi (saving_throw, spell_resistance, casting_time)
  3. Descrizioni (`desc_html` — il grosso del lavoro)

## Workflow con Git

```bash
# Fork e clone
git clone https://github.com/TUO-USERNAME/srd-v3.5-ita.git
cd srd-v3.5-ita

# Crea un branch per le tue traduzioni
git checkout -b traduzioni/spells-descrizioni

# Fai le modifiche...
# Verifica che il JSON sia valido
python -m json.tool data/i18n/it/spells.json > /dev/null

# Controlla lo stato
python scripts/translation_status.py spells

# Commit e push
git add data/i18n/it/spells.json
git commit -m "Aggiunte descrizioni IT per incantesimi A-C"
git push origin traduzioni/spells-descrizioni

# Apri una Pull Request su GitHub
```

## Validazione

Prima di fare commit, verifica che i file JSON siano validi:

```bash
# Verifica singolo file
python -m json.tool data/i18n/it/spells.json > /dev/null && echo "OK"

# Verifica tutti gli overlay IT
for f in data/i18n/it/*.json; do
  python -m json.tool "$f" > /dev/null && echo "$f: OK" || echo "$f: ERRORE"
done
```
