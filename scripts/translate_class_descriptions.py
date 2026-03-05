#!/usr/bin/env python3
"""
Translate class desc_html and table_html fields into Italian.
Only translates content within structural HTML tags (headers, labels, table cells),
leaving paragraph/prose text in clean English.

Usage:
    python scripts/translate_class_descriptions.py
"""

import json
import os
import re

# ── Translation maps (exported for use by other scripts) ────────────────

# Table headers
TABLE_HEADER_MAP = {
    "Base Attack Bonus": "Bonus di Attacco Base",
    "Base Attack<br/>Bonus": "Bonus di Attacco<br/>Base",
    "Fort Save": "Tempra",
    "Ref Save": "Riflessi",
    "Will Save": "Volontà",
    "Special": "Speciale",
    "Level": "Livello",
    "Spells per Day": "Incantesimi al Giorno",
    "Spells Known": "Incantesimi Conosciuti",
    "Bonus Spells": "Incantesimi Bonus",
    "Points/Day": "Punti/Giorno",
    "AC Bonus": "Bonus CA",
    "Unarmored<br/>Speed Bonus": "Bonus Velocità<br/>Senza Armatura",
    "Unarmored Speed Bonus": "Bonus Velocità Senza Armatura",
    "Flurry of Blows<br/>Attack Bonus": "Raffica di Colpi<br/>Bonus Attacco",
    "Flurry of Blows Attack Bonus": "Raffica di Colpi Bonus Attacco",
    "Unarmed<br/>Damage": "Danno<br/>Senz'Armi",
    "Unarmed Damage": "Danno Senz'Armi",
}

# Section headers (h2/h3/h4 content)
SECTION_MAP = {
    "Class Skills": "Abilità di Classe",
    "Class Features": "Privilegi di Classe",
    "Class Abilities": "Capacità di Classe",
    "Spells": "Incantesimi",
    "Spell List": "Lista Incantesimi",
    "Ex-Barbarians": "Ex-Barbari",
    "Ex-Bards": "Ex-Bardi",
    "Ex-Clerics": "Ex-Chierici",
    "Ex-Druids": "Ex-Druidi",
    "Ex-Monks": "Ex-Monaci",
    "Ex-Paladins": "Ex-Paladini",
    "Ex-Rangers": "Ex-Ranger",
    "Multiclass Note": "Nota Multiclasse",
}

# Strong/bold labels (appear as <strong>Label:</strong>)
LABEL_MAP = {
    "Alignment:": "Allineamento:",
    "Hit Die:": "Dado Vita:",
    "Hit Dice:": "Dadi Vita:",
    "Skill Points at 1st Level:": "Punti Abilità al 1° Livello:",
    "Skill Points at Each Additional Level:": "Punti Abilità ad Ogni Livello Addizionale:",
    "Weapon and Armor Proficiency:": "Competenza nelle Armi e Armature:",
    "Bonus Feats:": "Talenti Bonus:",
    "Bonus Feat:": "Talento Bonus:",
    "Requirements": "Requisiti",
    "To qualify": "Per qualificarsi",
    "Spellcasting:": "Lanciare Incantesimi:",
    "Spells:": "Incantesimi:",
    "Spells Per Day:": "Incantesimi al Giorno:",
    "Table:": "Tabella:",
}

# Skill names
SKILL_MAP = {
    "Appraise": "Valutare",
    "Balance": "Equilibrio",
    "Bluff": "Raggirare",
    "Climb": "Scalare",
    "Concentration": "Concentrazione",
    "Craft": "Artigianato",
    "Decipher Script": "Decifrare Scritti",
    "Diplomacy": "Diplomazia",
    "Disable Device": "Disattivare Congegni",
    "Disguise": "Camuffare",
    "Escape Artist": "Artista della Fuga",
    "Forgery": "Falsificare",
    "Gather Information": "Raccogliere Informazioni",
    "Handle Animal": "Addestrare Animali",
    "Heal": "Guarire",
    "Hide": "Nascondersi",
    "Intimidate": "Intimidire",
    "Jump": "Saltare",
    "Knowledge": "Conoscenze",
    "Listen": "Ascoltare",
    "Move Silently": "Muoversi Silenziosamente",
    "Open Lock": "Scassinare Serrature",
    "Perform": "Intrattenere",
    "Profession": "Professione",
    "Ride": "Cavalcare",
    "Search": "Cercare",
    "Sense Motive": "Percepire Intenzioni",
    "Sleight of Hand": "Rapidità di Mano",
    "Speak Language": "Parlare Linguaggi",
    "Spellcraft": "Conoscenze Magiche",
    "Spot": "Osservare",
    "Survival": "Sopravvivenza",
    "Swim": "Nuotare",
    "Tumble": "Acrobazia",
    "Use Magic Device": "Utilizzare Oggetti Magici",
    "Use Rope": "Usare Corde",
}

