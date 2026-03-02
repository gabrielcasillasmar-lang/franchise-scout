"""Web analyzer — extracts franchise-relevant info from official websites."""

import logging
import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

logger = logging.getLogger("analysis.web_analyzer")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "es-ES,es;q=0.9",
}

# Keywords for franchise section links
FRANCHISE_KEYWORDS = [
    "franquicia", "únete", "unete", "expansión", "expansion",
    "abre tu", "conviértete", "conviertete", "hazte franquiciado",
    "oportunidad de negocio", "hazte", "únete a nosotros",
]

# Prefixes that indicate a franchise-specific email
FRANCHISE_EMAIL_PREFIXES = [
    "franquicia", "expansion", "franquiciate", "unete",
    "network", "desarrollo",
]

# Form field keywords
FORM_KEYWORDS = [
    "nombre", "email", "teléfono", "telefono", "phone",
    "ciudad", "inversión", "inversion", "franquicia",
    "interés", "interes", "name", "city",
]

# Downloadable material patterns
DOWNLOAD_EXTENSIONS = [".pdf", ".doc", ".docx", ".ppt", ".zip"]
DOWNLOAD_KEYWORDS = [
    "dossier", "descarga", "presentación", "presentacion",
    "catálogo", "catalogo", "folleto", "download",
]


def _get_soup(url):
    resp = requests.get(url, headers=HEADERS, timeout=20, allow_redirects=True)
    resp.raise_for_status()
    return BeautifulSoup(resp.text, "lxml"), resp.url


def _find_franchise_section(soup, base_url):
    """Look for franchise/expansion section link in nav/header."""
    section_url = None
    for a in soup.find_all("a", href=True):
        text = a.get_text(strip=True).lower()
        href = a["href"].lower()
        combined = text + " " + href
        for kw in FRANCHISE_KEYWORDS:
            if kw in combined:
                section_url = urljoin(base_url, a["href"])
                return True, section_url
    return False, None


def _extract_emails(soup):
    """Extract emails from mailto: links and plain text."""
    emails = set()

    # From mailto links
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if href.startswith("mailto:"):
            email = href.replace("mailto:", "").split("?")[0].strip()
            if "@" in email:
                emails.add(email.lower())

    # From text content
    text = soup.get_text()
    found = re.findall(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", text)
    for e in found:
        emails.add(e.lower())

    return list(emails)


def _classify_email(email):
    """Classify email as 'franquicias' or 'general'."""
    prefix = email.split("@")[0].lower()
    for kw in FRANCHISE_EMAIL_PREFIXES:
        if kw in prefix:
            return "franquicias"
    return "general"


def _find_linkedin(soup):
    """Find LinkedIn company/profile URL."""
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if "linkedin.com/company" in href or "linkedin.com/in/" in href:
            return href
    return None


def _detect_form(soup):
    """Detect franchise capture forms (at least 2 relevant fields)."""
    for form in soup.find_all("form"):
        form_text = form.get_text().lower()
        form_html = str(form).lower()
        matches = 0
        for kw in FORM_KEYWORDS:
            if kw in form_text or kw in form_html:
                matches += 1
        if matches >= 2:
            return True
    return False


def _find_downloads(soup, base_url):
    """Find downloadable materials (PDFs, dossiers, etc.)."""
    downloads = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        text = a.get_text(strip=True).lower()
        href_lower = href.lower()

        # Check file extension
        is_file = any(href_lower.endswith(ext) for ext in DOWNLOAD_EXTENSIONS)
        # Check keywords in link text
        is_keyword = any(kw in text for kw in DOWNLOAD_KEYWORDS)

        if is_file or is_keyword:
            full_url = urljoin(base_url, href)
            label = a.get_text(strip=True) or full_url
            downloads.append({"label": label, "url": full_url})

    return downloads


def analyze(url):
    """Analyze a franchise's official website.
    Returns dict with analysis results.
    """
    result = {
        "web_oficial": url,
        "seccion_franquiciados": False,
        "url_seccion_franquiciados": None,
        "email": None,
        "tipo_email": None,
        "linkedin_url": None,
        "formulario_franquicia": False,
        "material_descargable": False,
        "url_material_descargable": None,
        "notas": "",
    }

    try:
        soup, final_url = _get_soup(url)
        result["web_oficial"] = final_url
    except Exception as e:
        result["notas"] = f"Error accediendo a web: {e}"
        logger.warning(f"Cannot access {url}: {e}")
        return result

    # 1. Franchise section
    has_section, section_url = _find_franchise_section(soup, final_url)
    result["seccion_franquiciados"] = has_section
    result["url_seccion_franquiciados"] = section_url

    # If franchise section found, also analyze that page
    section_soup = soup
    if section_url and section_url != final_url:
        try:
            section_soup, _ = _get_soup(section_url)
        except Exception as e:
            result["notas"] += f"Error en sección franquiciados: {e}. "
            logger.warning(f"Cannot access franchise section {section_url}: {e}")

    # 2. Emails (search both main page and franchise section)
    all_emails = set(_extract_emails(soup))
    if section_soup is not soup:
        all_emails.update(_extract_emails(section_soup))

    if all_emails:
        # Prefer franchise-type emails
        franchise_emails = [e for e in all_emails if _classify_email(e) == "franquicias"]
        if franchise_emails:
            result["email"] = franchise_emails[0]
            result["tipo_email"] = "franquicias"
        else:
            result["email"] = list(all_emails)[0]
            result["tipo_email"] = "general"

    # 3. LinkedIn
    linkedin = _find_linkedin(soup)
    if not linkedin and section_soup is not soup:
        linkedin = _find_linkedin(section_soup)
    result["linkedin_url"] = linkedin

    # 4. Franchise form
    has_form = _detect_form(soup)
    if not has_form and section_soup is not soup:
        has_form = _detect_form(section_soup)
    result["formulario_franquicia"] = has_form

    # 5. Downloadable material
    downloads = _find_downloads(soup, final_url)
    if section_soup is not soup:
        downloads.extend(_find_downloads(section_soup, section_url))

    if downloads:
        result["material_descargable"] = True
        result["url_material_descargable"] = downloads[0]["url"]

    return result
