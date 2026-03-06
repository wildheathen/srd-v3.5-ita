# PDF SRD Extract

Estrai testo HTML strutturato da PDF del SRD D&D 3.5 italiano (editorifolli.it), preservando grassetto, corsivo e struttura a blocchi.

## Quando usare

Quando l'utente chiede di:
- Estrarre testo da un PDF SRD (incantesimi, talenti, classi, mostri, regole, ecc.)
- Convertire un PDF SRD in HTML con formattazione
- Importare contenuti da PDF italiano del manuale D&D 3.5

## Come funziona

Lo script `scripts/pdf_to_html.py` usa un approccio ibrido:

1. **`pdftotext -layout`** per il testo completo (nessuna perdita)
2. **Parsing raw PDF streams** (zlib decompress) per identificare font Bold/Italic dai BaseFont
3. **Merge**: applica `<b>`/`<i>` al testo completo usando i frammenti formattati come lookup
4. **Struttura**: split in blocchi per entry (spell, feat, ecc.) con campi separati dalla descrizione
5. **Leggibilità**: `<br>` dopo ogni frase e prima di elenchi/sotto-voci in corsivo

## Uso

```bash
# Estrai da PDF locale
python scripts/pdf_to_html.py <pdf_path> <output_html_path>

# Esempio
python scripts/pdf_to_html.py /tmp/incantesimi_A.pdf /tmp/incantesimi_A.html
```

Se il PDF va scaricato da URL:
```bash
curl -sL "<url>" -o /tmp/input.pdf
python scripts/pdf_to_html.py /tmp/input.pdf /tmp/output.html
```

## Struttura output

Per gli incantesimi, l'HTML ha questa struttura per ogni entry:
```html
<div class="spell-block">
  <h3>NOME INCANTESIMO</h3>
  <p class="school"><i>Scuola (Sottoscuola) [Descrittore]</i></p>
  <p class="field"><b>Livello:</b> ...</p>
  <p class="field"><b>Componenti:</b> ...</p>
  ...
  <p class="desc">Descrizione con <b>grassetto</b> e <i>corsivo</i>...</p>
</div>
```

## Requisiti

- `pdftotext` deve essere nel PATH (incluso in Git for Windows: `C:\Program Files\Git\mingw64\bin\pdftotext.EXE`)
- Nessuna dipendenza Python esterna (usa solo `re`, `zlib`, `subprocess`)

## Limiti noti e cose da estendere

- **Tabelle**: non gestite. I PDF di classi/equipaggiamento contengono tabelle HTML che richiedono logica aggiuntiva. Quando si incontrano tabelle, bisogna estendere `format_spell_block()` o creare una funzione parallela.
- **Formato specifico incantesimi**: il parsing dei campi (Livello:, Componenti:, ecc.) e la separazione campo/descrizione sono ottimizzati per il formato incantesimi. Per talenti, classi, mostri servirà adattare i FIELD_LABELS e la logica di parsing.
- **Frammenti bold/italic parziali**: il PDF a volte spezza le parole tra text operations diverse, risultando in frammenti come "mi:" invece di "Resistenza agli incantesimi:". Il matching funziona lo stesso ma non è pulitissimo.
- **Encoding**: pdftotext produce latin-1 per questi PDF. Lo script prova utf-8 → latin-1 → cp1252 in sequenza.

## Sorgenti PDF

I PDF del SRD italiano sono su: `https://www.editorifolli.it/f/srd35/`
Pattern nomi: `srd35_10_01_incantesimi_A.pdf`, `srd35_10_02_incantesimi_B.pdf`, ecc.
