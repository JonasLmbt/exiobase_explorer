from __future__ import annotations
import matplotlib.pyplot as plt
import pandas as pd
import os
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from datetime import datetime

from PyQt5.QtWidgets import (
    QTabWidget, QWidget, QVBoxLayout, QHBoxLayout, QMenu, QFileDialog,
    QGraphicsOpacityEffect, QGroupBox, QLabel, QPushButton, QSizePolicy,
    QTreeWidget, QTreeWidgetItem, QDialogButtonBox, QDialog, QApplication,
    QComboBox, QTabBar, QToolTip, QMessageBox
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap
from shapely.geometry import Point


# region_view.py (new file) OR replace your MapConfigTab class in-place

from typing import Optional, Tuple

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QMenu, QFileDialog, QMessageBox,
    QPushButton, QTabWidget, QToolTip, QToolButton
)
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas

from .widgets_analysis import MethodSelectorWidget, ImpactSelectorWidget, WorldMapSettingsDialog, ImpactMultiSelectorButton

from .analysis_methods import RegionAnalysisRegistry, AnalysisMethod, WorldMapMethod
from .stage_methods import StageAnalysisRegistry, StageAnalysisMethod

from typing import Optional, List, Dict

import os
import matplotlib.pyplot as plt
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QMenu, QFileDialog, QMessageBox,
    QTabWidget, QToolButton
)
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas



def multiindex_to_nested_dict(multiindex: pd.MultiIndex) -> dict:
    """Convert MultiIndex to nested dictionary structure."""
    root = {}
    for keys in multiindex:
        current = root
        for key in keys:
            current = current.setdefault(key, {})
    return root


class VisualisationTab(QWidget):
    """Main visualization tab containing sub-tabs for different chart types."""

    def __init__(self, ui, parent=None):
        """
        Initialize the VisualisationTab.

        Args:
            ui (UserInterface): The parent user interface object.
            parent (QWidget, optional): The parent widget. Defaults to None.
        """
        super().__init__(parent)

        self.ui = ui
        self.iosystem = self.ui.iosystem
        self.general_dict = self.iosystem.index.general_dict

        self._init_ui()

    def _get_text(self, key, fallback):
        """Get text from general_dict with fallback."""
        return self.general_dict.get(key, fallback)

    def _init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout(self)

        # Create inner tab widget for different visualization types
        self.inner_tab_widget = QTabWidget()

        # Add visualization tabs
        self.inner_tab_widget.addTab(
            StageAnalysisTabContainer(ui=self.ui),
            self._get_text("Diagram", "Diagram")
        )
        self.inner_tab_widget.addTab(
            RegionAnalysisTabContainer(ui=self.ui),
            self._get_text("World Map", "World Map")
        )

        layout.addWidget(self.inner_tab_widget)


class StageAnalysisTabContainer(QWidget):
    """
    Container for multiple StageAnalysisViewTab instances with a '+' tab to add more.
    """
    def __init__(self, ui, parent=None):
        super().__init__(parent)
        self.ui = ui
        self.iosystem = self.ui.iosystem
        self.general_dict = self.iosystem.index.general_dict
        self._adding_tab = False
        self._init_ui()

    def _get_text(self, key, fallback):
        return self.general_dict.get(key, fallback)

    def _init_ui(self):
        layout = QVBoxLayout(self)

        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.tabCloseRequested.connect(self._on_tab_close_requested)
        self.tabs.tabBarClicked.connect(self._on_tab_clicked)

        self._add_view_tab()
        self._add_plus_tab()

        layout.addWidget(self.tabs)

    def _add_plus_tab(self):
        plus_widget = QWidget()
        idx = self.tabs.addTab(plus_widget, "+")
        self._remove_close_button(idx)

    def _remove_close_button(self, tab_index):
        self.tabs.tabBar().setTabButton(tab_index, QTabBar.RightSide, None)
        self.tabs.tabBar().setTabButton(tab_index, QTabBar.LeftSide, None)

    def _on_tab_clicked(self, index):
        if self._adding_tab:
            return
        if index == self.tabs.count() - 1:
            self._adding_tab = True
            try:
                self._add_view_tab()
            finally:
                self._adding_tab = False

    def _on_tab_close_requested(self, index):
        content = self.tabs.count() - 1  # exclude '+'
        if content <= 1:
            return
        if index == self.tabs.count() - 1:
            return
        self.tabs.removeTab(index)

    def _add_view_tab(self):
        new_tab = StageAnalysisViewTab(self.ui, parent=self.tabs)
        insert_at = max(0, self.tabs.count() - 1)
        idx = self.tabs.insertTab(insert_at, new_tab, new_tab.name)
        self.tabs.setCurrentIndex(idx)
        plus_idx = self.tabs.count() - 1
        if plus_idx >= 0 and self.tabs.tabText(plus_idx) == "+":
            self._remove_close_button(plus_idx)


