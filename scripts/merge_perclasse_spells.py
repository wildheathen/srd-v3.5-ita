#!/usr/bin/env python3
"""
Merge Italian spell data from incantesimi_ded35_per_classe.json into the overlay.

Reads the per-class JSON, matches spells to our existing data, and fills in
missing Italian fields (desc_html, components, casting_time, range,
target_area_effect, duration, saving_throw, spell_resistance, short_description).

Also abbreviates class names in the level field to match our convention.
"""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC_FILE = ROOT / "sources" / "contrib" / "incantesimi_ded35_per_classe.json"
SPELLS_FILE = ROOT / "data" / "spells.json"
OVERLAY_FILE = ROOT / "data" / "i18n" / "it" / "spells.json"

# ── Class-name abbreviation map ──────────────────────────────────────────────
# Full Italian class name → abbreviation used in our overlay
CLASS_ABBREV = {
    "Bardo":          "Brd",
    "Chierico":       "Chr",
    "Druido":         "Drd",
    "Mago":           "Mag",
    "Stregone":       "Str",
    "Stregone/Mago":  "Mag/Str",
    "Paladino":       "Pal",
    "Ranger":         "Rgr",
    "Assassino":      "Ass",
    "Guaritore":      "Guarigione",
    # Domain names stay as-is (Acqua, Aria, Fuoco, etc.)
}


def abbreviate_level(level_str: str) -> str:
    """Convert 'Bardo 0, Stregone/Mago 3' → 'Brd 0, Mag/Str 3'."""
    if not level_str:
        return level_str

    parts = []
    for part in level_str.split(","):
        part = part.strip()
        if not part:
            continue
        # Try to split into class + number
        m = re.match(r"^(.+?)\s+(\d+)$", part)
        if m:
            cls_name = m.group(1).strip()
            lvl_num = m.group(2)
            abbr = CLASS_ABBREV.get(cls_name, cls_name)
            parts.append(f"{abbr} {lvl_num}")
        else:
            parts.append(part)
    return ", ".join(parts)


def norm_name(s: str) -> str:
    """Normalize a name for fuzzy matching."""
    return re.sub(r"[^a-z0-9]", "", s.lower().strip()) if s else ""


def collect_source_spells(src_data: dict) -> dict:
    """Collect unique spells from the per-class JSON (keyed by id)."""
    spells = {}
    for cls_name, levels in src_data.items():
        for lvl, val in levels.items():
            if isinstance(val, list):
                for sp in val:
                    if sp["id"] not in spells:
                        spells[sp["id"]] = sp
            elif isinstance(val, dict):
                # Domini: nested dict of domain -> {level -> [spells]}
                for domain, domain_levels in val.items():
                    if isinstance(domain_levels, dict):
                        for dlvl, dspells in domain_levels.items():
                            if isinstance(dspells, list):
                                for sp in dspells:
                                    if sp["id"] not in spells:
                                        spells[sp["id"]] = sp
    return spells


def build_target_area_effect(sp: dict) -> str:
    """Combine target, area, effect fields into one string."""
    parts = []
    for field in ("target", "area", "effect"):
        v = sp.get(field, "").strip()
        if v:
            parts.append(v)
    return "; ".join(parts)


def build_desc_html(sp: dict) -> str:
    """Build desc_html from the description field.

    The description field contains the spell's full Italian description
    including any tables. We use it as-is since it's already HTML.
    """
    desc = sp.get("description", "").strip()
    if not desc:
        return ""

    # Add material components, focus, XP cost as extra paragraphs
    extras = []
    mc = sp.get("material_components", "").strip()
    amc = sp.get("arcane_material_components", "").strip()
    focus = sp.get("focus", "").strip()
    xp = sp.get("xp_cost", "").strip()

    if mc:
        extras.append(f"<p><i>Componente materiale: </i>{mc}</p>")
    if amc:
        extras.append(f"<p><i>Componente materiale arcana: </i>{amc}</p>")
    if focus:
        extras.append(f"<p><i>Focus: </i>{focus}</p>")
    if xp:
        extras.append(f"<p><i>Costo in PE: </i>{xp}</p>")

    return desc + "".join(extras)


