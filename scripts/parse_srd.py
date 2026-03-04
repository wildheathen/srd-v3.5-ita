#!/usr/bin/env python3
"""Parse SRD 3.5 HTML source files into structured JSON."""

import json
import re
import sys
from pathlib import Path

from bs4 import BeautifulSoup, NavigableString, Tag

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data"
SPELLS_DIR = REPO_ROOT / "spells"
RULES_DIR = REPO_ROOT / "basic-rules-and-legal"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_siblings_until(tag, stop_tags):
    """Collect Tag siblings after *tag* until one of *stop_tags* is hit."""
    siblings = []
    for sib in tag.next_siblings:
        if isinstance(sib, Tag):
            if sib.name in stop_tags:
                break
            siblings.append(sib)
    return siblings


def extract_label(tag):
    """If a <p> tag starts with <strong>Label:</strong>, return the label."""
    strong = tag.find("strong")
    if not strong:
        return None
    label_text = strong.get_text(strip=True)
    if label_text.endswith(":"):
        return label_text[:-1]
    return None


def siblings_to_html(siblings):
    """Join a list of Tag siblings into a single HTML string."""
    parts = [str(s).strip() for s in siblings if str(s).strip()]
    return "\n".join(parts) if parts else None


def load_soup(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        return BeautifulSoup(f.read(), "html.parser")


def write_json(data, filename):
    DATA_DIR.mkdir(exist_ok=True)
    outpath = DATA_DIR / filename
    with open(outpath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"Wrote {len(data)} entries to {outpath}")


# ---------------------------------------------------------------------------
# Spells
# ---------------------------------------------------------------------------

STAT_LABELS = {
    "Level", "Components", "Component", "Casting Time",
    "Range", "Duration", "Saving Throw", "Spell Resistance",
}

TARGET_AREA_LABELS = {
    "Target", "Targets", "Area", "Effect",
    "Target or Targets", "Target or Area", "Area or Target",
    "Target, Effect, or Area", "Target/Effect",
}

ALL_SPELL_LABELS = STAT_LABELS | TARGET_AREA_LABELS


def parse_school_line(text: str):
    text = text.strip()
    school = subschool = descriptor = None

    desc_match = re.search(r"\[([^\]]+)\]\s*$", text)
    if desc_match:
        descriptor = desc_match.group(1).strip()
        text = text[: desc_match.start()].strip()

    sub_match = re.search(r"\(([^)]+)\)", text)
    if sub_match:
        subschool = sub_match.group(1).strip()
        text = text[: sub_match.start()].strip()

    school = text.strip()
    return school, subschool, descriptor


def parse_spell(h2_tag):
    slug = h2_tag.get("id", "")
    name = h2_tag.get_text(strip=True)
    siblings = get_siblings_until(h2_tag, {"h2"})
    if not siblings:
        return None

    school = subschool = descriptor = None
    stat_start = 0

    if siblings and siblings[0].name == "p" and not siblings[0].find("strong"):
        school, subschool, descriptor = parse_school_line(
            siblings[0].get_text(strip=True)
        )
        stat_start = 1

    stats = {}
    desc_start = stat_start

    for i in range(stat_start, len(siblings)):
        sib = siblings[i]
        if sib.name != "p":
            desc_start = i
            break
        label = extract_label(sib)
        if label and label in ALL_SPELL_LABELS:
            full_text = sib.get_text(strip=True)
            colon_pos = full_text.find(":")
            value = full_text[colon_pos + 1 :].strip() if colon_pos != -1 else ""
            stats[label] = value
            desc_start = i + 1
        else:
            desc_start = i
            break
    else:
        desc_start = len(siblings)

    target_area_effect = None
    for lbl in TARGET_AREA_LABELS:
        if lbl in stats:
            target_area_effect = stats[lbl]
            break

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
        "desc_html": siblings_to_html(siblings[desc_start:]),
    }


def parse_all_spells():
    spell_files = sorted(SPELLS_DIR.glob("spells-*.html"))
    all_spells = []
    for fpath in spell_files:
        soup = load_soup(fpath)
        for h2 in soup.find_all("h2"):
            if h2.get_text(strip=True) == "Table of Contents":
                continue
            if not h2.get("id"):
                continue
            spell = parse_spell(h2)
            if spell:
                all_spells.append(spell)
        print(f"  {fpath.name}: {sum(1 for s in all_spells if True)} total so far")
    return all_spells


# ---------------------------------------------------------------------------
# Feats
# ---------------------------------------------------------------------------

FEAT_FIELDS = {"Prerequisite", "Prerequisites", "Benefit", "Benefits",
               "Normal", "Special"}


