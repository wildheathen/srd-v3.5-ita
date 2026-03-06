#!/usr/bin/env python3
"""
Translate formulaic/metadata fields for all SRD categories into Italian.
Uses mapping dictionaries for repeating values. Never overwrites existing translations.

Usage:
    python scripts/translate_metadata.py              # all categories
    python scripts/translate_metadata.py spells       # only spells
    python scripts/translate_metadata.py monsters     # only monsters
"""

import json
import os
import re
import sys

# ── Spell field mappings ─────────────────────────────────────────────────

DESCRIPTOR_MAP = {
    "Acid": "Acido",
    "Air": "Aria",
    "Chaotic": "Caotico",
    "Cold": "Freddo",
    "Creation": "Creazione",
    "Darkness": "Oscurità",
    "Death": "Morte",
    "Earth": "Terra",
    "Electricity": "Elettricità",
    "Evil": "Male",
    "Fear": "Paura",
    "Fire": "Fuoco",
    "Force": "Forza",
    "Good": "Bene",
    "Language Dependent": "Linguaggio-Dipendente",
    "Language-Dependent": "Linguaggio-Dipendente",
    "Lawful": "Legale",
    "Light": "Luce",
    "Mind-Affecting": "Influenza Mentale",
    "Sonic": "Sonoro",
    "Water": "Acqua",
    "see text": "vedi testo",
}


def translate_descriptor(val):
    if not val:
        return None
    # Direct match
    if val in DESCRIPTOR_MAP:
        return DESCRIPTOR_MAP[val]
    # Handle "see text for..." entries
    if val.startswith("see text for"):
        return "vedi testo"
    # Compound: split on ", "
    parts = [p.strip() for p in val.split(",")]
    translated = []
    for p in parts:
        t = DESCRIPTOR_MAP.get(p.strip())
        if t:
            translated.append(t)
        else:
            # Try "X or Y"
            if " or " in p:
                sub = [s.strip() for s in p.split(" or ")]
                sub_t = [DESCRIPTOR_MAP.get(s, s) for s in sub]
                translated.append(" o ".join(sub_t))
            else:
                translated.append(p)
    return ", ".join(translated)


# Spell resistance
SR_MAP = {
    "Yes": "Sì",
    "No": "No",
    "See text": "Vedi testo",
}

SR_TOKEN_MAP = {
    "Yes": "Sì",
    "No": "No",
    "harmless": "innocuo",
    "object": "oggetto",
    "see text": "vedi testo",
    "See text": "Vedi testo",
}


def translate_spell_resistance(val):
    if not val:
        return None
    if val in SR_MAP:
        return SR_MAP[val]
    result = val
    for en, it in SR_TOKEN_MAP.items():
        result = result.replace(en, it)
    # "and" -> "e", "or" -> "o"
    result = result.replace(" and ", " e ").replace(" or ", " o ")
    return result


# Saving throw
ST_TOKEN_MAP = {
    "Fortitude": "Tempra",
    "Reflex": "Riflessi",
    "Will": "Volontà",
    "None": "Nessuno",
    "No": "No",
    "negates": "nega",
    "partial": "parziale",
    "half": "dimezza",
    "harmless": "innocuo",
    "object": "oggetto",
    "see text": "vedi testo",
    "See text": "Vedi testo",
    "disbelief": "incredulità",
    "if interacted with": "se si interagisce",
    "blinding only": "solo accecamento",
    "varies": "variabile",
    "then": "poi",
    "and": "e",
    "or": "o",
}


def translate_saving_throw(val):
    if not val:
        return None
    if val == "None" or val == "None; see text":
        return val.replace("None", "Nessuno").replace("see text", "vedi testo")
    if val == "No":
        return "No"
    if val == "See text":
        return "Vedi testo"

    result = val
    # Order matters: longer tokens first to avoid partial replacement
    ordered = sorted(ST_TOKEN_MAP.items(), key=lambda x: -len(x[0]))
    for en, it in ordered:
        result = result.replace(en, it)
    return result


# Casting time
CASTING_TIME_MAP = {
    "1 standard action": "1 azione standard",
    "1 standard action or see text": "1 azione standard o vedi testo",
    "1 round": "1 round",
    "1 round; see text": "1 round; vedi testo",
    "1 minute": "1 minuto",
    "One minute": "1 minuto",
    "1 minute or longer; see text": "1 minuto o più; vedi testo",
    "1 minute/lb. created": "1 minuto/libbra creata",
    "10 minutes": "10 minuti",
    "10 minutes; see text": "10 minuti; vedi testo",
    "At least 10 minutes; see text": "Almeno 10 minuti; vedi testo",
    "30 minutes": "30 minuti",
    "1 hour": "1 ora",
    "12 hours": "12 ore",
    "24 hours": "24 ore",
    "1 free action": "1 azione gratuita",
    "2 rounds": "2 round",
    "3 rounds": "3 round",
    "3 full rounds": "3 round completi",
    "6 rounds": "6 round",
    "See text": "Vedi testo",
}


# Range
RANGE_MAP = {
    "Personal": "Personale",
    "Personal; see text": "Personale; vedi testo",
    "Touch": "Contatto",
    "Touch; see text": "Contatto; vedi testo",
    "Close (25 ft. + 5 ft./2 levels)": "Corto (7,5 m + 1,5 m/2 livelli)",
    "Close (25 ft. + 5 ft./2 levels); see text": "Corto (7,5 m + 1,5 m/2 livelli); vedi testo",
    "Close (25 ft. + 5 ft./2 levels) or see text": "Corto (7,5 m + 1,5 m/2 livelli) o vedi testo",
    "Close (25 ft. + 5 ft./2 levels)/ 100 ft.; see text": "Corto (7,5 m + 1,5 m/2 livelli) / 30 m; vedi testo",
    "Medium (100 ft. + 10 ft./level)": "Medio (30 m + 3 m/livello)",
    "Medium (100 ft. + 10 ft. level)": "Medio (30 m + 3 m/livello)",
    "Long (400 ft. + 40 ft./level)": "Lungo (120 m + 12 m/livello)",
    "Unlimited": "Illimitato",
    "See text": "Vedi testo",
    "Personal and touch": "Personale e contatto",
    "Personal or touch": "Personale o contatto",
    "Personal or close (25 ft. + 5 ft./2 levels)": "Personale o corto (7,5 m + 1,5 m/2 livelli)",
    "One mile": "1,5 km",
    "Anywhere within the area to be warded": "Ovunque nell'area da proteggere",
}


