#!/usr/bin/env python3
"""
Batch convert all downloaded SRD PDFs to HTML.
Uses spell mode for chapter 10 (incantesimi), generic mode for everything else.

Usage:
  python scripts/convert_all_pdfs.py [--pdf-dir /tmp/srd-pdf-ita] [--output-dir sources/pdf-ita]
  python scripts/convert_all_pdfs.py --force   # re-convert even if HTML exists
"""
import os
import sys
import re
import argparse
import traceback

# Add scripts dir to path so we can import pdf_to_html
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pdf_to_html


def pdf_to_html_name(pdf_filename):
    """Convert PDF filename to HTML filename by stripping srd35_XX_YY_ prefix."""
    name = os.path.splitext(pdf_filename)[0]
    # Strip srd35_XX_YY_ prefix (e.g., srd35_02_01_razze_elfi.pdf → razze_elfi.html)
    name = re.sub(r'^srd35_\d+_\d+_', '', name)
    return name + '.html'


def convert_all(pdf_dir, output_dir, force=False):
    """Convert all PDFs in pdf_dir to HTML in output_dir, preserving chapter structure."""
    if not os.path.isdir(pdf_dir):
        print(f"Error: PDF directory not found: {pdf_dir}")
        print("Run download_srd_pdfs.py first.")
        return False

    converted = 0
    skipped = 0
    errors = []

    # Walk chapter directories
    for chapter in sorted(os.listdir(pdf_dir)):
        chapter_pdf_dir = os.path.join(pdf_dir, chapter)
        if not os.path.isdir(chapter_pdf_dir):
            continue

        chapter_html_dir = os.path.join(output_dir, chapter)
        os.makedirs(chapter_html_dir, exist_ok=True)

        pdfs = sorted(f for f in os.listdir(chapter_pdf_dir) if f.endswith('.pdf'))
        if not pdfs:
            continue

        print(f"\n{'='*60}")
        print(f"Chapter: {chapter} ({len(pdfs)} PDFs)")
        print(f"{'='*60}")

        is_spells = chapter.startswith('10-')

        for pdf_name in pdfs:
            pdf_path = os.path.join(chapter_pdf_dir, pdf_name)
            html_name = pdf_to_html_name(pdf_name)
            html_path = os.path.join(chapter_html_dir, html_name)

            if os.path.exists(html_path) and not force:
                skipped += 1
                continue

            print(f"\n--- {pdf_name} -> {html_name} ---")
            try:
                if is_spells:
                    pdf_to_html.main_spells(pdf_path, html_path)
                else:
                    pdf_to_html.main_generic(pdf_path, html_path)
                converted += 1
            except Exception as e:
                print(f"  ERROR: {e}")
                traceback.print_exc()
                errors.append((pdf_name, str(e)))

    print(f"\n{'='*60}")
    print(f"SUMMARY: Converted: {converted}, Skipped: {skipped}, Errors: {len(errors)}")
    if errors:
        print("Failed files:")
        for f, e in errors:
            print(f"  {f}: {e}")

    return len(errors) == 0


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Batch convert SRD PDFs to HTML')
    parser.add_argument('--pdf-dir', default='/tmp/srd-pdf-ita',
                        help='Input PDF directory (default: /tmp/srd-pdf-ita)')
    parser.add_argument('--output-dir', default='sources/pdf-ita',
                        help='Output HTML directory (default: sources/pdf-ita)')
    parser.add_argument('--force', action='store_true',
                        help='Re-convert even if HTML already exists')
    args = parser.parse_args()
    success = convert_all(args.pdf_dir, args.output_dir, args.force)
    sys.exit(0 if success else 1)
