#!/usr/bin/env python3
"""Parse SRD 3.5 HTML source files into structured JSON."""

import json
import re
import sys
from pathlib import Path

from bs4 import BeautifulSoup, Tag

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data"
SPELLS_DIR = REPO_ROOT / "spells"

STAT_LABELS = {
    "Level",
    "Components",
    "Component",
    "Casting Time",
    "Range",
    "Duration",
    "Saving Throw",
    "Spell Resistance",
}

TARGET_AREA_LABELS = {
    "Target",
    "Targets",
    "Area",
    "Effect",
    "Target or Targets",
    "Target or Area",
    "Area or Target",
    "Target, Effect, or Area",
    "Target/Effect",
}

ALL_STAT_LABELS = STAT_LABELS | TARGET_AREA_LABELS


def parse_school_line(text: str):
    """Parse 'School (Subschool) [Descriptor]' into components."""
    text = text.strip()
    school = text
    subschool = None
    descriptor = None

    # Extract descriptor: [...] at end
    desc_match = re.search(r"\[([^\]]+)\]\s*$", text)
    if desc_match:
        descriptor = desc_match.group(1).strip()
        text = text[: desc_match.start()].strip()

    # Extract subschool: (...) after school name
    sub_match = re.search(r"\(([^)]+)\)", text)
    if sub_match:
        subschool = sub_match.group(1).strip()
        text = text[: sub_match.start()].strip()

    school = text.strip()
    return school, subschool, descriptor


def get_siblings_until_next_h2(h2_tag):
    """Collect all Tag siblings after h2 until the next h2."""
    siblings = []
    for sib in h2_tag.next_siblings:
        if isinstance(sib, Tag):
            if sib.name == "h2":
                break
            siblings.append(sib)
    return siblings


def extract_label(tag):
    """If a <p> tag starts with <strong>Label:</strong>, return the label name."""
    strong = tag.find("strong")
    if not strong:
        return None
    label_text = strong.get_text(strip=True)
    if label_text.endswith(":"):
        return label_text[:-1]
    return None


def parse_spell(h2_tag):
    """Parse a single spell from its <h2> tag and following siblings."""
    slug = h2_tag.get("id", "")
    name = h2_tag.get_text(strip=True)

    siblings = get_siblings_until_next_h2(h2_tag)
    if not siblings:
        return None

    # First <p> without <strong> = school line
    school = subschool = descriptor = None
    stat_start = 0

    if siblings and siblings[0].name == "p" and not siblings[0].find("strong"):
        school_text = siblings[0].get_text(strip=True)
        school, subschool, descriptor = parse_school_line(school_text)
        stat_start = 1

    # Parse stat fields
    stats = {}
    desc_start = stat_start

    for i in range(stat_start, len(siblings)):
        sib = siblings[i]
        if sib.name != "p":
            desc_start = i
            break
        label = extract_label(sib)
        if label and label in ALL_STAT_LABELS:
            # Value is full text minus "Label: " prefix
            full_text = sib.get_text(strip=True)
            colon_pos = full_text.find(":")
            value = full_text[colon_pos + 1 :].strip() if colon_pos != -1 else ""
            stats[label] = value
            desc_start = i + 1
        else:
            desc_start = i
            break
    else:
        # All siblings were stat lines (unlikely but handle it)
        desc_start = len(siblings)

    # Find target/area/effect value
    target_area_effect = None
    for lbl in TARGET_AREA_LABELS:
        if lbl in stats:
            target_area_effect = stats[lbl]
            break

    # Build desc_html from remaining siblings
    desc_parts = []
    for sib in siblings[desc_start:]:
        desc_parts.append(str(sib).strip())
    desc_html = "\n".join(desc_parts) if desc_parts else None

    return {
        "name": name,
        "slug": slug,
        "school": school,
        "subschool": subschool,
        "descriptor": descriptor,
        "level": stats.get("Level"),
        "components": stats.get("Components") or stats.get("Component"),
        "casting_time": stats.get("Casting Time"),
        "range": stats.get("Range"),
        "target_area_effect": target_area_effect,
        "duration": stats.get("Duration"),
        "saving_throw": stats.get("Saving Throw"),
        "spell_resistance": stats.get("Spell Resistance"),
        "desc_html": desc_html,
    }


def parse_spell_file(filepath):
    """Parse all spells from a single HTML file."""
    with open(filepath, "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f.read(), "html.parser")

    spells = []
    for h2 in soup.find_all("h2"):
        # Skip Table of Contents
        if h2.get_text(strip=True) == "Table of Contents":
            continue
        if not h2.get("id"):
            continue
        spell = parse_spell(h2)
        if spell:
            spells.append(spell)

    return spells


def parse_all_spells():
    """Parse all spell files and return combined list."""
    spell_files = sorted(SPELLS_DIR.glob("spells-*.html"))
    all_spells = []

    for fpath in spell_files:
        print(f"Parsing {fpath.name}...")
        spells = parse_spell_file(fpath)
        print(f"  Found {len(spells)} spells")
        all_spells.extend(spells)

    return all_spells


def main():
    DATA_DIR.mkdir(exist_ok=True)

    what = sys.argv[1] if len(sys.argv) > 1 else "all"

    if what in ("all", "spells"):
        spells = parse_all_spells()
        outpath = DATA_DIR / "spells.json"
        with open(outpath, "w", encoding="utf-8") as f:
            json.dump(spells, f, indent=2, ensure_ascii=False)
        print(f"\nWrote {len(spells)} spells to {outpath}")


if __name__ == "__main__":
    main()
