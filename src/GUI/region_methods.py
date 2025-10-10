from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Callable, Dict, Optional, Tuple
import matplotlib.pyplot as plt
from PyQt5.QtWidgets import QDialog, QWidget
import pandas as pd


class AnalysisMethod(ABC):
    """
    Abstract base class for region analysis methods used in RegionAnalysisViewTab.

    Each method renders a visualization given a data provider and the currently
    selected impact. Implementations may optionally expose a settings dialog
    and/or a small inline controls widget for the one-line toolbar.
    """

    #: Globally unique identifier for the method (used in registry & state)
    id: str
    #: Human-readable label shown in method selectors
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

        Args:
            parent_view (QWidget): The calling RegionAnalysisViewTab (access to UI/state).
            impact_choice (str): Selected impact identifier (or 'Subcontractors').
            get_world_data (Callable[[str], Tuple[pd.DataFrame, str]]): Provider returning
                (df, unit) for the given impact. The DataFrame includes at least
                ['region', 'value', 'percentage'] (and optionally 'geometry').

        Returns:
            matplotlib.figure.Figure: The rendered figure placed later by the caller.
        """
        raise NotImplementedError

    def create_settings_dialog(self, parent: QWidget) -> Optional[QDialog]:
        """
        Optionally return a settings dialog for this method.

        Args:
            parent (QWidget): Parent widget for modality/ownership.

        Returns:
            Optional[QDialog]: A dialog if settings are supported, else None.
        """
        return None

    def get_inline_controls(self, parent: QWidget) -> Optional[QWidget]:
        """
        Optionally return a compact inline controls widget (fits the one-line toolbar).

        Args:
            parent (QWidget): Parent widget for the controls.

        Returns:
            Optional[QWidget]: Inline controls widget, or None if not needed.
        """
        return None


class RegionAnalysisRegistry:
    """
    Registry for region-based analysis methods.

    Allows registering implementations, listing all, and retrieving by ID.
    """
    _methods: Dict[str, AnalysisMethod] = {}

    @classmethod
    def register(cls, method: AnalysisMethod) -> None:
        """Register (or overwrite) a method instance under its `id`."""
        cls._methods[method.id] = method

    @classmethod
    def all_methods(cls) -> Dict[str, AnalysisMethod]:
        """Return a shallow copy of all registered methods keyed by ID."""
        return dict(cls._methods)

    @classmethod
    def get(cls, method_id: str) -> Optional[AnalysisMethod]:
        """Retrieve a method by ID, or None if it is not registered."""
        return cls._methods.get(method_id)


class WorldMapMethod(AnalysisMethod):
    """
    Render a choropleth world map for the selected impact or subcontractors.

    Settings are kept in RegionAnalysisViewTab under method_state['world_map'].
    """
    id = "world_map"
    label = "World Map"
    label_key = "World Map"
    supports_settings = True

    def render(self, parent_view, impact_choice, get_world_data):
        """
        Delegate to the parent view's world-map renderer and store the latest df/unit.
        """
        fig, world_df, unit = parent_view._render_world_map_figure(impact_choice)
        parent_view._set_latest_world_df(world_df, unit)
        return fig


class TopNMethod(AnalysisMethod):
    """Bar chart showing the Top-n regions by impact, with up to 3 comparison impacts."""
    id = "topn"
    label = "Top n"
    label_key = "Top n"
    supports_settings = True

    def render(self, view, impact: str, get_world_df):
        """
        Render Top-n using SupplyChain backend, merging view state with sensible defaults.
        """
        st = {
            "n": 10,
            "title": "",                # empty -> let backend auto-title (localized)
            "orientation": "vertical",
            "bar_color": "tab10",
            "bar_width": 0.8,
            "relative": True,
            **view.method_state.get(self.id, {}),
        }

        # Primary impact defines sorting; add up to 3 extra comparison impacts
        primary = view._current_impact_key()
        extras  = list(view.get_extra_impacts())
        imps    = [primary] + [e for e in extras if e != primary][:3]

        user_title = (st.get("title") or "").strip()
        title = user_title if user_title else None  # None -> backend auto-title

        return view.ui.supplychain.plot_topn_by_impacts(
            impacts=imps,
            n=int(st.get("n", 10)),
            relative=bool(st.get("relative", True)),
            orientation=st.get("orientation", "vertical"),
            bar_color=st.get("bar_color", "tab10"),
            bar_width=float(st.get("bar_width", 0.8)),
            title=title,
            return_data=False,
        )


class FlopNMethod(AnalysisMethod):
    """Bar chart showing the Flop-n regions (lowest values), with comparison impacts."""
    id = "flopn"
    label = "Flop n"
    label_key = "Flop n"
    supports_settings = True

    def render(self, view, impact: str, get_world_df):
        """
        Render Flop-n using SupplyChain backend, merging view state with defaults.
        """
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
    """Pie chart of a single impact across regions (with sorting and thresholds)."""
    id = "pie"
    label = "Pie chart"
    label_key = "Pie chart"
    supports_settings = True

    def render(self, view, impact: str, get_world_df):
        """
        Render a pie chart using SupplyChain backend, applying view-managed state.
        """
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

        # If no custom title is provided, show a simple default with the current impact
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
