from __future__ import annotations
import matplotlib.pyplot as plt
import pandas as pd
import os
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from typing import Optional, Tuple, List, Dict, Callable

from .region_methods import RegionAnalysisRegistry, AnalysisMethod, WorldMapMethod
from .stage_methods import StageAnalysisRegistry, StageAnalysisMethod

from PyQt5.QtWidgets import (
    QTabWidget, QWidget, QVBoxLayout, QHBoxLayout, QMenu, QFileDialog,
    QGraphicsOpacityEffect, QLabel, QSizePolicy,
    QDialog, QApplication, QToolButton, QComboBox, QStyle,
    QTabBar, QMessageBox, QCheckBox, QDialogButtonBox, QSpinBox, QDoubleSpinBox, QPushButton, QTreeWidget, QTreeWidgetItem
)

from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtGui import QPixmap
from shapely.geometry import Point


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

    def _translate(self, key: str, fallback: str) -> str:
        """Return localized string; always cast to str to avoid non-str labels."""
        val = self.general_dict.get(key, fallback)
        if val is None:
            return str(fallback)
        return str(val)

    def _init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout(self)

        # Create inner tab widget for different visualization types
        self.inner_tab_widget = QTabWidget()

        # Add visualization tabs
        self.inner_tab_widget.addTab(
            StageAnalysisTabContainer(ui=self.ui),
            self._translate("Stage Analysis", "Stage Analysis")  
        )
        self.inner_tab_widget.addTab(
            RegionAnalysisTabContainer(ui=self.ui),
            self._translate("Region Analysis", "Region Analysis") 
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

    def _translate(self, key: str, fallback: str) -> str:
        """Return localized string; always cast to str to avoid non-str labels."""
        val = self.general_dict.get(key, fallback)
        if val is None:
            return str(fallback)
        return str(val)

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
        new_tab.titleChanged.connect(lambda t, w=new_tab: self._set_tab_title(w, t))

        insert_at = max(0, self.tabs.count() - 1)
        idx = self.tabs.insertTab(insert_at, new_tab, new_tab.name)
        self.tabs.setCurrentIndex(idx)

        new_tab._emit_title()

        plus_idx = self.tabs.count() - 1
        if plus_idx >= 0 and self.tabs.tabText(plus_idx) == "+":
            self._remove_close_button(plus_idx)

    def _set_tab_title(self, widget: QWidget, title: str):
        idx = self.tabs.indexOf(widget)
        if idx != -1:
            self.tabs.setTabText(idx, title)


class StageAnalysisViewTab(QWidget):
    """
    Single tab for stage (value-chain) analysis with a one-line toolbar and a plot area.

    Toolbar (one line):
      - Method selector (Bubble, Sankey/Treemap placeholders, …)
      - Multi-impact selector (button opens tree dialog)
      - Optional Settings button (hidden for now)

    Rendering is delegated to the selected StageAnalysisMethod.
    """
    titleChanged = pyqtSignal(str)
    stateChanged = pyqtSignal(dict)
    def __init__(self, ui, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.ui = ui
        self.iosystem = self.ui.iosystem
        self.general_dict = self.iosystem.index.general_dict
        self.name = self._translate("Bubble diagram", "Bubble diagram")
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

    def _translate(self, key: str, fallback: str) -> str:
        """Return localized string; always cast to str to avoid non-str labels."""
        val = self.general_dict.get(key, fallback)
        if val is None:
            return str(fallback)
        return str(val)
    
    # ---------------- UI ----------------
    def _init_ui(self):
        layout = QVBoxLayout(self)

        # one-line toolbar
        toolbar = QHBoxLayout()
        toolbar.setContentsMargins(0, 0, 0, 0)

        # method selector
        methods = StageAnalysisRegistry.all_methods()
        self.method_selector = MethodSelectorWidget(methods, tr=self._translate, parent=self)
        self.method_selector.methodChanged.connect(self._on_method_changed)
        toolbar.addWidget(self.method_selector)

        # multi-impact selector button
        self.impact_selector = ImpactMultiSelectorButton(self.impact_hierarchy, self._translate, parent=self)
        self.impact_selector.impactsChanged.connect(self._on_impacts_changed)
        toolbar.addWidget(self.impact_selector)

        # settings gear (no settings for bubble yet; keep for future)
        self.settings_btn = QToolButton(self)
        self.settings_btn.setText("⚙")
        self.settings_btn.setToolTip(self._translate("Open settings", "Open settings"))
        self.settings_btn.setVisible(False)
        toolbar.addWidget(self.settings_btn)

        toolbar.addStretch(1)
        layout.addLayout(toolbar)

        # plot area
        self.canvas = None
        self.plot_area = QVBoxLayout()
        self._create_placeholder()
        layout.addLayout(self.plot_area)

        self.save_btn = QToolButton(self)
        self.save_btn.setIcon(self.style().standardIcon(QStyle.SP_DialogSaveButton))
        self.save_btn.setToolTip(self._translate("Save plot", "Save plot"))
        self.save_btn.clicked.connect(self._save_high_quality)
        self.save_btn.setEnabled(False)
        toolbar.addWidget(self.save_btn)

    def _create_placeholder(self):
        fig = plt.figure()
        ax = fig.add_subplot(111)
        ax.text(0.5, 0.5, self._translate("Waiting for update…", "Waiting for update…"),
                ha='center', va='center', transform=ax.transAxes)
        ax.axis('off')
        self._set_canvas(fig)

    def _set_canvas(self, fig):
        if self.canvas:
            self.plot_area.removeWidget(self.canvas)
            self.canvas.setParent(None)
            self.canvas.deleteLater()
        # Ränder optimieren, bevor gerendert wird
        self._optimize_margins(fig)

        self.canvas = FigureCanvas(fig)
        self.canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.canvas.updateGeometry()

        self._setup_canvas_context_menu()
        self.plot_area.addWidget(self.canvas)
        self.canvas.draw()

        if hasattr(self, "save_btn"):
            self.save_btn.setEnabled(True)

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
        m = StageAnalysisRegistry.get(method_id)
        self.settings_btn.setVisible(bool(m and m.supports_settings))
        self._emit_title()
        self._schedule_update()
        self.stateChanged.emit(self.get_state())

    def _on_impacts_changed(self, _impacts: List[str]):
        self._emit_title()
        self._schedule_update()
        self.stateChanged.emit(self.get_state())

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
                ax.text(0.5, 0.5, self._translate("Please select impacts.", "Please select impacts."),
                        ha='center', va='center', transform=ax.transAxes)
                ax.axis('off')
                self._set_canvas(fig)
                return

            fig = method.render(self, impacts)
            self._set_canvas(fig)

        except Exception as e:
            fig = plt.figure()
            ax = fig.add_subplot(111)
            ax.text(0.5, 0.5, f"{self._translate('Error', 'Error')}: {str(e)}",
                    ha='center', va='center', transform=ax.transAxes)
            ax.axis('off')
            self._set_canvas(fig)
        finally:
            QApplication.restoreOverrideCursor()

    def get_state(self) -> dict:
        return {
            "method_id": self.method_selector.current_method(),
            "impacts": list(self.impact_selector.selected_impacts()),
            # placeholder for future per-method settings:
            "method_state": {},
        }

    def set_state(self, state: dict) -> None:
        if not state:
            return
        mid = state.get("method_id")
        if mid:
            self.method_selector.set_current_method(mid)
        imps = state.get("impacts")
        if isinstance(imps, list):
            self.impact_selector.set_selected_impacts(imps)
        self._emit_title()
        self._schedule_update()

    # ------------- context menu -------------
    def _setup_canvas_context_menu(self):
        self.canvas.setContextMenuPolicy(Qt.CustomContextMenu)
        self.canvas.customContextMenuRequested.connect(self._show_context_menu)

    def _show_context_menu(self, pos):
        menu = QMenu(self)
        save_action = menu.addAction(self._translate("Save plot", "Save plot"))
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
            self._translate("Save plot", "Save plot"),
            full_default_path,
            f"{self._translate('PNG Files', 'PNG Files')} (*.png);;"
            f"{self._translate('PDF Files', 'PDF Files')} (*.pdf);;"
            f"{self._translate('SVG Files', 'SVG Files')} (*.svg)"
        )
        if fname:
            try:
                save_kwargs = dict(dpi=600, bbox_inches='tight', facecolor='white',
                                   edgecolor='none', transparent=False, pad_inches=0.1)
                self.canvas.figure.savefig(fname, **save_kwargs)
                QMessageBox.information(
                    self,
                    self._translate("Success", "Success"),
                    f"{self._translate('Plot saved successfully', 'Plot saved successfully')}: {os.path.basename(fname)}"
                )
            except Exception as e:
                QMessageBox.warning(
                    self,
                    self._translate("Error", "Error"),
                    f"{self._translate('Error saving plot', 'Error saving plot')}: {str(e)}"
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

    def _emit_title(self):
        m = self._current_method()
        label = self._translate(m.label, m.label) if m else self._translate("Diagram", "Diagram")
        n = len(self.impact_selector.selected_impacts())
        sel = f"{self._translate('Selected', 'Selected')} ({n})"
        self.titleChanged.emit(f"{label} – {sel}")

    def _optimize_margins(self, fig):
        """
        Make the plot look centered without clipping the suptitle/labels.
        Use ONLY tight_layout with a safe 'rect' that leaves headroom.
        """
        try:
            has_suptitle = getattr(fig, "_suptitle", None) is not None
            if has_suptitle:
                # left, bottom, right, top
                # -> oben ~6% frei lassen für den Suptitel
                fig.tight_layout(rect=[0.02, 0.06, 0.98, 0.94], pad=0.4)
            else:
                # ohne Suptitel etwas mehr Top-Space
                fig.tight_layout(rect=[0.02, 0.06, 0.98, 0.98], pad=0.4)
        except Exception:
            # Fallback: lieber nichts tun, als zu schneiden
            pass


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

    def _translate(self, key: str, fallback: str) -> str:
        """Return localized string; always cast to str to avoid non-str labels."""
        val = self.general_dict.get(key, fallback)
        if val is None:
            return str(fallback)
        return str(val)

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
        new_tab = RegionAnalysisViewTab(self.ui, parent=self.map_tabs)

        # Listen to title/state updates
        new_tab.titleChanged.connect(lambda t, w=new_tab: self._set_tab_title(w, t))

        insert_at = self.map_tabs.count() - 1
        idx = self.map_tabs.insertTab(insert_at, new_tab, new_tab.name)
        self.map_tabs.setCurrentIndex(idx)

        # Initialize title once
        new_tab._emit_title()

        plus_tab_index = self.map_tabs.count() - 1
        if plus_tab_index >= 0 and self.map_tabs.tabText(plus_tab_index) == "+":
            self._remove_close_button(plus_tab_index)

    def _set_tab_title(self, widget: QWidget, title: str):
        idx = self.map_tabs.indexOf(widget)
        if idx != -1:
            self.map_tabs.setTabText(idx, title)


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
    titleChanged = pyqtSignal(str)
    stateChanged = pyqtSignal(dict)

    def __init__(self, ui, parent: Optional[QWidget] = None):
        super().__init__(parent)

        self.ui = ui
        self.iosystem = self.ui.iosystem
        self.general_dict = self.iosystem.index.general_dict
        self.name = self._translate("Subcontractors", "Subcontractors")  # initial tab title
        self.tab_widget = parent if isinstance(parent, QTabWidget) else None
        self._extra_impacts: list[str] = []   # stores additional impacts (max 3), canonical keys

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

    def _translate(self, key: str, fallback: str) -> str:
        """Return localized string; always cast to str to avoid non-str labels."""
        val = self.general_dict.get(key, fallback)
        if val is None:
            return str(fallback)
        return str(val)

    def _init_ui(self):
        layout = QVBoxLayout(self)

        # One-line toolbar
        toolbar = QHBoxLayout()
        toolbar.setContentsMargins(0, 0, 0, 0)

        # Method selector from registry
        methods = RegionAnalysisRegistry.all_methods()
        self.method_selector = MethodSelectorWidget(methods, tr=self._translate, parent=self)
        self.method_selector.methodChanged.connect(self._on_method_changed)
        toolbar.addWidget(self.method_selector)

        self.impact_selector = ImpactSelectorWidget(
            self.iosystem.impacts, tr=self._translate, include_subcontractors=True, parent=self
        )
        self.impact_selector.impactChanged.connect(self._on_impact_changed)
        toolbar.addWidget(self.impact_selector)

        self.extra_impacts_btn = QPushButton(self._translate("Compare impacts", "Compare impacts"), self)
        self.extra_impacts_btn.setToolTip(
            self._translate("Select up to 3 additional impacts to compare (does not affect ranking).",
                        "Select up to 3 additional impacts to compare (does not affect ranking).")
        )
        self.extra_impacts_btn.clicked.connect(self._open_extra_impacts_dialog)
        toolbar.addWidget(self.extra_impacts_btn)
        self._update_extra_button_text()

        # Optional: Settings button (only visible for methods with settings)
        self.settings_btn = QToolButton(self)
        self.settings_btn.setText("⚙")
        self.settings_btn.setToolTip(self._translate("Open settings", "Open settings"))
        self.settings_btn.clicked.connect(self._open_settings)
        toolbar.addWidget(self.settings_btn)

        # --- Save button (icon only) ---
        self.save_btn = QToolButton(self)
        self.save_btn.setIcon(self.style().standardIcon(QStyle.SP_DialogSaveButton))
        self.save_btn.setToolTip(self._translate("Save plot", "Save plot"))
        self.save_btn.clicked.connect(self._save_high_quality)
        self.save_btn.setEnabled(False)  # enabled after first figure arrives
        toolbar.addWidget(self.save_btn)

        toolbar.addStretch(1)  # keep it tight to one line

        layout.addLayout(toolbar)

        self._refresh_toolbar_visibility()

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
            self._translate("Waiting for update…", "Waiting for update…"),
            ha='center', va='center', transform=ax.transAxes
        )
        ax.axis('off')
        self._set_canvas(fig)

    def _set_canvas(self, fig):
        if self.canvas:
            self.plot_area.removeWidget(self.canvas)
            self.canvas.setParent(None)
            self.canvas.deleteLater()

        self._optimize_margins(fig)

        self.canvas = FigureCanvas(fig)
        self.canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.canvas.updateGeometry()
        self._setup_canvas_context_menu()
        self.plot_area.addWidget(self.canvas)
        self.canvas.draw()

        # enable Save now that a figure exists
        if hasattr(self, "save_btn"):
            self.save_btn.setEnabled(True)

    def _refresh_settings_button_visibility(self):
        method = self._current_method()
        self.settings_btn.setVisible(bool(method and method.supports_settings))

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
            ax.text(0.5, 0.5, f"{self._translate('Error', 'Error')}: {str(e)}",
                    ha='center', va='center', transform=ax.transAxes)
            ax.axis('off')
            self._set_canvas(fig)
        finally:
            QApplication.restoreOverrideCursor()

    def _get_world_df_for_impact(self, impact_choice: str) -> Tuple[pd.DataFrame, str]:
        if self._is_subcontractors(impact_choice):
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

        if self._is_subcontractors(impact_choice): 
            fig, world = self.ui.supplychain.plot_worldmap_by_subcontractors(**common_kwargs)
        else:
            fig, world = self.ui.supplychain.plot_worldmap_by_impact(impact_choice, **common_kwargs)

        unit = self._extract_unit(world)

        # Update caches for interactivity/other methods
        unit = self._extract_unit(world)
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
            f'{self._translate("Region", "Region")}: {hit.get("region", "-")}\n'
            f'{self._current_choice}: {self._format_value(value)} {unit}\n'
            f'{self._translate("Global share", "Global share")}: {self._format_value(percentage)} %'
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
        save_action = menu.addAction(self._translate("Save plot", "Save plot"))
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
            self._translate("Save plot", "Save plot"),
            full_default_path,
            f"{self._translate('PNG Files', 'PNG Files')} (*.png);;"
            f"{self._translate('PDF Files', 'PDF Files')} (*.pdf);;"
            f"{self._translate('SVG Files', 'SVG Files')} (*.svg)"
        )
        if fname:
            try:
                save_kwargs = dict(dpi=600, bbox_inches='tight', facecolor='white',
                                   edgecolor='none', transparent=False, pad_inches=0.1)
                self.canvas.figure.savefig(fname, **save_kwargs)
                QMessageBox.information(
                    self,
                    self._translate("Success", "Success"),
                    f"{self._translate('Plot saved successfully', 'Plot saved successfully')}: {os.path.basename(fname)}"
                )
            except Exception as e:
                QMessageBox.warning(
                    self,
                    self._translate("Error", "Error"),
                    f"{self._translate('Error saving plot', 'Error saving plot')}: {str(e)}"
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
        from .region_methods import RegionAnalysisRegistry
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

    def get_state(self) -> dict:
        """
        Return a minimal, serializable state of this tab:
        - method_id
        - impact (raw)
        - method_state (per-method settings dicts)
        """
        return {
            "method_id": self.method_selector.current_method(),
            "impact": self.impact_selector.current_impact(),
            "method_state": dict(self.method_state),  # shallow copy
        }

    def set_state(self, state: dict) -> None:
        """
        Restore a previously saved state. Will trigger a redraw.
        """
        if not state:
            return
        ms = state.get("method_state")
        if isinstance(ms, dict):
            self.method_state.update(ms)

        mid = state.get("method_id")
        if mid:
            self.method_selector.set_current_method(mid)

        imp = state.get("impact")
        if imp:
            self.impact_selector.set_current_impact(imp)

        # Ensure UI reflects the state
        self._refresh_settings_button_visibility()
        self._emit_title()
        self._schedule_update()

    def _emit_title(self):
        method = self._current_method()
        if not method:
            return
        mid = getattr(method, "id", "")
        st = self.method_state.get(mid, {})
        # label
        if mid == "topn":
            n = int(st.get("n", 10))
            method_label = f'{self._translate("Top", "Top")} {n}'
        elif mid == "flopn":
            n = int(st.get("n", 10))
            method_label = f'{self._translate("Flop", "Flop")} {n}'
        else:
            base = getattr(method, "label_key", getattr(method, "label", getattr(method, "id", "Method")))
            method_label = self._translate(base, base)

        # impacts im Titel (aus Settings oder aktuellem Impact)
        imps = list(st.get("impacts") or [self.impact_selector.current_impact()])
        impacts_txt = ", ".join(imps[:3])

        title = f"{method_label} – {impacts_txt}" if impacts_txt else method_label

        # Tabtext setzen
        if self.tab_widget:
            idx = self.tab_widget.indexOf(self)
            if idx != -1:
                self.tab_widget.setTabText(idx, title)

    def _on_method_changed(self, method_id: str):
        self._refresh_settings_button_visibility()
        self._refresh_toolbar_visibility()
        self._emit_title()
        self._schedule_update()
        if hasattr(self, "_emit_title"):
            self._emit_title()
        self.stateChanged.emit(self.get_state())

    def _on_impact_changed(self, impact: str):
        self._update_tab_name(self.impact_selector.current_text())  # optional: keeps old behavior
        self._emit_title()
        self._schedule_update()
        if hasattr(self, "_emit_title"):
            self._emit_title()
        self.stateChanged.emit(self.get_state())

    def _open_settings(self):
        method = self._current_method()
        if not method or not method.supports_settings:
            return
        mid = getattr(method, "id", None)
        state = self.method_state.get(mid, {})

        dlg = None
        if mid == "worldmap":
            dlg = WorldMapSettingsDialog(state, self._translate, parent=self)

        elif mid == "pie":
            dlg = PieChartSettingsDialog(state, self._translate, parent=self)

        elif mid in ("topn", "flopn"):
            dlg = TopFlopSettingsDialog(
                settings=self.method_state.get(mid, {}),
                tr=self._translate,             
                iosystem=self.iosystem,         
                parent=self
            )

        if dlg and dlg.exec_() == dlg.Accepted:
            self.method_state[mid] = dlg.get_settings()
            if hasattr(self, "_emit_title"):
                self._emit_title()
            self._schedule_update()

    def _is_subcontractors(self, value) -> bool:
        """Return True if 'value' denotes the special 'Subcontractors' choice."""
        raw = str(value).strip().lower()
        # raw keyword
        if raw == "subcontractors":
            return True
        loc = str(self._translate("Subcontractors", "Subcontractors")).strip().lower()
        return raw == loc

    def _optimize_margins(self, fig):
        """
        Make the plot look centered without clipping colorbars.
        If the figure already has its own colorbar axes, avoid tight_layout.
        """
        if getattr(fig, "_has_colorbar", False):
            try:
                # Lass rundum etwas Luft, aber kein tight_layout (clips cax)
                fig.subplots_adjust(left=0.02, right=0.98, bottom=0.06, top=0.94)
            except Exception:
                pass
            return

        try:
            has_suptitle = getattr(fig, "_suptitle", None) is not None
            if has_suptitle:
                fig.tight_layout(rect=[0.02, 0.06, 0.94, 0.94], pad=0.4)  # rechts etwas kleiner
            else:
                fig.tight_layout(rect=[0.02, 0.06, 0.96, 0.98], pad=0.4)
        except Exception:
            pass

    def _current_impact_key(self) -> str:
        """Canonical key of the primary impact from the single-select widget."""
        for attr in ("current_impact", "current_value", "currentText", "current_text"):
            f = getattr(self.impact_selector, attr, None)
            if callable(f):
                try:
                    return f()
                except Exception:
                    pass
        return ""

    def get_extra_impacts(self) -> list[str]:
        """Return up to 3 additional impacts, excluding the current primary if present."""
        primary = self._current_impact_key()
        return [i for i in self._extra_impacts if i and i != primary][:3]

    def _update_extra_button_text(self):
        n = len(self.get_extra_impacts())
        self.extra_impacts_btn.setText(f'{self._translate("Compare impacts", "Compare impacts")} ({n})')

    def _open_extra_impacts_dialog(self):
        """
        Open a tree dialog to pick up to 3 additional impacts (like the bubble tab).
        Primary impact is shown but cannot be selected.
        """
        # Build nested hierarchy from impact_multiindex
        try:
            hierarchy = {}
            mi = getattr(self.iosystem.index, "impact_multiindex", None)
            if mi is not None:
                for keys in mi:
                    cur = hierarchy
                    for key in keys:
                        cur = cur.setdefault(str(key), {})
            else:
                # fallback: flat list
                hierarchy = {"Impacts": {str(k): {} for k in self.iosystem.impacts}}
        except Exception:
            hierarchy = {"Impacts": {str(k): {} for k in self.iosystem.impacts}}

        # Create dialog
        dlg = QDialog(self); dlg.setWindowTitle(self._translate("Select Impacts", "Select Impacts"))
        dlg.setMinimumSize(360, 420)
        v = QVBoxLayout(dlg)
        v.addWidget(QLabel(self._translate("Choose up to 3 comparison impacts (sorting uses the main impact).",
                                        "Choose up to 3 comparison impacts (sorting uses the main impact).")))
        tree = QTreeWidget(dlg)
        tree.setHeaderHidden(True)
        tree.setSelectionMode(QTreeWidget.NoSelection)
        v.addWidget(tree)

        primary = self._current_impact_key()
        preselected = set(self._extra_impacts)

        # populate tree
        def add_items(parent, d: dict):
            for key, child in d.items():
                it = QTreeWidgetItem(parent)
                it.setText(0, key)
                it.setFlags(it.flags() | Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
                # If this is a leaf (no children) and equals primary, disable selection
                is_leaf = not bool(child)
                if is_leaf and key == primary:
                    it.setCheckState(0, Qt.Unchecked)
                    it.setFlags(it.flags() & ~Qt.ItemIsUserCheckable)
                    it.setDisabled(True)
                    it.setToolTip(0, self._translate("Primary impact (sorting); cannot be selected here.",
                                                    "Primary impact (sorting); cannot be selected here."))
                else:
                    it.setCheckState(0, Qt.Checked if key in preselected else Qt.Unchecked)
                if child:
                    add_items(it, child)

        add_items(tree, hierarchy)

        # Enforce max 3 checked leaves
        def _leaf_checked_count() -> int:
            cnt = 0
            def walk(item):
                nonlocal cnt
                if item.childCount() == 0 and (item.flags() & Qt.ItemIsUserCheckable):
                    if item.checkState(0) == Qt.Checked:
                        cnt += 1
                for i in range(item.childCount()):
                    walk(item.child(i))
            for i in range(tree.topLevelItemCount()):
                walk(tree.topLevelItem(i))
            return cnt

        def _on_item_changed(item, col):
            # Only enforce on leaves
            if item.childCount() > 0:
                return
            if not (item.flags() & Qt.ItemIsUserCheckable):
                return
            if item.checkState(0) == Qt.Checked:
                if _leaf_checked_count() > 3:
                    # revert this check
                    item.setCheckState(0, Qt.Unchecked)
                    QMessageBox.warning(
                        dlg,
                        self._translate("Limit exceeded", "Limit exceeded"),
                        self._translate("Please select at most 3 impacts.", "Please select at most 3 impacts.")
                    )

        tree.itemChanged.connect(_on_item_changed)

        # Buttons
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, dlg)
        v.addWidget(btns)

        def _collect_selection() -> list[str]:
            picked = []
            def walk(item):
                if item.childCount() == 0 and (item.flags() & Qt.ItemIsUserCheckable):
                    if item.checkState(0) == Qt.Checked:
                        picked.append(item.text(0))
                for i in range(item.childCount()):
                    walk(item.child(i))
            for i in range(tree.topLevelItemCount()):
                walk(tree.topLevelItem(i))
            # ensure primary excluded and limit 3
            return [x for x in picked if x != primary][:3]

        def _ok():
            self._extra_impacts = _collect_selection()
            self._update_extra_button_text()
            # persist in method_state for topn/flopn
            for mid in ("topn", "flopn"):
                st = self.method_state.get(mid, {})
                st["impacts_extras"] = list(self._extra_impacts)
                self.method_state[mid] = st
            # update plot/title
            if hasattr(self, "_emit_title"):
                self._emit_title()
            self._schedule_update()
            dlg.accept()

        btns.accepted.connect(_ok)
        btns.rejected.connect(dlg.reject)
        dlg.exec_()

    def _refresh_toolbar_visibility(self):
        """Show/hide toolbar widgets depending on selected method."""
        method = self._current_method()
        mid = getattr(method, "id", "")
        is_topflop = mid in ("topn", "flopn")
        if hasattr(self, "extra_impacts_btn"):
            self.extra_impacts_btn.setVisible(is_topflop)
        # Settings-Button wie gehabt:
        self.settings_btn.setVisible(bool(method and method.supports_settings))


class CountryInfoDialog(QDialog):
    """Dialog to show country information on map click."""

    def __init__(self, ui, country, choice, parent=None):
        super().__init__(parent)
        self.ui = ui
        self.iosystem = self.ui.iosystem
        self.general_dict = self.iosystem.index.general_dict

        # Dialog configuration
        self.setWindowTitle(self._translate("Info", "Info"))
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
            f'{self._translate("Global share", "Global share")}: {round(float(country.get("percentage", "-")), 2)} %'
            f'</div>'
        )
        text_label = QLabel(text, self)
        text_label.setAlignment(Qt.AlignCenter)
        text_label.setWordWrap(True)
        stack.addWidget(text_label)

    def _translate(self, key: str, fallback: str) -> str:
        """Return localized string; always cast to str to avoid non-str labels."""
        val = self.general_dict.get(key, fallback)
        if val is None:
            return str(fallback)
        return str(val)
    
    def mousePressEvent(self, event):
        """Close dialog on mouse click."""
        self.accept()


