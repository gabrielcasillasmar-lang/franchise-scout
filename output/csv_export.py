"""CSV output — writes franchise data to a CSV file."""

import csv
import logging
import os

from output.sheets import COLUMNS, _record_to_row

logger = logging.getLogger("output.csv")

DEFAULT_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "output", "franquicias.csv")


def write(records, path=None):
    """Write franchise records to a CSV file.

    records: list of dicts with franchise data + 'analysis' sub-dict.
    path: output file path (default: output/franquicias.csv).
    """
    if not records:
        logger.warning("No records to write")
        return

    path = path or DEFAULT_PATH
    os.makedirs(os.path.dirname(path), exist_ok=True)

    file_exists = os.path.exists(path) and os.path.getsize(path) > 0

    with open(path, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(COLUMNS)
        writer.writerows(_record_to_row(r) for r in records)

    logger.info(f"Written {len(records)} rows to {path}")
