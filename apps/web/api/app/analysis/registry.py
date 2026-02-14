from __future__ import annotations

from typing import Dict, Optional

from .base import StageAnalysisMethod


class StageAnalysisRegistry:
    def __init__(self) -> None:
        self._methods: Dict[str, StageAnalysisMethod] = {}

    def register(self, method: StageAnalysisMethod) -> None:
        self._methods[method.id] = method

    def get(self, method_id: str) -> Optional[StageAnalysisMethod]:
        return self._methods.get(method_id)

    def all(self) -> Dict[str, StageAnalysisMethod]:
        return dict(self._methods)


stage_registry = StageAnalysisRegistry()

