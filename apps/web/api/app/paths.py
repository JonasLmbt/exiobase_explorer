from __future__ import annotations

import os
from pathlib import Path


def repo_root() -> Path:
    # apps/web/api/app/paths.py -> repo root is 4 parents up
    return Path(__file__).resolve().parents[4]


def databases_dir() -> Path:
    env = os.environ.get("EXIOBASE_EXPLORER_DB_DIR")
    if env:
        return Path(env).expanduser().resolve()
    return repo_root() / "exiobase"


def fast_databases_dir() -> Path:
    return databases_dir() / "fast_databases"


def fast_database_path(year: int) -> Path:
    return fast_databases_dir() / f"FAST_IOT_{int(year)}_pxp"