class MethodSelectorWidget(QWidget):
    """
    One-line drop-down to select an analysis method.

    - Shows localized labels (via `tr`).
    - Keeps stable `method_id` in userData.
    - Emits methodChanged(method_id) on change.
    """
    methodChanged = pyqtSignal(str)

    def __init__(self, methods: Dict[str, object], tr: Callable[[str, str], str], parent=None):
        super().__init__(parent)
        self._methods = methods
        self._tr = tr

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.combo = QComboBox(self)
        for mid, m in self._methods.items():
            label = self._tr(getattr(m, "label", str(mid)), getattr(m, "label", str(mid)))
            self.combo.addItem(label, userData=mid)
        self.combo.currentIndexChanged.connect(self._emit_change)
        layout.addWidget(self.combo)

    def _emit_change(self, *_):
        mid = self.combo.currentData()
        if mid:
            self.methodChanged.emit(mid)

    def set_current_method(self, method_id: str) -> None:
        idx = self.combo.findData(method_id)
        if idx >= 0:
            self.combo.setCurrentIndex(idx)

    def current_method(self) -> str:
        return self.combo.currentData()

    def current_label(self) -> str:
        return self.combo.currentText()


class ImpactSelectorWidget(QWidget):
    impactChanged = pyqtSignal(str)
    ...
    def __init__(self, impacts, include_subcontractors=True, parent=None, tr=lambda k,f: f):
        super().__init__(parent)
        self._tr = tr
        self._combo = QComboBox(self)
        lay = QHBoxLayout(self); lay.setContentsMargins(0,0,0,0); lay.addWidget(self._combo)

        if include_subcontractors:
            lbl = self._tr("Subcontractors", "Subcontractors")
            self._combo.addItem(lbl, userData="Subcontractors")

        for key in list(impacts):
            lbl = self._tr(key, key)
            self._combo.addItem(lbl, userData=key)

        self._combo.currentIndexChanged.connect(self._emit_change)

    def _emit_change(self, *_):
        self.impactChanged.emit(self.current_impact())

    def current_impact(self) -> str:
        """Return canonical impact key from userData; fallback to text."""
        data = self._combo.currentData()
        return data if isinstance(data, str) and data else self._combo.currentText()

    def set_current_impact(self, key_or_label: str) -> None:
        """Select by canonical key (preferred) or by visible text."""
        for i in range(self._combo.count()):
            if self._combo.itemData(i) == key_or_label:
                self._combo.setCurrentIndex(i)
                return
        idx = self._combo.findText(key_or_label)
        if idx >= 0:
            self._combo.setCurrentIndex(idx)

    def current_text(self) -> str:
        """Visible label (translated)."""
        return self._combo.currentText()

    def set_current_display(self, label: str) -> None:
        """Alias: select by visible label."""
        idx = self._combo.findText(label)
        if idx >= 0:
            self._combo.setCurrentIndex(idx)


