"""Crystal Ball — FastAPI backend for D&D 3.5 SRD data."""

import json
import sqlite3
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

DB_PATH = Path(__file__).resolve().parent.parent / "dnd35.db"

app = FastAPI(title="Crystal Ball", version="0.1.0",
              description="D&D 3.5 SRD Reference API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def rows_to_dicts(rows):
    return [dict(r) for r in rows]


def apply_translation(item, entity_type, conn, lang="it"):
    """Overlay translated fields if available."""
    rows = conn.execute(
        "SELECT field, value FROM translations WHERE entity_type=? AND entity_id=? AND lang=?",
        (entity_type, item["id"], lang),
    ).fetchall()
    for row in rows:
        item[f"{row['field']}_{lang}"] = row["value"]
    return item


# ── Spells ──────────────────────────────────────────────────────────────

@app.get("/api/spells")
def list_spells(
    q: Optional[str] = Query(None, description="Search by name"),
    school: Optional[str] = None,
    level: Optional[str] = None,
    lang: Optional[str] = None,
    limit: int = Query(50, le=500),
    offset: int = 0,
):
    conn = get_db()
    sql = "SELECT * FROM spells WHERE 1=1"
    params = []

    if q:
        sql += " AND name LIKE ?"
        params.append(f"%{q}%")
    if school:
        sql += " AND school LIKE ?"
        params.append(f"%{school}%")
    if level:
        sql += " AND level LIKE ?"
        params.append(f"%{level}%")

    sql += " ORDER BY name LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    rows = rows_to_dicts(conn.execute(sql, params).fetchall())
    if lang:
        rows = [apply_translation(r, "spell", conn, lang) for r in rows]
    conn.close()
    return {"count": len(rows), "results": rows}


@app.get("/api/spells/{slug}")
def get_spell(slug: str, lang: Optional[str] = None):
    conn = get_db()
    row = conn.execute("SELECT * FROM spells WHERE slug=?", (slug,)).fetchone()
    if not row:
        conn.close()
        raise HTTPException(404, "Spell not found")
    item = dict(row)
    if lang:
        apply_translation(item, "spell", conn, lang)
    conn.close()
    return item


# ── Feats ───────────────────────────────────────────────────────────────

@app.get("/api/feats")
def list_feats(
    q: Optional[str] = Query(None),
    type: Optional[str] = None,
    lang: Optional[str] = None,
    limit: int = Query(50, le=500),
    offset: int = 0,
):
    conn = get_db()
    sql = "SELECT * FROM feats WHERE 1=1"
    params = []

    if q:
        sql += " AND name LIKE ?"
        params.append(f"%{q}%")
    if type:
        sql += " AND type=?"
        params.append(type)

    sql += " ORDER BY name LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    rows = rows_to_dicts(conn.execute(sql, params).fetchall())
    if lang:
        rows = [apply_translation(r, "feat", conn, lang) for r in rows]
    conn.close()
    return {"count": len(rows), "results": rows}


@app.get("/api/feats/{slug}")
def get_feat(slug: str, lang: Optional[str] = None):
    conn = get_db()
    row = conn.execute("SELECT * FROM feats WHERE slug=?", (slug,)).fetchone()
    if not row:
        conn.close()
        raise HTTPException(404, "Feat not found")
    item = dict(row)
    if lang:
        apply_translation(item, "feat", conn, lang)
    conn.close()
    return item


# ── Races ───────────────────────────────────────────────────────────────

@app.get("/api/races")
def list_races(lang: Optional[str] = None):
    conn = get_db()
    rows = rows_to_dicts(conn.execute("SELECT * FROM races ORDER BY name").fetchall())
    for r in rows:
        if r.get("traits_json"):
            r["traits"] = json.loads(r["traits_json"])
            del r["traits_json"]
    if lang:
        rows = [apply_translation(r, "race", conn, lang) for r in rows]
    conn.close()
    return {"count": len(rows), "results": rows}


@app.get("/api/races/{slug}")
def get_race(slug: str, lang: Optional[str] = None):
    conn = get_db()
    row = conn.execute("SELECT * FROM races WHERE slug=?", (slug,)).fetchone()
    if not row:
        conn.close()
        raise HTTPException(404, "Race not found")
    item = dict(row)
    if item.get("traits_json"):
        item["traits"] = json.loads(item["traits_json"])
        del item["traits_json"]
    if lang:
        apply_translation(item, "race", conn, lang)
    conn.close()
    return item


# ── Equipment ───────────────────────────────────────────────────────────

@app.get("/api/equipment")
def list_equipment(
    q: Optional[str] = Query(None),
    category: Optional[str] = None,
    lang: Optional[str] = None,
    limit: int = Query(50, le=500),
    offset: int = 0,
):
    conn = get_db()
    sql = "SELECT * FROM equipment WHERE 1=1"
    params = []

    if q:
        sql += " AND name LIKE ?"
        params.append(f"%{q}%")
    if category:
        sql += " AND category=?"
        params.append(category)

    sql += " ORDER BY name LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    rows = rows_to_dicts(conn.execute(sql, params).fetchall())
    for r in rows:
        if r.get("data_json"):
            r["data"] = json.loads(r["data_json"])
            del r["data_json"]
    if lang:
        rows = [apply_translation(r, "equipment", conn, lang) for r in rows]
    conn.close()
    return {"count": len(rows), "results": rows}


@app.get("/api/equipment/{item_id}")
def get_equipment(item_id: int, lang: Optional[str] = None):
    conn = get_db()
    row = conn.execute("SELECT * FROM equipment WHERE id=?", (item_id,)).fetchone()
    if not row:
        conn.close()
        raise HTTPException(404, "Equipment not found")
    item = dict(row)
    if item.get("data_json"):
        item["data"] = json.loads(item["data_json"])
        del item["data_json"]
    if lang:
        apply_translation(item, "equipment", conn, lang)
    conn.close()
    return item


# ── Classes ─────────────────────────────────────────────────────────────

@app.get("/api/classes")
def list_classes(lang: Optional[str] = None):
    conn = get_db()
    rows = rows_to_dicts(
        conn.execute("SELECT id, name, slug, hit_die, alignment FROM classes ORDER BY name").fetchall()
    )
    if lang:
        rows = [apply_translation(r, "class", conn, lang) for r in rows]
    conn.close()
    return {"count": len(rows), "results": rows}


@app.get("/api/classes/{slug}")
def get_class(slug: str, lang: Optional[str] = None):
    conn = get_db()
    row = conn.execute("SELECT * FROM classes WHERE slug=?", (slug,)).fetchone()
    if not row:
        conn.close()
        raise HTTPException(404, "Class not found")
    item = dict(row)
    if lang:
        apply_translation(item, "class", conn, lang)
    conn.close()
    return item
