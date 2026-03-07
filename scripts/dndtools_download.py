#!/usr/bin/env python3
"""
Phase A — Download spell HTML pages from dndtools.net into html_cache/.

Downloads list pages (paginated) for each book, extracts spell URLs,
then downloads individual spell detail pages using parallel workers.

Resume-safe: skips files that already exist.

Usage:
    python scripts/dndtools_download.py                     # download all books
    python scripts/dndtools_download.py PHB SC CArc          # download specific books
    python scripts/dndtools_download.py --test 100           # limit spells per book
    python scripts/dndtools_download.py --workers 100        # parallel workers (default 100)
    python scripts/dndtools_download.py --discover           # just discover books and counts
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

BASE_URL = "https://dndtools.net"
CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "html_cache")
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAX_RETRIES = 3
WORKERS = 100

# Known books with short abbreviations (for CLI convenience)
BOOK_ALIASES = {
    "PHB":  "players-handbook-v35--6",
    "SC":   "spell-compendium--86",
    "CArc": "complete-arcane--55",
    "CDiv": "complete-divine--56",
    "CAd":  "complete-adventurer--54",
    "PHB2": "players-handbook-ii--80",
    "DMG":  "dungeon-masters-guide-v35--4",
}

_print_lock = Lock()

def tprint(msg):
    with _print_lock:
        print(msg, flush=True)


class SpellListParser(HTMLParser):
    """Extract spell URLs and pagination info from a book's spell list page."""

    def __init__(self):
        super().__init__()
        self.spell_urls = []
        self.max_page = 1

    def handle_starttag(self, tag, attrs):
        if tag != "a":
            return
        attrs_dict = dict(attrs)
        href = attrs_dict.get("href", "")

        if re.match(r"/spells/[^/]+/[^/]+/", href) and "?" not in href:
            parts = href.strip("/").split("/")
            if len(parts) == 3 and parts[0] == "spells":
                if parts[1] not in ("schools", "sub-schools", "descriptors", "domains"):
                    full_url = BASE_URL + href
                    if full_url not in self.spell_urls:
                        self.spell_urls.append(full_url)

        page_match = re.search(r"\?page=(\d+)", href)
        if page_match:
            page_num = int(page_match.group(1))
            if page_num > self.max_page:
                self.max_page = page_num


class TotalItemsParser(HTMLParser):
    """Extract total item count from page text."""

    def __init__(self):
        super().__init__()
        self.total = 0
        self._text_chunks = []

    def handle_data(self, data):
        self._text_chunks.append(data)

    def get_total(self):
        text = " ".join(self._text_chunks)
        match = re.search(r"total\s+(\d+)\s+items", text, re.IGNORECASE)
        if match:
            self.total = int(match.group(1))
        return self.total


def fetch_url(url, retries=MAX_RETRIES):
    """Fetch a URL with retries."""
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": "Mozilla/5.0 (D&D SRD project - non-commercial cataloging)",
                "Accept": "text/html,application/xhtml+xml",
            })
            with urllib.request.urlopen(req, timeout=30) as resp:
                return resp.read().decode("utf-8", errors="replace")
        except (urllib.error.URLError, urllib.error.HTTPError,
                TimeoutError, ConnectionError, OSError) as e:
            if attempt < retries - 1:
                time.sleep(2 * (attempt + 1))
            else:
                return None
    return None


def save_html(filepath, html):
    """Save HTML to file, creating directories as needed."""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html)


def download_one_spell(spell_url, spells_dir):
    """Download a single spell page. Returns (slug, status)."""
    parts = spell_url.rstrip("/").split("/")
    spell_slug = parts[-1]
    spell_file = os.path.join(spells_dir, f"{spell_slug}.html")

    if os.path.exists(spell_file):
        return spell_slug, "cached"

    html = fetch_url(spell_url)
    if html:
        save_html(spell_file, html)
        return spell_slug, "downloaded"
    else:
        return spell_slug, "failed"


def slug_to_abbr(slug):
    """Convert a full book slug to a short abbreviation for directory names."""
    # Check known aliases first
    for abbr, known_slug in BOOK_ALIASES.items():
        if slug == known_slug:
            return abbr
    # Generate abbreviation from slug: "book-of-exalted-deeds--52" → "BoED-52"
    parts = slug.split("--")
    name_part = parts[0]
    id_part = parts[1] if len(parts) > 1 else ""
    # Use the slug itself as directory name (clean, unique)
    return name_part