class WorldMapSettingsDialog(QDialog):
    """
    Settings dialog for the World Map method.

    Exposes:
      - color (colormap) [+ reverse]
      - relative (bool)
      - show_legend (bool)
      - title (str)

      Classification:
        - mode: "binned" | "continuous"
        - k: int (binned)
        - custom_bins: List[float] | None (overrides k)
        - norm_mode: "linear" | "log" | "power" (continuous)
        - robust: float in % (continuous)
        - gamma: float (continuous)
    """

    # ---------- utils ----------
    def _t(self, key: str, fallback: str) -> str:
        """Translate via provided callback; always return a string."""
        try:
            return str(self._tr(key, fallback))
        except Exception:
            return str(fallback)

    def _format_bins_for_edit(self, bins):
        if not bins:
            return ""
        try:
            return ", ".join(str(float(b)) for b in bins)
        except Exception:
            return str(bins)

    def _parse_bins(self) -> Optional[list]:
        text = self.custom_bins.currentText().strip()
        if not text:
            return None
        try:
            parts = [p.strip() for p in text.replace(";", ",").split(",")]
            vals = [float(p) for p in parts if p]
            return vals if vals else None
        except Exception:
            return None

    # ---------- colormap combo ----------
    def _fill_colormap_combo(self):
        """Fill self.cmap with grouped, translated labels and internal names in userData."""
        self.cmap.clear()

        groups = [
            ("cm.group.perceptual", "Perceptual",
             ["viridis", "plasma", "inferno", "magma", "cividis", "turbo"]),
            ("cm.group.sequential", "Sequential",
             ["Reds", "Oranges", "Greens", "Blues", "Purples", "Greys",
              "YlGn", "YlGnBu", "GnBu", "BuGn", "PuBu", "BuPu",
              "OrRd", "PuRd", "RdPu", "YlOrBr", "YlOrRd"]),
            ("cm.group.diverging", "Diverging",
             ["BrBG", "PiYG", "PRGn", "PuOr", "RdBu", "RdGy", "RdYlBu", "RdYlGn",
              "Spectral", "coolwarm", "bwr", "seismic"]),
            ("cm.group.cyclic", "Cyclic", ["twilight", "twilight_shifted", "hsv"]),
            ("cm.group.qualitative", "Qualitative",
             ["tab10", "tab20", "tab20b", "tab20c", "Set1", "Set2", "Set3",
              "Pastel1", "Pastel2", "Accent", "Dark2", "Paired"]),
        ]

        for gi, (gkey, gname, names) in enumerate(groups):
            # Header (disabled)
            header = self._t(gkey, gname)
            self.cmap.addItem(header)
            idx = self.cmap.count() - 1
            item = self.cmap.model().item(idx)
            item.setFlags(Qt.NoItemFlags)
            item.setData(True, Qt.UserRole + 1)

            # Items
            for name in names:
                label = self._t(f"cmap.{name}", name)
                self.cmap.addItem(label, userData=name)

            # Separator between groups (not after the last one)
            if gi < len(groups) - 1:
                self.cmap.insertSeparator(self.cmap.count())

        # current selection (support saved *_r)
        saved = str(self._settings.get("color", "Reds"))
        is_rev = saved.endswith("_r")
        base = saved[:-2] if is_rev else saved
        i = self.cmap.findData(base)
        if i != -1:
            self.cmap.setCurrentIndex(i)
        self.reverse_cb.setChecked(bool(self._settings.get("cmap_reverse", is_rev)))

    # ---------- init ----------
    def __init__(self, settings: dict, tr: Callable[[str, str], str], parent=None):
        super().__init__(parent)
        self._tr = tr
        self.setWindowTitle(self._t("World Map Settings", "World Map Settings"))
        self.setModal(True)

        # Copy settings to avoid side effects until accepted
        self._settings = dict(settings or {})

        v = QVBoxLayout(self)

        # --- Basic ---
        v.addWidget(QLabel(self._t("Colormap", "Colormap")))
        row_cmap = QHBoxLayout()
        self.cmap = QComboBox(self)
        self.reverse_cb = QCheckBox(self._t("cm.reverse", "Reverse"), self)
        row_cmap.addWidget(self.cmap)
        row_cmap.addWidget(self.reverse_cb)
        v.addLayout(row_cmap)

        # Legend
        self.legend = QCheckBox(self._t("Show legend", "Show legend"), self)
        self.legend.setChecked(bool(self._settings.get("show_legend", False)))
        v.addWidget(self.legend)

        # Title
        v.addWidget(QLabel(self._t("Title (optional)", "Title (optional)")))
        self.title = QComboBox(self)
        self.title.setEditable(True)
        self.title.setInsertPolicy(QComboBox.InsertAtTop)
        self.title.setCurrentText(self._settings.get("title", "") or "")
        v.addWidget(self.title)

        # --- Classification ---
        v.addWidget(QLabel(self._t("Classification", "Classification")))
        row1 = QHBoxLayout(); v.addLayout(row1)
        row1.addWidget(QLabel(self._t("Mode", "Mode")))
        self.mode = QComboBox(self)
        self.mode.addItems(["binned", "continuous"])
        self.mode.setCurrentText(self._settings.get("mode", "binned"))
        row1.addWidget(self.mode)

        # Binned
        row_binned = QHBoxLayout(); v.addLayout(row_binned)
        row_binned.addWidget(QLabel(self._t("Classes (k)", "Classes (k)")))
        self.k = QSpinBox(self); self.k.setRange(2, 12)
        self.k.setValue(int(self._settings.get("k", 7)))
        row_binned.addWidget(self.k)

        row_bins = QHBoxLayout(); v.addLayout(row_bins)
        row_bins.addWidget(QLabel(self._t("Custom bins (comma-separated)", "Custom bins (comma-separated)")))
        self.custom_bins = QComboBox(self); self.custom_bins.setEditable(True)
        self.custom_bins.setCurrentText(self._format_bins_for_edit(self._settings.get("custom_bins")))
        row_bins.addWidget(self.custom_bins)

        # Continuous
        v.addWidget(QLabel(self._t("Normalization (continuous mode)", "Normalization (continuous mode)")))
        row_norm = QHBoxLayout(); v.addLayout(row_norm)
        row_norm.addWidget(QLabel(self._t("Norm", "Norm")))
        self.norm_mode = QComboBox(self)
        self.norm_mode.addItems(["linear", "log", "power"])
        self.norm_mode.setCurrentText(self._settings.get("norm_mode", "linear"))
        row_norm.addWidget(self.norm_mode)

        row_robust = QHBoxLayout(); v.addLayout(row_robust)
        row_robust.addWidget(QLabel(self._t("Robust clipping (%)", "Robust clipping (%)")))
        self.robust = QDoubleSpinBox(self)
        self.robust.setSuffix(" %"); self.robust.setRange(0.0, 20.0); self.robust.setSingleStep(0.5)
        self.robust.setValue(float(self._settings.get("robust", 2.0)))
        row_robust.addWidget(self.robust)

        row_gamma = QHBoxLayout(); v.addLayout(row_gamma)
        row_gamma.addWidget(QLabel(self._t("Gamma (power norm)", "Gamma (power norm)")))
        self.gamma = QDoubleSpinBox(self)
        self.gamma.setRange(0.1, 5.0); self.gamma.setSingleStep(0.1)
        self.gamma.setValue(float(self._settings.get("gamma", 0.7)))
        row_gamma.addWidget(self.gamma)

        # Visibility sync
        def _refresh_visibility():
            is_binned = self.mode.currentText() == "binned"
            self.k.setEnabled(is_binned); self.custom_bins.setEnabled(is_binned)
            is_cont = not is_binned
            self.norm_mode.setEnabled(is_cont); self.robust.setEnabled(is_cont); self.gamma.setEnabled(is_cont)
        self.mode.currentIndexChanged.connect(_refresh_visibility); _refresh_visibility()

        # Fill colormap list last (needs widgets)
        self._fill_colormap_combo()

        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        v.addWidget(buttons)

    # ---------- public ----------
    def get_settings(self) -> dict:
        """
        Collect all settings from the dialog into a dict.
        Colormap returns the internal name (e.g. 'Reds' or 'Reds_r').
        """
        cmap_internal = self.cmap.currentData() or self.cmap.currentText()
        if self.reverse_cb.isChecked() and not cmap_internal.endswith("_r"):
            cmap_internal = f"{cmap_internal}_r"

        return {
            "color": cmap_internal,
            "show_legend": bool(self.legend.isChecked()),
            "title": self.title.currentText().strip() or "",
            "mode": self.mode.currentText(),
            "k": int(self.k.value()),
            "custom_bins": self._parse_bins(),
            "norm_mode": self.norm_mode.currentText(),
            "robust": float(self.robust.value()),
            "gamma": float(self.gamma.value()),
            # keep reverse separately too (useful for UI state persistence)
            "cmap_reverse": bool(self.reverse_cb.isChecked()),
        }


