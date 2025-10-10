from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional
import matplotlib.pyplot as plt


class StageAnalysisMethod(ABC):
    """
    Abstract base class for stage-based (value chain level) analysis methods.

    Implementations receive a list of impact identifiers and must return a matplotlib Figure.
    """
    id: str
    label: str
    supports_settings: bool = False  # Implementations may enable and expose a settings dialog

    @abstractmethod
    def render(self, parent_view, impacts: List[str]) -> plt.Figure:
        """
        Render the visualization for the given impacts.

        Args:
            parent_view: The hosting view/widget that provides access to UI and data.
            impacts (List[str]): List of selected impact identifiers.

        Returns:
            matplotlib.figure.Figure: Rendered figure for display/embedding.
        """
        raise NotImplementedError

    def create_settings_dialog(self, parent_view):
        """
        Optionally create and return a modal settings dialog for this method.

        Args:
            parent_view: The hosting view/widget for parent/ownership.

        Returns:
            Optional[QDialog]: Settings dialog if `supports_settings` is True; otherwise None.
        """
        return None


class StageAnalysisRegistry:
    """
    Registry for available stage analysis methods.

    Allows lookup by method ID and iteration over all registered methods.
    """
    _methods: dict[str, StageAnalysisMethod] = {}

    @classmethod
    def register(cls, method: StageAnalysisMethod) -> None:
        """Register (or overwrite) a method instance under its `id`."""
        cls._methods[method.id] = method

    @classmethod
    def all_methods(cls) -> dict[str, StageAnalysisMethod]:
        """Return a shallow copy of all registered methods keyed by their IDs."""
        return dict(cls._methods)

    @classmethod
    def get(cls, method_id: str) -> Optional[StageAnalysisMethod]:
        """Retrieve a method by its ID, or None if not found."""
        return cls._methods.get(method_id)


class BubbleDiagramMethod(StageAnalysisMethod):
    """
    Render the existing bubble diagram using the SupplyChain backend.

    Accepts multiple impacts and forwards them to `plot_bubble_diagram(...)`.
    """
    id = "bubble"
    label = "Bubble diagram"

    # Public attributes could be added here for user-tunable settings.

    def render(self, parent_view, impacts: List[str]) -> plt.Figure:
        """
        Produce a bubble diagram for the selected impacts.

        Args:
            parent_view: Hosting view providing `ui.supplychain`.
            impacts (List[str]): Impact identifiers to visualize.

        Returns:
            matplotlib.figure.Figure: Bubble diagram.
        """
        # Defensive default: ensure a list is passed downstream
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
    """Placeholder method that displays a 'coming soon' Sankey diagram."""
    id = "sankey"
    label = "Sankey (coming soon)"

    def render(self, parent_view, impacts: List[str]) -> plt.Figure:
        """
        Show a placeholder figure for the future Sankey implementation.
        """
        fig = plt.figure()
        ax = fig.add_subplot(111)
        ax.text(0.5, 0.5, "Sankey diagram – coming soon", ha="center", va="center", transform=ax.transAxes)
        ax.axis("off")
        fig.tight_layout()
        return fig


class TreemapPlaceholderMethod(StageAnalysisMethod):
    """Placeholder method that displays a 'coming soon' Treemap."""
    id = "treemap"
    label = "Treemap (coming soon)"

    def render(self, parent_view, impacts: List[str]) -> plt.Figure:
        """
        Show a placeholder figure for the future Treemap implementation.
        """
        fig = plt.figure()
        ax = fig.add_subplot(111)
        ax.text(0.5, 0.5, "Treemap – coming soon", ha="center", va="center", transform=ax.transAxes)
        ax.axis("off")
        fig.tight_layout()
        return fig


# Register built-in methods at import time so they are available to the UI.
StageAnalysisRegistry.register(BubbleDiagramMethod())
StageAnalysisRegistry.register(SankeyPlaceholderMethod())
StageAnalysisRegistry.register(TreemapPlaceholderMethod())
