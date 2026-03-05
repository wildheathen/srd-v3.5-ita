#!/usr/bin/env python3
"""
Translate desc_html fields for rules, monsters, and spells into Italian.
Uses formulaic replacements for structural elements and common D&D terminology.

Reuses maps from translate_class_descriptions.py and adds category-specific maps.

Usage:
    python scripts/translate_all_desc_html.py              # all categories
    python scripts/translate_all_desc_html.py rules         # only rules
    python scripts/translate_all_desc_html.py monsters      # only monsters
    python scripts/translate_all_desc_html.py spells        # only spells
"""

import json
import os
import re
import sys

# Import shared maps from class descriptions script
from translate_class_descriptions import (
    TABLE_HEADER_MAP,
    LABEL_MAP,
    SKILL_MAP,
    ABILITY_ABBR_MAP,
    TERM_MAP,
    FEATURE_MAP,
)

# ── Rules-specific section headers ──────────────────────────────────────

RULES_SECTION_MAP = {
    # Ability scores
    "Ability Scores": "Punteggi di Caratteristica",
    "Ability Modifiers": "Modificatori di Caratteristica",
    "Abilities and Spellcasters": "Caratteristiche e Incantatori",
    "The Abilities": "Le Caratteristiche",
    "Strength (Str)": "Forza (For)",
    "Dexterity (Dex)": "Destrezza (Des)",
    "Constitution (Con)": "Costituzione (Cos)",
    "Intelligence (Int)": "Intelligenza (Int)",
    "Wisdom (Wis)": "Saggezza (Sag)",
    "Charisma (Cha)": "Carisma (Car)",
    # Alignment
    "Alignment": "Allineamento",
    "Good vs. Evil": "Bene contro Male",
    "Law vs. Chaos": "Legge contro Caos",
    "The Nine Alignments": "I Nove Allineamenti",
    # Combat
    "How Combat Works": "Come Funziona il Combattimento",
    "Combat Statistics": "Statistiche di Combattimento",
    "Attack Roll": "Tiro per Colpire",
    "Attack Bonus": "Bonus di Attacco",
    "Damage": "Danno",
    "Armor Class": "Classe Armatura",
    "Hit Points": "Punti Ferita",
    "Speed": "Velocità",
    "Saving Throws": "Tiri Salvezza",
    "Initiative": "Iniziativa",
    "Actions in Combat": "Azioni in Combattimento",
    "The Combat Round": "Il Round di Combattimento",
    "Standard Actions": "Azioni Standard",
    "Move Actions": "Azioni di Movimento",
    "Full-Round Actions": "Azioni di Round Completo",
    "Free Actions": "Azioni Gratuite",
    "Miscellaneous Actions": "Azioni Varie",
    "Attack of Opportunity": "Attacco di Opportunità",
    "Attacks of Opportunity": "Attacchi di Opportunità",
    # Movement
    "Carrying Capacity": "Capacità di Carico",
    "Movement": "Movimento",
    "Local Movement": "Movimento Locale",
    "Overland Movement": "Movimento su Lunghe Distanze",
    "Evasion and Pursuit": "Evasione e Inseguimento",
    "Moving Around in Squares": "Muoversi sui Quadretti",
    "Exploration": "Esplorazione",
    "Vision and Light": "Visione e Luce",
    "Breaking and Entering": "Scassinare ed Entrare",
    "Tactical Movement": "Movimento Tattico",
    "Moving in Three Dimensions": "Muoversi in Tre Dimensioni",
    # Dice
    "Dice": "Dadi",
    "Rounding Fractions": "Arrotondare le Frazioni",
    "Multiplying": "Moltiplicare",
    # Vital statistics
    "Vital Statistics": "Statistiche Vitali",
    "Age": "Età",
    "Height and Weight": "Altezza e Peso",
    # Skills
    "Skill Checks": "Prove di Abilità",
    "Skill Ranks": "Gradi nelle Abilità",
    "Using Skills": "Usare le Abilità",
    "Ability Checks": "Prove di Caratteristica",
    # Special abilities
    "Special Abilities": "Capacità Speciali",
    "Spell-Like Abilities": "Capacità Magiche",
    "Supernatural Abilities": "Capacità Soprannaturali",
    "Extraordinary Abilities": "Capacità Straordinarie",
    "Natural Abilities": "Capacità Naturali",
    # Conditions
    "Conditions": "Condizioni",
    "Blinded": "Accecato",
    "Confused": "Confuso",
    "Cowering": "Atterrito",
    "Dazed": "Frastornato",
    "Dazzled": "Abbagliato",
    "Deafened": "Assordato",
    "Disabled": "Inabile",
    "Dying": "Morente",
    "Energy Drained": "Risucchiato d'Energia",
    "Entangled": "Intralciato",
    "Exhausted": "Esausto",
    "Fascinated": "Affascinato",
    "Fatigued": "Affaticato",
    "Flat-Footed": "Colto alla Sprovvista",
    "Frightened": "Spaventato",
    "Grappling": "In Lotta",
    "Helpless": "Indifeso",
    "Incorporeal": "Incorporeo",
    "Invisible": "Invisibile",
    "Knocked Down": "Atterrato",
    "Nauseated": "Nauseato",
    "Panicked": "In Preda al Panico",
    "Paralyzed": "Paralizzato",
    "Petrified": "Pietrificato",
    "Pinned": "Immobilizzato",
    "Prone": "Prono",
    "Shaken": "Scosso",
    "Sickened": "Infermo",
    "Stable": "Stabile",
    "Staggered": "Barcollante",
    "Stunned": "Stordito",
    "Turned": "Scacciato",
    "Unconscious": "Privo di Sensi",
    # Special materials
    "Special Materials": "Materiali Speciali",
    "Adamantine": "Adamantio",
    "Darkwood": "Legno Scuro",
    "Dragonhide": "Pelle di Drago",
    "Iron, Cold": "Ferro Freddo",
    "Mithral": "Mithral",
    "Silver, Alchemical": "Argento Alchemico",
    # Treasure
    "Treasure": "Tesori",
    "Treasure Values per Encounter": "Valori del Tesoro per Incontro",
    # Environment / Nature
    "Forest Terrain": "Terreno Boschivo",
    "Marsh Terrain": "Terreno Paludoso",
    "Hills Terrain": "Terreno Collinare",
    "Mountain Terrain": "Terreno Montuoso",
    "Desert Terrain": "Terreno Desertico",
    "Plains Terrain": "Terreno Pianeggiante",
    "Aquatic Terrain": "Terreno Acquatico",
    "Underground": "Sotterraneo",
    "Urban Adventures": "Avventure Urbane",
    "Weather": "Clima",
    "The Environment": "L'Ambiente",
    # Traps
    "Traps": "Trappole",
    "Mechanical Traps": "Trappole Meccaniche",
    "Magic Traps": "Trappole Magiche",
    "Elements of a Trap": "Elementi di una Trappola",
    "Designing a Trap": "Progettare una Trappola",
    "Sample Traps": "Trappole di Esempio",
    # Planes
    "The Planes": "I Piani",
    "The Material Plane": "Il Piano Materiale",
    "The Ethereal Plane": "Il Piano Etereo",
    "The Plane of Shadow": "Il Piano delle Ombre",
    "The Astral Plane": "Il Piano Astrale",
    "The Outer Planes": "I Piani Esterni",
    "The Inner Planes": "I Piani Interni",
    # Magic items
    "Magic Items": "Oggetti Magici",
    "Intelligent Items": "Oggetti Intelligenti",
    "Cursed Items": "Oggetti Maledetti",
    "Artifacts": "Artefatti",
    "Magic Armor": "Armature Magiche",
    "Magic Weapons": "Armi Magiche",
    "Potions": "Pozioni",
    "Rings": "Anelli",
    "Rods": "Verghe",
    "Scrolls": "Pergamene",
    "Staffs": "Bastoni",
    "Wands": "Bacchette",
    "Wondrous Items": "Oggetti Meravigliosi",
    "Using Items": "Usare Oggetti",
    "Size and Magic Items": "Taglia e Oggetti Magici",
    "Magic Items and Detect Magic": "Oggetti Magici e Individuazione del Magico",
    "Creating Magic Items": "Creare Oggetti Magici",
    "Magic Item Descriptions": "Descrizioni degli Oggetti Magici",
    # Grapple
    "Grapple": "Lotta",
    "Grapple Checks": "Prove di Lotta",
    # Two-weapon fighting etc.
    "Two-Weapon Fighting": "Combattere con Due Armi",
    "Special Attacks": "Attacchi Speciali",
    "Special Initiative Actions": "Azioni Speciali di Iniziativa",
    "Combat Modifiers": "Modificatori di Combattimento",
    "Cover": "Copertura",
    "Concealment": "Occultamento",
    "Flanking": "Attacco ai Fianchi",
    "Mounted Combat": "Combattimento in Sella",
}