# Ability abbreviations in parentheses
ABILITY_ABBR_MAP = {
    "(Str)": "(For)",
    "(Dex)": "(Des)",
    "(Con)": "(Cos)",
    "(Int)": "(Int)",
    "(Wis)": "(Sag)",
    "(Cha)": "(Car)",
}

# Class feature names (for table cells only)
FEATURE_MAP = {
    "Fast movement": "Movimento veloce",
    "fast movement": "movimento veloce",
    "Rage": "Ira",
    "rage": "ira",
    "Greater rage": "Ira superiore",
    "Tireless rage": "Ira instancabile",
    "Mighty rage": "Ira possente",
    "Indomitable will": "Volontà indomabile",
    "Uncanny dodge": "Schivare prodigioso",
    "uncanny dodge": "schivare prodigioso",
    "Improved uncanny dodge": "Schivare prodigioso migliorato",
    "Trap sense": "Percepire trappole",
    "trap sense": "percepire trappole",
    "illiteracy": "analfabetismo",
    "Bardic music": "Musica bardica",
    "bardic music": "musica bardica",
    "Bardic knowledge": "Conoscenza bardica",
    "bardic knowledge": "conoscenza bardica",
    "Countersong": "Controcanzone",
    "countersong": "controcanzone",
    "Fascinate": "Affascinare",
    "fascinate": "affascinare",
    "Inspire courage": "Ispirare coraggio",
    "inspire courage": "ispirare coraggio",
    "Inspire competence": "Ispirare competenza",
    "inspire competence": "ispirare competenza",
    "Inspire greatness": "Ispirare grandezza",
    "inspire greatness": "ispirare grandezza",
    "Inspire heroics": "Ispirare eroismo",
    "Song of freedom": "Canzone di libertà",
    "Mass suggestion": "Suggestione di massa",
    "Turn undead": "Scacciare non morti",
    "turn undead": "scacciare non morti",
    "Turn or rebuke undead": "Scacciare o intimorire non morti",
    "turn or rebuke undead": "scacciare o intimorire non morti",
    "Spontaneous casting": "Lancio spontaneo",
    "spontaneous casting": "lancio spontaneo",
    "Wild shape": "Forma selvatica",
    "wild shape": "forma selvatica",
    "Venom immunity": "Immunità al veleno",
    "Resist nature's lure": "Resistere al richiamo della natura",
    "Trackless step": "Passo senza tracce",
    "Woodland stride": "Andatura nel bosco",
    "A thousand faces": "Mille volti",
    "Timeless body": "Corpo senza tempo",
    "Animal companion": "Compagno animale",
    "animal companion": "compagno animale",
    "Nature sense": "Senso della natura",
    "Flurry of blows": "Raffica di colpi",
    "flurry of blows": "raffica di colpi",
    "Evasion": "Evasione",
    "evasion": "evasione",
    "Improved evasion": "Evasione migliorata",
    "improved evasion": "evasione migliorata",
    "Still mind": "Mente ferma",
    "Ki strike": "Colpo ki",
    "ki strike": "colpo ki",
    "Slow fall": "Caduta lenta",
    "slow fall": "caduta lenta",
    "Purity of body": "Purezza del corpo",
    "Wholeness of body": "Completezza del corpo",
    "Diamond body": "Corpo diamantino",
    "Diamond soul": "Anima diamantina",
    "Quivering palm": "Palmo tremante",
    "Tongue of the sun and moon": "Lingua del sole e della luna",
    "Empty body": "Corpo vuoto",
    "Perfect self": "Sé perfetto",
    "Detect evil": "Individuare il male",
    "detect evil": "individuare il male",
    "Smite evil": "Punire il male",
    "smite evil": "punire il male",
    "Divine grace": "Grazia divina",
    "divine grace": "grazia divina",
    "Divine health": "Salute divina",
    "Lay on hands": "Imposizione delle mani",
    "lay on hands": "imposizione delle mani",
    "Aura of courage": "Aura di coraggio",
    "Remove disease": "Rimuovere malattie",
    "remove disease": "rimuovere malattie",
    "Special mount": "Destriero speciale",
    "special mount": "destriero speciale",
    "Code of conduct": "Codice di condotta",
    "Favored enemy": "Nemico prescelto",
    "favored enemy": "nemico prescelto",
    "Combat style": "Stile di combattimento",
    "combat style": "stile di combattimento",
    "Improved combat style": "Stile di combattimento migliorato",
    "Combat style mastery": "Padronanza dello stile di combattimento",
    "Endurance": "Resistenza fisica",
    "Swift tracker": "Seguire tracce rapido",
    "Camouflage": "Mimetismo",
    "Hide in plain sight": "Nascondersi in piena vista",
    "Sneak attack": "Attacco furtivo",
    "sneak attack": "attacco furtivo",
    "Trapfinding": "Trovare trappole",
    "trapfinding": "trovare trappole",
    "Special abilities": "Capacità speciali",
    "special abilities": "capacità speciali",
    "Crippling strike": "Colpo debilitante",
    "Defensive roll": "Rotolamento difensivo",
    "Opportunist": "Opportunista",
    "Skill mastery": "Padronanza nelle abilità",
    "Slippery mind": "Mente sfuggente",
    "Familiar": "Famiglio",
    "familiar": "famiglio",
    "Summon familiar": "Evocare famiglio",
    "Bonus feat": "Talento bonus",
    "bonus feat": "talento bonus",
    "Scribe Scroll": "Scrivere Pergamene",
}

