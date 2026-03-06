#!/usr/bin/env python3
"""Fix OCR artifacts in target_area_effect values in the Italian overlay."""

import json
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
OVERLAY = REPO_ROOT / "data" / "i18n" / "it" / "spells.json"


def fix_ocr(slug, val):
    """Apply systematic regex fixes for common OCR errors."""
    orig = val

    # === OCR suffix errors ===
    val = val.replace("emanaziuna", "emanazione")
    val = val.replace("diffusiuna", "diffusione")
    val = val.replace("propagaziuna", "propagazione")
    val = re.sub(r"aziuna\b", "azione", val)

    # === OCR letter confusions ===
    val = re.sub(r"(\d+)\s*rn\b", r"\1 m", val)   # rn -> m
    val = re.sub(r"(\d+,?\d*)\s*tn\b", r"\1 m", val)  # tn -> m
    val = re.sub(r"propagazion e\b", "propagazione", val)

    # === Broken words (space in middle) ===
    val = re.sub(r"\bpe r\b", "per", val)
    val = re.sub(r"\bd i\b", "di", val)
    val = re.sub(r"\bch e\b", "che", val)
    val = re.sub(r"\bco n\b", "con", val)
    val = re.sub(r"\bu n\b", "un", val)
    val = re.sub(r"\bun a\b", "una", val)
    val = re.sub(r"\bde l\b", "del", val)
    val = re.sub(r"\bogn i\b", "ogni", val)
    val = re.sub(r"\btr e\b", "tre", val)
    val = re.sub(r"\bti n\b", "un", val)
    val = re.sub(r"\besser e\b", "essere", val)
    val = re.sub(r"\bposson o\b", "possono", val)
    val = re.sub(r"\bcentrat a\b", "centrata", val)
    val = re.sub(r"\btoccat i\b", "toccati", val)
    val = re.sub(r"\bconsenzient e\b", "consenziente", val)
    val = re.sub(r"\bproiettil i\b", "proiettili", val)
    val = re.sub(r"\bmoment o\b", "momento", val)
    val = re.sub(r"\barbust i\b", "arbusti", val)
    val = re.sub(r"\bcinghi a\b", "cinghia", val)
    val = re.sub(r"\blivell o\b", "livello", val)
    val = re.sub(r"\braggi o\b", "raggio", val)
    val = re.sub(r"\bl'un a\b", "l'una", val)
    val = re.sub(r"\bl'un o\b", "l'uno", val)
    val = re.sub(r"delraggio", "del raggio", val)
    val = re.sub(r"possonotrovarsi", "possono trovarsi", val)
    val = val.replace("api\u00f9tdi", "a pi\u00f9 di")
    val = val.replace("l' una-", "l'una")
    val = re.sub(r"Unacreatura", "Una creatura", val)
    val = val.replace("l'unadataltra", "l'una dall'altra")
    val = val.replace("viventiinstliesplosione", "viventi in un'esplosione")
    val = re.sub(r"pi\s*\u00f9u", "pi\u00f9", val)
    val = re.sub(r"pi \u00f9", "pi\u00f9", val)
    val = re.sub(r"pi\s+\u00f9\s", "pi\u00f9 ", val)
    val = re.sub(r"\btoscata\b", "toccata", val)
    val = re.sub(r"viventetoscata", "vivente toccata", val)
    val = re.sub(r"\balt ra\b", "altra", val)
    val = re.sub(r"\boggetto\u00b7solido\b", "oggetto solido", val)  # middle dot
    val = val.replace("oggetto\u00b7solido", "oggetto solido")

    # === Fix double spaces and trailing artifacts ===
    val = re.sub(r"\s{2,}", " ", val)
    val = re.sub(r"\s*\.\s*$", "", val)
    val = val.strip()

    return val