# ── Rules-specific bold labels ──────────────────────────────────────────

RULES_LABEL_MAP = {
    "Action:": "Azione:",
    "Check:": "Prova:",
    "Special:": "Speciale:",
    "Try Again:": "Riprovare:",
    "Synergy:": "Sinergia:",
    "Untrained:": "Senza Addestramento:",
    "Restriction:": "Restrizione:",
    "Activation:": "Attivazione:",
    "Physical Description:": "Descrizione Fisica:",
    "Aura:": "Aura:",
    "Caster Level:": "Livello dell'Incantatore:",
    "Prerequisites:": "Prerequisiti:",
    "Market Price:": "Prezzo di Mercato:",
    "Cost to Create:": "Costo di Creazione:",
    "Cost:": "Costo:",
    "Weight:": "Peso:",
    "Trigger:": "Innesco:",
    "Reset:": "Ripristino:",
    "Effect:": "Effetto:",
    "Duration:": "Durata:",
    "Search DC:": "CD Cercare:",
    "Disable Device DC:": "CD Disattivare Congegni:",
    "Note:": "Nota:",
    "Size:": "Taglia:",
    "Speed:": "Velocità:",
    "Walk:": "Camminare:",
    "Hustle:": "Passo di Marcia:",
    "Run:": "Correre:",
    "Craft DC:": "CD Artigianato:",
    "Step 1:": "Passo 1:",
    "Step 2:": "Passo 2:",
    "Step 3:": "Passo 3:",
    "Step 4:": "Passo 4:",
    "Step 5:": "Passo 5:",
}

