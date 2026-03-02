"""Scraper for franquiciashoy.es — AJAX endpoint at /ajax/franquicias?page=N"""

import logging
import re
import time
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

logger = logging.getLogger("scrapers.franquiciashoy")

BASE = "https://www.franquiciashoy.es"
AJAX_URL = BASE + "/ajax/franquicias"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "es-ES,es;q=0.9",
    "X-Requested-With": "XMLHttpRequest",
}
DELAY = 2.5


def _get_ajax(page):
    resp = requests.get(AJAX_URL, params={"page": page}, headers=HEADERS, timeout=20)
    resp.raise_for_status()
    return BeautifulSoup(resp.text, "lxml")


def _extract_profiles(soup):
    """Extract franchise profile URLs from AJAX response."""
    links = set()
    for a in soup.find_all("a", href=True):
        href = a["href"]
        full = urljoin(BASE, href)
        # Profile URLs: /franquicias/<sector>/<subsector>/<name>
        if "/franquicias/" in full and full.rstrip("/").count("/") >= 5:
            if "?page=" not in full and "/ajax/" not in full:
                links.add(full)
    return links


def _get_max_page(soup):
    """Find last page from getFranquicias2(N) calls in pagination."""
    text = str(soup)
    matches = re.findall(r"getFranquicias2\((\d+)\)", text)
    if matches:
        return max(int(m) for m in matches)
    # Fallback: look for page numbers in pagination links
    max_page = 1
    for el in soup.find_all(["a", "span"], class_="page-link"):
        txt = el.get_text(strip=True)
        if txt.isdigit():
            max_page = max(max_page, int(txt))
    return max_page


def _parse_profile(url):
    """Parse a single franchise profile page."""
    resp = requests.get(url, headers={
        "User-Agent": HEADERS["User-Agent"],
        "Accept-Language": "es-ES,es;q=0.9",
    }, timeout=20)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "lxml")

    h1 = soup.find("h1")
    name = h1.get_text(strip=True) if h1 else None
    if not name:
        return None

    for prefix in ["Franquicia ", "Franquicias "]:
        if name.startswith(prefix):
            name = name[len(prefix):]

    # Sector from URL: /franquicias/<sector>/<subsector>/<name>
    parts = url.rstrip("/").split("/")
    sector_slug = ""
    for i, p in enumerate(parts):
        if p == "franquicias" and i + 1 < len(parts):
            sector_slug = parts[i + 1]
            break
    sector = sector_slug.replace("-", " ").title() if sector_slug else "Desconocido"

    # Try breadcrumb for better sector name
    for bc in soup.find_all(["nav", "ol", "ul", "div"], class_=lambda x: x and "bread" in (x or "").lower()):
        items = bc.find_all(["li", "a", "span"])
        for item in items:
            text = item.get_text(strip=True)
            if text.lower() not in ["inicio", "home", "franquicias", name.lower(), ""] and len(text) > 2:
                sector = text
                break

    return {
        "nombre": name,
        "sector": sector,
        "fuente": "franquiciashoy.es",
        "url_directorio": url,
    }


def scrape(max_items=None):
    """Scrape franquiciashoy.es via AJAX. Returns list of franchise dicts."""
    results = []

    # First page to get total pages
    soup = _get_ajax(1)
    max_page = _get_max_page(soup)
    logger.info(f"Found {max_page} pages via AJAX")

    profile_urls = []

    for page in range(1, max_page + 1):
        if max_items and len(profile_urls) >= max_items:
            break

        logger.info(f"Fetching AJAX page {page}/{max_page}")

        if page > 1:
            time.sleep(DELAY)
            soup = _get_ajax(page)

        urls = _extract_profiles(soup)
        profile_urls.extend(urls)
        logger.info(f"  Found {len(urls)} profiles on page {page}")

    # Deduplicate
    seen = set()
    unique = []
    for u in profile_urls:
        if u not in seen:
            seen.add(u)
            unique.append(u)
    profile_urls = unique

    if max_items:
        profile_urls = profile_urls[:max_items]

    logger.info(f"Total unique profiles to scrape: {len(profile_urls)}")

    for i, url in enumerate(profile_urls):
        logger.info(f"Scraping profile {i+1}/{len(profile_urls)}: {url}")
        try:
            time.sleep(DELAY)
            record = _parse_profile(url)
            if record:
                results.append(record)
                logger.info(f"  -> {record['nombre']} ({record['sector']})")
        except Exception as e:
            logger.warning(f"  Error scraping {url}: {e}")

    logger.info(f"franquiciashoy: {len(results)} franchises scraped")
    return results
