#!/usr/bin/env python3
"""
Traduce il table_html delle classi nell'overlay IT.

Applica sostituzioni sistematiche per:
- Intestazioni colonne (Level, Base Attack Bonus, Fort/Ref/Will Save, Special)
- Pattern ripetuti nelle celle Special (+1 level of existing ... class)
- Abilità specifiche per classe (rage, sneak attack, evasion, etc.)
- Terminologia generale D&D (damage reduction, uncanny dodge, etc.)

Uso:
    python scripts/translate_class_tables.py          # Mostra le modifiche (dry-run)
    python scripts/translate_class_tables.py --apply  # Applica le modifiche
"""

import argparse
import json
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
OVERLAY_PATH = REPO_ROOT / "data" / "i18n" / "it" / "classes.json"
EN_PATH = REPO_ROOT / "data" / "classes.json"

# ── Sostituzioni nelle intestazioni (th, caption) ──────────────────────

HEADER_REPLACEMENTS = [
    # Colonne (ordine: più lunghi prima per evitare match parziali)
    ("Flurry of Blows Attack Bonus", "Bonus di Attacco Raffica di Colpi"),
    ("Unarmored Speed Bonus", "Bonus Velocità Senza Armatura"),
    ("Base Attack Bonus", "Bonus di Attacco Base"),
    ("Base AttackBonus", "Bonus di Attacco Base"),
    ("BaseAttackBonus", "Bonus di Attacco Base"),
    ("Spells per Day", "Incantesimi al Giorno"),
    ("Bonus Spells", "Incantesimi Bonus"),
    ("Unarmed Damage", "Danno Senz'armi"),
    ("Fort Save", "Tempra"),
    ("FortSave", "Tempra"),
    ("Ref Save", "Riflessi"),
    ("RefSave", "Riflessi"),
    ("Will Save", "Volontà"),
    ("WillSave", "Volontà"),
    ("AC Bonus", "Bonus CA"),
    ("NPC Level", "Livello PNG"),
    # "Special" e "Level" sono troppo generici per str.replace → gestiti con regex in translate_headers()
]

# ── Pattern ripetuti nelle celle ────────────────────────────────────────

# Ordine importante: pattern più lunghi prima
CELL_PATTERNS = [
    # Classi di incantesimo
    (r"\+1 ?level of existing arcane spellcasting class/\+1 ?level of existing divine spellcasting class",
     "+1 livello di classe di incantesimi arcani esistente/+1 livello di classe di incantesimi divini esistente"),
    (r"\+1 ?level of existing arcane spellcasting class",
     "+1 livello di classe di incantesimi arcani esistente"),
    (r"\+1 ?level of existing divine spellcasting class",
     "+1 livello di classe di incantesimi divini esistente"),
    (r"\+1 ?level of existing spellcasting class",
     "+1 livello di classe di incantesimi esistente"),
    (r"\+1 ?level of existing class",
     "+1 livello di classe esistente"),

    # Saving throw bonuses
    (r"\+(\d) save against poison", r"+\1 ai tiri salvezza contro il veleno"),

    # Favored enemy
    (r"(\d)(?:st|nd|rd|th) favored enemy", r"\1° nemico prescelto"),

    # Smite
    (r"smite evil (\d)/day", r"punire il male \1/giorno"),
    (r"smite good (\d)/day", r"punire il bene \1/giorno"),

    # Rage
    (r"rage (\d)/day", r"ira \1/giorno"),

    # Remove disease
    (r"remove disease (\d)/week", r"rimuovere malattie \1/settimana"),

    # Combat style
    (r"combat style mastery", "maestria nello stile di combattimento"),
    (r"combat style", "stile di combattimento"),

    # Sneak attack (quelli ancora in EN)
    (r"sneak attack \+(\d+)d6", r"attacco furtivo +\1d6"),

    # Hide in plain sight
    ("hide in plain sight", "nascondersi in piena vista"),

    # Trap sense
    (r"trap sense \+(\d)", r"percepire trappole +\1"),

    # Breath weapon
    (r"breath weapon \((\d+d\d+)\)", r"arma a soffio (\1)"),

    # Natural armor increase
    (r"natural armor increase \(\+(\d)\)", r"bonus armatura naturale (+\1)"),

    # Ability boost
    (r"Ability boost \(Str \+(\d)\)", r"Aumento caratteristica (For +\1)"),
    (r"Ability boost \(Con \+(\d)\)", r"Aumento caratteristica (Cos +\1)"),
    (r"Ability boost \(Int \+(\d)\)", r"Aumento caratteristica (Int +\1)"),

    # Shadow jump
    (r"shadow jump (\d+) ft\.", r"salto nell'ombra \1 ft."),
    (r"Shadow jump (\d+) ft\.", r"Salto nell'ombra \1 ft."),

    # Planar terrain mastery
    (r"Planar terrain mastery", "Maestria del terreno planare"),

    # "/day" generico (per abilità già parzialmente tradotte)
    (r"(\d)/day\b", r"\1/giorno"),

    # "/week" generico
    (r"(\d)/week\b", r"\1/settimana"),

    # "Improved" + abilità specifiche (già parzialmente tradotte nell'overlay)
    (r"[Ii]mproved schivare prodigioso", "schivare prodigioso migliorato"),
    (r"[Ii]mproved reaction \+(\d)", r"reazione migliorata +\1"),
    (r"[Ii]mproved ally", "alleato migliorato"),

    # Arcane Trickster
    (r"[Rr]anged legerdemain", "trucco a distanza"),
    (r"[Ii]mpromptu attacco furtivo", "attacco furtivo improvvisato"),

    # Assassin: "spells" solo a fine lista (dopo virgola)
    (r",\s*spells\b", ", incantesimi"),

    # Cleanup: fix "evasionee" da overlay corrotti
    (r"\bevasionee\b", "evasione"),
]

