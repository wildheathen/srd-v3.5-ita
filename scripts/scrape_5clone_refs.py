#!/usr/bin/env python3
"""
Scrape 5clone.com for Italian D&D 3.5 reference data (feats, classes).

Collects Italian names, English names, source book (IT), and page numbers
from individual detail pages on 5clone.com.

Two-phase approach:
  1. Crawl listing pages to collect all detail-page URLs
  2. Fetch each detail page and extract metadata

Resume-safe: caches downloaded HTML in html_cache/5clone/.
Output: data/5clone/{category}_it.json

No external dependencies — uses only Python standard library.

Usage:
    python scripts/scrape_5clone_refs.py feats        # scrape feats
    python scripts/scrape_5clone_refs.py classes       # scrape classes
    python scripts/scrape_5clone_refs.py all           # scrape everything
    python scripts/scrape_5clone_refs.py feats --workers 20
"""

import json
import os
import re
import ssl
import sys
import time
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed
from html.parser import HTMLParser
from threading import Lock

# Workaround for SSLKEYLOGFILE permission errors on some Windows setups
if "SSLKEYLOGFILE" in os.environ:
    del os.environ["SSLKEYLOGFILE"]

BASE_URL = "https://www.5clone.com"
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE_DIR = os.path.join(REPO_ROOT, "html_cache", "5clone")
OUTPUT_DIR = os.path.join(REPO_ROOT, "data", "5clone")
MAX_RETRIES = 3
WORKERS = 10
DELAY = 0.15  # seconds between requests

# Category configs: listing page URL and expected pagination
CATEGORIES = {
    "feats": {
        "list_url": "/enciclopedia/d-d-3-5/77-talenti-ita-35",
        "items_per_page": 10,
        "max_pages": 85,       # safety limit (real ~80)
        "cache_subdir": "feats",
    },
    "classes": {
        "list_url": "/enciclopedia/d-d-3-5/72-classicdp-ita-35",
        "items_per_page": 10,
        "max_pages": 30,       # safety limit (real ~25)
        "cache_subdir": "classes",
    },
}

print_lock = Lock()
stats_lock = Lock()
stats = {"downloaded": 0, "cached": 0, "errors": 0}


def log(msg):
    with print_lock:
        print(msg, flush=True)


def fetch_url(url, retries=MAX_RETRIES):
    """Fetch URL with retries, return HTML string."""
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml",
        "Accept-Language": "it-IT,it;q=0.9,en;q=0.8",
    }
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=30, context=ctx) as resp:
                return resp.read().decode("utf-8", errors="replace")
        except Exception as e:
            if attempt == retries - 1:
                raise
            time.sleep(2 * (attempt + 1))
    return None


# ── Phase 1: Collect detail-page URLs from listing pages ──────────────


def extract_detail_links(html, list_path):
    """Extract detail page URLs from a listing page HTML."""
    # Links look like: /enciclopedia/d-d-3-5/77-talenti-ita-35/13207-afferrare-frecce
    # They have the list_path prefix plus one more path segment
    pattern = re.escape(list_path) + r'/(\d+-[a-z0-9-]+)'
    matches = re.findall(pattern, html)
    seen = set()
    links = []
    for slug in matches:
        full = f"{list_path}/{slug}"
        if full not in seen:
            seen.add(full)
            links.append(full)
    return links


def discover_urls(category):
    """Crawl all listing pages and return list of detail-page URLs."""
    cfg = CATEGORIES[category]
    list_path = cfg["list_url"]
    all_links = []
    seen = set()

    max_pages = cfg["max_pages"]
    items_pp = cfg["items_per_page"]

    log(f"[{category}] Discovering detail pages (up to {max_pages} listing pages)...")

    empty_streak = 0
    for page_idx in range(max_pages):
        offset = page_idx * items_pp
        url = f"{BASE_URL}{list_path}?start={offset}"

        cache_file = os.path.join(CACHE_DIR, cfg["cache_subdir"], f"list_page_{page_idx:03d}.html")
        os.makedirs(os.path.dirname(cache_file), exist_ok=True)

        if os.path.exists(cache_file):
            with open(cache_file, "r", encoding="utf-8") as f:
                html = f.read()
        else:
            try:
                html = fetch_url(url)
                with open(cache_file, "w", encoding="utf-8") as f:
                    f.write(html)
                time.sleep(DELAY)
            except Exception as e:
                log(f"  ERROR page {page_idx}: {e}")
                continue

        links = extract_detail_links(html, list_path)
        new = 0
        for link in links:
            if link not in seen:
                seen.add(link)
                all_links.append(link)
                new += 1

        if new == 0:
            empty_streak += 1
            if empty_streak >= 3:
                log(f"  3 consecutive empty pages at page {page_idx}, stopping discovery")
                break
        else:
            empty_streak = 0

        if (page_idx + 1) % 10 == 0:
            log(f"  Page {page_idx + 1}: {len(all_links)} unique URLs so far")

    log(f"[{category}] Total detail URLs discovered: {len(all_links)}")
    return all_links


# ── Phase 2: Scrape individual detail pages ───────────────────────────


