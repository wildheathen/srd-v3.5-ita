#!/usr/bin/env python3
"""
Translate class desc_html fields into Italian using formulaic HTML replacements.
Handles structural elements (headers, labels, table headers, skill names, ability names)
and common D&D terminology.

Usage:
    python scripts/translate_class_descriptions.py
"""

import json
import os
import re

# ── HTML structure replacements (order matters: longer first) ────────────

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

# Section headers (h3/h4 content)
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

# Strong/bold labels
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

# Common D&D terms in class descriptions
TERM_MAP = {
    "bonus feat": "talento bonus",
    "Bonus feat": "Talento bonus",
    "bonus feats": "talenti bonus",
    "fighter bonus feat": "talento bonus da guerriero",
    "fighter bonus feats": "talenti bonus da guerriero",
    "simple weapons": "armi semplici",
    "martial weapons": "armi da guerra",
    "simple and martial weapons": "armi semplici e da guerra",
    "all simple weapons": "tutte le armi semplici",
    "all martial weapons": "tutte le armi da guerra",
    "all simple and martial weapons": "tutte le armi semplici e da guerra",
    "light armor": "armatura leggera",
    "medium armor": "armatura media",
    "heavy armor": "armatura pesante",
    "all armor": "tutte le armature",
    "tower shields": "scudi torre",
    "shields": "scudi",
    "shield": "scudo",
    "hit points": "punti ferita",
    "Hit Points": "Punti Ferita",
    "hit point": "punto ferita",
    "damage reduction": "riduzione del danno",
    "Damage Reduction": "Riduzione del Danno",
    "spell resistance": "resistenza agli incantesimi",
    "Spell Resistance": "Resistenza agli Incantesimi",
    "saving throw": "tiro salvezza",
    "saving throws": "tiri salvezza",
    "Saving Throw": "Tiro Salvezza",
    "Fortitude": "Tempra",
    "Reflex": "Riflessi",
    "Will": "Volontà",
    "Armor Class": "Classe Armatura",
    "armor check penalty": "penalità di controllo dell'armatura",
    "base attack bonus": "bonus di attacco base",
    "Base Attack Bonus": "Bonus di Attacco Base",
    "attack of opportunity": "attacco di opportunità",
    "attacks of opportunity": "attacchi di opportunità",
    "challenge rating": "grado di sfida",
    "experience points": "punti esperienza",
    "caster level": "livello dell'incantatore",
    "Caster Level": "Livello dell'Incantatore",
    "spell level": "livello dell'incantesimo",
    "class level": "livello di classe",
    "character level": "livello del personaggio",
    "ability score": "punteggio di caratteristica",
    "ability scores": "punteggi di caratteristica",
    "Strength": "Forza",
    "Dexterity": "Destrezza",
    "Constitution": "Costituzione",
    "Intelligence": "Intelligenza",
    "Wisdom": "Saggezza",
    "Charisma": "Carisma",
    "1st level": "1° livello",
    "2nd level": "2° livello",
    "3rd level": "3° livello",
    "4th level": "4° livello",
    "5th level": "5° livello",
    "6th level": "6° livello",
    "7th level": "7° livello",
    "8th level": "8° livello",
    "9th level": "9° livello",
    "10th level": "10° livello",
    "11th level": "11° livello",
    "12th level": "12° livello",
    "13th level": "13° livello",
    "14th level": "14° livello",
    "15th level": "15° livello",
    "16th level": "16° livello",
    "17th level": "17° livello",
    "18th level": "18° livello",
    "19th level": "19° livello",
    "20th level": "20° livello",
    "1st-level": "1° livello",
    "2nd-level": "2° livello",
    "3rd-level": "3° livello",
    "4th-level": "4° livello",
    "5th-level": "5° livello",
    "6th-level": "6° livello",
    "7th-level": "7° livello",
    "8th-level": "8° livello",
    "9th-level": "9° livello",
}

# Class feature names (Special column in tables)
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
    "Trap sense": "Percepire trappole",
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

# Class name translations for table captions and references
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