# ── Sostituzioni esatte di abilità specifiche ───────────────────────────

ABILITY_TRANSLATIONS = [
    # Ordine: pattern più lunghi prima per evitare match parziali.
    # Ogni entry è (en, it). Verranno applicati con word boundary regex.

    # Monk (longer phrases first)
    ("tongue of the sun and moon", "linguaggio del sole e della luna"),
    ("ki strike (adamantine)", "colpo ki (adamantio)"),
    ("ki strike (lawful)", "colpo ki (legale)"),
    ("ki strike (magic)", "colpo ki (magico)"),
    ("wholeness of body", "completezza del corpo"),
    ("purity of body", "purezza del corpo"),
    ("perfect self", "perfezione dell'essere"),
    ("abundant step", "passo abbondante"),
    ("quivering palm", "palmo tremante"),
    ("greater flurry", "raffica superiore"),
    ("flurry of blows", "raffica di colpi"),
    ("unarmed strike", "colpo senz'armi"),
    ("diamond body", "anima diamantina"),
    ("diamond soul", "anima di diamante"),
    ("empty body", "corpo vuoto"),
    ("still mind", "mente quieta"),
    ("slow fall", "caduta lenta"),

    # Barbarian
    ("improved uncanny dodge", "schivare prodigioso migliorato"),
    ("uncanny dodge", "schivare prodigioso"),
    ("indomitable will", "volontà indomabile"),
    ("fast movement", "movimento veloce"),
    ("tireless rage", "ira instancabile"),
    ("greater rage", "ira superiore"),
    ("mighty rage", "ira possente"),
    ("illiteracy", "analfabetismo"),
    ("trapfinding", "trovare trappole"),

    # Bard
    ("bardic knowledge", "conoscenza bardica"),
    ("inspire competence", "ispirare competenza"),
    ("inspire greatness", "ispirare grandezza"),
    ("inspire heroics", "ispirare eroismo"),
    ("inspire courage", "ispirare coraggio"),
    ("song of freedom", "canzone di libertà"),
    ("mass suggestion", "suggestione di massa"),
    ("bardic music", "musica bardica"),
    ("countersong", "controcanto"),
    ("fascinate", "fascinazione"),

    # Cleric
    ("turn undead", "scacciare non morti"),
    ("command undead", "comandare non morti"),

    # Druid
    ("resist nature's lure", "resistere al richiamo della natura"),
    ("trackless step", "passo senza tracce"),
    ("woodland stride", "andatura nel bosco"),
    ("venom immunity", "immunità al veleno"),
    ("a thousand faces", "mille volti"),
    ("timeless body", "corpo senza tempo"),
    ("wild empathy", "empatia selvatica"),
    ("nature sense", "senso della natura"),
    ("wild shape", "forma selvatica"),

    # Paladin
    ("aura of courage", "aura di coraggio"),
    ("aura of good", "aura del bene"),
    ("divine health", "salute divina"),
    ("divine grace", "grazia divina"),
    ("detect evil", "individuare il male"),
    ("lay on hands", "imposizione delle mani"),
    ("special mount", "destriero speciale"),

    # Ranger
    ("swift tracker", "seguire tracce veloce"),
    ("wild empathy", "empatia selvatica"),
    ("camouflage", "mimetizzazione"),

    # Rogue
    ("special ability", "abilità speciale"),
    ("improved evasion", "evasione migliorata"),

    # Fighter
    ("bonus feat", "talento bonus"),

    # Sorcerer / Wizard
    ("summon familiar", "evocare famiglio"),
    ("Scribe Scroll", "Scrivere Pergamene"),

    # Assassin
    ("death attack", "attacco mortale"),
    ("poison use", "uso dei veleni"),

    # Blackguard
    ("aura of despair", "aura della disperazione"),
    ("dark blessing", "benedizione oscura"),
    ("fiendish servant", "servitore immondo"),
    ("aura of evil", "aura del male"),
    ("detect good", "individuare il bene"),

    # Dragon Disciple
    ("dragon apotheosis", "apoteosi del drago"),
    ("frightful presence", "presenza terrificante"),
    ("sleep immunity", "immunità al sonno"),
    ("claws and bite", "artigli e morso"),
    ("blindsense", "percezione cieca"),
    ("wings", "ali"),

    # Duelist
    ("enhanced mobility", "mobilità migliorata"),
    ("acrobatic charge", "carica acrobatica"),
    ("elaborate parry", "parata elaborata"),
    ("deflect arrows", "deviare frecce"),
    ("canny defense", "difesa astuta"),
    ("precise strike", "colpo preciso"),

    # Dwarven Defender
    ("defensive awareness", "consapevolezza difensiva"),
    ("defensive stance", "posizione difensiva"),
    ("mobile defense", "difesa mobile"),

    # Shadowdancer
    ("shadow illusion", "illusione d'ombra"),
    ("defensive roll", "capriola difensiva"),
    ("summon shadow", "evocare ombra"),
    ("slippery mind", "mente sfuggente"),
    ("darkvision", "scurovisione"),

    # Horizon Walker
    ("terrain mastery", "maestria del terreno"),

    # Archmage
    ("high arcana", "alta magia"),

    # Loremaster
    ("greater lore", "sapere superiore"),
    ("true lore", "sapere autentico"),

    # Thaumaturgist
    ("Augment Summoning", "Evocazione Potenziata"),
    ("contingent conjuration", "evocazione contingente"),
    ("extended summoning", "evocazione estesa"),
    ("planar cohort", "seguace planare"),

    # Generic (applica per ultimo)
    ("improved evasion", "evasione migliorata"),
    ("evasion", "evasione"),
    ("Track", "Seguire Tracce"),
    ("Endurance", "Resistenza Fisica"),
    ("Damage reduction", "Riduzione del danno"),
]

