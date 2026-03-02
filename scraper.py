#!/usr/bin/env python3
"""Franchise Scout — CLI principal.

Uso:
  python scraper.py --max 5          # test rápido (5 franquicias por fuente)
  python scraper.py --skip-analysis  # solo extrae nombres, sin analizar webs
  python scraper.py                  # pipeline completo
  python scraper.py --source mundo   # solo mundofranquicia
  python scraper.py --no-sheets      # no escribir a Google Sheets
"""

import argparse
import logging
import sys
import os
import time

# Ensure project root is in path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from scrapers.mundofranquicia import scrape as scrape_mundo
from scrapers.franquiciashoy import scrape as scrape_franquiciashoy
from analysis.search import find_official_website
from analysis.web_analyzer import analyze as analyze_website

SEARCH_DELAY = 6.0
ANALYSIS_DELAY = 2.0

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("franchise-scout")


def run_scraping(source, max_items):
    """Run scrapers for the specified source(s)."""
    all_records = []

    if source in ("all", "mundo"):
        logger.info("========== Source: mundofranquicia ==========")
        records = scrape_mundo(max_items=max_items)
        all_records.extend(records)

    if source in ("all", "franquiciashoy"):
        logger.info("========== Source: franquiciashoy ==========")
        records = scrape_franquiciashoy(max_items=max_items)
        all_records.extend(records)

    return all_records


def run_analysis(records):
    """Find official websites and analyze them."""
    for i, record in enumerate(records):
        logger.info(f"--- Analyzing {i+1}/{len(records)}: {record['nombre']} ---")

        # Search for official website
        time.sleep(SEARCH_DELAY)
        official_url = find_official_website(record["nombre"])

        if official_url:
            time.sleep(ANALYSIS_DELAY)
            analysis = analyze_website(official_url)
        else:
            analysis = {
                "web_oficial": "",
                "seccion_franquiciados": False,
                "url_seccion_franquiciados": None,
                "email": None,
                "tipo_email": None,
                "linkedin_url": None,
                "formulario_franquicia": False,
                "material_descargable": False,
                "url_material_descargable": None,
                "notas": "Web oficial no encontrada",
            }

        record["analysis"] = analysis

    return records


def run_sheets(records):
    """Write records to Google Sheets."""
    from output.sheets import write as write_sheets
    write_sheets(records)


def main():
    parser = argparse.ArgumentParser(description="Franchise Scout — scraper de franquicias españolas")
    parser.add_argument("--max", type=int, default=None, help="Max franchises per source (for testing)")
    parser.add_argument("--skip-analysis", action="store_true", help="Skip web analysis, only scrape directories")
    parser.add_argument("--no-sheets", action="store_true", help="Don't write to Google Sheets")
    parser.add_argument("--csv", nargs="?", const="output/franquicias.csv", default=None,
                        metavar="FILE", help="Export to CSV (default: output/franquicias.csv)")
    parser.add_argument(
        "--source",
        choices=["all", "mundo", "franquiciashoy"],
        default="all",
        help="Source to scrape (default: all)",
    )
    args = parser.parse_args()

    logger.info(
        f"Franchise Scout starting. source={args.source} max={args.max} "
        f"skip_analysis={args.skip_analysis}"
    )

    # Step 1: Scrape directories
    records = run_scraping(args.source, args.max)
    logger.info(f"Total franchises scraped: {len(records)}")

    if not records:
        logger.warning("No franchises found. Exiting.")
        return

    # Step 2: Analyze websites (unless skipped)
    if not args.skip_analysis:
        records = run_analysis(records)
    else:
        # Add empty analysis for sheets compatibility
        for r in records:
            r["analysis"] = {}

    # Step 3: Output results
    if args.csv:
        from output.csv_export import write as write_csv
        write_csv(records, path=args.csv)

    if not args.no_sheets and not args.csv:
        try:
            run_sheets(records)
        except FileNotFoundError as e:
            logger.error(str(e))
            logger.info("Skipping Google Sheets output. Results printed below:")
            _print_results(records)
    elif not args.csv:
        _print_results(records)

    logger.info("Done!")


def _print_results(records):
    """Print results to stdout as a simple table."""
    print("\n" + "=" * 80)
    print(f"{'RESULTADOS':^80}")
    print("=" * 80)
    for i, r in enumerate(records, 1):
        analysis = r.get("analysis", {})
        print(f"\n[{i}] {r['nombre']}")
        print(f"    Sector: {r['sector']}")
        print(f"    Fuente: {r['fuente']}")
        print(f"    URL directorio: {r['url_directorio']}")
        if analysis.get("web_oficial"):
            print(f"    Web oficial: {analysis['web_oficial']}")
        if analysis.get("email"):
            print(f"    Email: {analysis['email']} ({analysis.get('tipo_email', '')})")
        if analysis.get("linkedin_url"):
            print(f"    LinkedIn: {analysis['linkedin_url']}")
        if analysis.get("seccion_franquiciados"):
            print(f"    Sección franquiciados: {analysis.get('url_seccion_franquiciados', 'Sí')}")
        if analysis.get("formulario_franquicia"):
            print(f"    Formulario captación: Sí")
        if analysis.get("material_descargable"):
            print(f"    Material: {analysis.get('url_material_descargable', 'Sí')}")
        if analysis.get("notas"):
            print(f"    Notas: {analysis['notas']}")
    print("\n" + "=" * 80)


if __name__ == "__main__":
    main()