# Class name translations for table captions
CLASS_NAME_MAP = {
    "The Barbarian": "Il Barbaro",
    "The Bard": "Il Bardo",
    "The Cleric": "Il Chierico",
    "The Druid": "Il Druido",
    "The Fighter": "Il Guerriero",
    "The Monk": "Il Monaco",
    "The Paladin": "Il Paladino",
    "The Ranger": "Il Ranger",
    "The Rogue": "Il Ladro",
    "The Sorcerer": "Lo Stregone",
    "The Wizard": "Il Mago",
    "The Adept": "L'Adepto",
    "The Aristocrat": "L'Aristocratico",
    "The Commoner": "Il Popolano",
    "The Expert": "L'Esperto",
    "The Warrior": "Il Guerriero",
    "The Arcane Archer": "L'Arciere Arcano",
    "The Arcane Trickster": "Il Mistificatore Arcano",
    "The Archmage": "L'Arcimago",
    "The Assassin": "L'Assassino",
    "The Blackguard": "Il Cavaliere Nero",
    "The Dragon Disciple": "Il Discepolo del Drago",
    "The Duelist": "Il Duellante",
    "The Dwarven Defender": "Il Difensore Nanico",
    "The Eldritch Knight": "Il Cavaliere Mistico",
    "The Hierophant": "Lo Ierofante",
    "The Horizon Walker": "Il Camminatore dell'Orizzonte",
    "The Loremaster": "Il Maestro del Sapere",
    "The Mystic Theurge": "Il Teurgo Mistico",
    "The Shadowdancer": "Il Danzatore delle Ombre",
    "The Thaumaturgist": "Il Taumaturgo",
}

# Not exported: TERM_MAP removed — it caused mixed-language in prose


def _apply_map(text, mapping):
    """Apply a translation map to text, longer keys first."""
    for en, it in sorted(mapping.items(), key=lambda x: -len(x[0])):
        text = text.replace(en, it)
    return text


