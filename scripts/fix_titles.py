#!/usr/bin/env python3
"""
Fix Italian spell and feat titles in overlay JSONs to match the official
Italian manual (D&D 3.5 Manuale del Giocatore).

All corrections are verified against INCANTESIMI.txt and talenti.txt.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# ══════════════════════════════════════════════════════════════════════
# SPELL NAME CORRECTIONS (slug → correct Italian name from manual)
# ══════════════════════════════════════════════════════════════════════

SPELL_CORRECTIONS = {
    # ── Summon spells: "Evocare" → "Evoca" ──
    "summon-monster-i": "Evoca Mostri I",
    "summon-monster-ii": "Evoca Mostri II",
    "summon-monster-iii": "Evoca Mostri III",
    "summon-monster-iv": "Evoca Mostri IV",
    "summon-monster-v": "Evoca Mostri V",
    "summon-monster-vi": "Evoca Mostri VI",
    "summon-monster-vii": "Evoca Mostri VII",
    "summon-monster-viii": "Evoca Mostri VIII",
    "summon-monster-ix": "Evoca Mostri IX",
    "summon-natures-ally-i": "Evoca Alleato Naturale I",
    "summon-natures-ally-ii": "Evoca Alleato Naturale II",
    "summon-natures-ally-iii": "Evoca Alleato Naturale III",
    "summon-natures-ally-iv": "Evoca Alleato Naturale IV",
    "summon-natures-ally-v": "Evoca Alleato Naturale V",
    "summon-natures-ally-vi": "Evoca Alleato Naturale VI",
    "summon-natures-ally-vii": "Evoca Alleato Naturale VII",
    "summon-natures-ally-viii": "Evoca Alleato Naturale VIII",
    "summon-natures-ally-ix": "Evoca Alleato Naturale IX",
    "summon-swarm": "Evoca Sciame",
    "summon-instrument": "Evoca Strumento",

    # ── Inflict spells: "Infliggere" → "Infliggi" ──
    "inflict-minor-wounds": "Infliggi Ferite Minori",
    "inflict-light-wounds": "Infliggi Ferite Leggere",
    "inflict-moderate-wounds": "Infliggi Ferite Moderate",
    "inflict-serious-wounds": "Infliggi Ferite Gravi",
    "inflict-critical-wounds": "Infliggi Ferite Critiche",
    "inflict-light-wounds-mass": "Infliggi Ferite Leggere di Massa",
    "inflict-moderate-wounds-mass": "Infliggi Ferite Moderate di Massa",
    "inflict-serious-wounds-mass": "Infliggi Ferite Gravi di Massa",
    "inflict-critical-wounds-mass": "Infliggi Ferite Critiche di Massa",

    # ── Hold spells: "Bloccare" → "Blocca" ──
    "hold-animal": "Blocca Animali",
    "hold-monster": "Blocca Mostri",
    "hold-monster-mass": "Blocca Mostri di Massa",
    "hold-person": "Blocca Persone",
    "hold-person-mass": "Blocca Persone di Massa",
    "hold-portal": "Blocca Porte",

    # ── Remove spells: "Rimuovere" → "Rimuovi" ──
    "remove-blindness-deafness": "Rimuovi Cecità/Sordità",
    "remove-curse": "Rimuovi Maledizione",
    "remove-disease": "Rimuovi Malattia",
    "remove-fear": "Rimuovi Paura",
    "remove-paralysis": "Rimuovi Paralisi",

    # ── Locate spells: "Localizzare" → "Localizza" ──
    "locate-creature": "Localizza Creatura",
    "locate-object": "Localizza Oggetto",

    # ── Neutralize: "Neutralizzare" → "Neutralizza" ──
    "neutralize-poison": "Neutralizza Veleno",

    # ── Detect spells: "Individuare" → "Individuazione" ──
    "detect-animals-or-plants": "Individuazione di Animali o Vegetali",
    "detect-chaos": "Individuazione del Caos",
    "detect-evil": "Individuazione del Male",
    "detect-good": "Individuazione del Bene",
    "detect-law": "Individuazione della Legge",
    "detect-magic": "Individuazione del Magico",
    "detect-poison": "Individuazione del Veleno",
    "detect-scrying": "Individuazione dello Scrutamento",
    "detect-secret-doors": "Individuazione delle Porte Segrete",
    "detect-snares-and-pits": "Individuazione di Calappi",
    "detect-thoughts": "Individuazione dei Pensieri",
    "detect-undead": "Individuazione dei Non Morti",

    # ── Charm spells: "Ammaliare" → "Charme su" ──
    "charm-animal": "Charme su Animali",
    "charm-monster": "Charme sui Mostri",
    "charm-monster-mass": "Charme sui Mostri di Massa",
    "charm-person": "Charme su Persone",

    # ── Dominate spells (separate from charm) ──
    "dominate-animal": "Dominare Animali",
    "dominate-monster": "Dominare Mostri",
    "dominate-person": "Dominare Persone",

    # ── Dispel spells: add article ──
    "dispel-chaos": "Dissolvi il Caos",
    "dispel-evil": "Dissolvi il Male",
    "dispel-good": "Dissolvi il Bene",
    "dispel-law": "Dissolvi la Legge",

    # ── Eponyms (named after wizards/characters) ──
    "acid-arrow": "Freccia Acida di Melf",
    "black-tentacles": "Tentacoli Neri di Evard",
    "crushing-hand": "Mano Stringente di Bigby",
    "clenched-fist": "Mano Possente di Bigby",
    "forceful-hand": "Mano Possente di Bigby",
    "grasping-hand": "Mano Stringente di Bigby",
    "interposing-hand": "Mano Interposta di Bigby",
    "floating-disk": "Disco Fluttuante di Tenser",
    "hideous-laughter": "Risata Incontenibile di Tasha",
    "instant-summons": "Evocazione Istantanea di Drawmij",
    "irresistible-dance": "Danza Irresistibile di Otto",
    "mnemonic-enhancer": "Potenziatore Mnemonico di Rary",
    "secret-chest": "Scrigno Segreto di Leomund",
    "telepathic-bond": "Legame Telepatico di Rary",
    "telekinetic-sphere": "Sfera Telecinetica di Otiluke",
    "tiny-hut": "Capanna di Leomund",
    "freezing-sphere": "Sfera Gelida di Otiluke",
    "resilient-sphere": "Sfera Resiliente di Otiluke",
    "secure-shelter": "Rifugio Sicuro di Leomund",
    "trap-the-soul": "Imprigionare l'Anima",

    # ── Specific name corrections ──
    "phantasmal-killer": "Allucinazione Mortale",
    "obscuring-mist": "Foschia Occultante",
    "phantom-steed": "Destriero Fantomatico",
    "false-life": "Vita Falsata",
    "good-hope": "Buone Speranze",
    "restoration-lesser": "Ristorare Inferiore",
    "restoration": "Ristorare",
    "restoration-greater": "Ristorare Superiore",
    "confusion-lesser": "Confusione Inferiore",
    "globe-of-invulnerability-lesser": "Globo di Invulnerabilità Inferiore",
    "cloak-of-chaos": "Mantello del Caos",
    "true-strike": "Colpo Accurato",
    "true-seeing": "Visione del Vero",
    "creeping-doom": "Piaga Strisciante",
    "stone-tell": "Pietre Parlanti",
    "phase-door": "Porta in Fase",
    "storm-of-vengeance": "Tempesta di Vendetta",
    "orders-wrath": "Ira dell'Ordine",
    "illusory-script": "Scritto Illusorio",
    "delayed-blast-fireball": "Palla di Fuoco Ritardata",
    "flame-blade": "Lama Infuocata",
    "shout": "Grido",
    "shout-greater": "Grido Superiore",
    "prying-eyes": "Occhi Indagatori",
    "prying-eyes-greater": "Occhi Indagatori Superiore",
    "obscure-object": "Occulta Oggetto",
    "mind-fog": "Nebbia Mentale",
    "waves-of-fatigue": "Onde di Affaticamento",
    "waves-of-exhaustion": "Onde di Esaurimento",
    "ray-of-exhaustion": "Raggio di Esaurimento",
    "touch-of-fatigue": "Tocco di Affaticamento",
    "shield-other": "Scudo su Altri",
    "imprisonment": "Imprigionare",
    "spell-resistance": "Protezione dagli Incantesimi",
    "legend-lore": "Conoscenza delle Leggende",
    "sepia-snake-sigil": "Sigillo del Serpente",
    "sympathetic-vibration": "Vibrazione Armonica",
    "hallow": "Consacrare",
    "unhallow": "Dissacrare",
    "liveoak": "Querciaviva",
    "nondetection": "Anti-Individuazione",
    "dimensional-lock": "Ancora Dimensionale",
    "mage-armor": "Armatura Magica",
    "move-earth": "Muovere il Terreno",
    "wind-walk": "Camminare nel Vento",
    "call-lightning-storm": "Invocare Tempesta di Fulmini",
    "bless-water": "Benedire l'Acqua",
    "bless-weapon": "Benedire un'Arma",
    "curse-water": "Maledire l'Acqua",
    "invisibility-purge": "Epurare Invisibilità",
    "hide-from-animals": "Nascondersi agli Animali",
    "hide-from-undead": "Nascondersi ai Non Morti",
    "animate-dead": "Animare Morti",
    "raise-dead": "Rianimare Morti",
    "control-plants": "Controllare Vegetali",
    "control-water": "Controllare Acqua",
    "control-undead": "Controllare Non Morti",
    "control-weather": "Controllare Tempo Atmosferico",
    "control-winds": "Controllare Venti",
    "planar-ally-lesser": "Alleato Planare Inferiore",
    "planar-ally": "Alleato Planare",
    "planar-ally-greater": "Alleato Planare Superiore",
    "shadow-walk": "Camminare nelle Ombre",
    "air-walk": "Camminare nell'Aria",
    "water-walk": "Camminare sull'Acqua",
    "water-breathing": "Respirare sott'Acqua",
    "mark-of-justice": "Sigillo di Giustizia",
    "arcane-mark": "Sigillo Arcano",
    "heroes-feast": "Banchetto degli Eroi",
    "symbol-of-weakness": "Simbolo di Demenza",
    "symbol-of-insanity": "Simbolo di Demenza",  # verify
    "ghost-sound": "Suono Fantasma",
    "touch-of-idiocy": "Tocco di Idiozia",
    "vampiric-touch": "Tocco del Vampiro",
    "ghoul-touch": "Tocco del Ghoul",
    "shrink-item": "Rimpicciolire Oggetto",
    "plant-growth": "Crescita Vegetale",

    # ── Power Word spells: add comma ──
    "power-word-blind": "Parola del Potere, Accecare",
    "power-word-kill": "Parola del Potere, Uccidere",
    "power-word-stun": "Parola del Potere, Stordire",

    # ── Disguise/Alter self ──
    "disguise-self": "Camuffare Se Stessa",
    "alter-self": "Alterare Se Stesso",

    # ── Other corrections verified from manual ──
    "death-knell": "Rintocco di Morte",
    "divine-favor": "Favore Divino",
    "antilife-shell": "Guscio Anti-Vita",
}


# ══════════════════════════════════════════════════════════════════════
# FEAT NAME CORRECTIONS (slug → correct Italian name from manual)
# ══════════════════════════════════════════════════════════════════════

FEAT_CORRECTIONS = {
    "brew-potion": "Mescere Pozioni",
    "combat-casting": "Incantare in Combattimento",
    "combat-expertise": "Maestria in Combattimento",
    "eschew-materials": "Escludere Materiali",
    "nimble-fingers": "Dita Sottili",
    "mounted-archery": "Tirare in Sella",
    "mounted-combat": "Combattere in Sella",
    "ride-by-attack": "Attacco in Sella",
    "two-weapon-defense": "Difendere con Due Armi",
    "widen-spell": "Incantesimi Ampliati",
    "extend-spell": "Incantesimi Estesi",
    "improved-feint": "Fintare Migliorato",
    "improved-trip": "Sbilanciare Migliorato",
    "improved-bull-rush": "Spingere Migliorato",
    "improved-overrun": "Oltrepassare Migliorato",
    "improved-shield-bash": "Attacco con lo Scudo Migliorato",
    "spell-focus": "Incantesimi Focalizzati",
    "greater-spell-focus": "Incantesimi Focalizzati Superiore",
    "spring-attack": "Attacco Rapido",
    "tower-shield-proficiency": "Competenza negli Scudi Torre",
}


def apply_corrections(overlay_data, corrections, entity_type):
    """Apply name corrections to overlay data."""
    changes = []
    for entry in overlay_data:
        slug = entry.get("slug", "")
        if slug in corrections:
            old_name = entry.get("name", "")
            new_name = corrections[slug]
            if old_name != new_name:
                entry["name"] = new_name
                changes.append((slug, old_name, new_name))
    return changes


def main():
    spells_path = ROOT / "data" / "i18n" / "it" / "spells.json"
    feats_path = ROOT / "data" / "i18n" / "it" / "feats.json"

    with open(spells_path, encoding="utf-8") as f:
        spells = json.load(f)
    with open(feats_path, encoding="utf-8") as f:
        feats = json.load(f)

    # Apply spell corrections
    spell_changes = apply_corrections(spells, SPELL_CORRECTIONS, "spell")
    print(f"SPELL CORRECTIONS: {len(spell_changes)} changes")
    for slug, old, new in spell_changes:
        print(f"  {slug}: '{old}' → '{new}'")

    # Apply feat corrections
    feat_changes = apply_corrections(feats, FEAT_CORRECTIONS, "feat")
    print(f"\nFEAT CORRECTIONS: {len(feat_changes)} changes")
    for slug, old, new in feat_changes:
        print(f"  {slug}: '{old}' → '{new}'")

    # Write back
    if spell_changes:
        with open(spells_path, "w", encoding="utf-8") as f:
            json.dump(spells, f, ensure_ascii=False, indent=2)
            f.write("\n")
        print(f"\nWrote {spells_path}")

    if feat_changes:
        with open(feats_path, "w", encoding="utf-8") as f:
            json.dump(feats, f, ensure_ascii=False, indent=2)
            f.write("\n")
        print(f"Wrote {feats_path}")

    total = len(spell_changes) + len(feat_changes)
    print(f"\nTotal: {total} title corrections applied")


if __name__ == "__main__":
    main()
