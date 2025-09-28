from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Callable, Dict, Optional, Tuple
import matplotlib.pyplot as plt
from PyQt5.QtWidgets import QDialog, QWidget
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


class TopNMethod(AnalysisMethod):
    """
    Top-N regions by value. Uses SupplyChain.plot_topn_by_impact(data-only).
    """
    id = "top_n"
    label = "Top n"

    def __init__(self, n: int = 10):
        self.n = n

    def render(self, parent_view, impact_choice, _get_world_df):
        # Respect world-map setting 'relative' so Top/Flop basieren auf der gleichen Basis
        s = parent_view.method_state.get("world_map", {})
        relative = bool(s.get("relative", True))

        # Daten vom Backend holen (return_data=True, Figure ignorieren)
        _fig, df = parent_view.ui.supplychain.plot_topn_by_impact(
            impact_choice, n=self.n, relative=relative, return_data=True
        )

        # Robust konvertieren
        df = pd.DataFrame(df)
        unit = str(df["unit"].iloc[0]) if "unit" in df.columns and len(df) else ""

        # Frontend-Plot (i18n-sicher)
        fig = plt.figure()
        ax = fig.add_subplot(111)
        ax.bar(df["region"], df["value"])
        ax.set_ylabel(unit or "")
        title = f"{parent_view._get_text(self.label, self.label)} {self.n} – {impact_choice}"
        ax.set_title(title)
        ax.set_xticklabels(df["region"], rotation=45, ha="right")
        fig.tight_layout()
        return fig


class FlopNMethod(AnalysisMethod):
    """
    Flop-N regions (smallest values). Uses SupplyChain.plot_flopn_by_impact(data-only).
    """
    id = "flop_n"
    label = "Flop n"

    def __init__(self, n: int = 10):
        self.n = n

    def render(self, parent_view, impact_choice, _get_world_df):
        s = parent_view.method_state.get("world_map", {})
        relative = bool(s.get("relative", True))

        _fig, df = parent_view.ui.supplychain.plot_flopn_by_impact(
            impact_choice, n=self.n, relative=relative, return_data=True
        )

        df = pd.DataFrame(df)
        unit = str(df["unit"].iloc[0]) if "unit" in df.columns and len(df) else ""

        fig = plt.figure()
        ax = fig.add_subplot(111)
        ax.bar(df["region"], df["value"])
        ax.set_ylabel(unit or "")
        title = f"{parent_view._get_text(self.label, self.label)} {self.n} – {impact_choice}"
        ax.set_title(title)
        ax.set_xticklabels(df["region"], rotation=45, ha="right")
        fig.tight_layout()
        return fig


class PieChartMethod(AnalysisMethod):
    """
    Pie chart over regions. Uses SupplyChain.plot_pie_by_impact(data-only).
    """
    id = "pie"
    label = "Pie chart"

    def __init__(self, top_slices: int = 10):
        self.top_slices = top_slices

    def render(self, parent_view, impact_choice, _get_world_df):
        s = parent_view.method_state.get("world_map", {})
        relative = bool(s.get("relative", True))

        _fig, df = parent_view.ui.supplychain.plot_pie_by_impact(
            impact_choice, top_slices=self.top_slices, relative=relative, return_data=True
        )

        df = pd.DataFrame(df)
        unit = str(df["unit"].iloc[0]) if "unit" in df.columns and len(df) else ""

        # i18n für 'Others'
        others_key = parent_view._get_text("Others", "Others")
        if "label" in df.columns:
            df.loc[df["label"].astype(str).str.lower() == "others", "label"] = others_key

        fig = plt.figure()
        ax = fig.add_subplot(111)
        ax.pie(df["value"], labels=df["label"], autopct="%1.1f%%")
        ax.set_title(f'{parent_view._get_text(self.label, self.label)} – {impact_choice}')
        ax.axis("equal")
        fig.tight_layout()
        return fig


# Register built-in methods
RegionAnalysisRegistry.register(WorldMapMethod())
RegionAnalysisRegistry.register(TopNMethod())
RegionAnalysisRegistry.register(FlopNMethod())
RegionAnalysisRegistry.register(PieChartMethod())
