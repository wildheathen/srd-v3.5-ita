#!/usr/bin/env python3
"""
PDF to HTML converter for D&D SRD spell PDFs.
v4: Hybrid approach - pdftotext for complete text, PDF stream parsing for bold/italic.
"""
import re
import zlib
import subprocess
import sys
import os

# ─── Step 1: Get complete text via pdftotext ─────────────────────────────────

def get_complete_text(pdf_path):
    """Run pdftotext and return complete text with correct encoding."""
    result = subprocess.run(
        ['pdftotext', '-layout', pdf_path, '-'],
        capture_output=True
    )
    # pdftotext outputs latin-1 for this PDF
    for enc in ['utf-8', 'latin-1', 'cp1252']:
        try:
            text = result.stdout.decode(enc)
            # Verify it has Italian accented chars
            if any(c in text for c in 'àèéìòùÀÈÉÌÒÙ'):
                return text
        except:
            continue
    return result.stdout.decode('latin-1')


# ─── Step 2: Parse PDF streams for font/formatting info ──────────────────────

def decompress_streams(pdf_bytes):
    streams = []
    for m in re.finditer(rb'stream\r?\n(.*?)endstream', pdf_bytes, re.DOTALL):
        raw = m.group(1)
        try:
            streams.append(zlib.decompress(raw))
        except:
            try:
                streams.append(zlib.decompress(raw.rstrip()))
            except:
                pass
    return streams

def parse_font_map(pdf_bytes):
    font_map = {}
    font_refs = re.findall(rb'/([A-Z]\w*)\s+(\d+)\s+0\s+R', pdf_bytes)
    for obj_match in re.finditer(rb'(\d+)\s+0\s+obj.*?endobj', pdf_bytes, re.DOTALL):
        obj_num = obj_match.group(1).decode()
        obj_content = obj_match.group(0)
        base_font = re.search(rb'/BaseFont\s*/([^\s/\]>]+)', obj_content)
        if base_font:
            font_name = base_font.group(1).decode()
            for ref_name, ref_num in font_refs:
                if ref_num.decode() == obj_num:
                    font_map[ref_name.decode()] = font_name
    return font_map

def extract_pdf_string(text, start):
    """Extract a PDF string starting at '(' at position start.
    Handles nested balanced parens and escape sequences.
    Returns (extracted_string, end_position)."""
    assert text[start] == '('
    depth = 1
    i = start + 1
    result = []
    while i < len(text) and depth > 0:
        ch = text[i]
        if ch == '\\' and i + 1 < len(text):
            next_ch = text[i + 1]
            if next_ch == '(':
                result.append('(')
                i += 2
            elif next_ch == ')':
                result.append(')')
                i += 2
            elif next_ch == '\\':
                result.append('\\')
                i += 2
            elif next_ch == 'n':
                result.append('\n')
                i += 2
            elif next_ch == 'r':
                result.append('\r')
                i += 2
            elif next_ch == 't':
                result.append('\t')
                i += 2
            elif next_ch.isdigit():
                # Octal escape: 1-3 digits
                oct_str = next_ch
                k = i + 2
                while k < len(text) and k < i + 4 and text[k].isdigit():
                    oct_str += text[k]
                    k += 1
                result.append(chr(int(oct_str, 8)))
                i = k
            else:
                result.append(next_ch)
                i += 2
        elif ch == '(':
            depth += 1
            result.append('(')
            i += 1
        elif ch == ')':
            depth -= 1
            if depth > 0:
                result.append(')')
            i += 1
        else:
            result.append(ch)
            i += 1
    return ''.join(result), i

def fix_encoding(s):
    """Fix latin-1 encoded string to proper unicode."""
    try:
        return s.encode('latin-1').decode('cp1252')
    except:
        try:
            return s.encode('latin-1').decode('latin-1')
        except:
            return s

