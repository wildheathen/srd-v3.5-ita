#!/usr/bin/env python3
"""Import parsed JSON data into SQLite database."""

import json
import sqlite3
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data"
DB_PATH = REPO_ROOT / "dnd35.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS spells (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    slug TEXT UNIQUE NOT NULL,
    school TEXT,
    subschool TEXT,
    descriptor TEXT,
    level TEXT,
    components TEXT,
    casting_time TEXT,
    range TEXT,
    target_area_effect TEXT,
    duration TEXT,
    saving_throw TEXT,
    spell_resistance TEXT,
    desc_html TEXT
);

CREATE TABLE IF NOT EXISTS feats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    slug TEXT UNIQUE NOT NULL,
    type TEXT,
    prerequisites TEXT,
    benefit TEXT,
    normal TEXT,
    special TEXT,
    desc_html TEXT
);

CREATE TABLE IF NOT EXISTS races (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    slug TEXT UNIQUE NOT NULL,
    traits_json TEXT,
    desc_html TEXT
);

CREATE TABLE IF NOT EXISTS equipment (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    slug TEXT NOT NULL,
    category TEXT,
    data_json TEXT,
    desc_html TEXT
);

CREATE TABLE IF NOT EXISTS classes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    slug TEXT UNIQUE NOT NULL,
    hit_die TEXT,
    alignment TEXT,
    table_html TEXT,
    desc_html TEXT
);

CREATE TABLE IF NOT EXISTS translations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_type TEXT NOT NULL,
    entity_id INTEGER NOT NULL,
    lang TEXT NOT NULL DEFAULT 'it',
    field TEXT NOT NULL,
    value TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_translations_lookup
    ON translations(entity_type, entity_id, lang, field);

CREATE INDEX IF NOT EXISTS idx_spells_slug ON spells(slug);
CREATE INDEX IF NOT EXISTS idx_feats_slug ON feats(slug);
CREATE INDEX IF NOT EXISTS idx_races_slug ON races(slug);
CREATE INDEX IF NOT EXISTS idx_classes_slug ON classes(slug);
CREATE INDEX IF NOT EXISTS idx_equipment_slug ON equipment(slug);
"""


def import_spells(cur):
    path = DATA_DIR / "spells.json"
    if not path.exists():
        print("  spells.json not found, skipping")
        return 0
    with open(path) as f:
        data = json.load(f)
    for s in data:
        cur.execute(
            """INSERT OR REPLACE INTO spells
               (name, slug, school, subschool, descriptor, level, components,
                casting_time, range, target_area_effect, duration, saving_throw,
                spell_resistance, desc_html)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (s["name"], s["slug"], s["school"], s["subschool"], s["descriptor"],
             s["level"], s["components"], s["casting_time"], s["range"],
             s["target_area_effect"], s["duration"], s["saving_throw"],
             s["spell_resistance"], s["desc_html"]),
        )
    return len(data)


def import_feats(cur):
    path = DATA_DIR / "feats.json"
    if not path.exists():
        print("  feats.json not found, skipping")
        return 0
    with open(path) as f:
        data = json.load(f)
    for feat in data:
        cur.execute(
            """INSERT OR REPLACE INTO feats
               (name, slug, type, prerequisites, benefit, normal, special, desc_html)
               VALUES (?,?,?,?,?,?,?,?)""",
            (feat["name"], feat["slug"], feat["type"], feat["prerequisites"],
             feat["benefit"], feat["normal"], feat["special"], feat["desc_html"]),
        )
    return len(data)


def import_races(cur):
    path = DATA_DIR / "races.json"
    if not path.exists():
        print("  races.json not found, skipping")
        return 0
    with open(path) as f:
        data = json.load(f)
    for race in data:
        cur.execute(
            """INSERT OR REPLACE INTO races
               (name, slug, traits_json, desc_html)
               VALUES (?,?,?,?)""",
            (race["name"], race["slug"],
             json.dumps(race["traits"], ensure_ascii=False),
             race["desc_html"]),
        )
    return len(data)


def import_equipment(cur):
    path = DATA_DIR / "equipment.json"
    if not path.exists():
        print("  equipment.json not found, skipping")
        return 0
    with open(path) as f:
        data = json.load(f)
    for item in data:
        # Store all table columns as JSON
        extra = {k: v for k, v in item.items() if k not in ("name", "slug", "_category")}
        cur.execute(
            """INSERT INTO equipment
               (name, slug, category, data_json)
               VALUES (?,?,?,?)""",
            (item["name"], item["slug"], item["_category"],
             json.dumps(extra, ensure_ascii=False)),
        )
    return len(data)


def import_classes(cur):
    path = DATA_DIR / "classes.json"
    if not path.exists():
        print("  classes.json not found, skipping")
        return 0
    with open(path) as f:
        data = json.load(f)
    for cls in data:
        cur.execute(
            """INSERT OR REPLACE INTO classes
               (name, slug, hit_die, alignment, table_html, desc_html)
               VALUES (?,?,?,?,?,?)""",
            (cls["name"], cls["slug"], cls["hit_die"], cls["alignment"],
             cls["table_html"], cls["desc_html"]),
        )
    return len(data)


def main():
    # Remove existing DB to start fresh
    if DB_PATH.exists():
        DB_PATH.unlink()

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Create schema
    cur.executescript(SCHEMA)
    print("Schema created.")

    importers = [
        ("spells", import_spells),
        ("feats", import_feats),
        ("races", import_races),
        ("equipment", import_equipment),
        ("classes", import_classes),
    ]

    what = sys.argv[1] if len(sys.argv) > 1 else "all"

    for name, fn in importers:
        if what in ("all", name):
            count = fn(cur)
            print(f"Imported {count} {name}")

    conn.commit()
    conn.close()
    print(f"\nDatabase written to {DB_PATH}")


if __name__ == "__main__":
    main()