def parse_feat(h3_tag):
    slug = h3_tag.get("id", "")
    small = h3_tag.find("small")
    feat_type = None
    if small:
        m = re.search(r"\[([^\]]+)\]", small.get_text())
        if m:
            feat_type = m.group(1)
        small.decompose()
    name = h3_tag.get_text(strip=True)

    siblings = get_siblings_until(h3_tag, {"h2", "h3"})

    fields = {}
    current_field = None
    current_parts = []
    desc_parts = []

    for sib in siblings:
        label = extract_label(sib) if sib.name == "p" else None
        # Normalise singular/plural
        if label in ("Prerequisites", "Prerequisite"):
            label = "prerequisites"
        elif label in ("Benefits", "Benefit"):
            label = "benefit"
        elif label == "Normal":
            label = "normal"
        elif label == "Special":
            label = "special"
        else:
            label = None

        if label:
            # Save previous field
            if current_field:
                fields[current_field] = "\n".join(current_parts)
            current_field = label
            full_text = sib.get_text(strip=True)
            colon_pos = full_text.find(":")
            current_parts = [full_text[colon_pos + 1 :].strip()]
        elif current_field:
            # Continuation paragraph of current field
            current_parts.append(sib.get_text(strip=True))
        else:
            desc_parts.append(str(sib).strip())

    if current_field:
        fields[current_field] = "\n".join(current_parts)

    # Build desc_html from all siblings (preserving HTML)
    desc_html = siblings_to_html(siblings)

    return {
        "name": name,
        "slug": slug,
        "type": feat_type,
        "prerequisites": fields.get("prerequisites"),
        "benefit": fields.get("benefit"),
        "normal": fields.get("normal"),
        "special": fields.get("special"),
        "desc_html": desc_html,
    }


def parse_all_feats():
    filepath = RULES_DIR / "feats.html"
    soup = load_soup(filepath)
    feats = []

    # Only parse h3 tags that come after "Feat Descriptions" h2
    in_descriptions = False
    for tag in soup.find_all(["h2", "h3"]):
        if tag.name == "h2" and tag.get("id") == "feat-descriptions":
            in_descriptions = True
            continue
        if tag.name == "h3" and in_descriptions and tag.get("id"):
            feat = parse_feat(tag)
            if feat:
                feats.append(feat)

    return feats


# ---------------------------------------------------------------------------
# Races
# ---------------------------------------------------------------------------

def parse_race(h2_tag):
    slug = h2_tag.get("id", "")
    name = h2_tag.get_text(strip=True)
    siblings = get_siblings_until(h2_tag, {"h2"})

    # Collect all <li> items as traits
    traits = []
    for sib in siblings:
        if sib.name == "ul":
            for li in sib.find_all("li", recursive=False):
                traits.append(str(li.decode_contents()).strip())
        elif sib.name == "li":
            traits.append(str(sib.decode_contents()).strip())

    desc_html = siblings_to_html(siblings)

    return {
        "name": name,
        "slug": slug,
        "traits": traits,
        "desc_html": desc_html,
    }


# Known race IDs in races.html
RACE_IDS = {"humans", "dwarves", "elves", "gnomes", "half-elves", "half-orcs", "halflings"}


def parse_all_races():
    filepath = RULES_DIR / "races.html"
    soup = load_soup(filepath)
    races = []

    for h2 in soup.find_all("h2"):
        hid = h2.get("id", "")
        if hid in RACE_IDS:
            race = parse_race(h2)
            if race:
                races.append(race)

    return races


# ---------------------------------------------------------------------------
# Equipment
# ---------------------------------------------------------------------------

def parse_table_rows(table):
    """Parse an HTML table into a list of dicts using header row as keys."""
    rows = table.find_all("tr")
    if not rows:
        return []

    # Find header row (first row with <th> cells)
    headers = []
    data_start = 0
    for i, row in enumerate(rows):
        ths = row.find_all("th")
        # Skip colspan-only header rows (like "Spells per Day")
        if ths and not any(th.get("colspan") for th in ths if int(th.get("colspan", 1)) > 2):
            headers = [th.get_text(strip=True) for th in ths]
            data_start = i + 1
            break

    if not headers:
        return []

    items = []
    for row in rows[data_start:]:
        cells = row.find_all("td")
        if not cells:
            continue

        # Skip category rows (single cell spanning full width)
        if len(cells) == 1 and cells[0].get("colspan"):
            continue

        # Handle colspan in data cells
        values = []
        for cell in cells:
            values.append(cell.get_text(strip=True))

        # Pad or truncate to match headers
        while len(values) < len(headers):
            values.append("")
        values = values[: len(headers)]

        item = dict(zip(headers, values))
        items.append(item)

    return items