class PieChartSettingsDialog(QDialog):
    """Settings dialog for the Pie chart (i18n colormap groups + reverse)."""

    def __init__(self, settings: dict, tr: Callable[[str, str], str], parent=None):
        super().__init__(parent)
        self._tr = tr
        self._s = dict(settings or {})
        self.setWindowTitle(self._t("Pie chart settings", "Pie chart settings"))
        self.setModal(True)

        v = QVBoxLayout(self)

        # Top slices
        row_top = QHBoxLayout(); v.addLayout(row_top)
        row_top.addWidget(QLabel(self._t("Top slices", "Top slices")))
        self.top_slices = QSpinBox(self); self.top_slices.setRange(1, 50)
        self.top_slices.setValue(int(self._s.get("top_slices", 10)))
        row_top.addWidget(self.top_slices)

        # Min percentage
        row_min = QHBoxLayout(); v.addLayout(row_min)
        row_min.addWidget(QLabel(self._t("Minimum share (%)", "Minimum share (%)")))
        self.min_pct = QDoubleSpinBox(self); self.min_pct.setRange(0.0, 100.0); self.min_pct.setSingleStep(0.5)
        self.min_pct.setSuffix(" %")
        self.min_pct.setValue(float(self._s.get("min_pct", 0.0) or 0.0))
        row_min.addWidget(self.min_pct)

        # Sort order
        row_sort = QHBoxLayout(); v.addLayout(row_sort)
        row_sort.addWidget(QLabel(self._t("Sort slices", "Sort slices")))
        self.sort_slices = QComboBox(self)
        self.sort_slices.addItems(["desc", "asc", "original"])
        self.sort_slices.setCurrentText(self._s.get("sort_slices", "desc"))
        row_sort.addWidget(self.sort_slices)

        # Title
        v.addWidget(QLabel(self._t("Title (optional)", "Title (optional)")))
        self.title = QComboBox(self); self.title.setEditable(True)
        self.title.setInsertPolicy(QComboBox.InsertAtTop)
        self.title.setCurrentText(self._s.get("title", "") or "")
        v.addWidget(self.title)

        # Angle & direction
        row_ang = QHBoxLayout(); v.addLayout(row_ang)
        row_ang.addWidget(QLabel(self._t("Start angle", "Start angle")))
        self.start_angle = QSpinBox(self); self.start_angle.setRange(0, 360)
        self.start_angle.setValue(int(self._s.get("start_angle", 90)))
        row_ang.addWidget(self.start_angle)

        self.counterclockwise = QCheckBox(self._t("Counterclockwise", "Counterclockwise"))
        self.counterclockwise.setChecked(bool(self._s.get("counterclockwise", True)))
        row_ang.addWidget(self.counterclockwise)

        # Colormap (+ reverse), mit Gruppen & i18n
        v.addWidget(QLabel(self._t("Colormap", "Colormap")))
        row_cmap = QHBoxLayout(); v.addLayout(row_cmap)
        self.cmap = QComboBox(self)
        self.reverse_cb = QCheckBox(self._t("cm.reverse", "Reverse"))
        row_cmap.addWidget(self.cmap)
        row_cmap.addWidget(self.reverse_cb)
        self._fill_colormap_combo()  # setzt auch current & reverse

        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        v.addWidget(buttons)

    # ---- helpers ----
    def _t(self, key, fallback): 
        try: return str(self._tr(key, fallback))
        except Exception: return str(fallback)

    def _fill_colormap_combo(self):
        """Füllt Combo mit gruppierten, übersetzten Namen; interner Name in userData."""
        self.cmap.clear()

        groups = [
            ("cm.group.perceptual", "Perceptual",
             ["viridis", "plasma", "inferno", "magma", "cividis", "turbo"]),
            ("cm.group.sequential", "Sequential",
             ["Reds", "Oranges", "Greens", "Blues", "Purples", "Greys",
              "YlGn", "YlGnBu", "GnBu", "BuGn", "PuBu", "BuPu",
              "OrRd", "PuRd", "RdPu", "YlOrBr", "YlOrRd"]),
            ("cm.group.diverging", "Diverging",
             ["BrBG", "PiYG", "PRGn", "PuOr", "RdBu", "RdGy", "RdYlBu", "RdYlGn",
              "Spectral", "coolwarm", "bwr", "seismic"]),
            ("cm.group.cyclic", "Cyclic", ["twilight", "twilight_shifted", "hsv"]),
            ("cm.group.qualitative", "Qualitative",
             ["tab10", "tab20", "tab20b", "tab20c", "Set1", "Set2", "Set3",
              "Pastel1", "Pastel2", "Accent", "Dark2", "Paired"]),
        ]

        for gi, (gkey, gname, names) in enumerate(groups):
            # Header (deaktiviert)
            header = self._t(gkey, gname)
            self.cmap.addItem(header)
            idx = self.cmap.count() - 1
            item = self.cmap.model().item(idx)
            item.setFlags(Qt.NoItemFlags)
            item.setData(True, Qt.UserRole + 1)

            # Items mit übersetztem Label, internem Namen in userData
            for name in names:
                label = self._t(f"cmap.{name}", name)
                self.cmap.addItem(label, userData=name)

            if gi < len(groups) - 1:
                self.cmap.insertSeparator(self.cmap.count())

        # gespeicherten Zustand anwenden (unterstützt *_r)
        saved = str(self._s.get("color_map", "tab20"))
        is_rev = saved.endswith("_r")
        base = saved[:-2] if is_rev else saved
        i = self.cmap.findData(base)
        if i != -1:
            self.cmap.setCurrentIndex(i)
        self.reverse_cb.setChecked(bool(self._s.get("cmap_reverse", is_rev)))

    def get_settings(self) -> dict:
        """Sammelt alle Settings (color_map liefert internen Namen, ggf. mit _r)."""
        cmap_name = self.cmap.currentData() or self.cmap.currentText()
        if self.reverse_cb.isChecked() and not str(cmap_name).endswith("_r"):
            cmap_name = f"{cmap_name}_r"

        return {
            "top_slices": int(self.top_slices.value()),
            "min_pct": float(self.min_pct.value()) if self.min_pct.value() > 0 else None,
            "sort_slices": self.sort_slices.currentText(),
            "title": self.title.currentText().strip() or "",
            "start_angle": int(self.start_angle.value()),
            "counterclockwise": bool(self.counterclockwise.isChecked()),
            "color_map": str(cmap_name),
            "cmap_reverse": bool(self.reverse_cb.isChecked()),
        }
    

