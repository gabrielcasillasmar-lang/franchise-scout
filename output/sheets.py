"""Google Sheets output — writes franchise data to a Google Sheet."""

import logging
import os
import gspread
from google.oauth2.service_account import Credentials

logger = logging.getLogger("output.sheets")

SHEET_ID = "1A8JSxnmpcKGB4iXlhYlu9uRx_1Onu-wfJ9GfYiBzd3M"
TAB_NAME = "master"
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

COLUMNS = [
    "Nombre",
    "Sector",
    "Fuente directorio",
    "URL directorio",
    "Web oficial",
    "Sección franquiciados",
    "URL sección franquiciados",
    "Email encontrado",
    "Tipo email",
    "LinkedIn URL",
    "Formulario franquicia",
    "Material descargable",
    "URL material descargable",
    "Notas",
]


def _get_client():
    """Authenticate with Google using service account credentials."""
    creds_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "credentials.json")
    if not os.path.exists(creds_path):
        raise FileNotFoundError(
            f"credentials.json not found at {creds_path}. "
            "Place your Google Service Account JSON file there."
        )
    creds = Credentials.from_service_account_file(creds_path, scopes=SCOPES)
    return gspread.authorize(creds)


def _record_to_row(record):
    """Convert a franchise record dict to a row list matching COLUMNS order."""
    analysis = record.get("analysis", {})
    return [
        record.get("nombre", ""),
        record.get("sector", ""),
        record.get("fuente", ""),
        record.get("url_directorio", ""),
        analysis.get("web_oficial", ""),
        "Sí" if analysis.get("seccion_franquiciados") else "No",
        analysis.get("url_seccion_franquiciados", "") or "",
        analysis.get("email", "") or "",
        analysis.get("tipo_email", "") or "",
        analysis.get("linkedin_url", "") or "",
        "Sí" if analysis.get("formulario_franquicia") else "No",
        "Sí" if analysis.get("material_descargable") else "No",
        analysis.get("url_material_descargable", "") or "",
        analysis.get("notas", ""),
    ]


def write(records):
    """Write franchise records to Google Sheets.
    records: list of dicts with franchise data + 'analysis' sub-dict.
    """
    if not records:
        logger.warning("No records to write")
        return

    logger.info(f"Writing {len(records)} records to Google Sheets...")

    client = _get_client()
    spreadsheet = client.open_by_key(SHEET_ID)

    try:
        worksheet = spreadsheet.worksheet(TAB_NAME)
    except gspread.WorksheetNotFound:
        worksheet = spreadsheet.add_worksheet(title=TAB_NAME, rows=1000, cols=len(COLUMNS))

    # Check if headers exist
    existing = worksheet.row_values(1)
    if existing != COLUMNS:
        worksheet.update("A1", [COLUMNS])
        logger.info("Headers written")

    # Find next empty row
    all_values = worksheet.get_all_values()
    next_row = len(all_values) + 1

    # Prepare rows
    rows = [_record_to_row(r) for r in records]

    # Batch update
    cell_range = f"A{next_row}"
    worksheet.update(cell_range, rows)

    logger.info(f"Written {len(rows)} rows starting at row {next_row}")