# ── Monster-specific labels ─────────────────────────────────────────────

MONSTER_SECTION_MAP = {
    "Combat": "Combattimento",
    "Subraces": "Sottorazze",
    "Creating a Lycanthrope": "Creare un Licantropo",
    "Lycanthropy as an Affliction": "Licantropia come Afflizione",
    "Lycanthropes as Characters": "Licantropi come Personaggi",
    "Society": "Società",
    "Training": "Addestramento",
}

MONSTER_LABEL_MAP = {
    "Skills:": "Abilità:",
    "Feats:": "Talenti:",
    "Environment:": "Ambiente:",
    "Organization:": "Organizzazione:",
    "Challenge Rating:": "Grado di Sfida:",
    "Treasure:": "Tesoro:",
    "Alignment:": "Allineamento:",
    "Advancement:": "Avanzamento:",
    "Level Adjustment:": "Modificatore di Livello:",
    "Abilities:": "Caratteristiche:",
    "Special Qualities:": "Qualità Speciali:",
    "Special Attacks:": "Attacchi Speciali:",
    "Carrying Capacity:": "Capacità di Carico:",
    "Spell-Like Abilities:": "Capacità Magiche:",
    "Spells:": "Incantesimi:",
    "Alternate Form (Su):": "Forma Alternativa (Sop):",
    "Improved Grab (Ex):": "Presa Migliorata (Str):",
    "Poison (Ex):": "Veleno (Str):",
    "Breath Weapon (Su):": "Arma del Soffio (Sop):",
    "Constrict (Ex):": "Stritolare (Str):",
    "Rake (Ex):": "Artigliata (Str):",
    "Pounce (Ex):": "Balzo (Str):",
    "Trip (Ex):": "Sbilanciare (Str):",
    "Fast Healing (Ex):": "Guarigione Rapida (Str):",
    "Regeneration (Ex):": "Rigenerazione (Str):",
    "Create Spawn (Su):": "Creare Progenie (Sop):",
    "Trample (Ex):": "Travolgere (Str):",
    "Ferocity (Ex):": "Ferocia (Str):",
    "Change Shape (Su):": "Cambiare Forma (Sop):",
    "Damage Reduction (Su):": "Riduzione del Danno (Sop):",
    "Damage Reduction (Ex):": "Riduzione del Danno (Str):",
    "Energy Drain (Su):": "Risucchio d'Energia (Sop):",
    "Fear Aura (Su):": "Aura di Paura (Sop):",
    "Frightful Presence (Ex):": "Presenza Terrificante (Str):",
    "Spell Resistance (Ex):": "Resistenza agli Incantesimi (Str):",
    "Swallow Whole (Ex):": "Inghiottire (Str):",
    "Web (Ex):": "Ragnatela (Str):",
    "Gaze (Su):": "Sguardo (Sop):",
    "Curse of Lycanthropy (Su):": "Maledizione della Licantropia (Sop):",
    "Control Shape (Wis):": "Controllare Forma (Sag):",
}