def translate_range(val):
    if not val:
        return None
    if val in RANGE_MAP:
        return RANGE_MAP[val]
    # Convert ft. to m for numeric ranges
    m = re.match(r"^(\d+)\s*ft\.$", val)
    if m:
        feet = int(m.group(1))
        meters = round(feet * 0.3, 1)
        return f"{meters} m"
    # X ft.; see text
    m = re.match(r"^(\d+)\s*ft\.\s*;\s*see text$", val)
    if m:
        feet = int(m.group(1))
        meters = round(feet * 0.3, 1)
        return f"{meters} m; vedi testo"
    # X ft./level
    m = re.match(r"^(\d+)\s*ft\./level$", val)
    if m:
        feet = int(m.group(1))
        meters = round(feet * 0.3, 1)
        return f"{meters} m/livello"
    # X miles
    m = re.match(r"^(\d+)\s*miles?$", val)
    if m:
        miles = int(m.group(1))
        km = round(miles * 1.5, 1)
        return f"{km} km"
    # X mile/level
    m = re.match(r"^(\d+)\s*mile/level$", val)
    if m:
        return f"{m.group(1)} miglia/livello"
    # Up to X ft./level
    m = re.match(r"^Up to (\d+)\s*ft\./level$", val)
    if m:
        feet = int(m.group(1))
        meters = round(feet * 0.3, 1)
        return f"Fino a {meters} m/livello"
    return None  # can't translate


# Duration tokens
DURATION_TOKEN_MAP = {
    "Instantaneous": "Istantaneo",
    "Permanent": "Permanente",
    "Concentration": "Concentrazione",
    "See text": "Vedi testo",
    "see text": "vedi testo",
    "(D)": "(C)",
    "until discharged": "finché non viene scaricato",
    "until triggered": "finché non viene attivato",
    "or until discharged": "o finché non viene scaricato",
    "round": "round",
    "/level": "/livello",
    "/caster level": "/livello dell'incantatore",
    "hour": "ora",
    "hours": "ore",
    "day": "giorno",
    "days": "giorni",
    "minute": "minuto",
    "minutes": "minuti",
    "min.": "min.",
    "per three levels": "ogni tre livelli",
    "per two levels": "ogni due livelli",
    "or until completed": "o fino al completamento",
    "whichever comes first": "qualunque avvenga prima",
    "up to": "fino a",
    "maximum": "massimo",
    "or less": "o meno",
    "plus": "più",
    "then": "poi",
    "and": "e",
    "or": "o",
    "One": "Un",
}


def translate_duration(val):
    if not val:
        return None
    # Direct match for common ones
    simple = {
        "Instantaneous": "Istantaneo",
        "Permanent": "Permanente",
        "Concentration": "Concentrazione",
        "See text": "Vedi testo",
        "1 round": "1 round",
        "1 full round": "1 round completo",
        "1 min.": "1 min.",
        "1 minute": "1 minuto",
        "1 hour": "1 ora",
    }
    if val in simple:
        return simple[val]

    result = val
    # Replace tokens (longer first)
    ordered = sorted(DURATION_TOKEN_MAP.items(), key=lambda x: -len(x[0]))
    for en, it in ordered:
        result = result.replace(en, it)

    # "rounds" is same in IT but we still want to mark it as translated
    # Match patterns like "7 rounds", "1d6+2 rounds", "1d4+1 rounds"
    if result == val and re.match(r'^[\d\w+d]+\s+rounds?$', val):
        return val.replace("rounds", "round")

    return result if result != val else None


# Components
COMP_TOKEN_MAP = {
    "DF": "FD",
    "XP": "PE",
}


def translate_components(val):
    if not val:
        return None
    # Components like V, S, M, F are international abbreviations (same in Italian)
    # DF -> FD (Focus Divino), XP -> PE (Punti Esperienza)
    result = val
    result = re.sub(r'\bDF\b', 'FD', result)
    result = re.sub(r'\bXP\b', 'PE', result)
    result = result.replace("see text", "vedi testo")
    result = result.replace("Brd only", "solo Brd")
    # Always return a value since V/S/M/F are valid Italian abbreviations
    return result


# Level - class/domain abbreviation translation
CLASS_ABBR_MAP = {
    "Sor/Wiz": "Str/Mag",
    "Sor": "Str",
    "Wiz": "Mag",
    "Clr": "Chr",
    "Brd": "Brd",
    "Drd": "Drd",
    "Rgr": "Rgr",
    "Pal": "Pal",
}

DOMAIN_MAP = {
    "Air": "Aria",
    "Animal": "Animale",
    "Chaos": "Caos",
    "Death": "Morte",
    "Destruction": "Distruzione",
    "Earth": "Terra",
    "Evil": "Male",
    "Fire": "Fuoco",
    "Good": "Bene",
    "Healing": "Guarigione",
    "Knowledge": "Conoscenza",
    "Law": "Legge",
    "Luck": "Fortuna",
    "Magic": "Magia",
    "Plant": "Pianta",
    "Protection": "Protezione",
    "Strength": "Forza",
    "Sun": "Sole",
    "Travel": "Viaggio",
    "Trickery": "Inganno",
    "War": "Guerra",
    "Water": "Acqua",
}


def translate_level(val):
    if not val:
        return None
    parts = [p.strip() for p in val.split(",")]
    translated = []
    all_recognized = True
    for part in parts:
        m = re.match(r'^(.+?)\s+(\d+)$', part)
        if m:
            cls_name = m.group(1)
            lvl = m.group(2)
            t = CLASS_ABBR_MAP.get(cls_name) or DOMAIN_MAP.get(cls_name)
            if t:
                translated.append(f"{t} {lvl}")
            else:
                all_recognized = False
                translated.append(part)
        else:
            all_recognized = False
            translated.append(part)
    # Return result if all parts were recognized (even if same as input)
    if all_recognized:
        return ", ".join(translated)
    return None


