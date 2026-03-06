#!/usr/bin/env python3
"""
Scrape spell detail pages from 5clone.com to extract:
- Nome (Ita): Italian name
- Nome (Ing): English name
- Riferimento: Source manual + page number
- Descrizione sommaria: Brief description

IMPORTANT: Run this script on your LOCAL machine, not in CI/cloud.
The site blocks automated access from server IPs.

Prerequisites:
    pip install requests beautifulsoup4

Usage:
    python scripts/scrape_5clone.py              # scrape ITA detail pages
    python scripts/scrape_5clone.py --eng        # scrape ENG detail pages
    python scripts/scrape_5clone.py --resume     # resume interrupted scraping
    python scripts/scrape_5clone.py --test 5     # test with first 5 pages only

Produces: sources/contrib/5clone_spells_raw.json
"""

import argparse
import json
import random
import re
import sys
import time
from pathlib import Path

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    print("Installa le dipendenze: pip install requests beautifulsoup4")
    sys.exit(1)

REPO_ROOT = Path(__file__).resolve().parent.parent
CONTRIB = REPO_ROOT / "sources" / "contrib"
URLS_FILE = CONTRIB / "5clone_spell_urls.json"
OUTPUT_FILE = CONTRIB / "5clone_spells_raw.json"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "it-IT,it;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "DNT": "1",
}

# Mapping of Italian manual names to source codes
MANUAL_MAP = {
    "Manuale del Giocatore 3.5":    {"code": "PHB",  "abbr_it": "MdG",  "name_en": "Player's Handbook"},
    "Manuale del Giocatore":        {"code": "PHB",  "abbr_it": "MdG",  "name_en": "Player's Handbook"},
    "Perfetto Combattente":         {"code": "CW",   "abbr_it": "PC",   "name_en": "Complete Warrior"},
    "Perfetto Sacerdote":           {"code": "CD",   "abbr_it": "PS",   "name_en": "Complete Divine"},
    "Perfetto Arcanista":           {"code": "CA",   "abbr_it": "PA",   "name_en": "Complete Arcane"},
    "Perfetto Avventuriero":        {"code": "CAd",  "abbr_it": "PAv",  "name_en": "Complete Adventurer"},
    "Razze di Pietra":              {"code": "RoS",  "abbr_it": "RdP",  "name_en": "Races of Stone"},
    "Razze del Destino":            {"code": "RoD",  "abbr_it": "RdD",  "name_en": "Races of Destiny"},
    "Libro delle Imprese Eroiche":  {"code": "BoED", "abbr_it": "LIE",  "name_en": "Book of Exalted Deeds"},
    "Atlante Planare":              {"code": "PlH",  "abbr_it": "AP",   "name_en": "Planar Handbook"},
    "Draconomicon":                 {"code": "Drac", "abbr_it": "Drac", "name_en": "Draconomicon"},
    "Liber Mortis":                 {"code": "LM",   "abbr_it": "LM",   "name_en": "Libris Mortis"},
    "Signori della Follia":         {"code": "LoM",  "abbr_it": "SdF",  "name_en": "Lords of Madness"},
    "Eroi dell'Orrore":             {"code": "HoH",  "abbr_it": "EdO",  "name_en": "Heroes of Horror"},
    "Codex Immondo I":              {"code": "FC1",  "abbr_it": "CI1",  "name_en": "Fiendish Codex I"},
    "Codex Immondo I: Orde dell'Abisso": {"code": "FC1", "abbr_it": "CI1", "name_en": "Fiendish Codex I"},
}


def parse_reference(ref_text):
    """Parse reference field like 'Manuale del Giocatore 3.5, pag. 279'."""
    ref_text = ref_text.strip()
    # Try to extract manual name and page
    match = re.match(r"^(.+?),?\s*pag\.?\s*(\d+)\s*$", ref_text)
    if match:
        manual_name = match.group(1).strip()
        page = match.group(2)
    else:
        manual_name = ref_text
        page = None

    # Look up manual code
    source_code = None
    for key, info in MANUAL_MAP.items():
        if key.lower() in manual_name.lower() or manual_name.lower() in key.lower():
            source_code = info["code"]
            break

    return {
        "manual_name": manual_name,
        "source_code": source_code or manual_name,
        "page": page,
    }


