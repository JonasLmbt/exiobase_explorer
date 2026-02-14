from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from src.IOSystem import IOSystem


class StageAnalysisMethod(ABC):
    id: str
    label: str

    @abstractmethod
    def run(
        self,
        *,
        iosystem: IOSystem,
        selection: Dict[str, Any],
        analysis: Dict[str, Any],
        job_meta: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        raise NotImplementedError

