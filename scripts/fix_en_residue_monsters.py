#!/usr/bin/env python3
"""Fix English residue in monster overlay metadata fields.

Translates common English words/phrases left in organization, alignment,
and type fields after the initial automated translation pass.

Usage:
    python scripts/fix_en_residue_monsters.py          # dry-run
    python scripts/fix_en_residue_monsters.py --apply   # scrive nell'overlay
"""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
IT_PATH = ROOT / "data" / "i18n" / "it" / "monsters.json"

# Replacement patterns for organization field (order matters!)
ORG_REPLACEMENTS = [
    # Compound patterns first (most specific)
    (r'\bnoncombatants\b', 'non combattenti'),
    (r'\bnoncombatant\b', 'non combattente'),
    # Range: "of 3rd–6th level" or "of 3rd-6th level"
    (r'\bof (\d+)(?:st|nd|rd|th)[–\-](\d+)(?:st|nd|rd|th) level\b', r'di \1°–\2° livello'),
    # Single: "3rd-level" -> "3° livello"
    (r'(\d+)(?:st|nd|rd|th)-level\b', r'\1° livello'),
    # Single standalone: "3rd level" (without hyphen)
    (r'(\d+)(?:st|nd|rd|th) level\b', r'\1° livello'),
    (r'\bsergeants\b', 'sergenti'),
    (r'\bsergeant\b', 'sergente'),
    (r'\blieutenants\b', 'luogotenenti'),
    (r'\blieutenant\b', 'luogotenente'),
    (r'\bleaders?\b', 'capo'),
    (r'\badults\b', 'adulti'),
    (r'\badult\b', 'adulto'),
    (r'\bworkers\b', 'lavoratori'),
    (r'\bwokers\b', 'lavoratori'),  # typo in source
    (r'\bsoldiers\b', 'soldati'),
    (r'\bsoldier\b', 'soldato'),
    (r'\bsocerers?\b', 'stregoni'),  # typo in source
    (r'\bsorcerers?\b', 'stregoni'),
    (r'\btroupe\b', 'troupe'),  # keep as-is (used in Italian too)
    (r'\btribe\b', 'tribù'),
    (r'\bbrood\b', 'nidiata'),
    (r'\bguard\b', 'guardia'),
    # Simple word replacements
    (r'\bplus\b', 'più'),
    (r'\band\b', 'e'),
    (r'\bof\b', 'di'),
    (r'\bwith\b', 'con'),
    (r'\beach\b', 'ciascuno'),
    (r'\bany\b', 'qualsiasi'),
    (r'\bhave\b', 'hanno'),
    (r'\bper\b', 'ogni'),
    # Creature names in organization (keep in English but fix common ones)
    (r'\bogres\b', 'ogre'),
    (r'\bgiants\b', 'giganti'),
    (r'\bgiant\b', 'gigante'),
    (r'\bevil\b', 'malvagi'),
    (r'\bhags\b', 'megere'),
    (r'\bmummies\b', 'mummie'),
    (r'\bwarhounds\b', 'segugi da guerra'),
    (r'\bhounds\b', 'segugi'),
]

# Specific overrides for entries too complex for regex
ORG_OVERRIDES = {
    "aboleth": "Solitario, covata (2\u20134), o covata schiavista (1d3+1 più 7\u201312 skum)",
    "giant-ant-queen": "Alveare (1 più 10\u2013100 lavoratori e 5\u201320 soldati)",
    "mummy-lord-10th-level-cleric": "Solitario o guardia tombale (1 signore delle mummie e 6\u201310 mummie)",
    "nessian-warhound": "Solitario, coppia, o branco (1\u20132 segugi da guerra nessiani e 5\u201312 segugi infernali)",
    "violet-fungus": "Solitario, gruppo (2\u20134), o gruppo misto (2\u20134 funghi violetti e 3\u20135 strillatori)",
    "hag": "Solitario o congrega (3 megere di qualsiasi tipo più 1\u20138 ogre e 1\u20134 giganti malvagi)",
    "gnoll": None,  # too complex, skip
}


def fix_organization(slug, org):
    """Fix English residue in organization field."""
    if slug in ORG_OVERRIDES:
        override = ORG_OVERRIDES[slug]
        if override is None:
            return org, False  # skip
        return override, True

    original = org
    for pattern, replacement in ORG_REPLACEMENTS:
        org = re.sub(pattern, replacement, org, flags=re.IGNORECASE)

    # Clean up spacing
    org = re.sub(r'\s+', ' ', org)
    org = re.sub(r'\s*\n\s*', ' ', org)

    return org, org != original


def fix_alignment(slug, alignment):
    """Fix 'or' in alignment fields."""
    original = alignment
    alignment = re.sub(r'\bor\b', 'o', alignment)
    return alignment, alignment != original


def fix_type(slug, typ):
    """Fix English residue in type fields."""
    original = typ
    typ = re.sub(r'\bor smaller\b', 'o inferiore', typ)
    typ = re.sub(r'\bor larger\b', 'o superiore', typ)
    return typ, typ != original


def main():
    apply_mode = "--apply" in sys.argv

    with open(IT_PATH, encoding="utf-8") as f:
        monsters = json.load(f)

    org_fixed = 0
    org_skipped = []
    align_fixed = 0
    type_fixed = 0

    for m in monsters:
        slug = m["slug"]

        # Fix organization
        org = m.get("organization", "")
        if org:
            new_org, changed = fix_organization(slug, org)
            if changed:
                # Verify no English residue remains
                remaining = re.findall(
                    r'\b(plus|and|noncombatants?|sergeants?|leaders?|lieutenants?|'
                    r'workers?|soldiers?|with|each|any|have|evil|giants?|adults?|tribe)\b',
                    new_org, re.IGNORECASE
                )
                if remaining:
                    org_skipped.append(f"{slug}: residuo EN rimasto: {remaining} -> {new_org[:150]}")
                else:
                    if apply_mode:
                        m["organization"] = new_org
                    org_fixed += 1
                    print(f"  ORG FIX: {slug}")

        # Fix alignment
        alignment = m.get("alignment", "")
        if alignment and re.search(r'\bor\b', alignment):
            new_al, changed = fix_alignment(slug, alignment)
            if changed:
                if apply_mode:
                    m["alignment"] = new_al
                align_fixed += 1
                print(f"  ALIGN FIX: {slug}: {alignment} -> {new_al}")

        # Fix type
        typ = m.get("type", "")
        if typ and re.search(r'\bor\b', typ, re.IGNORECASE):
            new_typ, changed = fix_type(slug, typ)
            if changed:
                if apply_mode:
                    m["type"] = new_typ
                type_fixed += 1
                print(f"  TYPE FIX: {slug}: {typ} -> {new_typ}")

    print(f"\n{'='*60}")
    print(f"Organization fixed: {org_fixed}")
    print(f"Alignment fixed: {align_fixed}")
    print(f"Type fixed: {type_fixed}")

    if org_skipped:
        print(f"\n--- Organization con residuo EN (da segnalare) ---")
        for s in org_skipped:
            print(f"  {s}")

    if apply_mode:
        with open(IT_PATH, "w", encoding="utf-8") as f:
            json.dump(monsters, f, ensure_ascii=False, indent=2)
        print(f"\nScritto {IT_PATH}")
    else:
        print(f"\nDry-run. Usa --apply per scrivere le modifiche.")


if __name__ == "__main__":
    main()