# ── Spell-specific labels ───────────────────────────────────────────────

SPELL_LABEL_MAP = {
    "Material Component:": "Componente Materiale:",
    "Arcane Material Component:": "Componente Materiale Arcano:",
    "Material Components:": "Componenti Materiali:",
    "Focus:": "Focus:",
    "Arcane Focus:": "Focus Arcano:",
    "Divine Focus:": "Focus Divino:",
    "XP Cost:": "Costo in PE:",
    "Component:": "Componente:",
    "Components:": "Componenti:",
}

# ── Ability type abbreviation translations ──────────────────────────────

ABILITY_TYPE_MAP = {
    "(Ex)": "(Str)",
    "(Su)": "(Sop)",
    "(Sp)": "(Mag)",
}

# ── Common D&D terms for rules/monsters/spells ─────────────────────────

EXTRA_TERM_MAP = {
    # Attack types
    "ranged touch attack": "attacco di contatto a distanza",
    "melee touch attack": "attacco di contatto in mischia",
    "touch attack": "attacco di contatto",
    "ranged attack": "attacco a distanza",
    "melee attack": "attacco in mischia",
    "full attack": "attacco completo",
    "unarmed attack": "attacco senz'armi",
    "unarmed strike": "colpo senz'armi",
    # Creature types
    "Aberration": "Aberrazione",
    "Animal": "Animale",
    "Construct": "Costrutto",
    "Dragon": "Drago",
    "Elemental": "Elementale",
    "Fey": "Folletto",
    "Giant": "Gigante",
    "Humanoid": "Umanoide",
    "Magical Beast": "Bestia Magica",
    "Monstrous Humanoid": "Umanoide Mostruoso",
    "Ooze": "Melma",
    "Outsider": "Esterno",
    "Plant": "Pianta",
    "Undead": "Non Morto",
    "Vermin": "Parassita",
    # Sizes
    "Colossal": "Colossale",
    "Gargantuan": "Mastodontico",
    "Huge": "Enorme",
    "Large": "Grande",
    "Medium": "Medio",
    "Small": "Piccolo",
    "Tiny": "Minuscolo",
    "Diminutive": "Minuto",
    "Fine": "Piccolissimo",
    # Combat terms
    "natural armor": "armatura naturale",
    "natural weapon": "arma naturale",
    "natural weapons": "armi naturali",
    "grapple check": "prova di lotta",
    "grapple checks": "prove di lotta",
    "initiative check": "prova di iniziativa",
    "opposed check": "prova contrapposta",
    "ability check": "prova di caratteristica",
    "skill check": "prova di abilità",
    "skill checks": "prove di abilità",
    "level check": "prova di livello",
    "dispel check": "prova di dissoluzione",
    "concentration check": "prova di Concentrazione",
    # Status
    "flat-footed": "colto alla sprovvista",
    "helpless": "indifeso",
    "prone": "prono",
    "grappled": "in lotta",
    "pinned": "immobilizzato",
    "stunned": "stordito",
    "paralyzed": "paralizzato",
    "blinded": "accecato",
    "deafened": "assordato",
    "invisible": "invisibile",
    "incorporeal": "incorporeo",
    # Damage types
    "bludgeoning": "contundente",
    "piercing": "perforante",
    "slashing": "tagliente",
    "nonlethal damage": "danno non letale",
    "lethal damage": "danno letale",
    "subdual damage": "danno debilitante",
    "acid damage": "danni da acido",
    "fire damage": "danni da fuoco",
    "cold damage": "danni da freddo",
    "electricity damage": "danni da elettricità",
    "sonic damage": "danni da suono",
    # Magic
    "spell-like ability": "capacità magica",
    "spell-like abilities": "capacità magiche",
    "supernatural ability": "capacità soprannaturale",
    "supernatural abilities": "capacità soprannaturali",
    "extraordinary ability": "capacità straordinaria",
    "extraordinary abilities": "capacità straordinarie",
    "caster level": "livello dell'incantatore",
    "spell level": "livello dell'incantesimo",
    "DC ": "CD ",
    # Common phrases
    "per day": "al giorno",
    "per round": "per round",
    "once per day": "una volta al giorno",
    "twice per day": "due volte al giorno",
    "three times per day": "tre volte al giorno",
    "at will": "a volontà",
    "at-will": "a volontà",
    "line of sight": "linea di vista",
    "line of effect": "linea di effetto",
    "space/reach": "spazio/portata",
    "reach weapon": "arma con portata",
}