def _translate_tag_content(html, tag_pattern, translate_fn):
    """Translate content within specific HTML tags using a callback.

    tag_pattern: regex matching opening+content+closing, with group(1)=open, group(2)=content, group(3)=close
    translate_fn: function(content_string) -> translated_string
    """
    def replacer(m):
        open_tag = m.group(1)
        content = m.group(2)
        close_tag = m.group(3)
        translated = translate_fn(content)
        return f"{open_tag}{translated}{close_tag}"

    return re.sub(tag_pattern, replacer, html, flags=re.DOTALL)


def translate_class_desc_html(html):
    """Translate class desc_html — only structural elements, not prose."""
    if not html:
        return None

    result = html

    # 1. <th> tags — table headers
    def translate_th(content):
        return _apply_map(content, TABLE_HEADER_MAP)
    result = _translate_tag_content(result, r'(<th[^>]*>)(.*?)(</th>)', translate_th)

    # 2. <h2>/<h3>/<h4> tags — section headers
    all_sections = dict(SECTION_MAP)
    for en, it in CLASS_NAME_MAP.items():
        all_sections[f"Table: {en}"] = f"Tabella: {it}"
    def translate_heading(content):
        c = content.strip()
        return _apply_map(c, all_sections)
    result = _translate_tag_content(result, r'(<h[2-6][^>]*>)\s*(.*?)\s*(</h[2-6]>)', translate_heading)

    # 3. <strong> tags — bold labels
    def translate_strong(content):
        return _apply_map(content, LABEL_MAP)
    result = _translate_tag_content(result, r'(<strong>)(.*?)(</strong>)', translate_strong)

    # 4. <caption> tags
    def translate_caption(content):
        for en, it in CLASS_NAME_MAP.items():
            content = content.replace(f"Table: {en}", f"Tabella: {it}")
        return content
    result = _translate_tag_content(result, r'(<caption[^>]*>)(.*?)(</caption>)', translate_caption)

    # 5. <td> tags — table cells (feature names, ability abbreviations)
    def translate_td(content):
        c = content.strip()
        if not c or c.startswith('+') or c.startswith('−') or c[0].isdigit():
            return content  # skip numeric cells
        c = _apply_map(c, FEATURE_MAP)
        c = _apply_map(c, ABILITY_ABBR_MAP)
        return c
    result = _translate_tag_content(result, r'(<td[^>]*>)(.*?)(</td>)', translate_td)

    return result if result != html else None


def translate_table_html(html):
    """Translate class table_html (same structural approach)."""
    if not html:
        return None
    # table_html is purely structural — reuse the same function
    return translate_class_desc_html(html)


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(os.path.dirname(script_dir), "data")

    base_path = os.path.join(data_dir, "classes.json")
    overlay_path = os.path.join(data_dir, "i18n", "it", "classes.json")

    if not os.path.exists(base_path):
        print("classes.json not found")
        return

    with open(base_path, "r", encoding="utf-8") as f:
        base = json.load(f)

    overlay = []
    if os.path.exists(overlay_path):
        with open(overlay_path, "r", encoding="utf-8") as f:
            overlay = json.load(f)

    overlay_map = {}
    for entry in overlay:
        slug = entry.get("slug")
        if slug:
            overlay_map[slug] = entry

    added_desc = 0
    added_table = 0
    replaced_desc = 0
    replaced_table = 0

    for cls in base:
        slug = cls["slug"]
        if slug not in overlay_map:
            overlay_map[slug] = {"slug": slug}

        entry = overlay_map[slug]

        # Always re-translate desc_html (overwrite old mixed translations)
        translated = translate_class_desc_html(cls.get("desc_html"))
        if translated:
            if "desc_html" in entry:
                replaced_desc += 1
            else:
                added_desc += 1
            entry["desc_html"] = translated

        # Always re-translate table_html
        translated = translate_table_html(cls.get("table_html"))
        if translated:
            if "table_html" in entry:
                replaced_table += 1
            else:
                added_table += 1
            entry["table_html"] = translated

    result = sorted(overlay_map.values(), key=lambda x: x.get("slug", ""))
    os.makedirs(os.path.dirname(overlay_path), exist_ok=True)
    with open(overlay_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print(f"Classes: {added_desc} new + {replaced_desc} replaced desc_html, "
          f"{added_table} new + {replaced_table} replaced table_html")


if __name__ == "__main__":
    main()
