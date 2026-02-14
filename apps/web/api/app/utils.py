from __future__ import annotations

import base64
import io
from typing import Any, Dict

import pandas as pd


def multiindex_to_nested_dict(multiindex: pd.MultiIndex) -> dict:
    root: Dict[str, Any] = {}
    for keys in multiindex:
        current: Dict[str, Any] = root
        for key in keys:
            current = current.setdefault(str(key), {})
    return root


def fig_to_png_base64(fig) -> str:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=160, bbox_inches="tight")
    buf.seek(0)
    return base64.b64encode(buf.read()).decode("ascii")