def scrape_detail_page(url, session):
    """Scrape a single spell detail page."""
    resp = session.get(url, headers=HEADERS, timeout=20)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")

    result = {
        "url": url,
        "name_it": None,
        "name_en": None,
        "reference": None,
        "source_code": None,
        "manual_name": None,
        "page": None,
        "summary_it": None,
    }

    # Strategy 1: Look for labeled fields in the article/page content
    # Fields often appear as: "Nome (Ita): ...", "Nome (Ing): ...", etc.
    article = soup.find("div", class_="item-page") or soup.find("article") or soup.find("body")
    if not article:
        return result

    text = article.get_text("\n", strip=True)

    # Try regex patterns for labeled fields
    patterns = {
        "name_it": [
            r"Nome\s*\(?[Ii]ta(?:liano)?\)?\s*:\s*(.+?)(?:\n|$)",
            r"Nome\s*\(?[Ii]t\)?\s*:\s*(.+?)(?:\n|$)",
        ],
        "name_en": [
            r"Nome\s*\(?[Ii]ng(?:lese)?\)?\s*:\s*(.+?)(?:\n|$)",
            r"Nome\s*\(?[Ee]ng?\)?\s*:\s*(.+?)(?:\n|$)",
        ],
        "reference": [
            r"Riferimento\s*:\s*(.+?)(?:\n|$)",
            r"Fonte\s*:\s*(.+?)(?:\n|$)",
            r"Manuale\s*:\s*(.+?)(?:\n|$)",
        ],
        "summary_it": [
            r"Descrizione\s*(?:sommaria|breve)?\s*:\s*(.+?)(?:\n|$)",
        ],
    }

    for field, pats in patterns.items():
        for pat in pats:
            m = re.search(pat, text)
            if m:
                result[field] = m.group(1).strip()
                break

    # Strategy 2: Look for <dt>/<dd> or <strong>/<span> pairs
    if not result["name_it"]:
        for strong in article.find_all(["strong", "b", "dt"]):
            label = strong.get_text(strip=True).lower()
            sibling = strong.next_sibling
            value = ""
            if sibling:
                if hasattr(sibling, "get_text"):
                    value = sibling.get_text(strip=True)
                else:
                    value = str(sibling).strip().lstrip(":").strip()

            if "nome" in label and ("ita" in label or "it" in label):
                result["name_it"] = value
            elif "nome" in label and ("ing" in label or "eng" in label or "en" in label):
                result["name_en"] = value
            elif "riferimento" in label or "fonte" in label:
                result["reference"] = value
            elif "descrizione" in label:
                result["summary_it"] = value

    # Parse reference into components
    if result["reference"]:
        ref = parse_reference(result["reference"])
        result["source_code"] = ref["source_code"]
        result["manual_name"] = ref["manual_name"]
        result["page"] = ref["page"]

    # Fallback: use page title as name_it
    if not result["name_it"]:
        title = soup.find("title")
        if title:
            result["name_it"] = title.get_text(strip=True).split(" - ")[0].strip()

    return result


