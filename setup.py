"""
setup.py

This script is used to set up the Exiobase database for the IOSystem.
"""

import argparse
import logging
import os
import re
import shutil
import sys

from src.IOSystem import IOSystem

# Configure logging for clear output
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s - %(message)s',
    stream=sys.stdout  # Hier wird der Ausgabestrom explizit gesetzt
)

FAST_DB_PREFIX = "FAST_IOT_"
FAST_DB_SUFFIX = "_pxp"
FAST_DB_CONFIG_FILES = ["general.xlsx", "impacts.xlsx", "regions.xlsx", "sectors.xlsx", "units.xlsx"]

def _default_db_dir() -> str:
    return os.path.normpath(os.path.join(os.path.dirname(__file__), "exiobase"))


def _parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Prepare EXIOBASE fast-load databases for Exiobase Explorer.")
    p.add_argument(
        "db_dir",
        nargs="?",
        default=None,
        help="Folder containing EXIOBASE IOT_YYYY_pxp.zip files (default: ./exiobase).",
    )
    p.add_argument(
        "--delete-zips",
        action="store_true",
        help="Delete IOT_YYYY_pxp.zip files after a successful fast-db build (default: keep).",
    )
    p.add_argument(
        "--no-migrate-legacy-fastdb",
        action="store_true",
        help="Do not migrate legacy exiobase/fast_databases/* folders to the new flat exiobase/* layout.",
    )
    return p.parse_args(argv)


def _cleanup_fastdb_configs(fast_db_path: str) -> None:
    """
    Remove legacy per-fastdb config Excel files.

    Configs are now centrally managed under `config/`.
    """
    for name in FAST_DB_CONFIG_FILES:
        p = os.path.join(fast_db_path, name)
        try:
            if os.path.exists(p):
                os.remove(p)
        except Exception as e:
            logging.warning(f"Could not remove '{p}': {e}")


def _migrate_legacy_fastdb_layout(db_dir: str) -> None:
    legacy_dir = os.path.join(db_dir, "fast_databases")
    if not os.path.isdir(legacy_dir):
        return

    pattern = re.compile(rf"^{re.escape(FAST_DB_PREFIX)}(\d{{4}}){re.escape(FAST_DB_SUFFIX)}$")
    moved = 0
    for entry in os.listdir(legacy_dir):
        src = os.path.join(legacy_dir, entry)
        if not os.path.isdir(src):
            continue
        if not pattern.match(entry):
            continue
        dst = os.path.join(db_dir, entry)
        try:
            if os.path.exists(dst):
                logging.warning(f"Skip migrate (target exists): {dst}")
                continue
            shutil.move(src, dst)
            moved += 1
        except Exception as e:
            logging.warning(f"Could not migrate '{src}' -> '{dst}': {e}")

    try:
        # Remove legacy container folder if empty.
        if moved and not os.listdir(legacy_dir):
            os.rmdir(legacy_dir)
    except Exception:
        pass


def main(argv: list[str]) -> int:
    args = _parse_args(argv)

    databases_dir = _default_db_dir()
    databases_dir = os.path.normpath(os.environ.get("EXIOBASE_EXPLORER_DB_DIR", databases_dir))
    if args.db_dir:
        databases_dir = os.path.normpath(str(args.db_dir))

    if not os.path.isdir(databases_dir):
        raise FileNotFoundError(f"Database directory not found: {databases_dir}")

    # Ensure the rest of the application sees this location as its DB dir.
    os.environ["EXIOBASE_EXPLORER_DB_DIR"] = databases_dir
    logging.info(f"databases_dir: {databases_dir}\n")

    if not bool(args.no_migrate_legacy_fastdb):
        _migrate_legacy_fastdb_layout(databases_dir)

    zip_pattern = re.compile(r"IOT_(\d{4})_pxp\.zip$")
    for filename in sorted(os.listdir(databases_dir)):
        match = zip_pattern.match(filename)
        if not match:
            continue

        year = int(match.group(1))
        zip_path = os.path.join(databases_dir, filename)

        logging.info(f"Building/validating fast database for year {year} from '{filename}'...")
        dummy = IOSystem(year=year)
        dummy.load()

        # Fast-db config Excel files are legacy; remove them from the fast db folder.
        _cleanup_fastdb_configs(dummy.current_fast_database_path)

        if bool(args.delete_zips):
            try:
                os.remove(zip_path)
                logging.info(f"Deleted zip: {filename}")
            except Exception as e:
                logging.warning(f"Could not delete '{zip_path}': {e}")

        del dummy

    # Also sweep existing fast DBs (regardless of whether a zip was processed)
    # to remove legacy per-folder config files.
    fastdb_pattern = re.compile(rf"^{re.escape(FAST_DB_PREFIX)}(\d{{4}}){re.escape(FAST_DB_SUFFIX)}$")
    for entry in os.listdir(databases_dir):
        full = os.path.join(databases_dir, entry)
        if os.path.isdir(full) and fastdb_pattern.match(entry):
            _cleanup_fastdb_configs(full)

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
