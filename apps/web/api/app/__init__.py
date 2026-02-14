from __future__ import annotations

import sys
from pathlib import Path

# Ensure repo root is on sys.path when running via `uvicorn --app-dir apps/web/api`.
# This makes `import src...` work without requiring installation as a package.
_REPO_ROOT = Path(__file__).resolve().parents[4]
_repo_root_str = str(_REPO_ROOT)
if _repo_root_str not in sys.path:
    sys.path.insert(0, _repo_root_str)