def extract_formatted_fragments(streams, font_map):
    """Extract text fragments with bold/italic info from PDF streams."""
    bold_fragments = set()
    italic_fragments = set()

    for stream in streams:
        try:
            text = stream.decode('latin-1')
        except:
            text = stream.decode('utf-8', errors='replace')

        current_font = None
        current_bold = False
        current_italic = False

        for line in text.split('\n'):
            line = line.strip()

            # Font selection
            font_match = re.match(r'/(\w+)\s+[\d.]+\s+Tf', line)
            if font_match:
                fid = font_match.group(1)
                current_font = font_map.get(fid, fid)
                current_bold = 'Bold' in current_font or 'bold' in current_font
                current_italic = 'Italic' in current_font or 'italic' in current_font
                continue

            if not current_bold and not current_italic:
                continue  # Only care about formatted text

            # Extract all PDF strings from this line
            extracted = []
            i = 0
            while i < len(line):
                if line[i] == '(':
                    s, end = extract_pdf_string(line, i)
                    extracted.append(s)
                    i = end
                else:
                    i += 1

            # Check if this line has Tj or TJ operator
            if not re.search(r'T[jJ]', line):
                continue

            combined = ''.join(extracted)
            combined = fix_encoding(combined)
            combined = combined.strip()

            if combined and len(combined) >= 2:
                if current_bold:
                    bold_fragments.add(combined)
                if current_italic:
                    italic_fragments.add(combined)

    return bold_fragments, italic_fragments


# ─── Step 3: Build HTML with formatting ──────────────────────────────────────

FIELD_LABELS = [
    'Livello:', 'Componenti:', 'Tempo di lancio:', 'Raggio di azione:',
    'Bersaglio:', 'Bersagli:', 'Area:', 'Durata:', 'Tiro salvezza:',
    'Resistenza agli incantesimi:', 'Effetto:'
]

SCHOOLS = ['Ammaliamento', 'Abiurazione', 'Evocazione', 'Trasmutazione',
           'Illusione', 'Invocazione', 'Necromanzia', 'Divinazione', 'Universale']


def apply_bold_italic(text, bold_set, italic_set):
    """Apply <b> and <i> tags to text based on known formatted fragments."""
    # Sort fragments by length (longest first) to avoid partial matches
    bold_sorted = sorted(bold_set, key=len, reverse=True)
    italic_sorted = sorted(italic_set, key=len, reverse=True)

    # Build a character-level format map
    n = len(text)
    is_bold = [False] * n
    is_italic = [False] * n

    def match_fragments(frags, flags, check_boundaries=False):
        for frag in frags:
            if len(frag) < 2:
                continue
            start = 0
            while True:
                idx = text.find(frag, start)
                if idx == -1:
                    break
                # Skip bold fragments that don't align with word boundaries
                # (prevents PDF artifacts like "Component" matching inside "Componente")
                if check_boundaries:
                    before_ok = idx == 0 or not text[idx - 1].isalpha()
                    after_ok = (idx + len(frag) >= n
                                or not text[idx + len(frag)].isalpha())
                    if not (before_ok and after_ok):
                        start = idx + 1
                        continue
                for k in range(idx, idx + len(frag)):
                    flags[k] = True
                start = idx + 1

    match_fragments(bold_sorted, is_bold, check_boundaries=True)
    match_fragments(italic_sorted, is_italic, check_boundaries=False)

    # Build HTML from character-level map
    html_parts = []
    i = 0
    while i < n:
        b = is_bold[i]
        it = is_italic[i]
        # Find run of same formatting
        j = i
        while j < n and is_bold[j] == b and is_italic[j] == it:
            j += 1
        chunk = text[i:j]
        chunk = chunk.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        if b and it:
            html_parts.append(f'<b><i>{chunk}</i></b>')
        elif b:
            html_parts.append(f'<b>{chunk}</b>')
        elif it:
            html_parts.append(f'<i>{chunk}</i>')
        else:
            html_parts.append(chunk)
        i = j

    result = ''.join(html_parts)
    # Merge adjacent identical tags
    result = re.sub(r'</b>\s*<b>', '', result)
    result = re.sub(r'</i>\s*<i>', '', result)
    return result


