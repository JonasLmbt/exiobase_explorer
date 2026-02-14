from __future__ import annotations

import os
from pathlib import Path


def repo_root() -> Path:
    # apps/web/api/app/paths.py -> repo root is 4 parents up
    return Path(__file__).resolve().parents[4]

def config_dir() -> Path:
    return repo_root() / "config"


def databases_dir() -> Path:
    env = os.environ.get("EXIOBASE_EXPLORER_DB_DIR")
    if env:
        p = Path(env).expanduser().resolve()
        # Accept pointing directly at fast_databases or a FAST_IOT_YYYY_pxp folder.
        name = p.name.lower()
        if name == "fast_databases":
            return p.parent
        if name.startswith("fast_iot_") and name.endswith("_pxp"):
            return p.parent.parent
        return p
    return (repo_root() / "exiobase").resolve()


def fast_databases_dir() -> Path:
    return databases_dir() / "fast_databases"


def fast_database_path(year: int) -> Path:
    return fast_databases_dir() / f"FAST_IOT_{int(year)}_pxp"