def translate_class_desc_html(html):
    """Apply formulaic translations to class desc_html."""
    if not html:
        return None

    result = html

    # 1. Table headers (in <th> tags)
    for en, it in sorted(TABLE_HEADER_MAP.items(), key=lambda x: -len(x[0])):
        result = result.replace(f"<th>{en}</th>", f"<th>{it}</th>")

    # 2. Section headers (in <h3>/<h4> tags) - use regex for id attributes
    for en, it in SECTION_MAP.items():
        result = re.sub(
            rf'(<h[34][^>]*>)\s*{re.escape(en)}\s*(</h[34]>)',
            rf'\1{it}\2',
            result
        )

    # 3. Strong/bold labels
    for en, it in sorted(LABEL_MAP.items(), key=lambda x: -len(x[0])):
        result = result.replace(f"<strong>{en}</strong>", f"<strong>{it}</strong>")

    # 4. Class names in table captions
    for en, it in CLASS_NAME_MAP.items():
        result = result.replace(f"Table: {en}", f"Tabella: {it}")
        result = result.replace(f"table: {en}", f"tabella: {it}")

    # 5. Feature names in table cells
    for en, it in sorted(FEATURE_MAP.items(), key=lambda x: -len(x[0])):
        # In <td> cells
        result = result.replace(f">{en}<", f">{it}<")
        result = result.replace(f">{en},", f">{it},")
        # In regular text between tags, comma-separated in table cells
        result = result.replace(f", {en}", f", {it}")

    # 6. Ability abbreviations
    for en, it in ABILITY_ABBR_MAP.items():
        result = result.replace(en, it)

    # 7. Skill names (careful: only in skill list contexts and table references)
    for en, it in sorted(SKILL_MAP.items(), key=lambda x: -len(x[0])):
        # In parenthetical skill lists after "class skills"
        result = result.replace(f"{en} (", f"{it} (")
        # Standalone skill references
        result = result.replace(f"{en} check", f"prova di {it}")
        result = result.replace(f"{en} checks", f"prove di {it}")
        result = result.replace(f"{en} skill", f"abilità {it}")

    # 8. Common terms (longer first to avoid partial replacements)
    for en, it in sorted(TERM_MAP.items(), key=lambda x: -len(x[0])):
        result = result.replace(en, it)

    return result if result != html else None


def translate_table_html(html):
    """Apply formulaic translations to class table_html."""
    if not html:
        return None

    result = html

    # Table headers
    for en, it in sorted(TABLE_HEADER_MAP.items(), key=lambda x: -len(x[0])):
        result = result.replace(f"<th>{en}</th>", f"<th>{it}</th>")

    # Table captions
    for en, it in CLASS_NAME_MAP.items():
        result = result.replace(f"Table: {en}", f"Tabella: {it}")

    # Feature names in table cells
    for en, it in sorted(FEATURE_MAP.items(), key=lambda x: -len(x[0])):
        result = result.replace(f">{en}<", f">{it}<")
        result = result.replace(f">{en},", f">{it},")
        result = result.replace(f", {en}", f", {it}")

    return result if result != html else None


# hit_die is just "d12." etc. — same in Italian, no translation needed


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
    for cls in base:
        slug = cls["slug"]
        if slug not in overlay_map:
            overlay_map[slug] = {"slug": slug}

        entry = overlay_map[slug]

        # Translate desc_html if not already present
        if "desc_html" not in entry:
            translated = translate_class_desc_html(cls.get("desc_html"))
            if translated:
                entry["desc_html"] = translated
                added_desc += 1

        # Translate table_html if not already present
        if "table_html" not in entry:
            translated = translate_table_html(cls.get("table_html"))
            if translated:
                entry["table_html"] = translated
                added_table += 1

    result = sorted(overlay_map.values(), key=lambda x: x.get("slug", ""))
    os.makedirs(os.path.dirname(overlay_path), exist_ok=True)
    with open(overlay_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print(f"Classes: {added_desc} desc_html, {added_table} table_html translations added")


if __name__ == "__main__":
    main()
