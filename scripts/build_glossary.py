#!/usr/bin/env python3
"""
Build a D&D 3.5 translation glossary (EN->IT) for Crowdin import.

Sources:
1. Existing validated translations from i18n overlays
2. UI strings from frontend/i18n/
3. Standard D&D 3.5 terminology with fixed Italian translations

Output: data/glossary_crowdin.csv (Crowdin glossary format)
Format: Term (EN), Translation (IT), Part of Speech, Description, Domain

Usage:
    python scripts/build_glossary.py
"""
import csv
import json
import os
import sys

sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = os.path.join(os.path.dirname(__file__), '..')
DATA_DIR = os.path.join(BASE_DIR, 'data')
I18N_DIR = os.path.join(DATA_DIR, 'i18n', 'it')
FRONTEND_I18N = os.path.join(BASE_DIR, 'frontend', 'i18n')
OUTPUT_PATH = os.path.join(DATA_DIR, 'glossary_crowdin.csv')


def load_json(path):
    if not os.path.exists(path):
        return None
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def add(glossary, en, it, pos='', desc='', domain=''):
    """Add a term to the glossary if both EN and IT are non-empty and different."""
    en = (en or '').strip()
    it = (it or '').strip()
    if not en or not it:
        return
    if en.lower() == it.lower():
        return
    key = en.lower()
    # Keep first occurrence (priority: validated > generated)
    if key not in glossary:
        glossary[key] = {
            'term_en': en,
            'translation_it': it,
            'pos': pos,
            'description': desc,
            'domain': domain,
        }


