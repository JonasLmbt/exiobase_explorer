from __future__ import annotations

from typing import Dict, Optional

from .region_base import RegionAnalysisMethod


class RegionAnalysisRegistry:
    def __init__(self) -> None:
        self._methods: Dict[str, RegionAnalysisMethod] = {}

    def register(self, method: RegionAnalysisMethod) -> None:
        self._methods[method.id] = method

    def get(self, method_id: str) -> Optional[RegionAnalysisMethod]:
        return self._methods.get(method_id)

    def all(self) -> Dict[str, RegionAnalysisMethod]:
        return dict(self._methods)


region_registry = RegionAnalysisRegistry()