def discover_all_books():
    """Discover all book slugs from the spell index pages."""
    books_file = os.path.join(REPO_ROOT, "all_book_slugs_clean.json")
    if os.path.exists(books_file):
        with open(books_file, "r") as f:
            slugs = json.load(f)
        return slugs

    print("Discovering all books from spell index...")
    html = fetch_url(f"{BASE_URL}/spells/?page=1")
    if not html:
        print("ERROR: Could not fetch spell index")
        return []

    total_match = re.search(r"total\s+(\d+)\s+items", html)
    total = int(total_match.group(1)) if total_match else 0
    pages = (total + 19) // 20
    print(f"Total spells: {total}, Pages: {pages}")

    all_book_slugs = set()

    def extract_books(h):
        links = re.findall(r'/spells/([a-z0-9-]+--\d+)/', h)
        return set(links)

    all_book_slugs.update(extract_books(html))

    page_urls = [f"{BASE_URL}/spells/?page={p}" for p in range(2, pages + 1)]
    with ThreadPoolExecutor(max_workers=100) as pool:
        futures = {pool.submit(fetch_url, url): url for url in page_urls}
        for future in as_completed(futures):
            h = future.result()
            if h:
                all_book_slugs.update(extract_books(h))

    slugs = sorted(all_book_slugs)
    with open(books_file, "w") as f:
        json.dump(slugs, f, indent=2)
    print(f"Found {len(slugs)} books")
    return slugs