# Target / Area / Effect
TARGET_DIRECT_MAP = {
    "You": "Te stesso",
    "Creature touched": "Creatura toccata",
    "One creature": "Una creatura",
    "One living creature": "Una creatura vivente",
    "Living creature touched": "Creatura vivente toccata",
    "One creature/level, no two of which can be more than 30 ft. apart": "Una creatura/livello, non più di 9 m l'una dall'altra",
    "See text": "Vedi testo",
    "see text": "vedi testo",
    "Cone-shaped burst": "Scoppio a cono",
    "Cone-shaped emanation": "Emanazione a cono",
    "Ray": "Raggio",
    "Object touched": "Oggetto toccato",
    "One humanoid creature": "Una creatura umanoide",
    "One animal": "Un animale",
    "One creature or object": "Una creatura od oggetto",
    "You or creature touched": "Te stesso o creatura toccata",
    "Magical sensor": "Sensore magico",
    "Weapon touched": "Arma toccata",
    "Flask of water touched": "Fiasca d'acqua toccata",
    "One touched creature": "Una creatura toccata",
    "One creature/level": "Una creatura/livello",
    "One living creature touched": "Una creatura vivente toccata",
    "One willing creature": "Una creatura consenziente",
    "One willing creature touched": "Una creatura consenziente toccata",
    "One touched object weighing up to 5 lb./level": "Un oggetto toccato del peso fino a 2,5 kg/livello",
    "One creature or object/level, no two of which can be more than 30 ft. apart": "Una creatura od oggetto/livello, non più di 9 m l'uno dall'altro",
    "You and touched objects or other touched willing creatures": "Te stesso e oggetti toccati o altre creature consenzienti toccate",
    "One willing creature/level, no two of which can be more than 30 ft. apart": "Una creatura consenziente/livello, non più di 9 m l'una dall'altra",
    "One undead creature": "Una creatura non morta",
    "Up to one touched creature/level": "Fino a una creatura toccata/livello",
    "One creature touched/level": "Una creatura toccata/livello",
    "One or more creatures, no two of which can be more than 30 ft. apart": "Una o più creature, non più di 9 m l'una dall'altra",
    "One or more summoned creatures, no two of which can be more than 30 ft. apart": "Una o più creature evocate, non più di 9 m l'una dall'altra",
    "One plant creature": "Una creatura vegetale",
    "One creature or unattended object": "Una creatura od oggetto incustodito",
    "Creature or creatures touched (up to one/level)": "Creatura o creature toccate (fino a una/livello)",
    "One creature initially, then special; see text": "Una creatura inizialmente, poi speciale; vedi testo",
    "One or more living creatures within a 10-ft.-radius burst": "Una o più creature viventi entro scoppio con raggio di 3 m",
    "One Small or Medium humanoid": "Un umanoide Piccolo o Medio",
    "Up to one willing creature per level, all within 30 ft. of each other": "Fino a una creatura consenziente/livello, tutte entro 9 m l'una dall'altra",
    "One touched object of up to 2 cu. ft./level": "Un oggetto toccato fino a 0,06 m³/livello",
    "Creatures and objects within 40-ft.-radius spread centered on you": "Creature e oggetti entro diffusione con raggio di 12 m centrata su di te",
    "One creature; see text": "Una creatura; vedi testo",
    "Creature touched; see text": "Creatura toccata; vedi testo",
    "One creature or object of up to 1 cu. ft./level": "Una creatura od oggetto fino a 0,03 m³/livello",
    "Your touched staff": "Il tuo bastone toccato",
    "Ray of negative energy": "Raggio di energia negativa",
    "Fifty projectiles, all of which must be in contact with each other at the time of casting": "Cinquanta proiettili, tutti in contatto l'uno con l'altro al momento del lancio",
    "Sword-like beam": "Raggio a forma di spada",
    "Burst of light": "Scoppio di luce",
    "3-ft.-diameter disk of force": "Disco di forza di 90 cm di diametro",
    "Corpse touched": "Cadavere toccato",
    "Illusory sounds": "Suoni illusori",
    "Living humanoid touched": "Umanoide vivente toccato",
    "2d4 fresh berries touched": "2d4 bacche fresche toccate",
    "Your mount touched": "La tua cavalcatura toccata",
    "Ghostly hand": "Mano spettrale",
    "Melee weapon touched": "Arma da mischia toccata",
    "Tree touched": "Albero toccato",
    "Phantom watchdog": "Cane da guardia fantasma",
    "Flame in your palm": "Fiamma nel tuo palmo",
    "Corpse": "Cadavere",
    "Wooden quarterstaff touched": "Bastone di legno toccato",
    "Magic weapon of force": "Arma magica di forza",
    "Intelligible sound, usually speech": "Suono intelligibile, solitamente parlato",
    "One arrow of acid": "Una freccia acida",
    "One missile of acid": "Un missile acido",
    "One undead creature/level": "Una creatura non morta/livello",
    "One living creature with 5 or fewer HD": "Una creatura vivente con 5 o meno DV",
    "One creature of the humanoid type": "Una creatura di tipo umanoide",
    "One living creature per three levels": "Una creatura vivente per ogni tre livelli",
    "Up to one touched creature/level in a 30-ft.-radius burst": "Fino a una creatura toccata/livello entro scoppio con raggio di 9 m",
    "Creatures and objects within 10-ft.-radius spread": "Creature e oggetti entro diffusione con raggio di 3 m",
    "All allies within a 50-ft. burst, centered on you": "Tutti gli alleati entro scoppio con raggio di 15 m, centrato su di te",
    "All enemies within a 50-ft. burst, centered on you": "Tutti i nemici entro scoppio con raggio di 15 m, centrato su di te",
    "The caster and all allies within a 50-ft. burst, centered on the caster": "L'incantatore e tutti gli alleati entro scoppio con raggio di 15 m, centrato sull'incantatore",
    "One or more creatures or objects within a 40-ft.-radius burst": "Una o più creature od oggetti entro scoppio con raggio di 12 m",
    "Nonmagical, unattended object of up to 100 cu. ft./level": "Oggetto non magico, incustodito, fino a 2,8 m³/livello",
    "A creature or object of up to 1 cu. ft./level": "Una creatura od oggetto fino a 0,03 m³/livello",
    "One Small object per caster level; see text": "Un oggetto Piccolo/livello dell'incantatore; vedi testo",
    "One touched object weighing up to 5 lb./level and of up to 1 cu. ft./level": "Un oggetto toccato del peso fino a 2,5 kg/livello e fino a 0,03 m³/livello",
    "Metal equipment of one creature per two levels, no two of which can be more than 30 ft. apart; or 25 lb. of metal/level, all of which must be within a 30-ft. circle": "Equipaggiamento in metallo di una creatura per ogni due livelli, non più di 9 m l'una dall'altra; oppure 12 kg di metallo/livello, entro un cerchio di 9 m",
    "Metal equipment of one creature per two levels, no two of which can be more than 30 ft. apart; or 25 lb. of metal/level, none of which can be more than 30 ft. away from any of the rest": "Equipaggiamento in metallo di una creatura per ogni due livelli, non più di 9 m l'una dall'altra; oppure 12 kg di metallo/livello, non più di 9 m l'uno dall'altro",
    # Compound target phrases
    "Willing living creature touched": "Creatura vivente consenziente toccata",
    "Living creatures touched": "Creature viventi toccate",
    "Living creature touched": "Creatura vivente toccata",
    "One living creature touched per three levels": "Una creatura vivente toccata per ogni tre livelli",
    "Animal or tree touched": "Animale o albero toccato",
    "You and one other touched creature per three levels": "Te stesso e una altra creatura toccata per ogni tre livelli",
    "You and one touched creature per three levels": "Te stesso e una creatura toccata per ogni tre livelli",
    "You and touched objects or other willing creatures": "Te stesso e oggetti toccati o altre creature consenzienti",
    "You plus one willing creature per three levels, no two of which can be more than 30 ft. apart": "Te stesso più una creatura consenziente per ogni tre livelli, non più di 9 m l'una dall'altra",
    "One primary target, plus one secondary target/level (each of which must be within 30 ft.\n      of the primary target)": "Un bersaglio primario, più un bersaglio secondario/livello (ciascuno entro 9 m dal bersaglio primario)",
    "One primary target, plus one secondary target/level (each of which must be within 30 ft. of the primary target)": "Un bersaglio primario, più un bersaglio secondario/livello (ciascuno entro 9 m dal bersaglio primario)",
    "One weapon or fifty projectiles, all of which must be in contact with each other at the\n      time of casting": "Un'arma o cinquanta proiettili, tutti in contatto l'uno con l'altro al momento del lancio",
    "One weapon or fifty projectiles, all of which must be in contact with each other at the time of casting": "Un'arma o cinquanta proiettili, tutti in contatto l'uno con l'altro al momento del lancio",
    "One living creature/level, no two of which may be more than 30 ft. apart": "Una creatura vivente/livello, non più di 9 m l'una dall'altra",
    "One willing living creature per three levels, no two of which may be more than 30 ft.\n      apart": "Una creatura vivente consenziente per ogni tre livelli, non più di 9 m l'una dall'altra",
    "One willing living creature per three levels, no two of which may be more than 30 ft. apart": "Una creatura vivente consenziente per ogni tre livelli, non più di 9 m l'una dall'altra",
    "One creature plus one additional creature per four levels, no two of which can be more\n      than 30 ft. apart": "Una creatura più un'altra per ogni quattro livelli, non più di 9 m l'una dall'altra",
    "One creature plus one additional creature per four levels, no two of which can be more than 30 ft. apart": "Una creatura più un'altra per ogni quattro livelli, non più di 9 m l'una dall'altra",
    "Plants in a 40-ft.-radius spread": "Vegetali in una diffusione con raggio di 12 m",
    "Object touched or up to 5 sq. ft./level": "Oggetto toccato o fino a 0,5 m²/livello",
    "40-ft. radius emanating from the touched point": "Emanazione con raggio di 12 m dal punto toccato",
    "Line-shaped gust of severe wind emanating out from you to the extreme of the range": "Raffica di vento forte a forma di linea che emana da te fino al limite del raggio di azione",
    "One swarm of bats, rats, or spiders": "Uno sciame di pipistrelli, topi o ragni",
    "One swarm of centipedes per two levels": "Uno sciame di centopiedi per ogni due livelli",
    "Ten or more levitating eyes": "Dieci o più occhi levitanti",
    "Line from your hand": "Linea dalla tua mano",
    "Cloud spreads in 20-ft. radius from you, 20 ft. high": "Nube si diffonde in un raggio di 6 m da te, 6 m di altezza",
    "60-ft. line from you": "Linea di 18 m da te",
    "1 cu. ft./level of contaminated food and water": "0,03 m³/livello di cibo e acqua contaminati",
    "Object weighing up to 30 lb. or portal that can be opened or closed": "Oggetto del peso fino a 15 kg o portale che può essere aperto o chiuso",
    "Touched nonmagical circle of vine, rope, or thong with a 2 ft. diameter + 2 ft./level": "Cerchio non magico toccato di liana, corda o cinghia con 60 cm di diametro + 60 cm/livello",
    "One touched piece of wood no larger than 10 cu. ft. + 1 cu. ft./level": "Un pezzo di legno toccato non più grande di 0,3 m³ + 0,03 m³/livello",
    "One living creature per three levels, no two of which may be more than 30 ft. apart": "Una creatura vivente per ogni tre livelli, non più di 9 m l'una dall'altra",
    "Up to three elementals or outsiders, totaling no more than 12 HD, no two of which can be\n      more than 30 ft. apart when they appear": "Fino a tre elementali o esterni, per un totale di non più di 12 DV, non più di 9 m l'uno dall'altro quando appaiono",
    "Up to three elementals or outsiders, totaling no more than 12 HD, no two of which can be more than 30 ft. apart when they appear": "Fino a tre elementali o esterni, per un totale di non più di 12 DV, non più di 9 m l'uno dall'altro quando appaiono",
    "Up to three elementals or outsiders, totaling no more than 18 HD, no two of which can be\n      more than 30 ft. apart when they appear.": "Fino a tre elementali o esterni, per un totale di non più di 18 DV, non più di 9 m l'uno dall'altro quando appaiono",
    "Up to three elementals or outsiders, totaling no more than 18 HD, no two of which can be more than 30 ft. apart when they appear.": "Fino a tre elementali o esterni, per un totale di non più di 18 DV, non più di 9 m l'uno dall'altro quando appaiono",
    "Several living creatures, no two of which may be more than 30 ft. apart": "Diverse creature viventi, non più di 9 m l'una dall'altra",
    "Any number of creatures, no two of which can be more than 30 ft. apart": "Un numero qualsiasi di creature, non più di 9 m l'una dall'altra",
    "One called elemental or outsider of 6 HD or less": "Un elementale o esterno chiamato di 6 DV o meno",
    "One called creature per level": "Una creatura chiamata/livello",
    "Water breathing creatures touched": "Creature toccate che respirano sott'acqua",
    # More compound phrases
    "Living creatures, no two of which can be more than 60 ft. apart": "Creature viventi, non più di 18 m l'una dall'altra",
    "One or more humanoid creatures, no two of which can be more than 30 ft. apart": "Una o più creature umanoidi, non più di 9 m l'una dall'altra",
    "10-ft.-radius spherical emanation, centered on you": "Emanazione sferica con raggio di 3 m, centrata su di te",
    "20-ft.-radius spherical emanation, centered on you": "Emanazione sferica con raggio di 6 m, centrata su di te",
    "10-ft.-radius emanation centered on you": "Emanazione con raggio di 3 m centrata su di te",
    "Creatures and objects within 10-ft.-radius spread centered on you": "Creature e oggetti entro diffusione con raggio di 3 m centrata su di te",
    "One door, box, or chest with an area of up to 10 sq. ft./level": "Una porta, scrigno o scrigno con un'area fino a 1 m²/livello",
    "One portal, up to 20 sq. ft./level": "Un portale, fino a 2 m²/livello",
    "10-ft. hand": "Mano di 3 m",
    "One fire-based magic item": "Un oggetto magico basato sul fuoco",
    "One 20-ft. cube/level (S) or one fire-based magic item": "Un cubo di 6 m/livello (F) o un oggetto magico basato sul fuoco",
    "All magical effects and magic items within a 40-ft.-radius burst": "Tutti gli effetti magici e gli oggetti magici entro scoppio con raggio di 12 m",
    "Cylinder (10-ft. radius, 40 ft. high)": "Cilindro (raggio di 3 m, 12 m di altezza)",
    "One nonmagical ferrous object (or the volume of the object within 3 ft. of the touched point) or one ferrous creature": "Un oggetto ferroso non magico (o il volume dell'oggetto entro 90 cm dal punto toccato) o una creatura ferrosa",
    "One chest and up to 1 cu. ft. of goods/caster level": "Uno scrigno e fino a 0,03 m³ di beni/livello dell'incantatore",
    "One touched piece of rope from 5 to 30 ft. long": "Un pezzo di corda toccato, lungo da 1,5 a 9 m",
    "One Small wooden object/level, all within a 20-ft. radius": "Un oggetto di legno Piccolo/livello, tutti entro un raggio di 6 m",
    "Wall of thorny brush, up to one 10-ft. cube/level (S)": "Muro di arbusti spinosi, fino a un cubo di 3 m/livello (F)",
    "Up to four lights, all within a 10-ft.-radius area": "Fino a quattro luci, tutte entro un'area con raggio di 3 m",
    "One personal rune or mark, all of which must fit within 1 sq. ft.": "Un marchio o segno personale, tutto entro 900 cm²",
    "One or more extraplanar creatures, no two of which can be more than 30 ft. apart": "Una o più creature extraplanari, non più di 9 m l'una dall'altra",
    "One willing animal of Small, Medium, Large, or Huge size": "Un animale consenziente di taglia Piccola, Media, Grande o Enorme",
    "Creature or item touched": "Creatura o oggetto toccato",
    "Up to one touched creature/level": "Fino a una creatura toccata/livello",
    "One object of up to 10 cu. ft./ level": "Un oggetto fino a 0,3 m³/livello",
    "One object of up to 1 lb.": "Un oggetto fino a 0,5 kg",
    "An invisible, mindless, shapeless servant": "Un servitore invisibile, privo di mente e senza forma",
    "One invisible, mindless, shapeless servant": "Un servitore invisibile, privo di mente e senza forma",
    "Armor or shield touched": "Armatura o scudo toccato",
    "1-ft.-diameter/level sphere, centered around creatures or objects": "Sfera di 30 cm di diametro/livello, centrata su creature o oggetti",
    "One creature with 150 hp or less": "Una creatura con 150 pf o meno",
    "One creature with 100 hp or less": "Una creatura con 100 pf o meno",
    "One creature with 200 hp or less": "Una creatura con 200 pf o meno",
    "One summoned creature": "Una creatura evocata",
    "One touched object weighing up to 5 lb./level and of up to 1 cu. ft./level": "Un oggetto toccato del peso fino a 2,5 kg/livello e fino a 0,03 m³/livello",
    "One touched object of up to 5 lb./level and of up to 1 cu. ft./level": "Un oggetto toccato fino a 2,5 kg/livello e 0,03 m³/livello",
    "Up to one 10-ft. cube/level (S)": "Fino a un cubo di 3 m/livello (F)",
    "One creature per level touched": "Una creatura/livello toccata",
}