class TopFlopSettingsDialog(QDialog):
    """Settings dialog for Top/Flop with multi-impact selector (max 3 enforced here)."""

    def __init__(self, settings: dict, tr: Callable[[str, str], str], iosystem, parent=None):
        super().__init__(parent)
        self._tr = tr
        self._s = dict(settings or {})
        self.setWindowTitle(self._t("Top/Flop settings", "Top/Flop settings"))
        self.setModal(True)

        v = QVBoxLayout(self)

        # n
        row_n = QHBoxLayout(); v.addLayout(row_n)
        row_n.addWidget(QLabel(self._t("Count (n)", "Count (n)")))
        self.n = QSpinBox(self); self.n.setRange(1, 50)
        self.n.setValue(int(self._s.get("n", 10)))
        row_n.addWidget(self.n)

        # Title
        v.addWidget(QLabel(self._t("Title (optional)", "Title (optional)")))
        self.title = QComboBox(self); self.title.setEditable(True)
        self.title.setInsertPolicy(QComboBox.InsertAtTop)
        self.title.setCurrentText(self._s.get("title", "") or "")
        v.addWidget(self.title)

        # Orientation
        row_or = QHBoxLayout(); v.addLayout(row_or)
        row_or.addWidget(QLabel(self._t("Orientation", "Orientation")))
        self.orientation = QComboBox(self)
        self.orientation.addItems(["vertical", "horizontal"])
        self.orientation.setCurrentText(self._s.get("orientation", "vertical"))
        row_or.addWidget(self.orientation)

        # Relative
        self.relative = QCheckBox(self._t("Relative (%)", "Relative (%)"))
        self.relative.setChecked(bool(self._s.get("relative", True)))
        v.addWidget(self.relative)

        # bar color / width
        row_c = QHBoxLayout(); v.addLayout(row_c)
        row_c.addWidget(QLabel(self._t("Bar color / Colormap", "Bar color / Colormap")))
        self.bar_color = QComboBox(self)
        for name in ["tab10","tab20","viridis","plasma","magma","cividis","turbo",
                     "tab:blue","tab:orange","tab:green","tab:red","tab:purple","tab:brown"]:
            self.bar_color.addItem(name)
        self.bar_color.setEditable(True)
        self.bar_color.setCurrentText(self._s.get("bar_color", "tab10"))
        row_c.addWidget(self.bar_color)

        row_w = QHBoxLayout(); v.addLayout(row_w)
        row_w.addWidget(QLabel(self._t("Bar width", "Bar width")))
        self.bar_width = QDoubleSpinBox(self); self.bar_width.setRange(0.1, 1.2); self.bar_width.setSingleStep(0.05)
        self.bar_width.setValue(float(self._s.get("bar_width", 0.8)))
        row_w.addWidget(self.bar_width)

        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        v.addWidget(buttons)

    def _t(self, key, fallback):
        try: return str(self._tr(key, fallback))
        except Exception: return str(fallback)

    def accept(self):
        super().accept()

    def get_settings(self) -> dict:
        return {
            "n": int(self.n.value()),
            "title": self.title.currentText().strip() or "",
            "orientation": self.orientation.currentText(),
            "relative": bool(self.relative.isChecked()),
            "bar_color": self.bar_color.currentText(),
            "bar_width": float(self.bar_width.value()),
        }