def break_sentences(html):
    """Insert <br> after sentence-ending periods and before list-like items in HTML text.
    Operates on already-tagged HTML, so must preserve tags."""
    # 1. Line break after ". " followed by uppercase (new sentence), but not inside tags
    #    Match ". X" where X is uppercase letter — insert <br> before X
    html = re.sub(
        r'(\.) (?=(<[bi]>)*[A-ZÀÈÉÌÒÙ])',
        r'\1<br>\n',
        html
    )
    # 2. Line break before list ordinals: Primo, Secondo, Terzo, Quarto, Infine
    for word in ['Primo,', 'Secondo,', 'Terzo,', 'Quarto,', 'Quinto,', 'Infine,']:
        html = html.replace(f' {word}', f'<br>\n{word}')
    # 3. Line break before italic sub-entries that start a new concept
    #    e.g., "<i>Allarme mentale:</i>", "<i>Scheletri:</i>", "<i>Zombi:</i>"
    html = re.sub(
        r'(?<!\n) ?(<i>[A-ZÀÈÉÌÒÙ][^<]*?:</i>)',
        r'<br>\n\1',
        html
    )
    # 4. Extra spacing before Focus / Componente materiale / Costo in PE (double break)
    #    Uses plain-text matching to handle keywords split across HTML tags
    SPACING_KEYWORDS = [
        'Componente materiale arcana:', 'Componente materiale:',
        'Focus arcano:', 'Focus:', 'Costo in PE:'
    ]
    # Process longest keywords first; collect all matches then apply in reverse
    # order so insertions don't shift positions of subsequent matches
    insertions = []  # list of (html_pos, break_type)
    for kw in sorted(SPACING_KEYWORDS, key=len, reverse=True):
        plain = re.sub(r'<[^>]+>', '', html)
        search_start = 0
        while True:
            idx = plain.find(kw, search_start)
            if idx == -1:
                break
            search_start = idx + len(kw)

            # Map plain text position → HTML position
            h, p = 0, 0
            while p < idx and h < len(html):
                if html[h] == '<':
                    while h < len(html) and html[h] != '>':
                        h += 1
                    h += 1
                else:
                    h += 1
                    p += 1

            # Include preceding opening tags (<b>, <i>) that wrap the keyword
            while True:
                moved = False
                for tag in ['<i>', '<b>']:
                    if h >= len(tag) and html[h-len(tag):h] == tag:
                        h -= len(tag)
                        moved = True
                if not moved:
                    break

            insertions.append(h)

    # Apply insertions in reverse order (highest position first)
    for h in sorted(set(insertions), reverse=True):
        window = html[max(0, h-30):h]
        if '<br>\n<br>\n' in window or '<br>\n<br>' in window:
            continue
        if '<br>' in html[max(0, h-10):h]:
            html = html[:h] + '<br>\n' + html[h:]
        else:
            html = html[:h] + '<br>\n<br>\n' + html[h:]

    # Clean up: don't start with <br>
    html = re.sub(r'^(<br>\n)+', '', html)
    return html


def parse_spells(full_text, bold_set, italic_set):
    """Parse the full text into spell blocks with HTML formatting."""
    # Split into individual spell text blocks
    # Each spell starts with an ALL-CAPS name
    # Split by: line that is ALL CAPS (the spell name)

    # Normalize line endings
    full_text = full_text.replace('\r\n', '\n').replace('\r', '\n')

    # Remove form feed chars
    full_text = full_text.replace('\f', '\n')

    # The pdftotext -layout output has each spell as a dense paragraph
    # Split on patterns that look like spell names at the beginning
    # Spell names: sequences of uppercase letters, spaces, accented uppercase, slashes, apostrophes
    # They appear after a newline or at start

    # First, split the text into lines
    lines = full_text.split('\n')

    # Collect non-empty lines, merging continuation lines
    paragraphs = []
    current = ''
    for line in lines:
        stripped = line.strip()
        if not stripped:
            if current:
                paragraphs.append(current)
                current = ''
        else:
            if current:
                current += ' ' + stripped
            else:
                current = stripped
    if current:
        paragraphs.append(current)

    # Now parse each paragraph to find spell blocks
    spells = []
    header_text = ''

    for para in paragraphs:
        # Try to find spell name at the start
        # Spell name pattern: ALL CAPS words at the beginning, before the school
        spell_match = None
        for school in SCHOOLS:
            # Pattern: SPELL NAME School...
            pattern = rf'^([A-ZÀÈÉÌÒÙ][A-ZÀÈÉÌÒÙ\s/\'\-]+?)\s+({school})'
            m = re.match(pattern, para)
            if m:
                spell_match = m
                break

        if spell_match:
            spell_name = spell_match.group(1).strip()
            rest = para[spell_match.start(2):]
            spells.append({'name': spell_name, 'text': rest})
        elif para.startswith('This material is Open Game Content') or para.startswith('INCANTESIMI'):
            header_text = para
        elif spells:
            # Continuation of previous spell (happens with page breaks)
            spells[-1]['text'] += ' ' + para
        else:
            header_text += ' ' + para

    return header_text.strip(), spells