TARGET_TOKEN_MAP = {
    # Shape/geometry
    "radius spread": "diffusione con raggio",
    "radius burst": "scoppio con raggio",
    "radius emanation": "emanazione con raggio",
    "-radius spread": " diffusione con raggio",
    "-radius burst": " scoppio con raggio",
    "-radius emanation": " emanazione con raggio",
    "Cone-shaped": "A cono",
    "cone-shaped": "a cono",
    "centered on you": "centrata su di te",
    "centered on a point in space": "centrata su un punto nello spazio",
    "centered on a creature": "centrata su una creatura",
    "spread": "diffusione",
    "burst": "scoppio",
    "emanation": "emanazione",
    # Size references (ft → m)
    "5-ft.": "1,5 m",
    "10-ft.": "3 m",
    "15-ft.": "4,5 m",
    "20-ft.": "6 m",
    "30-ft.": "9 m",
    "40-ft.": "12 m",
    "50-ft.": "15 m",
    "60-ft.": "18 m",
    "80-ft.": "24 m",
    "100-ft.": "30 m",
    "120-ft.": "36 m",
    # Creature vocabulary
    "creature touched": "creatura toccata",
    "living creature": "creatura vivente",
    "willing creature": "creatura consenziente",
    "creature": "creatura",
    "creatures": "creature",
    "One": "Una",
    "one": "una",
    "object touched": "oggetto toccato",
    "object": "oggetto",
    "objects": "oggetti",
    "per level": "/livello",
    "/level": "/livello",
    "per caster level": "/livello dell'incantatore",
    "/caster level": "/livello dell'incantatore",
    "see text": "vedi testo",
    "See text": "Vedi testo",
    " or ": " o ",
    " and ": " e ",
    " no two of which can be more than ": ", non più di ",
    " apart": " l'una dall'altra",
    "up to": "fino a",
    "Up to": "Fino a",
    "Cloud spreads in": "Nube si diffonde in",
    "Fog spreads in": "Nebbia si diffonde in",
    " high": " di altezza",
    "long": "di lunghezza",
    "Wall": "Muro",
    "wall": "muro",
    "Cube": "Cubo",
    "cube": "cubo",
    "cylinder": "cilindro",
    "Line": "Linea",
    "line": "linea",
    "Personal": "Personale",
    # Size categories
    "Gargantuan": "Mastodontica",
    "Colossal": "Colossale",
    "Huge": "Enorme",
    "Large": "Grande",
    "Small": "Piccola",
    "Tiny": "Minuta",
    "Diminutive": "Minuscola",
    "Fine": "Piccolissima",
    "Medium": "Media",
    "or smaller": "o più piccola",
    "or larger": "o più grande",
    "or less": "o meno",
    "or fewer": "o meno",
    # Numbers
    "two": "due",
    "three": "tre",
    "four": "quattro",
    "five": "cinque",
    "six": "sei",
    "seven": "sette",
    "eight": "otto",
    "nine": "nove",
    "ten": "dieci",
    "fifty": "cinquanta",
    # Creature types
    "animals": "animali",
    "animal": "animale",
    "humanoids": "umanoidi",
    "humanoid": "umanoide",
    "undead": "non morta",
    "plants": "vegetali",
    "plant": "vegetale",
    "elementals": "elementali",
    "elemental": "elementale",
    "outsiders": "esterni",
    "outsider": "esterno",
    # Vocabulary
    "touched": "toccata",
    "summoned creatures": "creature evocate",
    "summoned": "evocata",
    "all allies": "tutti gli alleati",
    "All allies": "Tutti gli alleati",
    "all enemies": "tutti i nemici",
    "All enemies": "Tutti i nemici",
    "allies": "alleati",
    "enemies": "nemici",
    "weapon": "arma",
    "weapons": "armi",
    "nonmagical": "non magico",
    "projectiles": "proiettili",
    "corpses": "cadaveri",
    "corpse": "cadavere",
    "equipment": "equipaggiamento",
    "metal": "metallo",
    "within": "entro",
    "the caster": "l'incantatore",
    "The caster": "L'incantatore",
    "caster": "incantatore",
    "HD": "DV",
    " with ": " con ",
    " from ": " da ",
    " must be ": " devono essere ",
    " of each other": " l'uno dall'altro",
    "all of which must fit within": "tutti devono stare entro",
    "all of which must be in contact with each other at the time of casting": "tutti in contatto l'uno con l'altro al momento del lancio",
    # Geometry
    "radius": "raggio",
    "circle": "cerchio",
    "diameter": "diametro",
    "sphere": "sfera",
    "deep": "di profondità",
    "square": "quadrato con lato",
    # Units
    "25 lb.": "12 kg",
    "5 lb.": "2,5 kg",
    "10 lb.": "5 kg",
    "50 lb.": "25 kg",
    "100 lb.": "50 kg",
    "lb.": "kg",
    "cu. ft.": "m³",
    "sq. ft.": "m²",
    # Structural
    "levels": "livelli",
    "each": "ciascuno",
    "per two levels": "per ogni due livelli",
    "per three levels": "per ogni tre livelli",
    "per four levels": "per ogni quattro livelli",
    "weighing up to": "del peso fino a",
    "weighing": "del peso di",
    " fewer than ": " meno di ",
    " more than ": " più di ",
    " less than ": " meno di ",
    # Remaining structural words
    "from you": "da te",
    "from your hand": "dalla tua mano",
    "your": "tuo",
    "You": "Te stesso",
    "you": "te",
    " plus ": " più ",
    " other ": " altra ",
    "any number of": "un numero qualsiasi di",
    "Any number of": "Un numero qualsiasi di",
    "Several": "Diverse",
    "several": "diverse",
    " called ": " chiamata ",
    " may be ": " possano essere ",
    " no two of which may be ": ", non più di ",
    " no two of which can be ": ", non più di ",
    "no more than": "non più di",
    "totaling": "per un totale di",
    "when they appear": "quando appaiono",
    " additional ": " aggiuntiva ",
    " contaminated ": " contaminato ",
    " food ": " cibo ",
    " water": " acqua",
    " point": " punto",
    "Plants": "Vegetali",
    "Living": "Vivente",
    "Willing": "Consenziente",
    "Creatures": "Creature",
    "Objects": "Oggetti",
    "Object": "Oggetto",
    " portal": " portale",
    " item": " oggetto",
    " items": " oggetti",
    " hand": " mano",
    "Cylinder": "Cilindro",
    " wooden": " di legno",
    " ferrous": " ferroso",
    " thorny brush": " arbusti spinosi",
    " piece of wood": " pezzo di legno",
    " piece of rope": " pezzo di corda",
    " chest": " scrigno",
    " goods": " beni",
    " door": " porta",
    " box": " scatola",
    " rune": " runa",
    " mark": " segno",
    " personal ": " personale ",
    "extraplanar": "extraplanare",
    " size": " taglia",
    " range": " raggio di azione",
    " magical effects": " effetti magici",
    " magic items": " oggetti magici",
    " magic item": " oggetto magico",
    "spherical emanation": "emanazione sferica",
    "invisible": "invisibile",
    "mindless": "privo di mente",
    "shapeless": "senza forma",
    "servant": "servitore",
    "armor": "armatura",
    "Armor": "Armatura",
    "shield": "scudo",
    "Shield": "Scudo",
    " hp ": " pf ",
    " centered around ": " centrata su ",
    " centered on ": " centrata su ",
}