def parse_detail_page(html):
    """Extract metadata from a 5clone detail page using regex.

    Pages have fields like:
      Nome (Ita): Afferrare Frecce
      Nome (Ing): Snatch Arrows
      Riferimento: Manuale del Giocatore 3.5, pag. 89
      Descrizione sommaria: ...
    """
    result = {
        "name_it": "",
        "name_en": "",
        "source_book_it": "",
        "source_page_it": "",
    }

    # Strip HTML tags but preserve newlines between block elements
    text = re.sub(r'<br\s*/?>', '\n', html)
    text = re.sub(r'</(?:p|div|h[1-6]|li|tr|td|th|dt|dd)>', '\n', text)
    text = re.sub(r'<[^>]+>', '', text)
    # Decode entities
    text = text.replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
    text = text.replace('&#39;', "'").replace('&quot;', '"')
    text = re.sub(r'&#(\d+);', lambda m: chr(int(m.group(1))), text)
    text = re.sub(r'&nbsp;', ' ', text)

    # Extract fields using regex
    # Nome (Ita) or Nome (Italiano)
    m = re.search(r'Nome\s*\(?(?:Ita(?:liano)?|It)\)?\s*:\s*(.+?)(?:\n|$)', text, re.IGNORECASE)
    if m:
        result["name_it"] = m.group(1).strip()

    # Nome (Ing) or Nome (Inglese)
    m = re.search(r'Nome\s*\(?(?:Ing(?:lese)?|En[g]?)\)?\s*:\s*(.+?)(?:\n|$)', text, re.IGNORECASE)
    if m:
        result["name_en"] = m.group(1).strip()

    # Riferimento / Fonte / Manuale
    m = re.search(r'(?:Riferimento|Fonte|Manuale)\s*:\s*(.+?)(?:\n|$)', text, re.IGNORECASE)
    if m:
        ref_text = m.group(1).strip()
        # Parse "BookName, pag. NN" or "BookName pag. NN"
        ref_match = re.match(r'^(.+?),?\s*pag\.?\s*(\d+)\s*$', ref_text)
        if ref_match:
            result["source_book_it"] = ref_match.group(1).strip()
            result["source_page_it"] = ref_match.group(2).strip()
        else:
            result["source_book_it"] = ref_text

    # Fallback: title tag
    if not result["name_it"]:
        m = re.search(r'<title>([^<]+)</title>', html)
        if m:
            title = m.group(1).strip().split(" - ")[0].strip()
            result["name_it"] = title

    return result


def scrape_detail(url_path, cache_dir):
    """Download and parse a single detail page. Returns metadata dict."""
    slug = url_path.rstrip("/").split("/")[-1]
    cache_file = os.path.join(cache_dir, f"{slug}.html")

    if os.path.exists(cache_file):
        with open(cache_file, "r", encoding="utf-8") as f:
            html = f.read()
        with stats_lock:
            stats["cached"] += 1
    else:
        try:
            html = fetch_url(f"{BASE_URL}{url_path}")
            os.makedirs(os.path.dirname(cache_file), exist_ok=True)
            with open(cache_file, "w", encoding="utf-8") as f:
                f.write(html)
            with stats_lock:
                stats["downloaded"] += 1
            time.sleep(DELAY)
        except Exception as e:
            with stats_lock:
                stats["errors"] += 1
            log(f"  ERROR {slug}: {e}")
            return None

    meta = parse_detail_page(html)
    # Clean slug: remove numeric prefix "13207-afferrare-frecce" → "afferrare-frecce"
    slug_clean = re.sub(r'^\d+-', '', slug)
    meta["slug_5clone"] = slug_clean
    meta["url_path"] = url_path
    return meta


def scrape_category(category, workers):
    """Full pipeline: discover URLs → scrape detail pages → save JSON."""
    cfg = CATEGORIES[category]
    cache_dir = os.path.join(CACHE_DIR, cfg["cache_subdir"], "detail")
    os.makedirs(cache_dir, exist_ok=True)

    # Phase 1: Discover
    urls = discover_urls(category)
    if not urls:
        log(f"[{category}] No URLs found!")
        return

    # Phase 2: Scrape detail pages
    log(f"\n[{category}] Scraping {len(urls)} detail pages ({workers} workers)...")
    results = []
    done = 0

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(scrape_detail, url, cache_dir): url for url in urls}
        for future in as_completed(futures):
            done += 1
            result = future.result()
            if result:
                results.append(result)
            if done % 50 == 0 or done == len(urls):
                log(f"  Progress: {done}/{len(urls)} "
                    f"(new={stats['downloaded']}, cached={stats['cached']}, errors={stats['errors']})")

    # Sort by Italian name
    results.sort(key=lambda x: x.get("name_it", "").lower())

    # Save
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    out_path = os.path.join(OUTPUT_DIR, f"{category}_it.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    log(f"\n[{category}] Done! {len(results)} entries saved to {out_path}")
    with_book = sum(1 for r in results if r.get("source_book_it"))
    with_page = sum(1 for r in results if r.get("source_page_it"))
    with_en = sum(1 for r in results if r.get("name_en"))
    log(f"  With source book IT: {with_book} ({with_book*100//max(len(results),1)}%)")
    log(f"  With page number:    {with_page} ({with_page*100//max(len(results),1)}%)")
    log(f"  With English name:   {with_en} ({with_en*100//max(len(results),1)}%)")

    return results


def main():
    args = sys.argv[1:]
    workers = WORKERS

    # Parse --workers flag
    if "--workers" in args:
        idx = args.index("--workers")
        workers = int(args[idx + 1])
        args = args[:idx] + args[idx + 2:]

    categories = [a for a in args if a in CATEGORIES]
    if not args or "all" in args:
        categories = list(CATEGORIES.keys())
    if not categories:
        print(f"Usage: {sys.argv[0]} [feats|classes|all] [--workers N]")
        print(f"Available categories: {', '.join(CATEGORIES.keys())}")
        sys.exit(1)

    for cat in categories:
        log(f"\n{'='*60}")
        log(f"Scraping 5clone: {cat}")
        log(f"{'='*60}")
        # Reset stats per category
        stats["downloaded"] = 0
        stats["cached"] = 0
        stats["errors"] = 0
        scrape_category(cat, workers)


if __name__ == "__main__":
    main()