def clean_equipment_name(name):
    """Strip leading whitespace chars (nbsp) from equipment names."""
    return name.replace("\xa0", " ").strip()


def parse_equipment_table(soup, caption_pattern):
    """Find a table by caption pattern and parse it."""
    for table in soup.find_all("table"):
        cap = table.find("caption")
        if cap and re.search(caption_pattern, cap.get_text(), re.IGNORECASE):
            return parse_table_rows(table)
    return []


def parse_all_equipment():
    filepath = RULES_DIR / "equipment.html"
    soup = load_soup(filepath)

    all_items = []

    # Weapons table
    weapons = parse_equipment_table(soup, r"weapons")
    for w in weapons:
        name = clean_equipment_name(w.get(list(w.keys())[0], "") if w else "")
        if not name or name == "—":
            continue
        w["_category"] = "weapon"
        w["name"] = name
        w["slug"] = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
        all_items.append(w)

    # Armor table
    armor = parse_equipment_table(soup, r"armor and shields")
    for a in armor:
        name = clean_equipment_name(a.get(list(a.keys())[0], "") if a else "")
        if not name or name == "—":
            continue
        a["_category"] = "armor"
        a["name"] = name
        a["slug"] = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
        all_items.append(a)

    # Goods and Services table
    goods = parse_equipment_table(soup, r"goods and services")
    for g in goods:
        name = clean_equipment_name(g.get(list(g.keys())[0], "") if g else "")
        if not name or name == "—":
            continue
        g["_category"] = "goods"
        g["name"] = name
        g["slug"] = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
        all_items.append(g)

    return all_items


# ---------------------------------------------------------------------------
# Classes
# ---------------------------------------------------------------------------

CLASS_FILES = [
    "character-classes-i.html",
    "character-classes-ii.html",
    "npc-classes.html",
    "prestige-classes.html",
]

# IDs to skip (not actual class entries)
SKIP_CLASS_IDS = {
    "table-of-contents", "the-classes", "multiclass-characters",
    "class-and-level-features", "definitions-of-terms", "",
}


def parse_class(h2_tag):
    slug = h2_tag.get("id", "")
    name = h2_tag.get_text(strip=True)
    siblings = get_siblings_until(h2_tag, {"h2"})

    # Extract key fields from first few paragraphs
    hit_die = None
    alignment = None
    for sib in siblings:
        if sib.name == "p":
            label = extract_label(sib)
            if label == "Hit Die":
                hit_die = sib.get_text(strip=True).split(":", 1)[-1].strip()
            elif label == "Alignment":
                alignment = sib.get_text(strip=True).split(":", 1)[-1].strip()

    # Extract the level progression table (first table with "Level" header)
    table_html = None
    for sib in siblings:
        if sib.name == "table":
            cap = sib.find("caption")
            # The main progression table usually has a caption like "Table: The Barbarian"
            if cap or (sib.find("th") and "Level" in (sib.find("th").get_text() if sib.find("th") else "")):
                table_html = str(sib)
                break

    desc_html = siblings_to_html(siblings)

    return {
        "name": name,
        "slug": slug,
        "hit_die": hit_die,
        "alignment": alignment,
        "table_html": table_html,
        "desc_html": desc_html,
    }


def parse_all_classes():
    all_classes = []
    for fname in CLASS_FILES:
        filepath = RULES_DIR / fname
        if not filepath.exists():
            print(f"  Warning: {fname} not found, skipping")
            continue
        soup = load_soup(filepath)

        for h2 in soup.find_all("h2"):
            hid = h2.get("id", "")
            if hid in SKIP_CLASS_IDS:
                continue
            if hid == "table-of-contents" or h2.get_text(strip=True) == "Table of Contents":
                continue
            cls = parse_class(h2)
            if cls:
                all_classes.append(cls)
        print(f"  {fname}: {len(all_classes)} total so far")

    return all_classes


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    DATA_DIR.mkdir(exist_ok=True)
    what = sys.argv[1] if len(sys.argv) > 1 else "all"

    if what in ("all", "spells"):
        print("=== Parsing spells ===")
        data = parse_all_spells()
        write_json(data, "spells.json")

    if what in ("all", "feats"):
        print("=== Parsing feats ===")
        data = parse_all_feats()
        write_json(data, "feats.json")

    if what in ("all", "races"):
        print("=== Parsing races ===")
        data = parse_all_races()
        write_json(data, "races.json")

    if what in ("all", "equipment"):
        print("=== Parsing equipment ===")
        data = parse_all_equipment()
        write_json(data, "equipment.json")

    if what in ("all", "classes"):
        print("=== Parsing classes ===")
        data = parse_all_classes()
        write_json(data, "classes.json")


if __name__ == "__main__":
    main()