def main():
    glossary = {}  # key = en.lower(), value = dict

    # ════════════════════════════════════════════════════════════════════════
    # PART 1: Existing validated translations
    # ════════════════════════════════════════════════════════════════════════

    print('=== Part 1: Existing validated translations ===')

    # ── 1a. Ability scores ──────────────────────────────────────────────────
    ABILITIES = {
        'Strength': 'Forza', 'Dexterity': 'Destrezza', 'Constitution': 'Costituzione',
        'Intelligence': 'Intelligenza', 'Wisdom': 'Saggezza', 'Charisma': 'Carisma',
        'STR': 'FOR', 'DEX': 'DES', 'CON': 'COS', 'INT': 'INT', 'WIS': 'SAG', 'CHA': 'CAR',
    }
    for en, it in ABILITIES.items():
        add(glossary, en, it, 'noun', 'Ability score', 'Core Rules')

    # ── 1b. Schools of magic (from spell overlay) ───────────────────────────
    SCHOOLS = {
        'Abjuration': 'Abiurazione', 'Conjuration': 'Evocazione',
        'Divination': 'Divinazione', 'Enchantment': 'Ammaliamento',
        'Evocation': 'Invocazione', 'Illusion': 'Illusione',
        'Necromancy': 'Necromanzia', 'Transmutation': 'Trasmutazione',
        'Universal': 'Universale',
    }
    for en, it in SCHOOLS.items():
        add(glossary, en, it, 'noun', 'School of magic', 'Magic')

    # ── 1c. Subschools ──────────────────────────────────────────────────────
    SUBSCHOOLS = {
        'Calling': 'Richiamo', 'Creation': 'Creazione', 'Healing': 'Guarigione',
        'Summoning': 'Convocazione', 'Teleportation': 'Teletrasporto',
        'Charm': 'Charme', 'Compulsion': 'Compulsione',
        'Figment': 'Finzione', 'Glamer': 'Mascheramento', 'Pattern': 'Trama',
        'Phantasm': 'Fantasma', 'Shadow': 'Ombra',
        'Scrying': 'Scrutare',
    }
    for en, it in SUBSCHOOLS.items():
        add(glossary, en, it, 'noun', 'Subschool of magic', 'Magic')

    # ── 1d. Spell descriptors ───────────────────────────────────────────────
    DESCRIPTORS = {
        'Acid': 'Acido', 'Air': 'Aria', 'Chaotic': 'Caotico', 'Cold': 'Freddo',
        'Darkness': 'Oscurita', 'Death': 'Morte', 'Earth': 'Terra',
        'Electricity': 'Elettricita', 'Evil': 'Malvagio', 'Fear': 'Paura',
        'Fire': 'Fuoco', 'Force': 'Forza', 'Good': 'Buono', 'Language-Dependent': 'Extralinguistico',
        'Lawful': 'Legale', 'Light': 'Luce', 'Mind-Affecting': 'Influenza mentale',
        'Sonic': 'Sonoro', 'Water': 'Acqua',
    }
    for en, it in DESCRIPTORS.items():
        add(glossary, en, it, 'adj', 'Spell descriptor / energy type', 'Magic')

    # ── 1e. Creature types (from monster overlay) ───────────────────────────
    CREATURE_TYPES = {
        'Aberration': 'Aberrazione', 'Animal': 'Animale', 'Construct': 'Costrutto',
        'Dragon': 'Drago', 'Elemental': 'Elementale', 'Fey': 'Folletto',
        'Giant': 'Gigante', 'Humanoid': 'Umanoide', 'Magical Beast': 'Bestia Magica',
        'Monstrous Humanoid': 'Umanoide Mostruoso', 'Ooze': 'Melma',
        'Outsider': 'Esterno', 'Plant': 'Pianta', 'Undead': 'Non Morto',
        'Vermin': 'Parassita', 'Deathless': 'Non Morto Immortale',
        'Shapechanger': 'Mutaforma',
    }
    for en, it in CREATURE_TYPES.items():
        add(glossary, en, it, 'noun', 'Creature type', 'Monsters')

    # ── 1f. Creature subtypes ───────────────────────────────────────────────
    SUBTYPES = {
        'Aquatic': 'Acquatico', 'Augmented': 'Potenziato', 'Chaotic': 'Caotico',
        'Cold': 'Freddo', 'Earth': 'Terra', 'Evil': 'Malvagio',
        'Extraplanar': 'Extraplanare', 'Fire': 'Fuoco', 'Good': 'Buono',
        'Goblinoid': 'Goblinoide', 'Incorporeal': 'Incorporeo',
        'Lawful': 'Legale', 'Native': 'Nativo', 'Reptilian': 'Rettile',
        'Swarm': 'Sciame', 'Water': 'Acqua', 'Air': 'Aria',
        'Shapechanger': 'Mutaforma', 'Psionic': 'Psionico',
    }
    for en, it in SUBTYPES.items():
        add(glossary, en, it, 'adj', 'Creature subtype', 'Monsters')

    # ── 1g. Sizes ───────────────────────────────────────────────────────────
    SIZES = {
        'Fine': 'Minuscola', 'Diminutive': 'Piccolissima', 'Tiny': 'Minuta',
        'Small': 'Piccola', 'Medium': 'Media', 'Large': 'Grande',
        'Huge': 'Enorme', 'Gargantuan': 'Mastodontica', 'Colossal': 'Colossale',
    }
    for en, it in SIZES.items():
        add(glossary, en, it, 'adj', 'Creature size category', 'Core Rules')

    # ── 1h. Alignments ──────────────────────────────────────────────────────
    ALIGNMENTS = {
        'Lawful Good': 'Legale Buono', 'Neutral Good': 'Neutrale Buono',
        'Chaotic Good': 'Caotico Buono', 'Lawful Neutral': 'Legale Neutrale',
        'True Neutral': 'Neutrale Puro', 'Chaotic Neutral': 'Caotico Neutrale',
        'Lawful Evil': 'Legale Malvagio', 'Neutral Evil': 'Neutrale Malvagio',
        'Chaotic Evil': 'Caotico Malvagio',
        'Any': 'Qualsiasi', 'Usually': 'Di solito', 'Often': 'Spesso', 'Always': 'Sempre',
    }
    for en, it in ALIGNMENTS.items():
        add(glossary, en, it, 'noun' if ' ' in en else 'adv', 'Alignment', 'Core Rules')

    # ── 1i. Core classes ────────────────────────────────────────────────────
    CORE_CLASSES = {
        'Barbarian': 'Barbaro', 'Bard': 'Bardo', 'Cleric': 'Chierico',
        'Druid': 'Druido', 'Fighter': 'Guerriero', 'Monk': 'Monaco',
        'Paladin': 'Paladino', 'Ranger': 'Ranger', 'Rogue': 'Ladro',
        'Sorcerer': 'Stregone', 'Wizard': 'Mago',
        'Adept': 'Adepto', 'Aristocrat': 'Aristocratico', 'Commoner': 'Popolano',
        'Expert': 'Esperto', 'Warrior': 'Guerriero (NPC)',
    }
    for en, it in CORE_CLASSES.items():
        add(glossary, en, it, 'noun', 'Character class', 'Classes')

    # ── 1j. Skills (from skills overlay) ────────────────────────────────────
    skills_overlay = load_json(os.path.join(I18N_DIR, 'skills.json'))
    skills_base = load_json(os.path.join(DATA_DIR, 'skills.json'))
    if skills_overlay and skills_base:
        base_map = {s['slug']: s['name'] for s in skills_base}
        skill_count = 0
        for s in skills_overlay:
            en_name = base_map.get(s.get('slug', ''), '')
            it_name = s.get('name', '')
            if en_name and it_name:
                add(glossary, en_name, it_name, 'noun', 'Skill', 'Skills')
                skill_count += 1
        print(f'  Skills from overlay: {skill_count}')

    # ── 1k. Equipment (from equipment overlay) ──────────────────────────────
    equip_overlay = load_json(os.path.join(I18N_DIR, 'equipment.json'))
    equip_base = load_json(os.path.join(DATA_DIR, 'equipment.json'))
    if equip_overlay and equip_base:
        base_map = {e['slug']: e['name'] for e in equip_base}
        equip_count = 0
        for e in equip_overlay:
            en_name = base_map.get(e.get('slug', ''), '')
            it_name = e.get('name', '')
            if en_name and it_name:
                add(glossary, en_name, it_name, 'noun', 'Equipment', 'Equipment')
                equip_count += 1
        print(f'  Equipment from overlay: {equip_count}')

    # ── 1l. Races (from races overlay) ──────────────────────────────────────
    races_overlay = load_json(os.path.join(I18N_DIR, 'races.json'))
    races_base = load_json(os.path.join(DATA_DIR, 'races.json'))
    if races_overlay and races_base:
        base_map = {r['slug']: r['name'] for r in races_base}
        race_count = 0
        for r in races_overlay:
            en_name = base_map.get(r.get('slug', ''), '')
            it_name = r.get('name', '')
            if en_name and it_name:
                add(glossary, en_name, it_name, 'noun', 'Race', 'Races')
                race_count += 1
        print(f'  Races from overlay: {race_count}')

    # ── 1m. Sourcebooks (from sources.json) ─────────────────────────────────
    sources = load_json(os.path.join(DATA_DIR, 'sources.json'))
    if sources:
        src_count = 0
        for key, src in sources.items():
            en_name = src.get('name_en', '')
            it_name = src.get('name_it', '')
            if en_name and it_name:
                add(glossary, en_name, it_name, 'noun', f'Sourcebook ({key})', 'Sourcebooks')
                src_count += 1
        print(f'  Sourcebooks: {src_count}')

    # ── 1n. Spell names (from spells overlay) ──────────────────────────────
    spells_overlay = load_json(os.path.join(I18N_DIR, 'spells.json'))
    spells_base = load_json(os.path.join(DATA_DIR, 'spells.json'))
    if spells_overlay and spells_base:
        base_map = {s['slug']: s['name'] for s in spells_base}
        spell_count = 0
        for s in spells_overlay:
            en_name = base_map.get(s.get('slug', ''), '')
            it_name = s.get('name', '')
            if en_name and it_name:
                school = s.get('school', '')
                desc = f'Spell ({school})' if school else 'Spell'
                add(glossary, en_name, it_name, 'noun', desc, 'Spells')
                spell_count += 1
        print(f'  Spells from overlay: {spell_count}')

    # ── 1o. Feat names (from feats overlay) ─────────────────────────────────
    feats_overlay = load_json(os.path.join(I18N_DIR, 'feats.json'))
    feats_base = load_json(os.path.join(DATA_DIR, 'feats.json'))
    if feats_overlay and feats_base:
        base_map = {f['slug']: f['name'] for f in feats_base}
        feat_count = 0
        for f in feats_overlay:
            en_name = base_map.get(f.get('slug', ''), '')
            it_name = f.get('name', '')
            if en_name and it_name:
                add(glossary, en_name, it_name, 'noun', 'Feat', 'Feats')
                feat_count += 1
        print(f'  Feats from overlay: {feat_count}')

    # ── 1p. Class names (from classes overlay) ──────────────────────────────
    classes_overlay = load_json(os.path.join(I18N_DIR, 'classes.json'))
    classes_base = load_json(os.path.join(DATA_DIR, 'classes.json'))
    if classes_overlay and classes_base:
        base_map = {c['slug']: c['name'] for c in classes_base}
        class_count = 0
        for c in classes_overlay:
            en_name = base_map.get(c.get('slug', ''), '')
            it_name = c.get('name', '')
            if en_name and it_name:
                add(glossary, en_name, it_name, 'noun', 'Class', 'Classes')
                class_count += 1
        print(f'  Classes from overlay: {class_count}')

    # ── 1q. Monster names (from monsters overlay) ───────────────────────────
    monsters_overlay = load_json(os.path.join(I18N_DIR, 'monsters.json'))
    monsters_base = load_json(os.path.join(DATA_DIR, 'monsters.json'))
    if monsters_overlay and monsters_base:
        base_map = {m['slug']: m['name'] for m in monsters_base}
        monster_count = 0
        for m in monsters_overlay:
            en_name = base_map.get(m.get('slug', ''), '')
            it_name = m.get('name', '')
            if en_name and it_name:
                add(glossary, en_name, it_name, 'noun', 'Monster', 'Monsters')
                monster_count += 1
        print(f'  Monsters from overlay: {monster_count}')

    validated_count = len(glossary)
    print(f'\n  Total validated terms: {validated_count}')

    # ════════════════════════════════════════════════════════════════════════
    # PART 2: Standard D&D 3.5 terminology
    # ════════════════════════════════════════════════════════════════════════

    print('\n=== Part 2: Standard D&D 3.5 terminology ===')

    # ── 2a. Combat terms ────────────────────────────────────────────────────
    COMBAT = {
        'Armor Class': 'Classe Armatura',
        'AC': 'CA',
        'Hit Points': 'Punti Ferita',
        'HP': 'PF',
        'Hit Dice': 'Dadi Vita',
        'HD': 'DV',
        'Base Attack Bonus': 'Bonus di Attacco Base',
        'BAB': 'BAB',
        'Attack': 'Attacco',
        'Full Attack': 'Attacco Completo',
        'Damage': 'Danno',
        'Critical Hit': 'Colpo Critico',
        'Initiative': 'Iniziativa',
        'Saving Throw': 'Tiro Salvezza',
        'Fortitude': 'Tempra',
        'Reflex': 'Riflessi',
        'Will': 'Volonta',
        'Spell Resistance': 'Resistenza agli Incantesimi',
        'SR': 'RI',
        'Damage Reduction': 'Riduzione del Danno',
        'DR': 'RD',
        'Touch AC': 'CA di Contatto',
        'Flat-Footed': 'Colto alla Sprovvista',
        'Grapple': 'Lotta',
        'Charge': 'Carica',
        'Full-Round Action': 'Azione di Round Completo',
        'Standard Action': 'Azione Standard',
        'Move Action': 'Azione di Movimento',
        'Swift Action': 'Azione Veloce',
        'Immediate Action': 'Azione Immediata',
        'Free Action': 'Azione Gratuita',
        'Attack of Opportunity': 'Attacco di Opportunita',
        'AoO': 'AdO',
        'Threatened Area': 'Area Minacciata',
        'Flanking': 'Fiancheggiamento',
        'Cover': 'Copertura',
        'Concealment': 'Occultamento',
        'Melee': 'Mischia',
        'Ranged': 'Distanza',
        'Natural Armor': 'Armatura Naturale',
        'Touch Attack': 'Attacco di Contatto',
        'Ranged Touch Attack': 'Attacco di Contatto a Distanza',
        'Power Attack': 'Attacco Poderoso',
        'Two-Weapon Fighting': 'Combattere con Due Armi',
        'Sneak Attack': 'Attacco Furtivo',
        'Critical Threat': 'Minaccia di Critico',
        'Nonlethal Damage': 'Danno Non Letale',
    }
    for en, it in COMBAT.items():
        add(glossary, en, it, '', 'Combat term', 'Combat')

    # ── 2b. Magic terms ─────────────────────────────────────────────────────
    MAGIC = {
        'Spell': 'Incantesimo',
        'Spells': 'Incantesimi',
        'Spell Level': 'Livello Incantesimo',
        'Caster Level': 'Livello Incantatore',
        'CL': 'LI',
        'Casting Time': 'Tempo di Lancio',
        'Components': 'Componenti',
        'Verbal': 'Verbale',
        'Somatic': 'Somatica',
        'Material': 'Materiale',
        'Focus': 'Focus',
        'Divine Focus': 'Focus Divino',
        'XP Cost': 'Costo in PE',
        'Range': 'Gittata',
        'Close': 'Vicino',
        'Medium': 'Medio',
        'Long': 'Lungo',
        'Personal': 'Personale',
        'Touch': 'Contatto',
        'Target': 'Bersaglio',
        'Area': 'Area',
        'Effect': 'Effetto',
        'Duration': 'Durata',
        'Instantaneous': 'Istantanea',
        'Concentration': 'Concentrazione',
        'Permanent': 'Permanente',
        'Dismissible': 'Congedabile',
        'Prepared': 'Preparato',
        'Spontaneous': 'Spontaneo',
        'Arcane': 'Arcano',
        'Divine': 'Divino',
        'Spell Slot': 'Slot Incantesimo',
        'Metamagic': 'Metamagia',
        'Counterspell': 'Controincantesimo',
        'Dispel': 'Dissoluzione',
        'Dispel Magic': 'Dissolvi Magie',
        'Saving Throw': 'Tiro Salvezza',
        'Will negates': 'Volonta nega',
        'Fortitude half': 'Tempra dimezza',
        'Reflex half': 'Riflessi dimezza',
        'None': 'Nessuno',
        'Harmless': 'Innocuo',
        'Yes': 'Si',
        'No': 'No',
        'Cantrip': 'Trucchetto',
        'Orison': 'Orazione',
        'Domain': 'Dominio',
        'Spell-Like Ability': 'Capacita Magica',
        'Supernatural Ability': 'Capacita Soprannaturale',
        'Extraordinary Ability': 'Capacita Straordinaria',
        'Ex': 'Str',
        'Su': 'Sop',
        'Sp': 'Mag',
    }
    for en, it in MAGIC.items():
        add(glossary, en, it, '', 'Magic term', 'Magic')

    # ── 2c. Character terms ─────────────────────────────────────────────────
    CHARACTER = {
        'Level': 'Livello',
        'Character Level': 'Livello del Personaggio',
        'Class Level': 'Livello di Classe',
        'Experience Points': 'Punti Esperienza',
        'XP': 'PE',
        'Feat': 'Talento',
        'Feats': 'Talenti',
        'Skill': 'Abilita',
        'Skills': 'Abilita',
        'Skill Points': 'Punti Abilita',
        'Skill Ranks': 'Gradi di Abilita',
        'Ability Score': 'Punteggio di Caratteristica',
        'Ability Modifier': 'Modificatore di Caratteristica',
        'Base Save': 'Tiro Salvezza Base',
        'Prestige Class': 'Classe di Prestigio',
        'Base Class': 'Classe Base',
        'Multiclass': 'Multiclasse',
        'Level Adjustment': 'Modificatore di Livello',
        'Effective Character Level': 'Livello Effettivo del Personaggio',
        'ECL': 'LEP',
        'Hit Die': 'Dado Vita',
        'Alignment': 'Allineamento',
        'Proficiency': 'Competenza',
        'Proficient': 'Competente',
        'Prerequisite': 'Prerequisito',
        'Prerequisites': 'Prerequisiti',
        'Benefit': 'Beneficio',
        'Normal': 'Normale',
        'Special': 'Speciale',
        'Trained Only': 'Solo Addestrata',
        'Armor Check Penalty': 'Penalita di Armatura',
        'Class Skill': 'Abilita di Classe',
        'Cross-Class Skill': 'Abilita Fuori Classe',
        'Bonus Feat': 'Talento Bonus',
    }
    for en, it in CHARACTER.items():
        add(glossary, en, it, '', 'Character term', 'Core Rules')

    # ── 2d. Equipment categories ────────────────────────────────────────────
    EQUIPMENT_CATS = {
        'Weapon': 'Arma', 'Weapons': 'Armi',
        'Armor': 'Armatura', 'Shield': 'Scudo',
        'Light Armor': 'Armatura Leggera', 'Medium Armor': 'Armatura Media',
        'Heavy Armor': 'Armatura Pesante',
        'Simple Weapon': 'Arma Semplice', 'Martial Weapon': 'Arma da Guerra',
        'Exotic Weapon': 'Arma Esotica',
        'Light Weapon': 'Arma Leggera', 'One-Handed': 'A Una Mano',
        'Two-Handed': 'A Due Mani',
        'Slashing': 'Tagliente', 'Piercing': 'Perforante', 'Bludgeoning': 'Contundente',
        'Adventuring Gear': 'Equipaggiamento da Avventura',
        'Potion': 'Pozione', 'Scroll': 'Pergamena', 'Wand': 'Bacchetta',
        'Rod': 'Verga', 'Staff': 'Bastone', 'Ring': 'Anello',
        'Wondrous Item': 'Oggetto Meraviglioso',
        'Magic Item': 'Oggetto Magico',
        'Masterwork': 'Perfetto',
        'Enchantment Bonus': 'Bonus di Potenziamento',
        'Gold Pieces': 'Monete d\'Oro', 'GP': 'MO',
        'Silver Pieces': 'Monete d\'Argento', 'SP': 'MA',
        'Copper Pieces': 'Monete di Rame', 'CP': 'MR',
        'Platinum Pieces': 'Monete di Platino', 'PP': 'MP',
    }
    for en, it in EQUIPMENT_CATS.items():
        add(glossary, en, it, '', 'Equipment term', 'Equipment')

    # ── 2e. Monster stat block terms ────────────────────────────────────────
    MONSTER_TERMS = {
        'Challenge Rating': 'Grado di Sfida',
        'CR': 'GS',
        'Treasure': 'Tesoro',
        'Environment': 'Ambiente',
        'Organization': 'Organizzazione',
        'Advancement': 'Avanzamento',
        'Special Attacks': 'Attacchi Speciali',
        'Special Qualities': 'Qualita Speciali',
        'Speed': 'Velocita',
        'Space/Reach': 'Spazio/Portata',
        'Darkvision': 'Scurovisione',
        'Low-Light Vision': 'Visione Crepuscolare',
        'Blindsight': 'Vista Cieca',
        'Blindsense': 'Percezione Cieca',
        'Tremorsense': 'Percezione delle Vibrazioni',
        'Telepathy': 'Telepatia',
        'Regeneration': 'Rigenerazione',
        'Fast Healing': 'Guarigione Rapida',
        'Turn Resistance': 'Resistenza allo Scacciare',
        'Immunity': 'Immunita',
        'Resistance': 'Resistenza',
        'Vulnerability': 'Vulnerabilita',
    }
    for en, it in MONSTER_TERMS.items():
        add(glossary, en, it, '', 'Monster stat block term', 'Monsters')

    # ── 2f. Domains ─────────────────────────────────────────────────────────
    DOMAINS = {
        'Air Domain': 'Dominio dell\'Aria', 'Animal Domain': 'Dominio degli Animali',
        'Chaos Domain': 'Dominio del Caos', 'Death Domain': 'Dominio della Morte',
        'Destruction Domain': 'Dominio della Distruzione',
        'Earth Domain': 'Dominio della Terra', 'Evil Domain': 'Dominio del Male',
        'Fire Domain': 'Dominio del Fuoco', 'Good Domain': 'Dominio del Bene',
        'Healing Domain': 'Dominio della Guarigione',
        'Knowledge Domain': 'Dominio della Conoscenza',
        'Law Domain': 'Dominio della Legge', 'Luck Domain': 'Dominio della Fortuna',
        'Magic Domain': 'Dominio della Magia', 'Plant Domain': 'Dominio delle Piante',
        'Protection Domain': 'Dominio della Protezione',
        'Strength Domain': 'Dominio della Forza', 'Sun Domain': 'Dominio del Sole',
        'Travel Domain': 'Dominio del Viaggio', 'Trickery Domain': 'Dominio dell\'Inganno',
        'War Domain': 'Dominio della Guerra', 'Water Domain': 'Dominio dell\'Acqua',
    }
    for en, it in DOMAINS.items():
        add(glossary, en, it, 'noun', 'Cleric domain', 'Magic')

    # ── 2g. Feat types ──────────────────────────────────────────────────────
    FEAT_TYPES = {
        'General': 'Generale', 'Fighter Bonus Feat': 'Talento Bonus Guerriero',
        'Metamagic': 'Metamagico', 'Item Creation': 'Creazione Oggetto',
        'Epic': 'Epico', 'Psionic': 'Psionico', 'Divine': 'Divino',
        'Tactical': 'Tattico', 'Exalted': 'Esaltato', 'Vile': 'Vile',
        'Wild': 'Selvaggio', 'Heritage': 'Retaggio',
    }
    for en, it in FEAT_TYPES.items():
        add(glossary, en, it, 'adj', 'Feat type', 'Feats')

    # ── 2h. Conditions ──────────────────────────────────────────────────────
    CONDITIONS = {
        'Blinded': 'Accecato', 'Confused': 'Confuso', 'Cowering': 'Atterrito',
        'Dazed': 'Frastornato', 'Dazzled': 'Abbagliato', 'Dead': 'Morto',
        'Deafened': 'Assordato', 'Disabled': 'Inabile', 'Dying': 'Morente',
        'Entangled': 'Intralciato', 'Exhausted': 'Esausto',
        'Fascinated': 'Affascinato', 'Fatigued': 'Affaticato',
        'Flat-Footed': 'Colto alla Sprovvista', 'Frightened': 'Spaventato',
        'Grappling': 'In Lotta', 'Helpless': 'Indifeso',
        'Incorporeal': 'Incorporeo', 'Invisible': 'Invisibile',
        'Nauseated': 'Nauseato', 'Panicked': 'In Panico',
        'Paralyzed': 'Paralizzato', 'Petrified': 'Pietrificato',
        'Pinned': 'Immobilizzato', 'Prone': 'Prono',
        'Shaken': 'Scosso', 'Sickened': 'Infermo',
        'Stable': 'Stabile', 'Staggered': 'Barcollante',
        'Stunned': 'Stordito', 'Turned': 'Scacciato',
        'Unconscious': 'Privo di Sensi',
    }
    for en, it in CONDITIONS.items():
        add(glossary, en, it, 'adj', 'Condition', 'Combat')

    # ── 2i. Miscellaneous game terms ────────────────────────────────────────
    MISC = {
        'Difficulty Class': 'Classe Difficolta',
        'DC': 'CD',
        'round': 'round',
        'Turn Undead': 'Scacciare Non Morti',
        'Rebuke Undead': 'Intimorire Non Morti',
        'Channel Energy': 'Incanalare Energia',
        'Wild Shape': 'Forma Selvatica',
        'Rage': 'Ira',
        'Bardic Music': 'Musica Bardica',
        'Smite Evil': 'Punire il Male',
        'Lay on Hands': 'Imposizione delle Mani',
        'Evasion': 'Eludere',
        'Improved Evasion': 'Eludere Migliorato',
        'Uncanny Dodge': 'Schivata Prodigiosa',
        'Improved Uncanny Dodge': 'Schivata Prodigiosa Migliorata',
        'Trap Sense': 'Percepire Trappole',
        'Trapfinding': 'Trovare Trappole',
        'Familiar': 'Famiglio',
        'Animal Companion': 'Compagno Animale',
        'Spellbook': 'Libro degli Incantesimi',
        'Bonus Spell': 'Incantesimo Bonus',
        'Spell Failure': 'Fallimento Incantesimo',
        'Arcane Spell Failure': 'Fallimento Incantesimo Arcano',
        'Natural Weapon': 'Arma Naturale',
        'Unarmed Strike': 'Colpo Senz\'Armi',
        'Ability Damage': 'Danno alle Caratteristiche',
        'Ability Drain': 'Risucchio di Caratteristica',
        'Energy Drain': 'Risucchio di Energia',
        'Negative Level': 'Livello Negativo',
        'Spell Component': 'Componente dell\'Incantesimo',
    }
    for en, it in MISC.items():
        add(glossary, en, it, '', 'Game term', 'Core Rules')

    generated_count = len(glossary) - validated_count
    print(f'  Added {generated_count} standard D&D terms')

    # ════════════════════════════════════════════════════════════════════════
    # OUTPUT
    # ════════════════════════════════════════════════════════════════════════

    total = len(glossary)
    print(f'\n=== Output ===')
    print(f'  Total glossary entries: {total}')

    # Sort: standard terms first (by domain), then entity names (spells, feats, etc.)
    entity_domains = {'Spells', 'Feats', 'Classes', 'Monsters'}
    standard = sorted(
        [v for v in glossary.values() if v['domain'] not in entity_domains],
        key=lambda x: (x['domain'], x['term_en'].lower())
    )
    entities = sorted(
        [v for v in glossary.values() if v['domain'] in entity_domains],
        key=lambda x: (x['domain'], x['term_en'].lower())
    )

    all_entries = standard + entities

    # Write Crowdin CSV format
    with open(OUTPUT_PATH, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        # Crowdin glossary header
        writer.writerow(['Term (EN)', 'Translation (IT)', 'Part of Speech', 'Description', 'Domain'])
        for entry in all_entries:
            writer.writerow([
                entry['term_en'],
                entry['translation_it'],
                entry['pos'],
                entry['description'],
                entry['domain'],
            ])

    print(f'  Saved to: {OUTPUT_PATH}')

    # Domain breakdown
    from collections import Counter
    domains = Counter(v['domain'] for v in glossary.values())
    print(f'\n  Domain breakdown:')
    for domain, count in domains.most_common():
        print(f'    {domain:20s} {count:5d}')


if __name__ == '__main__':
    main()
