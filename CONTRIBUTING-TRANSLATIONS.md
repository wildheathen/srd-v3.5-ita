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
| `name` | stringa | "Fireball" | "Palla di Fuoco" | ✅ Fatto |
| `school` | stringa | "Evocation" | "Invocazione" | ✅ Fatto |
| `subschool` | stringa/null | "Creation" | "Creazione" | ✅ Fatto |
| `descriptor` | stringa/null | "Fire" | "Fuoco" | ❌ Da fare |
| `level` | stringa | "Sor/Wiz 3" | — | ⚠️ Contiene abbreviazioni classi |
| `components` | stringa | "V, S, M" | — | ⚠️ Abbreviazioni standard |
| `casting_time` | stringa | "1 standard action" | "1 azione standard" | ❌ Da fare |
| `range` | stringa | "Long (400 ft. + 40 ft./level)" | "Lungo (120 m + 12 m/livello)" | ❌ Da fare |
| `target_area_effect` | stringa | "One creature" | "Una creatura" | ❌ Da fare |
| `duration` | stringa | "1 round/level" | "1 round/livello" | ❌ Da fare |
| `saving_throw` | stringa | "Reflex half" | "Riflessi dimezza" | ❌ Da fare |
| `spell_resistance` | stringa | "Yes" | "Sì" | ❌ Da fare |
| `desc_html` | HTML | (descrizione completa) | — | ❌ Da fare |

### Talenti (`feats.json`) — 111 entries

| Campo | Tipo | Esempio EN | Esempio IT | Stato |
|-------|------|-----------|-----------|-------|
| `name` | stringa | "Power Attack" | "Attacco Poderoso" | ✅ Fatto |
| `type` | stringa | "General" | "Generale" | ✅ Fatto |
| `prerequisites` | stringa/null | "Str 13" | "For 13" | ❌ Da fare |
| `benefit` | stringa | "On your action..." | "Nel tuo turno..." | ❌ Da fare |
| `normal` | stringa/null | "Without this feat..." | "Senza questo talento..." | ❌ Da fare |
| `special` | stringa/null | "A fighter may..." | "Un guerriero può..." | ❌ Da fare |
| `desc_html` | HTML | (descrizione completa) | — | ❌ Da fare |

### Classi (`classes.json`) — 31 entries

| Campo | Tipo | Esempio EN | Esempio IT | Stato |
|-------|------|-----------|-----------|-------|
| `name` | stringa | "Wizard" | "Mago" | ✅ Fatto |
| `hit_die` | stringa | "d4." | — | ⚠️ Dato numerico |
| `alignment` | stringa | "Any" | "Qualsiasi" | ❌ Da fare |
| `table_html` | HTML | (tabella progressione) | — | ❌ Da fare |
| `desc_html` | HTML | (descrizione classe) | — | ❌ Da fare |

### Razze (`races.json`) — 7 entries

| Campo | Tipo | Esempio EN | Esempio IT | Stato |
|-------|------|-----------|-----------|-------|
| `name` | stringa | "Elves" | "Elfi" | ✅ Fatto |
| `traits` | array | ["Medium size", ...] | ["Taglia media", ...] | ❌ Da fare |
| `desc_html` | HTML | (descrizione razza) | — | ❌ Da fare |

### Mostri (`monsters.json`) — 289 entries

| Campo | Tipo | Esempio EN | Esempio IT | Stato |
|-------|------|-----------|-----------|-------|
| `name` | stringa | "Aboleth" | "Aboleth" | ✅ Fatto |
| `type` | stringa | "Huge Aberration (Aquatic)" | "Aberrazione Enorme (Acquatica)" | ❌ Da fare |
| `environment` | stringa | "Underground" | "Sotterraneo" | ❌ Da fare |
| `organization` | stringa | "Solitary, brood (2–4)" | "Solitario, nidiata (2–4)" | ❌ Da fare |
| `alignment` | stringa | "Usually lawful evil" | "Solitamente legale malvagio" | ❌ Da fare |
| `desc_html` | HTML | (descrizione completa) | — | ❌ Da fare |

> **Nota:** I campi numerici dello stat block (`hit_dice`, `initiative`, `speed`, `armor_class`, `saves`, `abilities`, `challenge_rating`, ecc.) generalmente non necessitano di traduzione.

### Equipaggiamento (`equipment.json`) — 288 entries

| Campo | Tipo | Esempio EN | Esempio IT | Stato |
|-------|------|-----------|-----------|-------|
| `name` | stringa | "Longsword" | "Spada Lunga" | ❌ Da fare |
| `category` | stringa | "weapon" | "arma" | ❌ Da fare |
| `desc_html` | HTML | (descrizione) | — | ❌ Da fare |

> **Nota:** L'overlay equipaggiamento è attualmente vuoto (`[]`).

### Regole (`rules.json`) — 19 pagine

| Campo | Tipo | Esempio EN | Esempio IT | Stato |
|-------|------|-----------|-----------|-------|
| `name` | stringa | "Basic Rules and Ability Scores" | "Regole Base e Punteggi Abilità" | ✅ Fatto |
| `desc_html` | HTML | (contenuto pagina intero) | — | ❌ Da fare |

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

### 1. Tradurre contenuti SRD (data overlay)

1. **Identifica cosa tradurre** — Esegui `python scripts/translation_status.py` per vedere i campi mancanti
2. **Apri il file overlay** — Es. `data/i18n/it/spells.json`
3. **Trova l'entry per slug** — Cerca lo slug dell'entry che vuoi tradurre
4. **Aggiungi i campi tradotti** — Se l'entry esiste già, aggiungi i nuovi campi. Se non esiste, aggiungi un nuovo oggetto con lo `slug`

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