def convert_ft_in_string(val):
    """Convert X ft. patterns to X m in a string."""
    def repl(m):
        feet = int(m.group(1))
        meters = round(feet * 0.3, 1)
        # Use comma for Italian decimal separator
        meters_str = str(meters).replace('.', ',')
        if meters_str.endswith(',0'):
            meters_str = meters_str[:-2]
        return f"{meters_str} m"
    return re.sub(r'(\d+)\s*ft\.', repl, val)


def translate_target_area_effect(val):
    if not val:
        return None
    # Normalize whitespace for matching (SRD values may have newlines + spaces)
    val_norm = re.sub(r"\s+", " ", val).strip()
    # Direct match
    if val_norm in TARGET_DIRECT_MAP:
        return TARGET_DIRECT_MAP[val_norm]
    if val in TARGET_DIRECT_MAP:
        return TARGET_DIRECT_MAP[val]
    # Token replacement
    result = val_norm
    # Replace tokens (longer first)
    ordered = sorted(TARGET_TOKEN_MAP.items(), key=lambda x: -len(x[0]))
    for en, it in ordered:
        result = result.replace(en, it)
    # Convert remaining ft. to m
    result = convert_ft_in_string(result)
    # Clean up double spaces from token replacements
    result = re.sub(r"\s{2,}", " ", result).strip()
    return result if result != val_norm else None


