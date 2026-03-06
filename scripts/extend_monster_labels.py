#!/usr/bin/env python3
"""Estende le traduzioni strutturali dei mostri con nuove label di abilita.

Aggiunge traduzioni per ~150+ label di abilita dei mostri nel desc_html
che non erano coperte dalla mappa originale in translate_all_desc_html.py.

Usage:
    python scripts/extend_monster_labels.py          # dry-run
    python scripts/extend_monster_labels.py --apply   # scrive nell'overlay
"""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EN_PATH = ROOT / "data" / "monsters.json"
IT_PATH = ROOT / "data" / "i18n" / "it" / "monsters.json"

# ── Extended monster ability labels ────────────────────────────────────

# Ability type translations
ABILITY_TYPE = {
    "(Ex)": "(Str)",
    "(Su)": "(Sop)",
    "(Sp)": "(Mag)",
}

# Common monster abilities not yet in translate_all_desc_html.py
EXTENDED_LABELS = {
    # Senses
    "Blindsense (Ex):": "Percezione Cieca (Str):",
    "Blindsight (Ex):": "Vista Cieca (Str):",
    "All-Around Vision (Ex):": "Visione a 360° (Str):",
    "True Seeing (Su):": "Vedere il Vero (Sop):",
    "Darkvision (Ex):": "Scurovisione (Str):",
    "Low-Light Vision (Ex):": "Visione Crepuscolare (Str):",
    "Keen Scent (Ex):": "Fiuto Acuto (Str):",
    "Scent (Ex):": "Fiuto (Str):",
    "Tremorsense (Ex):": "Percezione Tellurica (Str):",

    # Combat abilities
    "Rend (Ex):": "Dilaniare (Str):",
    "Smite Evil (Su):": "Punire il Male (Sop):",
    "Rage (Ex):": "Ira (Str):",
    "Stunning Fist (Ex):": "Pugno Stordente (Str):",
    "Blood Drain (Ex):": "Risucchio di Sangue (Str):",
    "Engulf (Ex):": "Inghiottire (Str):",
    "Rock Throwing (Ex):": "Scagliare Rocce (Str):",
    "Rock Catching (Ex):": "Afferrare Rocce (Str):",
    "Whirlwind (Su):": "Turbine (Sop):",
    "Augmented Critical (Ex):": "Critico Aumentato (Str):",
    "Powerful Charge (Ex):": "Carica Poderosa (Str):",

    # Defensive abilities
    "Damage Reduction:": "Riduzione del Danno:",
    "Spell Resistance:": "Resistenza agli Incantesimi:",
    "Immunity to Magic (Ex):": "Immunità alla Magia (Str):",
    "Evasion (Ex):": "Evasione (Str):",
    "Improved Evasion (Ex):": "Evasione Migliorata (Str):",
    "Uncanny Dodge (Ex):": "Schivare Prodigioso (Str):",
    "Improved Uncanny Dodge (Ex):": "Schivare Prodigioso Migliorato (Str):",

    # Special movement
    "Earth Glide (Ex):": "Scivolare nella Terra (Str):",
    "Jet (Ex):": "Propulsione (Str):",
    "Water Breathing (Ex):": "Respirare sott'Acqua (Str):",
    "Amphibious (Ex):": "Anfibio (Str):",
    "Air Mastery (Ex):": "Padronanza dell'Aria (Str):",
    "Earth Mastery (Ex):": "Padronanza della Terra (Str):",
    "Water Mastery (Ex):": "Padronanza dell'Acqua (Str):",
    "Fire Mastery (Ex):": "Padronanza del Fuoco (Str):",

    # Supernatural abilities
    "Energy Drain (Su):": "Risucchio d'Energia (Sop):",
    "Ethereal Jaunt (Su):": "Viaggio Etereo (Sop):",
    "Aura of Menace (Su):": "Aura di Minaccia (Sop):",
    "Ghoul Fever (Su):": "Febbre del Ghoul (Sop):",
    "Mummy Rot (Su):": "Putredine della Mummia (Sop):",
    "Burn (Ex):": "Bruciare (Str):",

    # Natural abilities
    "Disease (Ex):": "Malattia (Str):",
    "Paralysis (Ex):": "Paralisi (Str):",
    "Heat (Ex):": "Calore (Str):",
    "Acid (Ex):": "Acido (Str):",
    "Ink Cloud (Ex):": "Nube d'Inchiostro (Str):",
    "Distraction (Ex):": "Distrazione (Str):",
    "Hive Mind (Ex):": "Mente Alveare (Str):",

    # Empathy
    "Wild Empathy (Ex):": "Empatia Selvatica (Str):",
    "Boar Empathy (Ex):": "Empatia con i Cinghiali (Str):",
    "Wolf Empathy (Ex):": "Empatia con i Lupi (Str):",
    "Rat Empathy (Ex):": "Empatia con i Ratti (Str):",
    "Bear Empathy (Ex):": "Empatia con gli Orsi (Str):",
    "Tiger Empathy (Ex):": "Empatia con le Tigri (Str):",

    # Form changes
    "Alternate Form (Su):": "Forma Alternativa (Sop):",
    "Change Shape (Su):": "Cambiare Forma (Sop):",
    "Lycanthropic Empathy (Ex):": "Empatia Licantropica (Str):",

    # Gaze attacks
    "Gaze (Su):": "Sguardo (Sop):",
    "Petrifying Gaze (Su):": "Sguardo Pietrificante (Sop):",

    # Spell-like
    "Spell-Like Abilities:": "Capacità Magiche:",
    "Spell-Like Abilities (Sp):": "Capacità Magiche (Mag):",
    "Other Spell-Like Abilities:": "Altre Capacità Magiche:",
    "Psionics (Sp):": "Psionici (Mag):",
    "Psionics (Su):": "Psionici (Sop):",
    "Telepathy (Su):": "Telepatia (Sop):",

    # Stat block labels (used in some monster pages)
    "Size and Type:": "Taglia e Tipo:",
    "Armor Class:": "Classe Armatura:",
    "Attacks:": "Attacchi:",
    "Damage:": "Danno:",
    "Speed:": "Velocità:",
    "Challenge Ratings:": "Gradi di Sfida:",
    "Hit Dice:": "Dadi Vita:",
    "Hit Dice and Hit Points:": "Dadi Vita e Punti Ferita:",
    "Initiative:": "Iniziativa:",
    "Face/Reach:": "Spazio/Portata:",
    "Base Attack/Grapple:": "Attacco Base/Lotta:",
    "Full Attack:": "Attacco Completo:",
    "Attack:": "Attacco:",
    "Saves:": "Tiri Salvezza:",
    "Defensive Abilities:": "Capacità Difensive:",
    "DR:": "RD:",
    "SR:": "RI:",

    # Remaining specific abilities
    "Lay on Hands (Su):": "Imposizione delle Mani (Sop):",
    "Speak with Animals (Su):": "Parlare con gli Animali (Sop):",
    "Speak with Sharks (Ex):": "Parlare con gli Squali (Str):",
    "Vulnerability to Sunlight (Ex):": "Vulnerabilità alla Luce Solare (Str):",
    "Freedom of Movement (Su):": "Libertà di Movimento (Sop):",
    "Astral Projection and Etherealness (Su):": "Proiezione Astrale ed Eterealità (Sop):",
    "Immunity to Transformation (Ex):": "Immunità alla Trasformazione (Str):",
    "Dance of Ruin (Su):": "Danza della Rovina (Sop):",
    "Protection from Sonics (Ex):": "Protezione dai Suoni (Str):",
    "Invisible in Light (Ex):": "Invisibile nella Luce (Str):",
    "Aura of Despair (Su):": "Aura di Disperazione (Sop):",
    "Aura of Evil (Ex):": "Aura del Male (Str):",
    "Fists of Thunder and Lightning (Su):": "Pugni del Tuono e del Fulmine (Sop):",
    "Scare (Ex or Su):": "Spaventare (Str o Sop):",
    "Immunity to Electricity (Ex):": "Immunità all'Elettricità (Str):",
    "Sorcerers and Wizards:": "Stregoni e Maghi:",
}