def format_spell_block(name, text, bold_set, italic_set):
    """Format a single spell into an HTML block."""
    # Strategy: find all field label positions, split into:
    #   school (before first field), fields (label:value pairs), description (after last field value)

    field_pattern = '|'.join(re.escape(f) for f in FIELD_LABELS)

    # Find ALL field label matches
    field_matches = list(re.finditer(field_pattern, text))

    if not field_matches:
        # No fields found - treat everything as school + description
        parts = []
        desc_html = apply_bold_italic(text, bold_set, italic_set)
        parts.append(f'  <p class="desc">{desc_html}</p>')
        name_escaped = name.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        return f'<div class="spell-block">\n  <h3>{name_escaped}</h3>\n{"".join(parts)}\n</div>'

    # School = text before first field
    school_text = text[:field_matches[0].start()].strip()

    # Find the LAST field that's a "standard closing field"
    # Usually "Resistenza agli incantesimi:" is the last field before description.
    # But sometimes it's another field. We find the last field match and split after its value.
    # The value of the last field ends where the description begins.

    # Build field texts: each field runs from its label to the next label
    fields = []
    for i, m in enumerate(field_matches):
        start = m.start()
        end = field_matches[i + 1].start() if i + 1 < len(field_matches) else len(text)
        field_full = text[start:end].strip()
        fields.append({'start': start, 'end': end, 'text': field_full, 'label': m.group()})

    # Now find where fields end and description begins.
    # The last "header field" is typically "Resistenza agli incantesimi:" or the last field
    # whose value is short (single line). After that, the description starts.
    # Heuristic: find the last field whose label is in FIELD_LABELS and whose value
    # (text after the colon) starts with a short known pattern.

    # Find "Resistenza agli incantesimi:" - if present, it's the boundary
    res_idx = None
    for i, f in enumerate(fields):
        if f['label'] == 'Resistenza agli incantesimi:':
            res_idx = i
            break  # Take the first occurrence (it's the real one, not in description)

    def split_last_field(f):
        """Split a field's text into (field_value, description_remainder).
        The field value is the short part after the label; the description is everything after."""
        label = f['label']
        after_label = f['text'][len(label):].strip()

        # Known value patterns per field type
        if label == 'Resistenza agli incantesimi:':
            val_match = re.match(r'^(Sì\s*(?:\([^)]*\))?|No|Vedi testo)\s*', after_label)
        elif label == 'Tiro salvezza:':
            val_match = re.match(r'^(Nessuno|Volontà[^.]*?|Tempra[^.]*?|Riflessi[^.]*?|Vedi testo)(?:\s+(?=[A-Z][a-z])|\s*$)', after_label)
        elif label == 'Durata:':
            # Value: "10 minuti per livello (I)" — stop before first uppercase letter starting a new sentence
            val_match = re.match(r'^([^.]*?(?:\([IiCcLlDd]\))?)(?:\s+(?=[A-Z][a-zàèéìòù]))', after_label)
            if not val_match:
                # Try simpler: take until first ". " or until uppercase sentence start
                val_match = re.match(r'^(.+?)(?:\s+(?=[A-ZÀÈÉÌÒÙL][a-zàèéìòù\']))', after_label)
        else:
            val_match = None

        if val_match:
            return label + ' ' + val_match.group(0).strip(), after_label[val_match.end():].strip()
        else:
            return label + ' ' + after_label, ''

    if res_idx is not None:
        boundary_idx = res_idx
    else:
        # No "Resistenza" field - use last field as boundary
        boundary_idx = len(fields) - 1

    f = fields[boundary_idx]
    field_value, remaining = split_last_field(f)

    # Clean fields: take all fields up to boundary, replace boundary with clean value
    clean_fields = [fi['text'] for fi in fields[:boundary_idx]]
    clean_fields.append(field_value)

    # Description = remaining from boundary field + any subsequent field-like text
    desc_parts = []
    if remaining:
        desc_parts.append(remaining)
    for fi in fields[boundary_idx + 1:]:
        desc_parts.append(fi['text'])
    desc_text = ' '.join(desc_parts).strip()

    # Build HTML
    parts = []

    if school_text:
        parts.append(f'  <p class="school"><i>{school_text}</i></p>')

    for field in clean_fields:
        field_html = apply_bold_italic(field, bold_set, italic_set)
        parts.append(f'  <p class="field">{field_html}</p>')

    if desc_text:
        desc_html = apply_bold_italic(desc_text, bold_set, italic_set)
        desc_html = break_sentences(desc_html)
        parts.append(f'  <p class="desc">{desc_html}</p>')

    name_escaped = name.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    inner = '\n'.join(parts)
    return f'<div class="spell-block">\n  <h3>{name_escaped}</h3>\n{inner}\n</div>'