def load_progress():
    """Load previously scraped data for resume support."""
    if OUTPUT_FILE.exists():
        with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def save_progress(data):
    """Save current scraping progress."""
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def main():
    parser = argparse.ArgumentParser(description="Scrape 5clone.com spell details")
    parser.add_argument("--eng", action="store_true", help="Scrape English detail pages instead of Italian")
    parser.add_argument("--resume", action="store_true", help="Resume interrupted scraping")
    parser.add_argument("--test", type=int, default=0, help="Test with N pages only")
    parser.add_argument("--delay-min", type=float, default=1.5, help="Min delay between requests (seconds)")
    parser.add_argument("--delay-max", type=float, default=3.0, help="Max delay between requests (seconds)")
    parser.add_argument("--workers", type=int, default=1, help="Number of parallel workers (default 1)")
    args = parser.parse_args()

    if not URLS_FILE.exists():
        print(f"ERROR: {URLS_FILE} non trovato.")
        print("Esegui prima: python scripts/parse_5clone_index.py")
        return

    with open(URLS_FILE, "r", encoding="utf-8") as f:
        urls_data = json.load(f)

    source_key = "eng_spells" if args.eng else "ita_spells"
    spells_to_scrape = urls_data[source_key]

    # Load progress for resume
    scraped = load_progress() if args.resume else []
    scraped_urls = {s["url"] for s in scraped}

    # Filter out already-scraped
    remaining = [s for s in spells_to_scrape if s["url"] not in scraped_urls]

    if args.test > 0:
        remaining = remaining[:args.test]

    total = len(spells_to_scrape)
    done = len(scraped)
    to_do = len(remaining)

    print(f"Totale incantesimi: {total}")
    print(f"Già scaricati: {done}")
    print(f"Da scaricare: {to_do}")
    if args.workers > 1:
        print(f"Workers paralleli: {args.workers}")
    else:
        print(f"Delay: {args.delay_min}-{args.delay_max}s tra richieste")
    print()

    if to_do == 0:
        print("Nessun incantesimo da scaricare. Tutto completato!")
        return

    # ── Parallel mode ────────────────────────────────────────────────────
    if args.workers > 1:
        from concurrent.futures import ThreadPoolExecutor, as_completed
        import threading

        lock = threading.Lock()
        counter = [done]  # mutable counter for threads

        def fetch_one(spell):
            session = requests.Session()
            url = spell["url"]
            name = spell["name"]
            try:
                result = scrape_detail_page(url, session)
                result["index_name"] = name
                result["index_id"] = spell.get("id", 0)
                with lock:
                    counter[0] += 1
                    src = result.get("source_code", "?")
                    en = result.get("name_en", "?")
                    print(f"[{counter[0]}/{total}] {name} OK [{src}] EN: {en}")
                return result
            except Exception as e:
                with lock:
                    counter[0] += 1
                    print(f"[{counter[0]}/{total}] {name} ERROR: {e}")
                return None

        results = []
        with ThreadPoolExecutor(max_workers=args.workers) as executor:
            futures = {executor.submit(fetch_one, spell): spell for spell in remaining}
            try:
                for future in as_completed(futures):
                    result = future.result()
                    if result:
                        results.append(result)
                    # Save progress every 100
                    if len(results) % 100 == 0:
                        save_progress(scraped + results)
                        print(f"  [Progresso salvato: {done + len(results)}/{total}]")
            except KeyboardInterrupt:
                print("\nInterrotto! Salvataggio progresso...")
                executor.shutdown(wait=False, cancel_futures=True)

        scraped.extend(results)
        save_progress(scraped)
        print(f"\nScraping completato! Salvati {len(scraped)} incantesimi in {OUTPUT_FILE}")
        print(f"\nProssimo passo: python scripts/merge_5clone_spells.py")
        return

    # ── Sequential mode ──────────────────────────────────────────────────
    session = requests.Session()
    errors = 0
    max_consecutive_errors = 10

    for i, spell in enumerate(remaining, 1):
        url = spell["url"]
        name = spell["name"]
        print(f"[{done + i}/{total}] {name}...", end=" ", flush=True)

        try:
            result = scrape_detail_page(url, session)
            # Merge index data with scraped data
            result["index_name"] = name
            result["index_id"] = spell.get("id", 0)
            scraped.append(result)
            errors = 0

            # Show what we found
            src = result.get("source_code", "?")
            en = result.get("name_en", "?")
            print(f"OK [{src}] EN: {en}")

        except requests.exceptions.HTTPError as e:
            print(f"HTTP ERROR {e.response.status_code}")
            errors += 1
            if e.response.status_code == 403:
                print("\n  ATTENZIONE: Il sito sta bloccando le richieste.")
                print("  Prova ad aumentare il delay con --delay-min e --delay-max")
                if errors >= 3:
                    print("  Troppi 403 consecutivi, salvataggio e interruzione.")
                    save_progress(scraped)
                    return
        except Exception as e:
            print(f"ERROR: {e}")
            errors += 1

        if errors >= max_consecutive_errors:
            print(f"\n  Troppi errori consecutivi ({max_consecutive_errors}), interruzione.")
            break

        # Save progress every 50 pages
        if i % 50 == 0:
            save_progress(scraped)
            print(f"  [Progresso salvato: {done + i}/{total}]")

        # Random delay to be polite
        delay = random.uniform(args.delay_min, args.delay_max)
        time.sleep(delay)

    save_progress(scraped)
    print(f"\nScraping completato! Salvati {len(scraped)} incantesimi in {OUTPUT_FILE}")
    print(f"\nProssimo passo: python scripts/merge_5clone_spells.py")


if __name__ == "__main__":
    main()