class ImpactMultiSelectorButton(QWidget):
    """
    Compact one-line multi-impact selector with a button that opens a tree dialog.

    Usage:
      - Instantiate with a nested impact hierarchy (dict[str, dict, ...]).
      - Call set_defaults(list[str]) to define initially selected impacts.
      - Connect to impactsChanged(list[str]) to react to changes.
      - The button text shows "Selected (n)".
    """
    impactsChanged = pyqtSignal(list)

    def __init__(self, nested_hierarchy: Dict, tr, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._tr = tr  # translation callable
        self._hierarchy = nested_hierarchy or {}
        self._selected = set()
        self._defaults = set()

        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)

        self.btn = QPushButton(self)
        self.btn.clicked.connect(self._open_dialog)
        lay.addWidget(self.btn)

        self._update_button_text()

    def set_defaults(self, defaults: List[str]) -> None:
        """Define default selection; also sets current selection to these defaults."""
        self._defaults = set(defaults or [])
        self._selected = set(defaults or [])
        self._update_button_text()

    def selected_impacts(self) -> List[str]:
        """Return the current selection as a list (order not guaranteed)."""
        return list(self._selected)

    def set_selected_impacts(self, impacts: List[str]) -> None:
        self._selected = set(impacts or [])
        self._update_button_text()
        self.impactsChanged.emit(self.selected_impacts())

    # ---------------- internal ----------------
    def _update_button_text(self) -> None:
        count = len(self._selected)
        self.btn.setText(f"{self._tr('Selected', 'Selected')} ({count})")

    def _open_dialog(self):
        dlg = QDialog(self)
        dlg.setWindowTitle(self._tr("Select Impacts", "Select Impacts"))
        dlg.setMinimumSize(350, 300)
        v = QVBoxLayout(dlg)

        v.addWidget(QLabel(f"{self._tr('Select Impacts', 'Select Impacts')}:"))

        tree = QTreeWidget(dlg)
        tree.setHeaderHidden(True)
        tree.setSelectionMode(QTreeWidget.NoSelection)
        v.addWidget(tree)

        # populate
        def add_items(parent_item, data_dict, level=0):
            for key, val in data_dict.items():
                item = QTreeWidgetItem(parent_item)
                # store raw key, display localized text
                item.setData(0, Qt.UserRole + 1, key)
                item.setText(0, self._tr(key, key))
                item.setData(0, Qt.UserRole, level)
                item.setFlags(item.flags() | Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
                item.setCheckState(0, Qt.Checked if key in self._selected else Qt.Unchecked)
                if isinstance(val, dict) and val:
                    add_items(item, val, level + 1)
                    
        add_items(tree, self._hierarchy)

        # buttons row
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, dlg)
        row = QHBoxLayout()
        reset_btn = QPushButton(self._tr("Reset to Defaults", "Reset to Defaults"), dlg)
        reset_btn.clicked.connect(lambda: self._reset_to_defaults(tree))
        row.addWidget(reset_btn)
        row.addStretch(1)
        row.addWidget(buttons)
        v.addLayout(row)

        buttons.accepted.connect(lambda: self._accept_dialog(tree, dlg))
        buttons.rejected.connect(dlg.reject)

        dlg.exec_()

    def _reset_to_defaults(self, tree: QTreeWidget):
        def walk(item: QTreeWidgetItem):
            raw = item.data(0, Qt.UserRole + 1)
            item.setCheckState(0, Qt.Checked if raw in self._defaults else Qt.Unchecked)
            for i in range(item.childCount()):
                walk(item.child(i))
        for i in range(tree.topLevelItemCount()):
            walk(tree.topLevelItem(i))

    def _accept_dialog(self, tree: QTreeWidget, dlg: QDialog):
        new_sel = set()
        def collect(item: QTreeWidgetItem):
            raw = item.data(0, Qt.UserRole + 1)
            if raw is not None and (item.flags() & Qt.ItemIsUserCheckable) and item.checkState(0) == Qt.Checked:
                new_sel.add(raw)
            for i in range(item.childCount()):
                collect(item.child(i))
        for i in range(tree.topLevelItemCount()):
            collect(tree.topLevelItem(i))

        self._selected = new_sel
        self._update_button_text()
        self.impactsChanged.emit(self.selected_impacts())
        dlg.accept()