# Pre-compila regex con word boundary per ogni abilità
ABILITY_REGEXES = []
for en, it in ABILITY_TRANSLATIONS:
    # Escape per regex, poi aggiungi word boundaries
    pattern = re.compile(r'\b' + re.escape(en) + r'\b', re.IGNORECASE)
    ABILITY_REGEXES.append((pattern, en, it))

# ── Titoli tabelle ──────────────────────────────────────────────────────

TABLE_TITLES = {
    "Table: The Adept": "Tabella: L'Adepto",
    "Table: The Arcane Archer": "Tabella: L'Arciere Arcano",
    "Table: The Arcane Trickster": "Tabella: L'Imbroglione Arcano",
    "Table: The Archmage": "Tabella: L'Arcimago",
    "Table: The Aristocrat": "Tabella: L'Aristocratico",
    "Table: The Assassin": "Tabella: L'Assassino",
    "Table: The Barbarian": "Tabella: Il Barbaro",
    "Table: The Bard": "Tabella: Il Bardo",
    "Table: The Blackguard": "Tabella: Il Cavaliere Oscuro",
    "Table: The Cleric": "Tabella: Il Chierico",
    "Table: The Commoner": "Tabella: Il Popolano",
    "Table: The Dragon Disciple": "Tabella: Il Discepolo del Drago",
    "Table: The Druid": "Tabella: Il Druido",
    "Table: The Duelist": "Tabella: Il Duellante",
    "Table: The Dwarven Defender": "Tabella: Il Difensore Nanico",
    "Table: The Eldritch Knight": "Tabella: Il Cavaliere Mistico",
    "Table: The Expert": "Tabella: L'Esperto",
    "Table: The Fighter": "Tabella: Il Guerriero",
    "Table: The Hierophant": "Tabella: Lo Ierofante",
    "Table: The Horizon Walker": "Tabella: Il Camminatore dell'Orizzonte",
    "Table: The Loremaster": "Tabella: Il Maestro del Sapere",
    "Table: The Monk": "Tabella: Il Monaco",
    "Table: The Mystic Theurge": "Tabella: Il Teurgo Mistico",
    "Table: The Paladin": "Tabella: Il Paladino",
    "Table: The Ranger": "Tabella: Il Ranger",
    "Table: The Rogue": "Tabella: Il Ladro",
    "Table: The Shadowdancer": "Tabella: Il Danzatore d'Ombre",
    "Table: The Sorcerer": "Tabella: Lo Stregone",
    "Table: The Thaumaturgist": "Tabella: Il Taumaturgo",
    "Table: The Warrior": "Tabella: Il Guerriero (PNG)",
    "Table: The Wizard": "Tabella: Il Mago",
}