# Section headings for monsters
EXTENDED_SECTIONS = {
    "Combat": "Combattimento",
    "Strategies and Tactics": "Strategie e Tattiche",
    "Sample Encounters": "Incontri Esempio",
    "Ecology": "Ecologia",
    "Typical Physical Characteristics": "Caratteristiche Fisiche Tipiche",
    "Alignment": "Allineamento",
    "Subraces": "Sottorazze",
}


def translate_monster_labels(desc_html):
    """Apply extended label translations to monster desc_html."""
    if not desc_html:
        return None, 0

    result = desc_html
    changes = 0

    # Build a lookup that handles already-translated ability types
    # The overlay may have (Str)/(Sop)/(Mag) instead of (Ex)/(Su)/(Sp)
    REVERSE_TYPE = {"(Str)": "(Ex)", "(Sop)": "(Su)", "(Mag)": "(Sp)"}
    expanded_labels = dict(EXTENDED_LABELS)
    for en_label, it_label in list(EXTENDED_LABELS.items()):
        # For each label, also create a version with IT ability types
        for it_type, en_type in REVERSE_TYPE.items():
            if en_type in en_label:
                it_key = en_label.replace(en_type, it_type)
                if it_key not in expanded_labels:
                    expanded_labels[it_key] = it_label

    # 1. Translate <strong>Label:</strong> patterns
    def translate_strong(m):
        nonlocal changes
        content = m.group(2)

        # Try exact match (handles both EN and IT ability type variants)
        if content in expanded_labels:
            changes += 1
            return f"{m.group(1)}{expanded_labels[content]}{m.group(3)}"

        return m.group(0)

    result = re.sub(r'(<strong>)(.*?)(</strong>)', translate_strong, result, flags=re.DOTALL)

    # 2. Translate section headings
    def translate_heading(m):
        nonlocal changes
        open_tag = m.group(1)
        content = m.group(2).strip()
        close_tag = m.group(3)

        if content in EXTENDED_SECTIONS:
            changes += 1
            return f"{open_tag}{EXTENDED_SECTIONS[content]}{close_tag}"
        return m.group(0)

    result = re.sub(r'(<h[2-6][^>]*>)\s*(.*?)\s*(</h[2-6]>)', translate_heading, result, flags=re.DOTALL)

    return result if result != desc_html else None, changes


def main():
    apply_mode = "--apply" in sys.argv

    with open(IT_PATH, encoding="utf-8") as f:
        monsters = json.load(f)

    total_changes = 0
    monsters_changed = 0

    for m in monsters:
        desc = m.get("desc_html", "")
        if not desc:
            continue

        new_desc, changes = translate_monster_labels(desc)
        if new_desc and changes > 0:
            if apply_mode:
                m["desc_html"] = new_desc
            total_changes += changes
            monsters_changed += 1

    print(f"\n{'='*60}")
    print(f"Mostri modificati: {monsters_changed}")
    print(f"Label tradotte: {total_changes}")

    if apply_mode:
        with open(IT_PATH, "w", encoding="utf-8") as f:
            json.dump(monsters, f, ensure_ascii=False, indent=2)
        print(f"\nScritto {IT_PATH}")
    else:
        print(f"\nDry-run. Usa --apply per scrivere le modifiche.")


if __name__ == "__main__":
    main()
