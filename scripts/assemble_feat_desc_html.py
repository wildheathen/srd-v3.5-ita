#!/usr/bin/env python3
"""Assembla feat desc_html dai campi individuali già tradotti.

Per ogni feat che ha benefit/prerequisites/normal/special tradotti ma
manca di desc_html, ricostruisce il desc_html combinando i campi
con la stessa struttura HTML dell'inglese.

Usage:
    python scripts/assemble_feat_desc_html.py          # dry-run
    python scripts/assemble_feat_desc_html.py --apply   # scrive nell'overlay
"""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EN_PATH = ROOT / "data" / "feats.json"
IT_PATH = ROOT / "data" / "i18n" / "it" / "feats.json"

# Traduzioni delle label nelle sezioni desc_html
LABEL_MAP = {
    "Prerequisite": "Prerequisito",
    "Prerequisites": "Prerequisiti",
    "Benefit": "Beneficio",
    "Benefits": "Benefici",
    "Normal": "Normale",
    "Special": "Speciale",
}

# Traduzioni per le frasi introduttive (feats tipo "Choose a type of...")
INTRO_MAP = {
    "exotic-weapon-proficiency": "Scegli un tipo di arma esotica. Sai come usare quel tipo di arma esotica in combattimento.",
    "greater-spell-focus": "Scegli una scuola di magia a cui hai già applicato il talento Focalizzazione Magica.",
    "greater-weapon-focus": "Scegli un tipo di arma per il quale hai già selezionato Focalizzazione sull'Arma. Puoi anche scegliere combattere senz'armi o lottare come arma ai fini di questo talento.",
    "greater-weapon-specialization": "Scegli un tipo di arma per il quale hai già selezionato Specializzazione sull'Arma. Puoi anche scegliere combattere senz'armi o lottare come arma ai fini di questo talento.",
    "improved-critical": "Scegli un tipo di arma.",
    "improved-familiar": "Questo talento permette agli incantatori di acquisire un nuovo famiglio da una lista non standard, ma solo quando potrebbero normalmente acquisire un nuovo famiglio.",
    "martial-weapon-proficiency": "Scegli un tipo di arma da guerra. Sai come usare quel tipo di arma da guerra in combattimento.",
    "rapid-reload": "Scegli un tipo di balestra (a mano, leggera o pesante).",
    "skill-focus": "Scegli un'abilità.",
    "spell-focus": "Scegli una scuola di magia.",
    "two-weapon-fighting": None,  # has desc_html already
    "weapon-focus": "Scegli un tipo di arma. Puoi anche scegliere combattere senz'armi o lottare come arma ai fini di questo talento.",
    "weapon-specialization": "Scegli un tipo di arma per il quale hai già selezionato Focalizzazione sull'Arma. Puoi anche scegliere combattere senz'armi o lottare come arma ai fini di questo talento.",
}


def extract_en_sections(desc_html):
    """Estrae le sezioni dal desc_html EN, restituendo intro e sezioni strutturate."""
    if not desc_html:
        return None, []

    # Split per paragrafi
    paragraphs = re.split(r'(?=<p[\s>])', desc_html)
    paragraphs = [p.strip() for p in paragraphs if p.strip()]

    intro_parts = []
    sections = []

    for p in paragraphs:
        # Cerca label forte: <strong>Label:</strong>
        match = re.search(r'<strong>(Prerequisites?|Benefits?|Normal|Special)\s*:?\s*</strong>', p, re.IGNORECASE)
        if match:
            label = match.group(1)
            # Normalizza: "Prerequisites" -> "Prerequisites"
            sections.append(label)
        else:
            # È una intro (prima delle sezioni strutturate)
            if not sections:
                intro_parts.append(p)

    return intro_parts, sections


