from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Tuple

from src.IOSystem import IOSystem


@dataclass(frozen=True)
class CoreKey:
    year: int
    language: str


_CACHE: Dict[CoreKey, IOSystem] = {}


def get_iosystem(year: int, language: str) -> IOSystem:
    key = CoreKey(year=year, language=language)
    cached = _CACHE.get(key)
    if cached is not None:
        return cached

    ios = IOSystem(year=year, language=language).load()
    _CACHE[key] = ios
    return ios