# ── Monster field mappings ───────────────────────────────────────────────

SIZE_MAP = {
    "Fine": "Piccolissima",
    "Diminutive": "Minuscola",
    "Tiny": "Minuta",
    "Small": "Piccola",
    "Medium": "Media",
    "Large": "Grande",
    "Huge": "Enorme",
    "Gargantuan": "Mastodontica",
    "Colossal": "Colossale",
}

CREATURE_TYPE_MAP = {
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
}

SUBTYPE_MAP = {
    "Air": "Aria",
    "Aquatic": "Acquatico",
    "Augmented": "Potenziato",
    "Chaotic": "Caotico",
    "Cold": "Freddo",
    "Earth": "Terra",
    "Evil": "Malvagio",
    "Extraplanar": "Extraplanare",
    "Fire": "Fuoco",
    "Good": "Buono",
    "Incorporeal": "Incorporeo",
    "Lawful": "Legale",
    "Native": "Nativo",
    "Shapechanger": "Mutaforma",
    "Swarm": "Sciame",
    "Water": "Acqua",
    "Angel": "Angelo",
    "Archon": "Arconte",
    "Baatezu": "Baatezu",
    "Demon": "Demone",
    "Devil": "Diavolo",
    "Eladrin": "Eladrin",
    "Goblinoid": "Goblinoide",
    "Gnoll": "Gnoll",
    "Reptilian": "Rettile",
    "Human": "Umano",
    "Elf": "Elfo",
    "Orc": "Orco",
    "Dwarf": "Nano",
    "Tanar'ri": "Tanar'ri",
}


