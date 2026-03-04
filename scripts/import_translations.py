#!/usr/bin/env python3
"""Import Italian translations into the translations table.

Reads a JSON file with the format:
[
  {
    "entity_type": "spell",
    "slug": "fireball",
    "field": "name",
    "value": "Palla di Fuoco"
  },
  ...
]

Usage:
  python scripts/import_translations.py translations_it.json
  python scripts/import_translations.py data/translations/*.json
"""

import json
import sqlite3
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = REPO_ROOT / "dnd35.db"

# Map entity_type to table name for slug → id lookup
ENTITY_TABLE = {
    "spell": "spells",
    "feat": "feats",
    "race": "races",
    "class": "classes",
    "equipment": "equipment",
}


def import_file(conn, filepath):
    """Import translations from a single JSON file."""
    with open(filepath) as f:
        entries = json.load(f)

    cur = conn.cursor()
    imported = 0
    skipped = 0

    for entry in entries:
        entity_type = entry["entity_type"]
        slug = entry.get("slug")
        entity_id = entry.get("entity_id")
        field = entry["field"]
        value = entry["value"]
        lang = entry.get("lang", "it")

        # Resolve slug to id if needed
        if entity_id is None and slug:
            table = ENTITY_TABLE.get(entity_type)
            if not table:
                print(f"  Unknown entity_type: {entity_type}, skipping")
                skipped += 1
                continue
            row = cur.execute(
                f"SELECT id FROM {table} WHERE slug=?", (slug,)
            ).fetchone()
            if not row:
                print(f"  {entity_type} slug '{slug}' not found, skipping")
                skipped += 1
                continue
            entity_id = row[0]

        # Upsert translation
        cur.execute(
            """INSERT INTO translations (entity_type, entity_id, lang, field, value)
               VALUES (?, ?, ?, ?, ?)
               ON CONFLICT(entity_type, entity_id, lang, field)
               DO UPDATE SET value=excluded.value""",
            (entity_type, entity_id, lang, field, value),
        )
        imported += 1

    conn.commit()
    return imported, skipped


def ensure_unique_constraint(conn):
    """Add unique constraint on translations if not present."""
    cur = conn.cursor()
    # Check if the unique index exists
    indices = cur.execute(
        "SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='translations'"
    ).fetchall()
    idx_names = [r[0] for r in indices]
    if "idx_translations_unique" not in idx_names:
        cur.execute(
            """CREATE UNIQUE INDEX IF NOT EXISTS idx_translations_unique
               ON translations(entity_type, entity_id, lang, field)"""
        )
        conn.commit()


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/import_translations.py <file.json> [...]")
        print("\nJSON format:")
        print('[{"entity_type": "spell", "slug": "fireball", "field": "name", "value": "Palla di Fuoco"}]')
        sys.exit(1)

    conn = sqlite3.connect(DB_PATH)
    ensure_unique_constraint(conn)

    for arg in sys.argv[1:]:
        for filepath in Path(".").glob(arg) if "*" in arg else [Path(arg)]:
            if not filepath.exists():
                print(f"File not found: {filepath}")
                continue
            print(f"Importing {filepath}...")
            imported, skipped = import_file(conn, filepath)
            print(f"  Imported: {imported}, Skipped: {skipped}")

    conn.close()


if __name__ == "__main__":
    main()