def translate_headers(html):
    """Translate column headers inside <th> tags, handling 'Special' and 'Level' safely."""
    def replace_th(m):
        content = m.group(1)
        attrs = m.group(0).split('>')[0] + '>'
        # Apply safe replacements first
        for en, it in HEADER_REPLACEMENTS:
            content = content.replace(en, it)
        # "Special" → "Speciale" solo se è l'intero contenuto del <th>
        if content.strip() == "Special":
            content = content.replace("Special", "Speciale")
        # "Level" → "Livello" solo se è l'intero contenuto o "Level" standalone
        if content.strip() == "Level":
            content = content.replace("Level", "Livello")
        return attrs + content + '</th>'

    return re.sub(r'<th[^>]*>(.*?)</th>', replace_th, html, flags=re.DOTALL)


def translate_table_html(html):
    """Apply all translations to a class table_html."""
    if not html:
        return html

    # 1. Table titles
    for en, it in TABLE_TITLES.items():
        html = html.replace(en, it)

    # 2. Header replacements (inside <th> only)
    html = translate_headers(html)

    # 3. Cell patterns (regex)
    for pattern, replacement in CELL_PATTERNS:
        html = re.sub(pattern, replacement, html, flags=re.IGNORECASE)

    # 4. Ability translations (word boundary regex, longest first)
    for pattern, en, it in ABILITY_REGEXES:
        def make_replacer(original_en, translation):
            def replacer(m):
                matched = m.group(0)
                # Preserva la capitalizzazione del primo carattere
                if matched[0].isupper() and translation[0].islower():
                    return translation[0].upper() + translation[1:]
                elif matched[0].islower() and translation[0].isupper():
                    return translation[0].lower() + translation[1:]
                return translation
            return replacer
        html = pattern.sub(make_replacer(en, it), html)

    # 5. Capitalizza la prima lettera in ogni cella <td>
    def capitalize_td(m):
        prefix = m.group(1)  # <td ...>
        content = m.group(2)
        if content and content[0].islower():
            content = content[0].upper() + content[1:]
        return prefix + content
    html = re.sub(r'(<td[^>]*>)([^<])', capitalize_td, html)

    return html


def main():
    parser = argparse.ArgumentParser(description="Traduci table_html delle classi")
    parser.add_argument("--apply", action="store_true", help="Applica le modifiche")
    args = parser.parse_args()

    overlay = json.load(open(OVERLAY_PATH, encoding="utf-8"))
    en_data = json.load(open(EN_PATH, encoding="utf-8"))
    en_map = {c["slug"]: c for c in en_data}

    changes = 0
    for entry in overlay:
        slug = entry["slug"]

        # Se non c'è table_html nell'overlay, copialo dall'EN
        if "table_html" not in entry:
            en_table = en_map.get(slug, {}).get("table_html")
            if en_table:
                entry["table_html"] = en_table

        old_html = entry.get("table_html", "")
        if not old_html:
            continue

        new_html = translate_table_html(old_html)

        if new_html != old_html:
            changes += 1
            print(f"\n{'='*60}")
            print(f"  {slug}")
            print(f"{'='*60}")

            # Show diffs (simplified)
            old_lines = old_html.split("\n")
            new_lines = new_html.split("\n")
            for i, (ol, nl) in enumerate(zip(old_lines, new_lines)):
                if ol != nl:
                    print(f"  - {ol.strip()[:100]}")
                    print(f"  + {nl.strip()[:100]}")

            entry["table_html"] = new_html

    print(f"\n{'='*60}")
    print(f"  Totale classi modificate: {changes}")
    print(f"{'='*60}")

    if args.apply and changes > 0:
        with open(OVERLAY_PATH, "w", encoding="utf-8") as f:
            json.dump(overlay, f, ensure_ascii=False, indent=2)
        print(f"\n  Salvato: {OVERLAY_PATH}")
    elif changes > 0:
        print("\n  Usa --apply per salvare le modifiche")


if __name__ == "__main__":
    main()