def main(pdf_path, output_path):
    print("Step 1: Extracting complete text via pdftotext...")
    full_text = get_complete_text(pdf_path)
    print(f"  Got {len(full_text)} chars")

    print("Step 2: Parsing PDF streams for bold/italic info...")
    with open(pdf_path, 'rb') as f:
        pdf_bytes = f.read()
    font_map = parse_font_map(pdf_bytes)
    print(f"  Fonts: {font_map}")
    streams = decompress_streams(pdf_bytes)
    bold_set, italic_set = extract_formatted_fragments(streams, font_map)
    print(f"  Bold fragments: {len(bold_set)}")
    print(f"  Italic fragments: {len(italic_set)}")
    # Show some examples
    for b in sorted(bold_set, key=len)[:5]:
        print(f"    B: {b!r}")
    for it in sorted(italic_set, key=len)[:5]:
        print(f"    I: {it!r}")

    print("Step 3: Parsing spell blocks...")
    header, spells = parse_spells(full_text, bold_set, italic_set)
    print(f"  Found {len(spells)} spells")
    for s in spells[:5]:
        print(f"    - {s['name']}")

    print("Step 4: Generating HTML...")
    spell_html_blocks = []
    for spell in spells:
        block = format_spell_block(spell['name'], spell['text'], bold_set, italic_set)
        spell_html_blocks.append(block)

    body = '\n\n'.join(spell_html_blocks)

    full_html = f'''<!DOCTYPE html>
<html lang="it">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Incantesimi (A) — SRD 3.5 ITA</title>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    font-family: 'Times New Roman', Georgia, serif;
    max-width: 900px;
    margin: 0 auto;
    padding: 20px 30px;
    background: #faf8f0;
    color: #1a1a1a;
    line-height: 1.55;
    font-size: 15px;
  }}
  h1 {{
    text-align: center;
    font-size: 1.8em;
    margin-bottom: 8px;
    color: #8b0000;
  }}
  .intro {{
    text-align: center;
    color: #666;
    font-size: 0.9em;
    margin-bottom: 28px;
    padding-bottom: 16px;
    border-bottom: 2px solid #8b0000;
  }}
  .spell-block {{
    margin-bottom: 20px;
    padding: 14px 18px;
    background: #fff;
    border-left: 4px solid #8b0000;
    border-radius: 2px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.07);
  }}
  .spell-block h3 {{
    font-size: 1.15em;
    color: #8b0000;
    margin-bottom: 4px;
    letter-spacing: 0.5px;
  }}
  .spell-block .school {{
    color: #555;
    margin-bottom: 6px;
    font-size: 0.95em;
  }}
  .spell-block .field {{
    margin: 1px 0;
    font-size: 0.95em;
  }}
  .spell-block .desc {{
    margin: 8px 0 0 0;
    text-align: justify;
  }}
  .spell-block p:last-child {{
    margin-bottom: 0;
  }}
</style>
</head>
<body>
<h1>INCANTESIMI (A)</h1>
<p class="intro">This material is Open Game Content, licensed under the Open Game License v1.0a.</p>
{body}
</body>
</html>'''

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(full_html)
    print(f"Done! Written {len(full_html)} chars to {output_path}")


if __name__ == '__main__':
    pdf_path = sys.argv[1] if len(sys.argv) > 1 else '/tmp/incantesimi_A.pdf'
    output_path = sys.argv[2] if len(sys.argv) > 2 else '/tmp/incantesimi_A_structured.html'
    main(pdf_path, output_path)