# ── Magic item specific labels ──────────────────────────────────────────

MAGIC_ITEM_LABEL_MAP = {
    "Aura:": "Aura:",
    "Caster Level:": "Livello dell'Incantatore:",
    "Activation:": "Attivazione:",
    "Prerequisites:": "Prerequisiti:",
    "Market Price:": "Prezzo di Mercato:",
    "Cost to Create:": "Costo di Creazione:",
    "Weight:": "Peso:",
    "Construction:": "Costruzione:",
    "Slot:": "Slot:",
}

# ── Schools of magic ────────────────────────────────────────────────────

SCHOOL_MAP = {
    "Abjuration": "Abiurazione",
    "Conjuration": "Evocazione",
    "Divination": "Divinazione",
    "Enchantment": "Ammaliamento",
    "Evocation": "Invocazione",
    "Illusion": "Illusione",
    "Necromancy": "Necromanzia",
    "Transmutation": "Trasmutazione",
    "Universal": "Universale",
}


def translate_generic_desc_html(html, extra_label_map=None, extra_section_map=None):
    """Apply formulaic translations to desc_html for any category."""
    if not html:
        return None

    result = html

    # 1. Table headers
    for en, it in sorted(TABLE_HEADER_MAP.items(), key=lambda x: -len(x[0])):
        result = result.replace(f"<th>{en}</th>", f"<th>{it}</th>")

    # 2. Section headers (h2/h3/h4)
    all_sections = dict(RULES_SECTION_MAP)
    if extra_section_map:
        all_sections.update(extra_section_map)
    for en, it in sorted(all_sections.items(), key=lambda x: -len(x[0])):
        result = re.sub(
            rf'(<h[2-6][^>]*>)\s*{re.escape(en)}\s*(</h[2-6]>)',
            rf'\1{it}\2',
            result
        )

    # 3. Strong/bold labels (combine all label maps)
    all_labels = dict(LABEL_MAP)
    all_labels.update(RULES_LABEL_MAP)
    if extra_label_map:
        all_labels.update(extra_label_map)
    for en, it in sorted(all_labels.items(), key=lambda x: -len(x[0])):
        result = result.replace(f"<strong>{en}</strong>", f"<strong>{it}</strong>")

    # 3b. Italic labels (for spells: <em>Material Component:</em>)
    for en, it in sorted(all_labels.items(), key=lambda x: -len(x[0])):
        result = result.replace(f"<em>{en}</em>", f"<em>{it}</em>")
        result = result.replace(f"<i>{en}</i>", f"<i>{it}</i>")

    # 4. Ability type abbreviations (Ex) → (Str), (Su) → (Sop), (Sp) → (Mag)
    for en, it in ABILITY_TYPE_MAP.items():
        result = result.replace(en, it)

    # 5. Ability abbreviations (Str) → (For), etc.
    for en, it in ABILITY_ABBR_MAP.items():
        result = result.replace(en, it)

    # 6. Skill names in context
    for en, it in sorted(SKILL_MAP.items(), key=lambda x: -len(x[0])):
        result = result.replace(f"{en} check", f"prova di {it}")
        result = result.replace(f"{en} checks", f"prove di {it}")
        result = result.replace(f"{en} skill", f"abilità {it}")
        result = result.replace(f"{en} (", f"{it} (")

    # 7. Schools of magic
    for en, it in sorted(SCHOOL_MAP.items(), key=lambda x: -len(x[0])):
        result = result.replace(f"<strong>{en}</strong>", f"<strong>{it}</strong>")

    # 8. Feature names (class features that appear in other contexts)
    for en, it in sorted(FEATURE_MAP.items(), key=lambda x: -len(x[0])):
        result = result.replace(f">{en}<", f">{it}<")

    # 9. Common terms (combined, longer first)
    all_terms = dict(TERM_MAP)
    all_terms.update(EXTRA_TERM_MAP)
    for en, it in sorted(all_terms.items(), key=lambda x: -len(x[0])):
        result = result.replace(en, it)

    return result if result != html else None