class StageAnalysisViewTab(QWidget):
    """
    Single tab for stage (value-chain) analysis with a one-line toolbar and a plot area.

    Toolbar (one line):
      - Method selector (Bubble, Sankey/Treemap placeholders, …)
      - Multi-impact selector (button opens tree dialog)
      - Optional Settings button (hidden for now)

    Rendering is delegated to the selected StageAnalysisMethod.
    """

    def __init__(self, ui, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.ui = ui
        self.iosystem = self.ui.iosystem
        self.general_dict = self.iosystem.index.general_dict
        self.name = self._get_text("Diagram", "Diagram")
        self.tab_widget = parent if isinstance(parent, QTabWidget) else None

        # build impact hierarchy (from MultiIndex -> nested dict)
        mi = self.iosystem.index.impact_multiindex
        self.impact_hierarchy: Dict = multiindex_to_nested_dict(mi)

        # UI + state
        self._init_ui()

        # debounce for auto-update
        self._debounce = QTimer(self)
        self._debounce.setInterval(200)
        self._debounce.setSingleShot(True)
        self._debounce.timeout.connect(self._update_plot)

        # initial selection + draw
        self._init_default_impacts()
        self._schedule_update()

    def _get_text(self, key, fallback):
        return self.general_dict.get(key, fallback)

    # ---------------- UI ----------------
    def _init_ui(self):
        layout = QVBoxLayout(self)

        # one-line toolbar
        toolbar = QHBoxLayout()
        toolbar.setContentsMargins(0, 0, 0, 0)

        # method selector
        methods = StageAnalysisRegistry.all_methods()
        self.method_selector = MethodSelectorWidget(methods, parent=self)
        self.method_selector.methodChanged.connect(self._on_method_changed)
        toolbar.addWidget(self.method_selector)

        # multi-impact selector button
        self.impact_selector = ImpactMultiSelectorButton(self.impact_hierarchy, self._get_text, parent=self)
        self.impact_selector.impactsChanged.connect(self._on_impacts_changed)
        toolbar.addWidget(self.impact_selector)

        # settings gear (no settings for bubble yet; keep for future)
        self.settings_btn = QToolButton(self)
        self.settings_btn.setText("⚙")
        self.settings_btn.setToolTip(self._get_text("Open settings", "Open settings"))
        self.settings_btn.setVisible(False)
        toolbar.addWidget(self.settings_btn)

        toolbar.addStretch(1)
        layout.addLayout(toolbar)

        # plot area
        self.canvas = None
        self.plot_area = QVBoxLayout()
        self._create_placeholder()
        layout.addLayout(self.plot_area)

    def _create_placeholder(self):
        fig = plt.figure()
        ax = fig.add_subplot(111)
        ax.text(0.5, 0.5, self._get_text("Waiting for update…", "Waiting for update…"),
                ha='center', va='center', transform=ax.transAxes)
        ax.axis('off')
        self._set_canvas(fig)

    def _set_canvas(self, fig):
        if self.canvas:
            self.plot_area.removeWidget(self.canvas)
            self.canvas.setParent(None)
            self.canvas.deleteLater()
        self.canvas = FigureCanvas(fig)
        self._setup_canvas_context_menu()
        self.plot_area.addWidget(self.canvas)
        self.canvas.draw()

    # ------------- default impacts -------------
    def _init_default_impacts(self):
        """
        Set reasonable defaults similar to your previous DiagramTab.
        """
        impacts = self.iosystem.impacts
        defaults = []
        if len(impacts) > 3:  defaults.append(impacts[3])   # GHG
        if len(impacts) > 32: defaults.append(impacts[32])  # Water
        if len(impacts) > 125: defaults.append(impacts[125])# Land
        if len(impacts) > 0:  defaults.append(impacts[0])   # Value creation
        if len(impacts) > 2:  defaults.append(impacts[2])   # Labor time

        self.impact_selector.set_defaults(defaults)

    # ------------- events -------------
    def _on_method_changed(self, method_id: str):
        # update tab title to method label for clarity
        m = StageAnalysisRegistry.get(method_id)
        if m and self.tab_widget:
            idx = self.tab_widget.indexOf(self)
            if idx != -1:
                self.tab_widget.setTabText(idx, m.label)
        # (optional) toggle settings button if some methods support settings later
        self.settings_btn.setVisible(bool(m and m.supports_settings))
        self._schedule_update()

    def _on_impacts_changed(self, _impacts: List[str]):
        # keep title readable; you can also show count like "Bubble (5)"
        m = StageAnalysisRegistry.get(self.method_selector.current_method())
        if m and self.tab_widget:
            idx = self.tab_widget.indexOf(self)
            if idx != -1:
                self.tab_widget.setTabText(idx, m.label)
        self._schedule_update()

    # ------------- update loop -------------
    def _schedule_update(self):
        self._debounce.start()

    def _update_plot(self):
        from PyQt5.QtWidgets import QApplication
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            method = self._current_method()
            impacts = self.impact_selector.selected_impacts()

            if not method:
                raise RuntimeError("No analysis method selected.")
            if not impacts:
                # Show a gentle hint instead of raising
                fig = plt.figure()
                ax = fig.add_subplot(111)
                ax.text(0.5, 0.5, self._get_text("Please select impacts.", "Please select impacts."),
                        ha='center', va='center', transform=ax.transAxes)
                ax.axis('off')
                self._set_canvas(fig)
                return

            fig = method.render(self, impacts)
            self._set_canvas(fig)

        except Exception as e:
            fig = plt.figure()
            ax = fig.add_subplot(111)
            ax.text(0.5, 0.5, f"{self._get_text('Error', 'Error')}: {str(e)}",
                    ha='center', va='center', transform=ax.transAxes)
            ax.axis('off')
            self._set_canvas(fig)
        finally:
            QApplication.restoreOverrideCursor()

    # ------------- context menu -------------
    def _setup_canvas_context_menu(self):
        self.canvas.setContextMenuPolicy(Qt.CustomContextMenu)
        self.canvas.customContextMenuRequested.connect(self._show_context_menu)

    def _show_context_menu(self, pos):
        menu = QMenu(self)
        save_action = menu.addAction(self._get_text("Save plot", "Save plot"))
        action = menu.exec_(self.canvas.mapToGlobal(pos))
        if action == save_action:
            self._save_high_quality()

    def _save_high_quality(self):
        default_filename = self._generate_filename()
        home_dir = os.path.expanduser("~")
        download_dir = os.path.join(home_dir, "Downloads")
        if not os.path.exists(download_dir):
            download_dir = home_dir
        full_default_path = os.path.join(download_dir, default_filename)

        fname, _ = QFileDialog.getSaveFileName(
            self,
            self._get_text("Save plot", "Save plot"),
            full_default_path,
            f"{self._get_text('PNG Files', 'PNG Files')} (*.png);;"
            f"{self._get_text('PDF Files', 'PDF Files')} (*.pdf);;"
            f"{self._get_text('SVG Files', 'SVG Files')} (*.svg)"
        )
        if fname:
            try:
                save_kwargs = dict(dpi=600, bbox_inches='tight', facecolor='white',
                                   edgecolor='none', transparent=False, pad_inches=0.1)
                self.canvas.figure.savefig(fname, **save_kwargs)
                QMessageBox.information(
                    self,
                    self._get_text("Success", "Success"),
                    f"{self._get_text('Plot saved successfully', 'Plot saved successfully')}: {os.path.basename(fname)}"
                )
            except Exception as e:
                QMessageBox.warning(
                    self,
                    self._get_text("Error", "Error"),
                    f"{self._get_text('Error saving plot', 'Error saving plot')}: {str(e)}"
                )

    def _generate_filename(self) -> str:
        method = StageAnalysisRegistry.get(self.method_selector.current_method())
        method_part = (method.label if method else "Method").replace(" ", "")
        from datetime import datetime
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"Stages_{method_part}_{ts}.png"

    def _current_method(self) -> Optional[StageAnalysisMethod]:
        mid = self.method_selector.current_method()
        return StageAnalysisRegistry.get(mid)


class RegionAnalysisTabContainer(QWidget):
    """
    Container for multiple region analysis views (parallel tabs).

    Each tab holds a RegionAnalysisViewTab with a one-line toolbar and a plot area.
    """

    def __init__(self, ui, parent=None):
        super().__init__(parent)
        self.ui = ui
        self.iosystem = self.ui.iosystem
        self.general_dict = self.iosystem.index.general_dict
        self._adding_tab = False
        self._init_ui()

    def _get_text(self, key, fallback):
        return self.general_dict.get(key, fallback)

    def _init_ui(self):
        layout = QVBoxLayout(self)

        self.map_tabs = QTabWidget()
        self.map_tabs.setTabsClosable(True)
        self.map_tabs.tabCloseRequested.connect(self._on_tab_close_requested)
        self.map_tabs.tabBarClicked.connect(self._on_tab_clicked)

        # initial content + "+" tab
        self._add_map_tab()
        self._add_plus_tab()

        layout.addWidget(self.map_tabs)

    def _add_plus_tab(self):
        plus_widget = QWidget()
        idx = self.map_tabs.addTab(plus_widget, "+")
        self._remove_close_button(idx)

    def _remove_close_button(self, tab_index):
        self.map_tabs.tabBar().setTabButton(tab_index, QTabBar.RightSide, None)
        self.map_tabs.tabBar().setTabButton(tab_index, QTabBar.LeftSide, None)

    def _on_tab_clicked(self, index):
        """Create a new tab only when '+' is clicked, guard against reentrancy."""
        if self._adding_tab:
            return
        if index == self.map_tabs.count() - 1:  # '+' tab
            self._adding_tab = True
            try:
                self._add_map_tab()
            finally:
                self._adding_tab = False

    def _on_tab_close_requested(self, index):
        content_count = self.map_tabs.count() - 1
        if content_count <= 1:
            return
        if index == self.map_tabs.count() - 1:
            return
        self.map_tabs.removeTab(index)

    def _add_map_tab(self):
        """Add a new region analysis tab just before the '+' tab."""
        new_tab = RegionAnalysisViewTab(self.ui, parent=self.map_tabs)
        insert_at = max(0, self.map_tabs.count() - 1)  # before '+'
        idx = self.map_tabs.insertTab(insert_at, new_tab, new_tab.name)
        self.map_tabs.setCurrentIndex(idx)

        # keep '+' tab without close button
        plus_tab_index = self.map_tabs.count() - 1
        if plus_tab_index >= 0 and self.map_tabs.tabText(plus_tab_index) == "+":
            self._remove_close_button(plus_tab_index)


class RegionAnalysisViewTab(QWidget):
    """
    A single region-analysis tab with a compact one-line toolbar and a plot area.

    Toolbar (one line):
      - Method selector (World Map, Top n, Flop n, Pie chart, …)
      - Impact selector (incl. 'Subcontractors' if desired)
      - Optional Settings button (visible if selected method supports settings)
      - (Auto-update via debounce on changes; no extra Update button required)

    The class reuses the worldmap data provider to feed Top/Flop/Pie without
    requiring backend changes: we fetch df via existing worldmap functions with
    `return_data=True`, then render alternative plots from that dataframe.
    """

    def __init__(self, ui, parent: Optional[QWidget] = None):
        super().__init__(parent)

        self.ui = ui
        self.iosystem = self.ui.iosystem
        self.general_dict = self.iosystem.index.general_dict
        self.name = self._get_text("Subcontractors", "Subcontractors")  # initial tab title
        self.tab_widget = parent if isinstance(parent, QTabWidget) else None

        # Latest data (df with region/value/percentage) to be reused by non-map methods
        self._latest_df: Optional[pd.DataFrame] = None
        self._latest_unit: Optional[str] = None

        # Build UI
        self._init_ui()

        # Debounce timer for auto-update
        self._debounce = QTimer(self)
        self._debounce.setInterval(200)
        self._debounce.setSingleShot(True)
        self._debounce.timeout.connect(self._update_plot)

        # Initial draw
        self._schedule_update()

        self._world_gdf = None       # GeoDataFrame with geometry (EPSG:4326)
        self._world_sindex = None    # spatial index
        self._current_choice = None  # remember current impact/mode for tooltips/dialog
        self._map_ax = None  # matplotlib Axes that holds the world map
        self.method_state = {
            "world_map": {
                "color": "Reds",
                "show_legend": False,
                "title": "",
                "mode": "binned",           # "binned" | "continuous"
                "k": 7,
                "custom_bins": None,        # list[float] or None
                "norm_mode": "linear",      # for "continuous"
                "robust": 2.0,              # for "continuous"
                "gamma": 0.7,               # for "continuous"
            }
        }

    def _get_text(self, key, fallback):
        return self.general_dict.get(key, fallback)

    def _init_ui(self):
        layout = QVBoxLayout(self)

        # One-line toolbar
        toolbar = QHBoxLayout()
        toolbar.setContentsMargins(0, 0, 0, 0)

        # Method selector from registry
        methods = RegionAnalysisRegistry.all_methods()
        self.method_selector = MethodSelectorWidget(methods, parent=self)
        self.method_selector.methodChanged.connect(self._on_method_changed)
        toolbar.addWidget(self.method_selector)

        # Impact selector (incl. subcontractors like before)
        self.impact_selector = ImpactSelectorWidget(self.iosystem.impacts, include_subcontractors=True, parent=self)
        self.impact_selector.impactChanged.connect(self._on_impact_changed)
        toolbar.addWidget(self.impact_selector)

        # Optional: Settings button (only visible for methods with settings)
        self.settings_btn = QToolButton(self)
        self.settings_btn.setText("⚙")
        self.settings_btn.setToolTip(self._get_text("Open settings", "Open settings"))
        self.settings_btn.clicked.connect(self._open_settings)
        toolbar.addWidget(self.settings_btn)

        toolbar.addStretch(1)  # keep it tight to one line

        layout.addLayout(toolbar)

        # Plot area
        self.canvas = None
        self.plot_area = QVBoxLayout()
        self._create_initial_placeholder()
        layout.addLayout(self.plot_area)

        self._refresh_settings_button_visibility()

    def _create_initial_placeholder(self):
        fig = plt.figure()
        ax = fig.add_subplot(111)
        ax.text(
            0.5, 0.5,
            self._get_text("Waiting for update…", "Waiting for update…"),
            ha='center', va='center', transform=ax.transAxes
        )
        ax.axis('off')
        self._set_canvas(fig)

    def _set_canvas(self, fig):
        if self.canvas:
            self.plot_area.removeWidget(self.canvas)
            self.canvas.setParent(None)
            self.canvas.deleteLater()
        self.canvas = FigureCanvas(fig)
        self._setup_canvas_context_menu()
        self.plot_area.addWidget(self.canvas)
        self.canvas.draw()

    def _on_method_changed(self, method_id: str):
        self._refresh_settings_button_visibility()
        self._schedule_update()

    def _on_impact_changed(self, impact: str):
        # keep tab title aligned with impact (as in your original map tab)
        self._update_tab_name(impact)
        self._schedule_update()

    def _refresh_settings_button_visibility(self):
        method = self._current_method()
        self.settings_btn.setVisible(bool(method and method.supports_settings))

    def _open_settings(self):
        method = self._current_method()
        if not method or not method.supports_settings:
            return
        # Build dialog with current state
        current = dict(self.method_state.get("world_map", {}))
        dlg = WorldMapSettingsDialog(current, self._get_text, parent=self)
        if dlg.exec_() == dlg.Accepted:
            # Save back and update
            self.method_state["world_map"] = dlg.get_settings()
            self._schedule_update()

    def _schedule_update(self):
        self._debounce.start()

    def _update_plot(self):
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            method = self._current_method()
            impact = self.impact_selector.current_impact()

            if not method:
                raise RuntimeError("No analysis method selected.")

            if isinstance(method, WorldMapMethod):
                # 1) Render figure (stellt auch _latest_df und GeoIndex via _render_world_map_figure ein)
                fig = method.render(self, impact, self._get_world_df_for_impact)

                # 2) Canvas ERST setzen ...
                self._set_canvas(fig)

                # 3) ... und JETZT die Karten-Achse aus der aktuellen Figure ermitteln
                try:
                    axes = self.canvas.figure.axes
                    # Bevorzugt die erste Achse mit Daten (häufig die Karte, nicht die Colorbar)
                    self._map_ax = None
                    for ax in axes:
                        if getattr(ax, "has_data", lambda: True)() and len(getattr(ax, "patches", [])) >= 0:
                            self._map_ax = ax
                            break
                    if self._map_ax is None and axes:
                        self._map_ax = axes[0]
                except Exception:
                    self._map_ax = None

                # 4) Interaktionen NACH dem Setzen der Canvas verbinden
                self._wire_worldmap_interactions()

            else:
                # Nicht-WorldMap-Methoden: Daten updaten, rendern, Canvas setzen, Interaktionen trennen
                df, unit = self._get_world_df_for_impact(impact)
                self._set_latest_world_df(df, unit)
                fig = method.render(self, impact, self._get_world_df_for_impact)
                self._set_canvas(fig)
                self._disconnect_worldmap_interactions()

        except Exception as e:
            fig = plt.figure()
            ax = fig.add_subplot(111)
            ax.text(0.5, 0.5, f"{self._get_text('Error', 'Error')}: {str(e)}",
                    ha='center', va='center', transform=ax.transAxes)
            ax.axis('off')
            self._set_canvas(fig)
        finally:
            QApplication.restoreOverrideCursor()

    def _get_world_df_for_impact(self, impact_choice: str) -> Tuple[pd.DataFrame, str]:
        if impact_choice == self._get_text("Subcontractors", "Subcontractors"):
            fig, world = self.ui.supplychain.plot_worldmap_by_subcontractors(
                color="Blues", relative=True, return_data=True, title=None
            )
        else:
            fig, world = self.ui.supplychain.plot_worldmap_by_impact(
                impact_choice, return_data=True, color="Reds", title=None
            )

        unit = self._extract_unit(world)

        df = pd.DataFrame(world)
        for col in ["region", "value", "percentage"]:
            if col not in df.columns:
                df[col] = None
        if "unit" not in df.columns:
            df["unit"] = unit

        return df, unit

    def _set_latest_world_df(self, df: pd.DataFrame, unit: Optional[str]):
        self._latest_df = df
        self._latest_unit = unit or ""

    def _render_world_map_figure(self, impact_choice: str):
        s = self.method_state.get("world_map", {})

        common_kwargs = dict(
            color=s.get("color", "Reds"),
            title=(s.get("title") or None),
            show_legend=bool(s.get("show_legend", False)),
            return_data=True,
            mode=s.get("mode", "binned"),
            k=int(s.get("k", 7)),
            custom_bins=s.get("custom_bins") or None,
            norm_mode=s.get("norm_mode", "linear"),
            robust=float(s.get("robust", 2.0)),
            gamma=float(s.get("gamma", 0.7)),
        )

        if impact_choice == self._get_text("Subcontractors", "Subcontractors"):
            fig, world = self.ui.supplychain.plot_worldmap_by_subcontractors(**common_kwargs)
        else:
            fig, world = self.ui.supplychain.plot_worldmap_by_impact(impact_choice, **common_kwargs)

        unit = self._extract_unit(world)

        # Update caches for interactivity/other methods
        import pandas as pd
        df = pd.DataFrame(world)
        self._set_latest_world_df(df, unit)
        self._update_geospatial_index(world)
        self._current_choice = impact_choice

        return fig, df, unit

    def _wire_worldmap_interactions(self):
        """
        Connect hover and click only for world map with valid spatial index.
        """
        if not self.canvas or self._world_gdf is None or self._world_sindex is None:
            self._disconnect_worldmap_interactions()
            return
        self._disconnect_worldmap_interactions()
        self._cid_hover = self.canvas.mpl_connect('motion_notify_event', self._on_hover)
        self._cid_click = self.canvas.mpl_connect('button_press_event', self._on_click)

    def _disconnect_worldmap_interactions(self):
        if not self.canvas:
            return
        try:
            if hasattr(self, "_cid_hover"):
                self.canvas.mpl_disconnect(self._cid_hover)
                del self._cid_hover
            if hasattr(self, "_cid_click"):
                self.canvas.mpl_disconnect(self._cid_click)
                del self._cid_click
        except Exception:
            pass  # safe to ignore

    def _on_hover(self, event):
        from PyQt5.QtWidgets import QToolTip
        if (event.inaxes is None or self._map_ax is None or event.inaxes is not self._map_ax
            or event.xdata is None or event.ydata is None):
            QToolTip.hideText()
            return

        hit = self._hit_country_at(event.xdata, event.ydata)
        if hit is None:
            QToolTip.hideText()
            return

        value = hit.get("value", 0)
        percentage = hit.get("percentage", 0)
        unit = hit.get("unit", "")
        text = (
            f'{self._get_text("Region", "Region")}: {hit.get("region", "-")}\n'
            f'{self._current_choice}: {self._format_value(value)} {unit}\n'
            f'{self._get_text("Global share", "Global share")}: {self._format_value(percentage)} %'
        )
        QToolTip.showText(self.canvas.mapToGlobal(event.guiEvent.pos()), text, widget=self.canvas)

    def _on_click(self, event):
        if (event.inaxes is None or self._map_ax is None or event.inaxes is not self._map_ax
            or event.xdata is None or event.ydata is None):
            return
        hit = self._hit_country_at(event.xdata, event.ydata)
        if hit is None:
            return
        dlg = CountryInfoDialog(ui=self.ui, country=hit, choice=self._current_choice, parent=self)
        dlg.exec_()

    def _setup_canvas_context_menu(self):
        self.canvas.setContextMenuPolicy(Qt.CustomContextMenu)
        self.canvas.customContextMenuRequested.connect(self._show_context_menu)

    def _show_context_menu(self, pos):
        menu = QMenu(self)
        save_action = menu.addAction(self._get_text("Save plot", "Save plot"))
        action = menu.exec_(self.canvas.mapToGlobal(pos))
        if action == save_action:
            self._save_high_quality()

    def _save_high_quality(self):
        default_filename = self._generate_filename()
        home_dir = os.path.expanduser("~")
        download_dir = os.path.join(home_dir, "Downloads")
        if not os.path.exists(download_dir):
            download_dir = home_dir
        full_default_path = os.path.join(download_dir, default_filename)

        fname, _ = QFileDialog.getSaveFileName(
            self,
            self._get_text("Save plot", "Save plot"),
            full_default_path,
            f"{self._get_text('PNG Files', 'PNG Files')} (*.png);;"
            f"{self._get_text('PDF Files', 'PDF Files')} (*.pdf);;"
            f"{self._get_text('SVG Files', 'SVG Files')} (*.svg)"
        )
        if fname:
            try:
                save_kwargs = dict(dpi=600, bbox_inches='tight', facecolor='white',
                                   edgecolor='none', transparent=False, pad_inches=0.1)
                self.canvas.figure.savefig(fname, **save_kwargs)
                QMessageBox.information(
                    self,
                    self._get_text("Success", "Success"),
                    f"{self._get_text('Plot saved successfully', 'Plot saved successfully')}: {os.path.basename(fname)}"
                )
            except Exception as e:
                QMessageBox.warning(
                    self,
                    self._get_text("Error", "Error"),
                    f"{self._get_text('Error saving plot', 'Error saving plot')}: {str(e)}"
                )

    def _generate_filename(self) -> str:
        impact = self.impact_selector.current_impact()
        method = RegionAnalysisRegistry.get(self.method_selector.current_method())
        method_part = (method.label if method else "Method").replace(" ", "")
        impact_part = self._clean_filename(impact) if impact else "Impact"
        from datetime import datetime
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"Regions_{method_part}_{impact_part}_{ts}.png"

    def _clean_filename(self, text: str) -> str:
        rep = {
            ' ': '_', '/': '_', '\\': '_', ':': '_', '*': '_', '?': '_', '"': '_',
            '<': '_', '>': '_', '|': '_', 'ä': 'ae', 'ö': 'oe', 'ü': 'ue', 'ß': 'ss',
            'Ä': 'Ae', 'Ö': 'Oe', 'Ü': 'Ue'
        }
        for o, n in rep.items():
            text = text.replace(o, n)
        while '__' in text:
            text = text.replace('__', '_')
        return text.strip('_')

    def _update_tab_name(self, text: str):
        if self.tab_widget:
            idx = self.tab_widget.indexOf(self)
            if idx != -1:
                self.tab_widget.setTabText(idx, text)

    def _current_method(self) -> Optional[AnalysisMethod]:
        mid = self.method_selector.current_method()
        from .analysis_methods import RegionAnalysisRegistry
        return RegionAnalysisRegistry.get(mid)

    def _update_geospatial_index(self, gdf_like):
        """Hold GeoDataFrame as-is (plot CRS), build spatial index; no forced reprojection."""
        try:
            import geopandas as gpd
        except Exception:
            self._world_gdf = None
            self._world_sindex = None
            return

        if gdf_like is None:
            self._world_gdf = None
            self._world_sindex = None
            return

        # Upgrade DataFrame with 'geometry' column to GeoDataFrame if needed
        if isinstance(gdf_like, gpd.GeoDataFrame):
            gdf = gdf_like
        else:
            if hasattr(gdf_like, "columns") and "geometry" in gdf_like.columns:
                gdf = gpd.GeoDataFrame(gdf_like, geometry="geometry", crs=getattr(gdf_like, "crs", None))
            else:
                self._world_gdf = None
                self._world_sindex = None
                return

        # Spatial index aufbauen
        _ = gdf.sindex
        self._world_gdf = gdf
        self._world_sindex = gdf.sindex

    def _format_value(self, value) -> str:
        """
        Format numeric values for tooltips/dialog with adaptive precision.
        """
        try:
            val = float(value)
        except (TypeError, ValueError):
            return str(value)
        if abs(val) >= 1_000_000:
            return f"{val:,.1f}"
        if abs(val) >= 1_000:
            return f"{val:,.2f}"
        if abs(val) >= 1:
            return f"{val:.3f}"
        if abs(val) >= 0.001:
            return f"{val:.6f}"
        return f"{val:.2e}"

    def _hit_country_at(self, x, y):
        """Return row (Series) of hit country at data coords (x,y), or None."""
        if self._world_gdf is None or self._world_sindex is None:
            return None

        pt = Point(x, y)
        # kleiner Toleranzpuffer relativ zum Achsenbereich
        try:
            xmin, xmax = self._map_ax.get_xlim()
            ymin, ymax = self._map_ax.get_ylim()
            tol = 0.002 * max(abs(xmax - xmin), abs(ymax - ymin))  # 0.2% vom Achsenbereich
        except Exception:
            tol = 1e-6

        pt_buf = pt.buffer(tol)

        try:
            # schnelle BBox-Filterung
            bbox = (pt.x, pt.y, pt.x, pt.y)
            candidates = list(self._world_sindex.intersection(bbox))
        except Exception:
            candidates = range(len(self._world_gdf))

        for idx in candidates:
            try:
                geom = self._world_gdf.geometry.iloc[idx]
                # intersects ist toleranter als contains; mit Puffer sehr robust
                if geom.intersects(pt_buf):
                    return self._world_gdf.iloc[idx]
            except Exception:
                continue
        return None

    def _extract_unit(self, world) -> str:
        """
        Robustly extract a unit string from the returned 'world' object.
        Prefers DataFrame/GeoDataFrame column 'unit'. Falls back to dict or attr.
        """
        try:
            import pandas as pd  # local import is ok
            if isinstance(world, pd.DataFrame):
                if "unit" in world.columns and len(world) > 0:
                    return str(world["unit"].iloc[0])
                return ""
            # dict fallback
            if isinstance(world, dict) and "unit" in world:
                return str(world["unit"])
            # last-resort attribute (avoid DF .unit which returns a Series)
            u = getattr(world, "unit", "")
            return "" if u is None else str(u)
        except Exception:
            return ""



class CountryInfoDialog(QDialog):
    """Dialog to show country information on map click."""

    def __init__(self, ui, country, choice, parent=None):
        super().__init__(parent)
        self.ui = ui
        self.iosystem = self.ui.iosystem
        self.general_dict = self.iosystem.index.general_dict

        # Dialog configuration
        self.setWindowTitle(self._get_text("Info", "Info"))
        self.setFixedSize(320, 220)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        # Main layout with background and text overlay
        from PyQt5.QtWidgets import QStackedLayout
        stack = QStackedLayout(self)
        stack.setContentsMargins(0, 0, 0, 0)
        stack.setStackingMode(QStackedLayout.StackAll)

        # Background: Flag with transparency
        flag_name = f"{country.get('exiobase', '-').lower()}.png"
        flag_path = os.path.join(self.iosystem.data_dir, "flags", flag_name)
        bg_label = QLabel()
        bg_label.setScaledContents(True)
        bg_label.setFixedSize(self.size())

        if os.path.exists(flag_path):
            pixmap = QPixmap(flag_path).scaled(
                self.size(), Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation
            )
            bg_label.setPixmap(pixmap)
        else:
            bg_label.setStyleSheet("background-color: #fff;")

        # Transparency effect
        opacity_effect = QGraphicsOpacityEffect(bg_label)
        opacity_effect.setOpacity(0.3)
        bg_label.setGraphicsEffect(opacity_effect)
        stack.addWidget(bg_label)

        # Text label with country information
        text = (
            f'<div style="color: #000; font-size:16px;">'
            f'<b>{country.get("region", "-")}</b><br>'
            f'{choice}: {round(float(country.get("value", "-")), 3)} {country.get("unit", "-")}<br>'
            f'{self._get_text("Global share", "Global share")}: {round(float(country.get("percentage", "-")), 2)} %'
            f'</div>'
        )
        text_label = QLabel(text, self)
        text_label.setAlignment(Qt.AlignCenter)
        text_label.setWordWrap(True)
        stack.addWidget(text_label)

    def _get_text(self, key, fallback):
        """Get text from general_dict with fallback."""
        return self.general_dict.get(key, fallback)

    def mousePressEvent(self, event):
        """Close dialog on mouse click."""
        self.accept()