def build_desc_html(slug, en_feat, it_feat):
    """Costruisce desc_html IT dal template EN e dai campi IT tradotti."""
    en_desc = en_feat.get("desc_html", "")
    if not en_desc:
        return None, "no EN desc_html"

    intro_parts, en_sections = extract_en_sections(en_desc)

    parts = []

    # 1. Intro paragraph (se presente)
    if intro_parts:
        intro_it = INTRO_MAP.get(slug)
        if intro_it is None and slug not in INTRO_MAP:
            return None, f"intro non tradotta: {slug}"
        if intro_it:
            parts.append(f"<p>{intro_it}</p>")

    # 2. Sezioni strutturate
    field_map = {
        "Prerequisite": "prerequisites",
        "Prerequisites": "prerequisites",
        "Benefit": "benefit",
        "Benefits": "benefit",
        "Normal": "normal",
        "Special": "special",
    }

    for label in en_sections:
        field = field_map.get(label)
        if not field:
            continue

        it_value = it_feat.get(field)
        if not it_value:
            # Il campo non esiste nell'EN per questo feat (es. no prerequisites)
            en_value = en_feat.get(field)
            if not en_value:
                continue
            # Il campo esiste in EN ma non è tradotto in IT — skip
            return None, f"campo '{field}' non tradotto"

        it_label = LABEL_MAP.get(label, label)
        parts.append(f"<p><strong>{it_label}:</strong> {it_value}</p>")

    if not parts:
        return None, "nessun contenuto assemblato"

    return "\n".join(parts), None


def main():
    apply_mode = "--apply" in sys.argv

    with open(EN_PATH, encoding="utf-8") as f:
        en_feats = json.load(f)
    with open(IT_PATH, encoding="utf-8") as f:
        it_feats = json.load(f)

    it_by_slug = {f["slug"]: f for f in it_feats}
    en_by_slug = {f["slug"]: f for f in en_feats}

    assembled = 0
    replaced = 0
    skipped = []
    quality_issues = []

    for it_feat in it_feats:
        slug = it_feat["slug"]
        en_feat = en_by_slug.get(slug)
        if not en_feat:
            continue

        has_desc = "desc_html" in it_feat and it_feat["desc_html"]

        # Se ha già desc_html, controlla se è OCR di bassa qualità
        if has_desc:
            existing = it_feat["desc_html"]
            # Controlla segni di OCR sporco: tutto in un unico <p>, spazi prima di punteggiatura
            is_single_p = existing.count("<p>") <= 1 and existing.count("<p ") == 0
            has_ocr_artifacts = bool(re.search(r' [.,;:!?]', existing)) or bool(re.search(r'[a-z] [A-Z]', existing))

            if is_single_p and has_ocr_artifacts:
                # Prova ad assemblare una versione migliore
                new_desc, err = build_desc_html(slug, en_feat, it_feat)
                if new_desc and not err:
                    # L'assemblato è strutturato meglio
                    if apply_mode:
                        it_feat["desc_html"] = new_desc
                    replaced += 1
                    print(f"  SOSTITUITO (OCR -> assemblato): {slug}")
                else:
                    quality_issues.append(f"{slug}: OCR desc_html di bassa qualità ma non assemblabile: {err}")
            continue

        # Manca desc_html — prova ad assemblare
        new_desc, err = build_desc_html(slug, en_feat, it_feat)
        if new_desc and not err:
            if apply_mode:
                it_feat["desc_html"] = new_desc
            assembled += 1
            print(f"  ASSEMBLATO: {slug}")
        else:
            skipped.append(f"{slug}: {err}")

    print(f"\n{'='*60}")
    print(f"Assemblati: {assembled}")
    print(f"Sostituiti (OCR->assemblato): {replaced}")
    print(f"Saltati: {len(skipped)}")

    if skipped:
        print(f"\n--- Saltati (da segnalare) ---")
        for s in skipped:
            print(f"  {s}")

    if quality_issues:
        print(f"\n--- Problemi qualità OCR ---")
        for q in quality_issues:
            print(f"  {q}")

    if apply_mode:
        with open(IT_PATH, "w", encoding="utf-8") as f:
            json.dump(it_feats, f, ensure_ascii=False, indent=2)
        print(f"\nScritto {IT_PATH}")
    else:
        print(f"\nDry-run. Usa --apply per scrivere le modifiche.")


if __name__ == "__main__":
    main()
