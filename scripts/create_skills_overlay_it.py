#!/usr/bin/env python3
"""
Create Italian overlay for skills from PDF SRD and known translations.

Sources:
  - sources/pdf-ita/04-abilita/elencoabilita.html (18 skill descriptions)
  - Official Italian skill name mapping (MdG/SRD IT)

Target: data/i18n/it/skills.json
"""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCES_DIR = ROOT / "sources" / "pdf-ita" / "04-abilita"
DATA_DIR = ROOT / "data"
OVERLAY_PATH = DATA_DIR / "i18n" / "it" / "skills.json"
BASE_PATH = DATA_DIR / "skills.json"

# Official Italian names for D&D 3.5 skills (from Manuale del Giocatore)
# EN slug → IT name
SKILL_NAMES_IT = {
    # Core SRD skills (from MdG 3.5)
    "appraise": "Valutare",
    "balance": "Equilibrio",
    "bluff": "Raggirare",
    "climb": "Scalare",
    "concentration": "Concentrazione",
    "craft": "Artigianato",
    "decipher-script": "Decifrare Scritture",
    "diplomacy": "Diplomazia",
    "disable-device": "Disattivare Congegni",
    "disguise": "Camuffare",
    "escape-artist": "Artista della Fuga",
    "forgery": "Falsificare",
    "gather-information": "Raccogliere Informazioni",
    "handle-animal": "Addestrare Animali",
    "heal": "Guarire",
    "hide": "Nascondersi",
    "intimidate": "Intimidire",
    "jump": "Saltare",
    "knowledge-arcana": "Conoscenze (Arcane)",
    "knowledge-architecture-and-engineering": "Conoscenze (Architettura e Ingegneria)",
    "knowledge-dungeoneering": "Conoscenze (Sotterranei)",
    "knowledge-geography": "Conoscenze (Geografia)",
    "knowledge-history": "Conoscenze (Storia)",
    "knowledge-local": "Conoscenze (Locali)",
    "knowledge-nature": "Conoscenze (Natura)",
    "knowledge-nobility-and-royalty": "Conoscenze (Nobiltà e Regalità)",
    "knowledge-religion": "Conoscenze (Religione)",
    "knowledge-the-planes": "Conoscenze (Piani)",
    "listen": "Ascoltare",
    "move-silently": "Muoversi Silenziosamente",
    "open-lock": "Scassinare Serrature",
    "perform": "Intrattenere",
    "profession": "Professione",
    "ride": "Cavalcare",
    "search": "Cercare",
    "sense-motive": "Percepire Intenzioni",
    "sleight-of-hand": "Rapidità di Mano",
    "speak-language": "Parlare Linguaggi",
    "spellcraft": "Sapienza Magica",
    "spot": "Osservare",
    "survival": "Sopravvivenza",
    "swim": "Nuotare",
    "tumble": "Acrobazia",
    "use-magic-device": "Utilizzare Oggetti Magici",
    "use-rope": "Utilizzare Corde",
    # Additional SRD skills
    "alchemy": "Alchimia",
    "animal-empathy": "Empatia Animale",
    "autohypnosis": "Autoipnosi",
    "control-shape": "Controllare Forma",
    "innuendo": "Allusione",
    "intuit-direction": "Senso della Direzione",
    "knowledge": "Conoscenze",
    "psicraft": "Sapienza Psichica",
    "read-lips": "Leggere Labbra",
    "remote-view": "Visione Remota",
    "scry": "Scrutare",
    "stabilize-self": "Stabilizzarsi",
    "wilderness-lore": "Conoscenza della Natura",
    # Additional from dndtools
    "iaijutsu-focus": "Iaijutsu Focus",
    "lucid-dreaming": "Sogno Lucido",
    "martial-lore": "Conoscenze Marziali",
    "truespeak": "Linguaggio Vero",
}


def extract_skills_from_html(filepath):
    """Extract skill entries from the Italian SRD HTML file.

    Returns dict: IT_name_upper → {check, action, special, synergy, ...}
    """
    with open(filepath, encoding="utf-8") as f:
        content = f.read()

    body_match = re.search(r"<body>(.*)</body>", content, re.DOTALL)
    if not body_match:
        return {}
    body = body_match.group(1)

    # Split by h3 headings (skill entries)
    parts = re.split(r"<h3>([^<]+)</h3>", body)

    skills = {}
    i = 1  # Skip preamble before first h3
    while i < len(parts):
        heading = parts[i].strip()
        content_after = parts[i + 1] if i + 1 < len(parts) else ""
        i += 2

        # Parse heading: NAME (ABILITY; FLAGS)
        m = re.match(r"(.+?)\s*\(([^)]+)\)", heading)
        if not m:
            continue

        name = " ".join(m.group(1).split()).strip()
        ability_info = m.group(2).strip()

        # Build desc_html from content
        # Clean up the content
        desc = content_after.strip()

        # Remove leading/trailing whitespace and normalize
        desc = re.sub(r"\s+", " ", desc)

        # Restore paragraph structure
        desc = desc.replace("</p> <p>", "</p>\n<p>")
        desc = desc.replace("</p><p>", "</p>\n<p>")

        skills[name.upper()] = {
            "name_it": name.title() if name.isupper() else name,
            "ability_info": ability_info,
            "desc_html": desc.strip(),
        }

    return skills


