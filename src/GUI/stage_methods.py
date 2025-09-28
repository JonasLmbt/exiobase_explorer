# stage_methods.py
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import List, Optional
import matplotlib.pyplot as plt


class StageAnalysisMethod(ABC):
    """
    Abstract base for stage-based analysis methods (value chain levels).

    Methods receive a list of impacts (possibly multiple) and must return a matplotlib Figure.
    """
    id: str
    label: str
    supports_settings: bool = False  # future methods may toggle this

    @abstractmethod
    def render(self, parent_view, impacts: List[str]) -> plt.Figure:
        """Render the visualization for the selected impacts."""
        raise NotImplementedError

    def create_settings_dialog(self, parent_view):
        """Optional: return a settings dialog (if supports_settings is True)."""
        return None


class StageAnalysisRegistry:
    """Simple registry for stage analysis methods."""
    _methods: dict[str, StageAnalysisMethod] = {}

    @classmethod
    def register(cls, method: StageAnalysisMethod) -> None:
        cls._methods[method.id] = method

    @classmethod
    def all_methods(cls) -> dict[str, StageAnalysisMethod]:
        return dict(cls._methods)

    @classmethod
    def get(cls, method_id: str) -> Optional[StageAnalysisMethod]:
        return cls._methods.get(method_id)


class BubbleDiagramMethod(StageAnalysisMethod):
    """
    Renders the existing bubble diagram using the SupplyChain backend.

    It accepts multiple impacts and forwards them to `plot_bubble_diagram(...)`.
    """
    id = "bubble"
    label = "Bubble diagram"

    # You could add public attributes for size/lines/etc. if you want settings later.

    def render(self, parent_view, impacts: List[str]) -> plt.Figure:
        # Defensive: ensure at least one impact
        impacts = impacts or []
        fig = parent_view.ui.supplychain.plot_bubble_diagram(
            impacts,
            size=1,
            lines=True,
            line_width=1,
            line_color="gray",
            text_position="center",
        )
        return fig


class SankeyPlaceholderMethod(StageAnalysisMethod):
    """Placeholder for a future Sankey visualization."""
    id = "sankey"
    label = "Sankey (coming soon)"

    def render(self, parent_view, impacts: List[str]) -> plt.Figure:
        fig = plt.figure()
        ax = fig.add_subplot(111)
        ax.text(0.5, 0.5, "Sankey diagram – coming soon", ha="center", va="center", transform=ax.transAxes)
        ax.axis("off")
        fig.tight_layout()
        return fig


class TreemapPlaceholderMethod(StageAnalysisMethod):
    """Placeholder for a future Treemap visualization."""
    id = "treemap"
    label = "Treemap (coming soon)"

    def render(self, parent_view, impacts: List[str]) -> plt.Figure:
        fig = plt.figure()
        ax = fig.add_subplot(111)
        ax.text(0.5, 0.5, "Treemap – coming soon", ha="center", va="center", transform=ax.transAxes)
        ax.axis("off")
        fig.tight_layout()
        return fig


# Register built-ins
StageAnalysisRegistry.register(BubbleDiagramMethod())
StageAnalysisRegistry.register(SankeyPlaceholderMethod())
StageAnalysisRegistry.register(TreemapPlaceholderMethod())