def translate_monster_type(val):
    """Translate 'Size Type (Subtype)' monster type string."""
    if not val:
        return None
    # Many monster entries have non-standard formats
    # Check if it starts with a known size
    m = re.match(r'^(Fine|Diminutive|Tiny|Small|Medium|Large|Huge|Gargantuan|Colossal)\s+(.+)$', val)
    if not m:
        return None

    size_en = m.group(1)
    rest = m.group(2)
    size_it = SIZE_MAP.get(size_en, size_en)

    # Split type and subtype
    m2 = re.match(r'^(.+?)\s*\(([^)]+)\)(.*)$', rest)
    if m2:
        type_en = m2.group(1).strip()
        subtypes_en = m2.group(2).strip()
        trailing = m2.group(3).strip()

        type_it = CREATURE_TYPE_MAP.get(type_en, type_en)

        # Translate subtypes (comma-separated)
        sub_parts = [s.strip() for s in subtypes_en.split(",")]
        sub_trans = [SUBTYPE_MAP.get(s, s) for s in sub_parts]
        subtypes_it = ", ".join(sub_trans)

        result = f"{size_it} {type_it} ({subtypes_it})"
        if trailing:
            result += " " + trailing
        return result
    else:
        type_en = rest.strip()
        type_it = CREATURE_TYPE_MAP.get(type_en, type_en)
        return f"{size_it} {type_it}"


ALIGN_TOKEN_MAP = {
    "Always": "Sempre",
    "Usually": "Solitamente",
    "Often": "Spesso",
    "Any": "Qualsiasi",
    "chaotic": "caotico",
    "lawful": "legale",
    "neutral": "neutrale",
    "evil": "malvagio",
    "good": "buono",
    "Evil": "Malvagio",
    "(any)": "(qualsiasi)",
}


def translate_alignment(val):
    if not val:
        return None
    result = val
    # Longer tokens first
    ordered = sorted(ALIGN_TOKEN_MAP.items(), key=lambda x: -len(x[0]))
    for en, it in ordered:
        result = result.replace(en, it)
    # Handle parenthetical notes
    result = result.replace("same as creator", "uguale al creatore")
    return result if result != val else None


ENVIRONMENT_TOKEN_MAP = {
    "Any": "Qualsiasi",
    "Temperate": "Temperato",
    "Warm": "Caldo",
    "Cold": "Freddo",
    "Tropical": "Tropicale",
    "aquatic": "acquatico",
    "forests": "foreste",
    "forest": "foresta",
    "hills": "colline",
    "mountains": "montagne",
    "mountain": "montagna",
    "plains": "pianure",
    "marshes": "paludi",
    "marsh": "palude",
    "deserts": "deserti",
    "desert": "deserto",
    "underground": "sotterraneo",
    "land": "terra",
    "ocean": "oceano",
    "water": "acqua",
    " and ": " e ",
    " or ": " o ",
    "plane": "piano",
    "-aligned": "",
    "A lawful evil": "Un piano legale malvagio",
    "A chaotic evil": "Un piano caotico malvagio",
    "A chaotic good": "Un piano caotico buono",
    "A lawful good": "Un piano legale buono",
    "A neutral evil": "Un piano neutrale malvagio",
}


def translate_environment(val):
    if not val:
        return None
    result = val
    # Handle planar environments first
    for en, it in sorted(ENVIRONMENT_TOKEN_MAP.items(), key=lambda x: -len(x[0])):
        result = result.replace(en, it)
    return result if result != val else None


ORGANIZATION_TOKEN_MAP = {
    "Solitary": "Solitario",
    "solitary": "solitario",
    "pair": "coppia",
    "Pair": "Coppia",
    "pack": "branco",
    "gang": "banda",
    "band": "banda",
    "flock": "stormo",
    "herd": "mandria",
    "swarm": "sciame",
    "colony": "colonia",
    "squad": "squadra",
    "troop": "truppa",
    "company": "compagnia",
    "clutch": "nidiata",
    "brood": "covata",
    "pride": "branco",
    "hunting party": "gruppo di caccia",
    "patrol": "pattuglia",
    "wing": "stormo",
    "flight": "stormo",
    "cluster": "gruppo",
    "nest": "nido",
    "or": "o",
}


def translate_organization(val):
    if not val:
        return None
    result = val
    for en, it in sorted(ORGANIZATION_TOKEN_MAP.items(), key=lambda x: -len(x[0])):
        result = result.replace(en, it)
    return result if result != val else None


# ── Feat field mappings ──────────────────────────────────────────────────

FEAT_TYPE_MAP = {
    "General": "Generale",
    "Metamagic": "Metamagico",
    "Item Creation": "Creazione Oggetti",
    "Special": "Speciale",
    "Fighter Bonus Feat": "Talento Bonus Guerriero",
}


# ── Class alignment translations ─────────────────────────────────────────

CLASS_ALIGNMENT_MAP = {
    "Any.": "Qualsiasi.",
    "Any nonlawful.": "Qualsiasi non legale.",
    "Any lawful.": "Qualsiasi legale.",
    "Any evil.": "Qualsiasi malvagio.",
    "Any good.": "Qualsiasi buono.",
    "Any chaotic.": "Qualsiasi caotico.",
    "Any nonchaotic.": "Qualsiasi non caotico.",
    "Any nonevil.": "Qualsiasi non malvagio.",
    "Any nongood.": "Qualsiasi non buono.",
    "Any nonlawful and nongood.": "Qualsiasi non legale e non buono.",
    "Lawful good.": "Legale buono.",
    "Neutral.": "Neutrale.",
}


# ── Main logic ───────────────────────────────────────────────────────────