# Mapping from Italian SRD skill names to EN slugs
IT_SKILL_NAME_TO_SLUG = {
    "ACROBAZIA": "tumble",
    "ADDESTRARE ANIMALI": "handle-animal",
    "ARTISTA DELLA FUGA": "escape-artist",
    "CONOSCENZE": "knowledge",
    "DECIFRARE SCRITTURE": "decipher-script",
    "DISATTIVARE CONGEGNI": "disable-device",
    "EQUILIBRIO": "balance",
    "MUOVERSI SILENZIOSAMENTE": "move-silently",
    "NASCONDERSI": "hide",
    "NUOTARE": "swim",
    "PARLARE LINGUAGGI": "speak-language",
    "PROFESSIONE": "profession",
    "RAPIDITÀ DI MANO": "sleight-of-hand",
    "SALTARE": "jump",
    "SAPIENZA MAGICA": "spellcraft",
    "SCALARE": "climb",
    "SCASSINARE SERRATURE": "open-lock",
    "UTILIZZARE OGGETTI MAGICI": "use-magic-device",
}


def main():
    dry_run = "--dry-run" in sys.argv

    if dry_run:
        print("=== DRY RUN MODE (no files will be modified) ===\n")

    # Load base data
    with open(BASE_PATH, encoding="utf-8") as f:
        base = json.load(f)

    base_map = {e["slug"]: e for e in base}

    # Load existing overlay if it exists
    if OVERLAY_PATH.exists():
        with open(OVERLAY_PATH, encoding="utf-8") as f:
            overlay = json.load(f)
        print(f"Loaded existing overlay with {len(overlay)} entries")
    else:
        overlay = []
        print("No existing overlay found, creating new one")

    overlay_map = {e["slug"]: e for e in overlay}

    # Extract skill descriptions from PDF SRD
    pdf_skills = {}
    elenco_path = SOURCES_DIR / "elencoabilita.html"
    if elenco_path.exists():
        pdf_skills = extract_skills_from_html(elenco_path)
        print(f"Extracted {len(pdf_skills)} skill descriptions from PDF SRD\n")

    # Create/update overlay entries
    added = 0
    updated = 0

    for base_entry in base:
        slug = base_entry["slug"]
        category = base_entry.get("category", "skill")

        # Get Italian name
        it_name = SKILL_NAMES_IT.get(slug)
        if not it_name:
            continue

        # Check if we have PDF SRD description
        pdf_desc = None
        for it_key, en_slug in IT_SKILL_NAME_TO_SLUG.items():
            if en_slug == slug and it_key in pdf_skills:
                pdf_desc = pdf_skills[it_key]
                break

        if slug in overlay_map:
            # Update existing entry
            entry = overlay_map[slug]
            changes = []

            if not entry.get("name"):
                if not dry_run:
                    entry["name"] = it_name
                changes.append("+name")

            if pdf_desc and not entry.get("desc_html", "").strip():
                if not dry_run:
                    entry["desc_html"] = pdf_desc["desc_html"]
                changes.append("+desc_html")

            if changes:
                if "translation_source" not in entry:
                    if not dry_run:
                        entry["translation_source"] = "pdf" if pdf_desc else "manual"
                        entry["reviewed"] = False
                updated += 1
                print(f"  Updated {slug}: {', '.join(changes)}")
        else:
            # Create new entry
            new_entry = {
                "slug": slug,
                "name": it_name,
            }

            if pdf_desc:
                new_entry["desc_html"] = pdf_desc["desc_html"]
                new_entry["translation_source"] = "pdf"
            else:
                new_entry["translation_source"] = "manual"

            new_entry["reviewed"] = False

            if not dry_run:
                overlay.append(new_entry)
                overlay_map[slug] = new_entry
            added += 1
            print(f"  Added {slug}: {it_name}" + (" (with desc_html)" if pdf_desc else ""))

    print(f"\nSummary:")
    print(f"  Base skills: {len(base)} ({sum(1 for e in base if e.get('category') == 'skill')} skills, {sum(1 for e in base if e.get('category') == 'skill_trick')} tricks)")
    print(f"  IT names mapped: {sum(1 for s in base if s['slug'] in SKILL_NAMES_IT)}")
    print(f"  PDF descriptions: {len(pdf_skills)}")
    print(f"  Updated: {updated}")
    print(f"  Added: {added}")
    print(f"  Total overlay: {len(overlay)}")

    # Skills without IT name
    unmapped = [e["slug"] for e in base if e["slug"] not in SKILL_NAMES_IT]
    if unmapped:
        print(f"\n  Skills without IT name ({len(unmapped)}):")
        for s in sorted(unmapped):
            print(f"    {s}: {base_map[s]['name']}")

    if not dry_run and (added > 0 or updated > 0):
        overlay.sort(key=lambda e: e.get("slug", ""))
        with open(OVERLAY_PATH, "w", encoding="utf-8") as f:
            json.dump(overlay, f, ensure_ascii=False, indent=2)
            f.write("\n")
        print(f"\nWritten {len(overlay)} entries to {OVERLAY_PATH}")
    elif dry_run:
        print("\nDry run complete. No files modified.")
    else:
        print("\nNo changes needed.")


if __name__ == "__main__":
    main()