def download_book(book_slug, test_limit=0, workers=WORKERS):
    """Download all spell pages for a book using parallel workers."""
    abbr = slug_to_abbr(book_slug)
    book_dir = os.path.join(CACHE_DIR, abbr)
    spells_dir = os.path.join(book_dir, "spells")
    os.makedirs(spells_dir, exist_ok=True)

    # Phase 1: Download list pages and collect spell URLs
    all_spell_urls = []
    page = 1

    list_url = f"{BASE_URL}/spells/{book_slug}/?page={page}"
    list_file = os.path.join(book_dir, f"list_page_{page}.html")

    if os.path.exists(list_file):
        with open(list_file, "r", encoding="utf-8") as f:
            html = f.read()
    else:
        html = fetch_url(list_url)
        if not html:
            print(f"  [ERROR] Could not fetch list page for {book_slug}")
            return [], 0
        save_html(list_file, html)

    parser = SpellListParser()
    parser.feed(html)
    all_spell_urls.extend(parser.spell_urls)
    max_page = parser.max_page

    total_parser = TotalItemsParser()
    total_parser.feed(html)
    total = total_parser.get_total()

    # Download remaining list pages in parallel
    if max_page > 1:
        list_tasks = []
        for pg in range(2, max_page + 1):
            lf = os.path.join(book_dir, f"list_page_{pg}.html")
            if os.path.exists(lf):
                with open(lf, "r", encoding="utf-8") as f:
                    p = SpellListParser()
                    p.feed(f.read())
                    all_spell_urls.extend(p.spell_urls)
            else:
                list_tasks.append((pg, f"{BASE_URL}/spells/{book_slug}/?page={pg}", lf))

        if list_tasks:
            with ThreadPoolExecutor(max_workers=min(workers, len(list_tasks))) as pool:
                futures = {}
                for pg, url, lf in list_tasks:
                    futures[pool.submit(fetch_url, url)] = (pg, url, lf)
                for future in as_completed(futures):
                    pg, url, lf = futures[future]
                    h = future.result()
                    if h:
                        save_html(lf, h)
                        p = SpellListParser()
                        p.feed(h)
                        all_spell_urls.extend(p.spell_urls)

    # Deduplicate
    seen = set()
    unique_urls = []
    for url in all_spell_urls:
        if url not in seen:
            seen.add(url)
            unique_urls.append(url)
    all_spell_urls = unique_urls

    if test_limit > 0:
        all_spell_urls = all_spell_urls[:test_limit]

    # Phase 2: Download spell pages in parallel
    to_download = []
    cached = 0
    for spell_url in all_spell_urls:
        parts = spell_url.rstrip("/").split("/")
        spell_slug_name = parts[-1]
        spell_file = os.path.join(spells_dir, f"{spell_slug_name}.html")
        if os.path.exists(spell_file):
            cached += 1
        else:
            to_download.append(spell_url)

    downloaded = 0
    failed = 0
    failed_urls = []

    if to_download:
        t0 = time.time()
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {
                pool.submit(download_one_spell, url, spells_dir): url
                for url in to_download
            }
            done_count = 0
            for future in as_completed(futures):
                slug_name, status = future.result()
                done_count += 1
                if status == "downloaded":
                    downloaded += 1
                elif status == "failed":
                    failed += 1
                    failed_urls.append(futures[future])
                if done_count % 100 == 0 or done_count == len(to_download):
                    elapsed = time.time() - t0
                    rate = done_count / elapsed if elapsed > 0 else 0
                    tprint(f"    [{abbr}] {done_count}/{len(to_download)} "
                           f"({downloaded} ok, {failed} fail) "
                           f"[{rate:.0f} req/s]")

    # Save manifest
    manifest = {
        "slug": book_slug,
        "abbr": abbr,
        "total_spells": len(all_spell_urls),
        "spell_urls": all_spell_urls,
    }
    manifest_file = os.path.join(book_dir, "manifest.json")
    with open(manifest_file, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    return all_spell_urls, failed


def main():
    args = sys.argv[1:]
    test_limit = 0
    workers = WORKERS
    target_slugs = None
    discover_only = False

    i = 0
    while i < len(args):
        if args[i] == "--test" and i + 1 < len(args):
            test_limit = int(args[i + 1])
            i += 2
        elif args[i] == "--workers" and i + 1 < len(args):
            workers = int(args[i + 1])
            i += 2
        elif args[i] == "--discover":
            discover_only = True
            i += 1
        else:
            # Check if it's a known alias or a full slug
            arg = args[i]
            matched_slug = None
            for alias, slug in BOOK_ALIASES.items():
                if arg.lower() == alias.lower():
                    matched_slug = slug
                    break
            if not matched_slug and re.match(r"^[a-z0-9-]+--\d+$", arg):
                matched_slug = arg
            if matched_slug:
                if target_slugs is None:
                    target_slugs = []
                target_slugs.append(matched_slug)
                i += 1
                continue
            print(f"Unknown argument: {arg}")
            print(f"Aliases: {', '.join(BOOK_ALIASES.keys())}")
            print(f"Or use full slug like: complete-arcane--55")
            sys.exit(1)

    # Discover all books
    all_slugs = discover_all_books()

    if target_slugs is None:
        target_slugs = all_slugs

    if discover_only:
        print(f"\n{len(all_slugs)} books with spells on dndtools.net:")
        for s in all_slugs:
            print(f"  {s}")
        return

    print(f"\nD&D Tools Spell Downloader")
    print(f"Cache dir: {CACHE_DIR}")
    print(f"Books: {len(target_slugs)}")
    print(f"Workers: {workers}")
    if test_limit:
        print(f"Test mode: {test_limit} spells per book")
    print()

    os.makedirs(CACHE_DIR, exist_ok=True)

    total_spells = 0
    total_failed = 0
    book_stats = []

    for book_slug in target_slugs:
        abbr = slug_to_abbr(book_slug)
        urls, failed = download_book(book_slug, test_limit, workers)
        count = len(urls)
        total_spells += count
        total_failed += failed
        if count > 0:
            status = f" ({failed} failed)" if failed else ""
            tprint(f"  {abbr}: {count} spells{status}")
        book_stats.append({"slug": book_slug, "abbr": abbr, "count": count, "failed": failed})

    print(f"\n{'='*60}")
    print(f"Done! Total spells: {total_spells} across {len(target_slugs)} books")
    if total_failed:
        print(f"Total failed: {total_failed}")
    print(f"HTML cache: {CACHE_DIR}")

    # Save global stats
    stats_file = os.path.join(CACHE_DIR, "download_stats.json")
    with open(stats_file, "w", encoding="utf-8") as f:
        json.dump({"total_spells": total_spells, "books": book_stats}, f, indent=2)


if __name__ == "__main__":
    main()
