"""Web search module — DuckDuckGo Instant Answer API + URL guessing fallback."""

import logging
import re
import time
import requests

logger = logging.getLogger("analysis.search")

DELAY = 6.0

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
}

# Domains to filter out from results
EXCLUDED_DOMAINS = {
    "mundofranquicia.com",
    "franquiciashoy.es",
    "generaldefranquicias.com",
    "infofranquicias.com",
    "100franquicias.com",
    "wikipedia.org",
    "youtube.com",
    "facebook.com",
    "instagram.com",
    "tripadvisor.com",
    "tripadvisor.es",
    "linkedin.com",
    "twitter.com",
    "x.com",
    "duckduckgo.com",
}


def _is_excluded(url):
    url_lower = url.lower()
    for domain in EXCLUDED_DOMAINS:
        if domain in url_lower:
            return True
    return False


def _ddg_instant_answer(query):
    """Use DuckDuckGo Instant Answer API to find official website."""
    try:
        resp = requests.get(
            "https://api.duckduckgo.com/",
            params={"q": query, "format": "json", "no_redirect": 1},
            headers=HEADERS,
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()

        # Check Results first (often contains "Official site")
        for r in data.get("Results", []):
            url = r.get("FirstURL", "")
            if url and not _is_excluded(url):
                return url

        # Check AbstractURL
        abstract = data.get("AbstractURL", "")
        if abstract and not _is_excluded(abstract):
            return abstract

        # Check RelatedTopics
        for r in data.get("RelatedTopics", []):
            url = r.get("FirstURL", "")
            if url and not _is_excluded(url):
                return url

    except Exception as e:
        logger.warning(f"DDG API failed: {e}")
    return None


def _google_search(query, num_results=10):
    """Search using googlesearch-python (may be blocked in some environments)."""
    try:
        from googlesearch import search as gsearch
        results = []
        for url in gsearch(query, num_results=num_results, lang="es"):
            if not _is_excluded(url):
                results.append(url)
        return results if results else None
    except Exception as e:
        logger.warning(f"Google search failed: {e}")
        return None


def _guess_url(franchise_name):
    """Try to guess the official website by constructing common URL patterns."""
    slug = re.sub(r"[^a-z0-9]", "", franchise_name.lower())
    # Also try with hyphens for multi-word names
    slug_hyphen = re.sub(r"\s+", "-", franchise_name.lower().strip())
    slug_hyphen = re.sub(r"[^a-z0-9-]", "", slug_hyphen)

    candidates = []
    for s in [slug, slug_hyphen]:
        if not s:
            continue
        candidates.extend([
            f"https://www.{s}.es",
            f"https://www.{s}.com",
            f"https://{s}.es",
            f"https://{s}.com",
        ])

    for url in candidates:
        try:
            resp = requests.head(
                url, headers=HEADERS, timeout=5, allow_redirects=True
            )
            if resp.status_code < 400:
                final = resp.url
                if not _is_excluded(final):
                    return final
        except Exception:
            continue
    return None


def find_official_website(franchise_name):
    """Find the official website for a franchise.
    Strategy: DDG API -> Google -> URL guessing.
    Returns URL string or None.
    """
    logger.info(f"Searching official website for: {franchise_name}")

    # 1. DDG Instant Answer API (fast, reliable)
    # Try with just the name first, then with "franquicia" for context
    for query in [franchise_name, f"{franchise_name} franquicia"]:
        url = _ddg_instant_answer(query)
        if url:
            logger.info(f"  Found via DDG API: {url}")
            return url

    # 2. Google search
    time.sleep(DELAY)
    results = _google_search(f"{franchise_name} franquicia web oficial")
    if results:
        logger.info(f"  Found via Google: {results[0]}")
        return results[0]

    # 3. URL guessing
    logger.info("  Trying URL guessing...")
    url = _guess_url(franchise_name)
    if url:
        logger.info(f"  Found via URL guess: {url}")
        return url

    logger.info("  No official website found")
    return None