def main():
    dry_run = "--dry-run" in sys.argv

    # Load files
    with open(SRC_FILE, "r", encoding="utf-8") as f:
        src_data = json.load(f)

    with open(SPELLS_FILE, "r", encoding="utf-8") as f:
        our_spells = json.load(f)

    with open(OVERLAY_FILE, "r", encoding="utf-8") as f:
        our_it = json.load(f)

    # Build lookup maps
    our_it_by_slug = {e["slug"]: e for e in our_it}
    our_by_name_en = {}
    our_by_name_it = {}
    our_by_slug = {}

    for sp in our_spells:
        our_by_slug[sp["slug"]] = sp
        n = norm_name(sp["name"])
        if n:
            our_by_name_en[n] = sp
        it_entry = our_it_by_slug.get(sp["slug"])
        if it_entry and it_entry.get("name"):
            ni = norm_name(it_entry["name"])
            if ni:
                our_by_name_it[ni] = sp

    # Collect source spells
    src_spells = collect_source_spells(src_data)
    print(f"Source spells: {len(src_spells)}")

    # Stats
    stats = {
        "matched": 0,
        "unmatched": 0,
        "filled_desc_html": 0,
        "filled_components": 0,
        "filled_casting_time": 0,
        "filled_range": 0,
        "filled_target_area_effect": 0,
        "filled_duration": 0,
        "filled_saving_throw": 0,
        "filled_spell_resistance": 0,
        "filled_short_description": 0,
        "filled_level": 0,
    }

    # Field mapping: overlay_field → (source_field, transform_fn or None)
    FIELD_MAP = {
        "desc_html":          ("__desc_html__", None),   # special handling
        "components":         ("components", None),
        "casting_time":       ("casting_time", None),
        "range":              ("range", None),
        "target_area_effect": ("__target_area_effect__", None),  # special
        "duration":           ("duration", None),
        "saving_throw":       ("saving_throw", None),
        "spell_resistance":   ("spell_resistance", None),
        "short_description":  ("short_description", None),
    }

    for sid, sp in src_spells.items():
        name_en = sp.get("altname", "").strip()
        name_it = sp.get("name", "").strip()

        # Find matching spell
        found = our_by_name_en.get(norm_name(name_en))
        if not found:
            found = our_by_name_it.get(norm_name(name_it))
        if not found:
            slug = re.sub(r"[^a-z0-9]+", "-", name_en.lower()).strip("-")
            found = our_by_slug.get(slug)
        if not found:
            stats["unmatched"] += 1
            continue

        stats["matched"] += 1
        slug = found["slug"]

        # Ensure overlay entry exists
        if slug not in our_it_by_slug:
            our_it_by_slug[slug] = {"slug": slug}

        it = our_it_by_slug[slug]

        # Fill missing fields
        for overlay_field in FIELD_MAP:
            if it.get(overlay_field, "").strip():
                continue  # Already has data

            if overlay_field == "desc_html":
                src_val = build_desc_html(sp)
            elif overlay_field == "target_area_effect":
                src_val = build_target_area_effect(sp)
            else:
                src_field = FIELD_MAP[overlay_field][0]
                src_val = sp.get(src_field, "").strip()

            if src_val:
                it[overlay_field] = src_val
                stats[f"filled_{overlay_field}"] += 1

        # Fill level if missing (with abbreviation)
        if not it.get("level", "").strip():
            src_level = sp.get("level", "").strip()
            if src_level:
                it["level"] = abbreviate_level(src_level)
                stats["filled_level"] += 1

    # Rebuild overlay list
    # Preserve existing order, add any new entries at end
    existing_slugs = {e["slug"] for e in our_it}
    new_it = list(our_it)  # keep existing entries (they're the same objects, already modified in-place)
    for slug, entry in our_it_by_slug.items():
        if slug not in existing_slugs:
            new_it.append(entry)

    # Print stats
    print(f"\nMatched: {stats['matched']}")
    print(f"Unmatched: {stats['unmatched']}")
    print(f"\nCampi riempiti:")
    for k, v in sorted(stats.items()):
        if k.startswith("filled_") and v > 0:
            print(f"  {k.replace('filled_', '')}: +{v}")

    if dry_run:
        print("\n[DRY RUN] No files written.")
        return

    # Save overlay
    with open(OVERLAY_FILE, "w", encoding="utf-8") as f:
        json.dump(new_it, f, ensure_ascii=False, indent=2)
    print(f"\nOverlay salvato: {OVERLAY_FILE}")


if __name__ == "__main__":
    main()
