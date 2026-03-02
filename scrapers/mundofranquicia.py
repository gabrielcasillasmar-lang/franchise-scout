"""Scraper for mundofranquicia.com — HTML estático, paginado en /buscador-de-franquicias/page/N/"""

import logging
import time
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

logger = logging.getLogger("scrapers.mundofranquicia")

BASE = "https://www.mundofranquicia.com"
LISTING_URL = BASE + "/buscador-de-franquicias/"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "es-ES,es;q=0.9",
}
DELAY = 2.5


def _get(url):
    resp = requests.get(url, headers=HEADERS, timeout=20)
    resp.raise_for_status()
    return BeautifulSoup(resp.text, "lxml")


def _extract_profiles(soup):
    """Extract franchise profile URLs from a listing page."""
    links = set()
    for a in soup.find_all("a", href=True):
        href = a["href"]
        # Profile URLs look like /franquicia/<sector>/<name>/
        if "/franquicia/" in href and href.count("/") >= 4:
            full = urljoin(BASE, href)
            # Filter out non-profile pages
            if any(
                skip in full
                for skip in [
                    "franquiciar-un-negocio",
                    "buscador-de-franquicias",
                    "post_type=",
                    "%tax_categoria%",
                    "%tax_",
                ]
            ):
                continue
            links.add(full)
    return links


def _parse_profile(url):
    """Parse a single franchise profile page."""
    soup = _get(url)
    h1 = soup.find("h1")
    name = h1.get_text(strip=True).replace("Franquicias ", "").replace("Franquicia ", "") if h1 else None
    if not name:
        return None

    # Extract sector from URL path: /franquicia/<sector>/<name>/
    parts = url.rstrip("/").split("/")
    sector_slug = parts[-2] if len(parts) >= 2 else "desconocido"
    sector = sector_slug.replace("-", " ").title()

    # Try breadcrumb for better sector name
    for bc in soup.find_all(["nav", "ol", "ul"], class_=lambda x: x and "bread" in (x or "").lower()):
        items = bc.find_all("li")
        for item in items:
            text = item.get_text(strip=True).lower()
            if text not in ["inicio", "home", "franquicias", name.lower()] and len(text) > 2:
                sector = item.get_text(strip=True)
                break

    return {
        "nombre": name,
        "sector": sector,
        "fuente": "mundofranquicia.com",
        "url_directorio": url,
    }


def _get_max_page(soup):
    """Find last page number from pagination links."""
    max_page = 1
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if "/page/" in href:
            try:
                num = int(href.rstrip("/").split("/page/")[1].split("/")[0].split("#")[0])
                max_page = max(max_page, num)
            except (ValueError, IndexError):
                pass
    return max_page


def scrape(max_items=None):
    """Scrape mundofranquicia.com. Returns list of franchise dicts."""
    results = []
    soup = _get(LISTING_URL)
    max_page = _get_max_page(soup)
    logger.info(f"Found {max_page} pages in buscador")

    profile_urls = []

    for page in range(1, max_page + 1):
        if max_items and len(profile_urls) >= max_items:
            break

        url = LISTING_URL if page == 1 else f"{LISTING_URL}page/{page}/"
        logger.info(f"Fetching listing page {page}: {url}")

        if page > 1:
            time.sleep(DELAY)
            soup = _get(url)

        urls = _extract_profiles(soup)
        profile_urls.extend(urls)
        logger.info(f"  Found {len(urls)} profiles on page {page}")

    # Deduplicate preserving order
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

    logger.info(f"mundofranquicia: {len(results)} franchises scraped")
    return results