def translate_category(category, extra_label_map=None, extra_section_map=None):
    """Translate desc_html for a given category."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(os.path.dirname(script_dir), "data")

    base_path = os.path.join(data_dir, f"{category}.json")
    overlay_path = os.path.join(data_dir, "i18n", "it", f"{category}.json")

    if not os.path.exists(base_path):
        print(f"{category}.json not found")
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

    added = 0
    skipped = 0
    for item in base:
        slug = item.get("slug")
        if not slug:
            continue

        if slug not in overlay_map:
            overlay_map[slug] = {"slug": slug}

        entry = overlay_map[slug]

        # Only translate if not already present
        if "desc_html" not in entry:
            translated = translate_generic_desc_html(
                item.get("desc_html"),
                extra_label_map=extra_label_map,
                extra_section_map=extra_section_map,
            )
            if translated:
                entry["desc_html"] = translated
                added += 1
            else:
                skipped += 1

    result = sorted(overlay_map.values(), key=lambda x: x.get("slug", ""))
    os.makedirs(os.path.dirname(overlay_path), exist_ok=True)
    with open(overlay_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print(f"{category}: {added} desc_html translations added ({skipped} unchanged)")


def main():
    categories = sys.argv[1:] if len(sys.argv) > 1 else ["rules", "monsters", "spells"]

    for cat in categories:
        if cat == "rules":
            translate_category("rules", RULES_LABEL_MAP, RULES_SECTION_MAP)
        elif cat == "monsters":
            translate_category("monsters", MONSTER_LABEL_MAP, MONSTER_SECTION_MAP)
        elif cat == "spells":
            translate_category("spells", SPELL_LABEL_MAP)
        else:
            print(f"Unknown category: {cat}")


if __name__ == "__main__":
    main()