# Manual overrides for badly corrupted entries that can't be regex-fixed
MANUAL_OVERRIDES = {
    "animate-rope": "Un oggetto simile a una corda, lungo fino a 15 m + 1,5 m/livello; vedi testo",
    "barkskin": "Creatura vivente toccata",
    "faerie-fire": "Creature e oggetti entro una diffusione con raggio di 1,5 m",
    "animate-plants": "Una vegetale Grande per ogni tre livelli o tutti i vegetali entro raggio d'azione; vedi testo",
    "clone": "Un clone",
    "dictum": "Creature non legali entro una propagazione con raggio di 12 m centrata su di te",
    "erase": "Una pergamena o due pagine",
    "feather-fall": "Un oggetto o creatura in caduta libera di taglia Media o inferiore per livello, non pi\u00f9 di 6 m l'uno dall'altro",
    "illusory-wall": "Immagine di 30 cm x 3 m x 3 m",
    "levitate": "Te stesso o una creatura consenziente o un oggetto (peso totale fino a 50 kg/livello)",
    "lullaby": "Creature viventi entro un'esplosione del raggio di 3 m",
    "mage-hand": "Un oggetto non magico incustodito del peso fino a 2,5 kg",
    "mages-sword": "Una spada",
    "mages-magnificent-mansion": "Magione extradimensionale, fino a tre cubi con spigolo di 3 m per livello (F)",
    "meteor-swarm": "Quattro propagazioni del raggio di 12 m; vedi testo",
    "orders-wrath": "Creature non legali entro un'esplosione che riempie un cubo con spigolo di 9 m",
    "phantom-steed": "Una creatura quasi-reale simile a un cavallo",
    "project-image": "Un duplicato d'ombra",
    "pyrotechnics": "Una fonte di fuoco, fino a un cubo con spigolo di 6 m",
    "rainbow-pattern": "Luci colorate con una diffusione del raggio di 6 m",
    "sepia-snake-sigil": "Un libro o un'opera scritta toccata",
    "shadow-walk": "Fino a una creatura toccata per livello",
    "shillelagh": "Un randello o bastone di quercia non magico toccato",
    "secure-shelter": "Struttura con lato di 6 m",
    "sympathetic-vibration": "Una struttura autoportante",
    "resilient-sphere": "Sfera di 30 cm di diametro per livello, centrata su una creatura",
    "sequester": "Una creatura consenziente o oggetto (fino a un cubo con spigolo di 60 cm per livello) toccato",
    "rope-trick": "Un pezzo di corda toccato lungo da 1,5 m a 9 m",
    "locate-object": "Cerchio centrato su di te, con un raggio di 120 m + 12 m/livello",
    "circle-of-death": "Diverse creature viventi entro un'esplosione del raggio di 12 m",
    "animal-messenger": "Un animale Minuto",
    "implosion": "Una creatura corporea per round",
    "polymorph-any-object": "Una creatura, o un oggetto non magico di fino a 2,7 m\u00b3/livello",
    "transmute-rock-to-mud": "Fino a due cubi con spigolo di 3 m per livello (F)",
    "move-earth": "Terra in un'area fino a un quadrato con lato di 225 m e fino a 3 m di profondit\u00e0 (F)",
    "control-plants": "Fino a 2 DV/livello di creature vegetali, non pi\u00f9 di 9 m l'una dall'altra",
    "command-plants": "Fino a 2 DV/livello di creature vegetali, non pi\u00f9 di 9 m l'una dall'altra",
    "reincarnate": "Creatura morta toccata",
    "speak-with-dead": "Una creatura morta",
    "shocking-grasp": "Creatura o oggetto toccato",
    "stone-shape": "Pietra od oggetto di pietra toccato, fino a 270 dm\u00b3 + 27 dm\u00b3 per livello",
    "warp-wood": "1 oggetto di legno Piccolo per livello, tutti entro un raggio di 6 m",
    "tiny-hut": "Sfera del raggio di 6 m centrata sulla tua posizione",
    "summon-instrument": "Uno strumento musicale tenuto in mano evocato",
    "instant-summons": "Un oggetto del peso di 2,5 kg o meno la cui dimensione maggiore \u00e8 1,8 m o meno",
    "ironwood": "Un oggetto di legno di ferro del peso fino a 2,5 kg/livello",
    "detect-poison": "Una creatura, un oggetto, o un cubo con spigolo di 1,5 m",
    "nondetection": "Creatura o oggetto toccato",
    "neutralize-poison": "Creatura o oggetto di fino a 0,03 m\u00b3/livello toccato",
    "obscure-object": "Un oggetto toccato del peso fino a 50 kg/livello",
    "secret-page": "Pagina toccata, fino a 0,27 m\u00b2 di dimensione",
    "holy-aura": "Una creatura per livello entro un'esplosione del raggio di 6 m centrata sull'incantatore",
    "unholy-aura": "Una creatura per livello entro un'esplosione del raggio di 6 m centrata su di te",
    "cloak-of-chaos": "Una creatura per livello entro un'esplosione del raggio di 6 m centrata su di te",
    "explosive-runes": "Un oggetto toccato che non pesi pi\u00f9 di 5 kg",
    "owls-wisdom-mass": "Una creatura per livello, che non possono trovarsi a pi\u00f9 di 9 m l'una dall'altra",
    "reduce-person-mass": "Una creatura umanoide per livello, che non possono trovarsi a pi\u00f9 di 9 m l'una dall'altra",
    "teleport-object": "Un oggetto toccato del peso fino a 25 kg/livello e 0,08 m\u00b3/livello",
    "illusory-script": "Un oggetto toccato del peso non superiore a 5 kg",
    "minor-creation": "Oggetto non magico di materia vegetale inanimata fino a 27 dm\u00b3 per livello",
    "creeping-doom": "Tre o pi\u00f9 sciami striscianti, che non possono trovarsi a pi\u00f9 di 9 m l'uno dall'altro; vedi testo",
    "mislead": "Incantatore/duplicato illusorio",
    "transformation": "Incantatore",
    "command-undead": "Una creatura non morta",
    "control-weather": "Cerchio con raggio di 3 km centrato su di te; vedi testo",
    "magic-stone": "Fino a tre ciottoli toccati",
    "cure-critical-wounds-mass": "Una creatura per livello, non pi\u00f9 di 9 m l'una dall'altra",
    "dimension-door": "Incantatore e oggetti toccati oppure altre creature toccate consenzienti",
    "remove-paralysis": "Fino a quattro creature, non pi\u00f9 di 9 m l'una dall'altra",
    "invisibility-mass": "Un numero qualsiasi di creature, non pi\u00f9 di 54 m l'una dall'altra",
    "seeming": "Una creatura per ogni due livelli, non pi\u00f9 di 9 m l'una dall'altra",
    "spike-stones": "Un quadrato con lato di 6 m per livello",
    "wall-of-thorns": "Muro di arbusti spinosi, fino a un cubo con spigolo di 3 m per livello (F)",
    "produce-flame": "Fiamma nel palmo della mano dell'incantatore",
    "dispel-evil": "L'incantatore e una creatura malvagia di un altro piano toccata; oppure l'incantatore e un incantesimo malvagio su una creatura toccata",
    "disrupting-weapon": "Un'arma da mischia",
    "burning-hands": "Esplosione a forma di cono",
    "heroes-feast": "Banchetto per una creatura per livello",
}


def main():
    with open(OVERLAY, "r", encoding="utf-8") as f:
        data = json.load(f)

    changes = []

    for e in data:
        slug = e["slug"]
        if slug in MANUAL_OVERRIDES:
            old = e.get("target_area_effect", "")
            new = MANUAL_OVERRIDES[slug]
            if old != new:
                changes.append((slug, old, new))
                e["target_area_effect"] = new
        elif "target_area_effect" in e:
            old = e["target_area_effect"]
            new = fix_ocr(slug, old)
            if new != old:
                changes.append((slug, old, new))
                e["target_area_effect"] = new

    with open(OVERLAY, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"Fixed {len(changes)} target_area_effect values\n")
    for slug, old, new in sorted(changes):
        print(f"  {slug}:")
        print(f"    OLD: {old[:120]}")
        print(f"    NEW: {new[:120]}")
        print()


if __name__ == "__main__":
    main()
