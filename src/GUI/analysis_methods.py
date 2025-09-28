from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Callable, Dict, Optional, Tuple
import matplotlib.pyplot as plt
from PyQt5.QtWidgets import QDialog, QWidget, QSpinBox, QLabel, QHBoxLayout
import pandas as pd


class AnalysisMethod(ABC):
    """
    Abstract base class for an analysis method used in RegionAnalysisViewTab.

    Each method is responsible for rendering its visualization given a data provider and
    the currently selected impact. Methods can optionally provide a settings dialog and
    inline controls (e.g., a spin box for Top-N).
    """

    #: Globally unique identifier for the method (used in registry & saving state)
    id: str
    #: Human-readable label shown to the user in the method selector
    label: str
    #: Whether this method offers an external settings dialog
    supports_settings: bool = False

    @abstractmethod
    def render(
        self,
        parent_view: QWidget,
        impact_choice: str,
        get_world_data: Callable[[str], Tuple[pd.DataFrame, str]],
    ) -> plt.Figure:
        """
        Render the visualization for the given impact.

        Parameters
        ----------
        parent_view : QWidget
            The calling view (RegionAnalysisViewTab); can be used to access UI state.
        impact_choice : str
            The selected impact (or 'Subcontractors').
        get_world_data : Callable[[str], Tuple[pd.DataFrame, str]]
            A callable returning a tuple (df, unit) for the given impact, where df has at least:
            ['region', 'value', 'percentage'] and possibly 'geometry' for world map.

        Returns
        -------
        matplotlib.figure.Figure
            The rendered figure (caller will place it on the canvas).
        """
        raise NotImplementedError

    def create_settings_dialog(self, parent: QWidget) -> Optional[QDialog]:
        """Return a settings dialog if the method supports settings, else None."""
        return None

    def get_inline_controls(self, parent: QWidget) -> Optional[QWidget]:
        """
        Return a small inline widget with controls (e.g., Top-N spin box) that fits the one-line toolbar.
        Return None if no inline controls are needed.
        """
        return None


class RegionAnalysisRegistry:
    """
    Registry for region-based analysis methods.

    New methods can be added by calling `RegionAnalysisRegistry.register(method_cls)`.
    """
    _methods: Dict[str, AnalysisMethod] = {}

    @classmethod
    def register(cls, method: AnalysisMethod) -> None:
        cls._methods[method.id] = method

    @classmethod
    def all_methods(cls) -> Dict[str, AnalysisMethod]:
        return dict(cls._methods)

    @classmethod
    def get(cls, method_id: str) -> Optional[AnalysisMethod]:
        return cls._methods.get(method_id)


class WorldMapMethod(AnalysisMethod):
    """
    Render a choropleth world map for the selected impact or subcontractors.

    Settings are held by RegionAnalysisViewTab (method_state['world_map']).
    """
    id = "world_map"
    label = "World Map"
    supports_settings = True

    def render(self, parent_view, impact_choice, get_world_data):
        # Delegate rendering to the view; it reads method_state['world_map']
        fig, world_df, unit = parent_view._render_world_map_figure(impact_choice)
        parent_view._set_latest_world_df(world_df, unit)
        return fig


class _TopNBase(AnalysisMethod):
    """
    Shared logic for Top/Flop N methods.

    Expects a dataframe with columns ['region', 'value'] from the view's data provider.
    """
    def __init__(self, default_n: int = 10):
        self.n = default_n  # default Top/Flop count
        self._inline_widget = None  # created lazily

    def get_inline_controls(self, parent: QWidget) -> Optional[QWidget]:
        if self._inline_widget is None:
            box = QHBoxLayout()
            box.setContentsMargins(0, 0, 0, 0)
            label = QLabel("N:")
            spin = QSpinBox()
            spin.setRange(1, 50)
            spin.setValue(self.n)
            spin.valueChanged.connect(lambda v: setattr(self, "n", v))

            container = QWidget(parent)
            container.setLayout(box)
            box.addWidget(label)
            box.addWidget(spin)
            self._inline_widget = container
        return self._inline_widget

    def _get_sorted(self, df: pd.DataFrame, ascending: bool) -> pd.DataFrame:
        # Defensive: drop rows with non-numeric values
        safe = df.copy()
        safe["value"] = pd.to_numeric(safe["value"], errors="coerce")
        safe = safe.dropna(subset=["value"])
        safe = safe.sort_values("value", ascending=ascending)
        return safe


class TopNMethod(_TopNBase):
    """Bar chart of the Top-N regions by value for the selected impact."""
    id = "top_n"
    label = "Top n"

    def render(self, parent_view, impact_choice, get_world_data):
        df, unit = get_world_data(impact_choice)
        sorted_df = self._get_sorted(df, ascending=False).head(self.n)

        fig = plt.figure()
        ax = fig.add_subplot(111)
        ax.bar(sorted_df["region"], sorted_df["value"])
        ax.set_title(f"Top {self.n} – {impact_choice}")
        ax.set_ylabel(unit or "")
        ax.set_xticklabels(sorted_df["region"], rotation=45, ha="right")
        fig.tight_layout()
        return fig


class FlopNMethod(_TopNBase):
    """Bar chart of the Flop-N (lowest) regions by value for the selected impact."""
    id = "flop_n"
    label = "Flop n"

    def render(self, parent_view, impact_choice, get_world_data):
        df, unit = get_world_data(impact_choice)
        sorted_df = self._get_sorted(df, ascending=True).head(self.n)

        fig = plt.figure()
        ax = fig.add_subplot(111)
        ax.bar(sorted_df["region"], sorted_df["value"])
        ax.set_title(f"Flop {self.n} – {impact_choice}")
        ax.set_ylabel(unit or "")
        ax.set_xticklabels(sorted_df["region"], rotation=45, ha="right")
        fig.tight_layout()
        return fig


class PieChartMethod(AnalysisMethod):
    """Pie chart of regional shares for the selected impact."""
    id = "pie_chart"
    label = "Pie chart"

    def render(self, parent_view, impact_choice, get_world_data):
        df, unit = get_world_data(impact_choice)
        # keep top 10 slices + aggregate rest as "Others" for readability
        safe = df.copy()
        safe["value"] = pd.to_numeric(safe["value"], errors="coerce")
        safe = safe.dropna(subset=["value"])
        safe = safe.sort_values("value", ascending=False)
        top = safe.head(10)
        others_val = safe["value"].iloc[10:].sum()
        labels = list(top["region"])
        values = list(top["value"])
        if others_val > 0:
            labels.append("Others")
            values.append(others_val)

        fig = plt.figure()
        ax = fig.add_subplot(111)
        ax.pie(values, labels=labels, autopct="%1.1f%%", startangle=90)
        ax.set_title(f"{impact_choice}")
        ax.axis("equal")
        fig.tight_layout()
        return fig


# Register built-in methods
RegionAnalysisRegistry.register(WorldMapMethod())
RegionAnalysisRegistry.register(TopNMethod())
RegionAnalysisRegistry.register(FlopNMethod())
RegionAnalysisRegistry.register(PieChartMethod())
