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
    label_key = "World Map"
    supports_settings = True

    def render(self, parent_view, impact_choice, get_world_data):
        # Delegate rendering to the view; it reads method_state['world_map']
        fig, world_df, unit = parent_view._render_world_map_figure(impact_choice)
        parent_view._set_latest_world_df(world_df, unit)
        return fig


class TopNMethod(AnalysisMethod):
    id = "topn"
    label = "Top n"
    label_key = "Top n"
    supports_settings = True

    def render(self, view, impact: str, get_world_df):
        st = {
            "n": 10,
            "title": "",                # optional custom title; empty -> backend auto-title
            "orientation": "vertical",
            "bar_color": "tab10",
            "bar_width": 0.8,
            "relative": True,
            **view.method_state.get(self.id, {}),
        }

        # primärer Impact (sortiert danach) + bis zu 3 Vergleichsimpacts
        primary = view._current_impact_key()
        extras  = list(view.get_extra_impacts())
        imps    = [primary] + [e for e in extras if e != primary][:3]

        # WICHTIG: leer/None übergeben -> Backend baut Titel (lokalisiert)
        user_title = (st.get("title") or "").strip()
        title = user_title if user_title else None

        return view.ui.supplychain.plot_topn_by_impacts(
            impacts=imps,
            n=int(st.get("n", 10)),
            relative=bool(st.get("relative", True)),
            orientation=st.get("orientation", "vertical"),
            bar_color=st.get("bar_color", "tab10"),
            bar_width=float(st.get("bar_width", 0.8)),
            title=title,                 # None/"" => Auto-Titel im Backend
            return_data=False,
        )


class FlopNMethod(AnalysisMethod):
    id = "flopn"
    label = "Flop n"
    label_key = "Flop n"
    supports_settings = True

    def render(self, view, impact: str, get_world_df):
        st = {
            "n": 10,
            "title": "",
            "orientation": "vertical",
            "bar_color": "tab10",
            "bar_width": 0.8,
            "relative": True,
            **view.method_state.get(self.id, {}),
        }

        primary = view._current_impact_key()
        extras  = list(view.get_extra_impacts())
        imps    = [primary] + [e for e in extras if e != primary][:3]

        user_title = (st.get("title") or "").strip()
        title = user_title if user_title else None

        return view.ui.supplychain.plot_flopn_by_impacts(
            impacts=imps,
            n=int(st.get("n", 10)),
            relative=bool(st.get("relative", True)),
            orientation=st.get("orientation", "vertical"),
            bar_color=st.get("bar_color", "tab10"),
            bar_width=float(st.get("bar_width", 0.8)),
            title=title,                
            return_data=False,
        )


class PieChartMethod(AnalysisMethod):
    id = "pie"
    label = "Pie chart"          
    label_key = "Pie chart"
    supports_settings = True

    def render(self, view, impact: str, get_world_df):
        state = {
            "top_slices": 10,
            "min_pct": None,
            "sort_slices": "desc",
            "title": "",
            "start_angle": 90,
            "counterclockwise": True,
            "color_map": "tab20",
            "cmap_reverse": False,
            **view.method_state.get(self.id, {})
        }

        color_name = state["color_map"]
        if state.get("cmap_reverse") and not str(color_name).endswith("_r"):
            color_name = f"{color_name}_r"

        title = state["title"] or f'{view._translate("Pie chart", "Pie chart")} – {impact}'

        return view.ui.supplychain.plot_pie_by_impact(
            impact,
            top_slices=state["top_slices"],
            min_pct=state["min_pct"],
            sort_slices=state["sort_slices"],
            title=title,
            start_angle=state["start_angle"],
            counterclockwise=state["counterclockwise"],
            color_map=color_name,
            return_data=False
        )


# Register built-in methods
RegionAnalysisRegistry.register(WorldMapMethod())
RegionAnalysisRegistry.register(TopNMethod())
RegionAnalysisRegistry.register(FlopNMethod())
RegionAnalysisRegistry.register(PieChartMethod())