def load_json(path):
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_overlay(overlay, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(overlay, f, ensure_ascii=False, indent=2)
        f.write("\n")


def merge_field(existing_entry, field, value):
    """Add a translated field only if not already present."""
    if field not in existing_entry and value is not None:
        existing_entry[field] = value
        return True
    return False


def translate_spells(data_dir):
    base = load_json(os.path.join(data_dir, "spells.json"))
    overlay_path = os.path.join(data_dir, "i18n", "it", "spells.json")
    overlay = load_json(overlay_path)

    # Index by slug
    overlay_map = {}
    for entry in overlay:
        slug = entry.get("slug")
        if slug:
            overlay_map[slug] = entry

    added = 0
    warnings = []

    for spell in base:
        slug = spell["slug"]
        if slug not in overlay_map:
            overlay_map[slug] = {"slug": slug}

        entry = overlay_map[slug]

        # Descriptor
        t = translate_descriptor(spell.get("descriptor"))
        if merge_field(entry, "descriptor", t):
            added += 1

        # Spell resistance
        t = translate_spell_resistance(spell.get("spell_resistance"))
        if merge_field(entry, "spell_resistance", t):
            added += 1

        # Saving throw
        t = translate_saving_throw(spell.get("saving_throw"))
        if merge_field(entry, "saving_throw", t):
            added += 1

        # Casting time
        ct = spell.get("casting_time")
        t = CASTING_TIME_MAP.get(ct)
        if merge_field(entry, "casting_time", t):
            added += 1
        elif ct and "casting_time" not in entry:
            warnings.append(f"  casting_time: {ct}")

        # Range
        t = translate_range(spell.get("range"))
        if merge_field(entry, "range", t):
            added += 1
        elif spell.get("range") and "range" not in entry:
            warnings.append(f"  range: {spell['range']}")

        # Duration
        t = translate_duration(spell.get("duration"))
        if merge_field(entry, "duration", t):
            added += 1

        # Components
        t = translate_components(spell.get("components"))
        if merge_field(entry, "components", t):
            added += 1

        # Level
        t = translate_level(spell.get("level"))
        if merge_field(entry, "level", t):
            added += 1

        # Target/Area/Effect
        t = translate_target_area_effect(spell.get("target_area_effect"))
        if merge_field(entry, "target_area_effect", t):
            added += 1

    # Rebuild overlay as list sorted by slug
    result = sorted(overlay_map.values(), key=lambda x: x.get("slug", ""))
    save_overlay(result, overlay_path)

    if warnings:
        unique_warnings = sorted(set(warnings))
        print(f"  WARNINGS ({len(unique_warnings)} untranslated values):")
        for w in unique_warnings[:20]:
            print(f"    {w}")

    print(f"  Spells: {added} new field translations added")
    return added


def translate_monsters(data_dir):
    base = load_json(os.path.join(data_dir, "monsters.json"))
    overlay_path = os.path.join(data_dir, "i18n", "it", "monsters.json")
    overlay = load_json(overlay_path)

    overlay_map = {}
    for entry in overlay:
        slug = entry.get("slug")
        if slug:
            overlay_map[slug] = entry

    added = 0

    for monster in base:
        slug = monster["slug"]
        if slug not in overlay_map:
            overlay_map[slug] = {"slug": slug}

        entry = overlay_map[slug]

        # Type
        t = translate_monster_type(monster.get("type"))
        if merge_field(entry, "type", t):
            added += 1

        # Alignment
        t = translate_alignment(monster.get("alignment"))
        if merge_field(entry, "alignment", t):
            added += 1

        # Environment
        t = translate_environment(monster.get("environment"))
        if merge_field(entry, "environment", t):
            added += 1

        # Organization
        t = translate_organization(monster.get("organization"))
        if merge_field(entry, "organization", t):
            added += 1

    result = sorted(overlay_map.values(), key=lambda x: x.get("slug", ""))
    save_overlay(result, overlay_path)
    print(f"  Monsters: {added} new field translations added")
    return added


def translate_feats(data_dir):
    base = load_json(os.path.join(data_dir, "feats.json"))
    overlay_path = os.path.join(data_dir, "i18n", "it", "feats.json")
    overlay = load_json(overlay_path)

    overlay_map = {}
    for entry in overlay:
        slug = entry.get("slug")
        if slug:
            overlay_map[slug] = entry

    added = 0

    for feat in base:
        slug = feat["slug"]
        if slug not in overlay_map:
            overlay_map[slug] = {"slug": slug}

        entry = overlay_map[slug]

        # Type
        t = FEAT_TYPE_MAP.get(feat.get("type"))
        if merge_field(entry, "type", t):
            added += 1

    result = sorted(overlay_map.values(), key=lambda x: x.get("slug", ""))
    save_overlay(result, overlay_path)
    print(f"  Feats: {added} new field translations added")
    return added


def translate_classes(data_dir):
    base = load_json(os.path.join(data_dir, "classes.json"))
    overlay_path = os.path.join(data_dir, "i18n", "it", "classes.json")
    overlay = load_json(overlay_path)

    overlay_map = {}
    for entry in overlay:
        slug = entry.get("slug")
        if slug:
            overlay_map[slug] = entry

    added = 0

    for cls in base:
        slug = cls["slug"]
        if slug not in overlay_map:
            overlay_map[slug] = {"slug": slug}

        entry = overlay_map[slug]

        # Alignment
        align = cls.get("alignment")
        t = CLASS_ALIGNMENT_MAP.get(align)
        if not t and align:
            t = translate_alignment(align)
        if merge_field(entry, "alignment", t):
            added += 1

    result = sorted(overlay_map.values(), key=lambda x: x.get("slug", ""))
    save_overlay(result, overlay_path)
    print(f"  Classes: {added} new field translations added")
    return added


CATEGORY_HANDLERS = {
    "spells": translate_spells,
    "monsters": translate_monsters,
    "feats": translate_feats,
    "classes": translate_classes,
}


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(os.path.dirname(script_dir), "data")

    category_filter = sys.argv[1] if len(sys.argv) > 1 else None

    if category_filter:
        if category_filter not in CATEGORY_HANDLERS:
            print(f"Unknown category: {category_filter}")
            print(f"Available: {', '.join(CATEGORY_HANDLERS.keys())}")
            sys.exit(1)
        handlers = {category_filter: CATEGORY_HANDLERS[category_filter]}
    else:
        handlers = CATEGORY_HANDLERS

    total = 0
    for cat, handler in handlers.items():
        total += handler(data_dir)

    print(f"\nTotal: {total} new translations added")


if __name__ == "__main__":
    main()
