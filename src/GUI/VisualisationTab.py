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
            DiagramParentTab(ui=self.ui),
            self._get_text("Diagram", "Diagram")
        )
        self.inner_tab_widget.addTab(
            WorldMapTab(ui=self.ui),
            self._get_text("World Map", "World Map")
        )

        layout.addWidget(self.inner_tab_widget)


class DiagramParentTab(QWidget):
    """Parent tab for managing multiple diagram views with parallel tabs."""

    def __init__(self, ui, parent=None):
        """
        Initialize the DiagramParentTab.

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

        # Create tab widget for multiple diagrams
        self.diagram_tabs = QTabWidget()
        self.diagram_tabs.setTabsClosable(True)
        self.diagram_tabs.tabCloseRequested.connect(self._on_tab_close_requested)
        self.diagram_tabs.tabBarClicked.connect(self._on_tab_clicked)

        # Add initial diagram and "+" tab
        self._add_diagram_tab()
        self._add_plus_tab()

        layout.addWidget(self.diagram_tabs)

    def _add_plus_tab(self):
        """Add the "+" tab for creating new diagrams."""
        plus_widget = QWidget()
        idx = self.diagram_tabs.addTab(plus_widget, "+")
        self._remove_close_button(idx)

    def _remove_close_button(self, tab_index):
        """Remove the close button for a specific tab."""
        # Remove the close button by setting it to None
        self.diagram_tabs.tabBar().setTabButton(tab_index, QTabBar.RightSide, None)
        self.diagram_tabs.tabBar().setTabButton(tab_index, QTabBar.LeftSide, None)

    def _on_tab_clicked(self, index):
        """Handle tab clicks - create new tab if "+" is clicked."""
        if index == self.diagram_tabs.count() - 1:  # "+" tab clicked
            self._add_diagram_tab()

    def _on_tab_close_requested(self, index):
        """Handle tab close requests."""
        content_count = self.diagram_tabs.count() - 1  # Exclude "+" tab

        # Don't allow closing if only one content tab left
        if content_count <= 1:
            return

        # Don't allow closing the "+" tab
        if index == self.diagram_tabs.count() - 1:
            return

        self.diagram_tabs.removeTab(index)

    def _add_diagram_tab(self):
        """Add a new diagram configuration tab."""
        new_tab = DiagramTab(self.ui, parent=self.diagram_tabs)

        # Insert before "+" tab
        insert_at = self.diagram_tabs.count() - 1
        idx = self.diagram_tabs.insertTab(insert_at, new_tab, new_tab.name)

        # Set focus to new tab
        self.diagram_tabs.setCurrentIndex(idx)

        # Ensure the "+" tab doesn't have a close button
        plus_tab_index = self.diagram_tabs.count() - 1
        if plus_tab_index >= 0 and self.diagram_tabs.tabText(plus_tab_index) == "+":
            self._remove_close_button(plus_tab_index)


class DiagramTab(QWidget):
    """Tab for supply chain diagram visualization."""

    def __init__(self, ui, parent=None):
        """
        Initialize the DiagramTab.

        Args:
            ui (UserInterface): The parent user interface object.
            parent (QWidget, optional): The parent widget. Defaults to None.
        """
        super().__init__(parent)

        self.ui = ui
        self.iosystem = self.ui.iosystem
        self.general_dict = self.iosystem.index.general_dict
        self.name = self._get_text("Diagram", "Diagram")
        self.tab_widget = parent if isinstance(parent, QTabWidget) else None

        # Convert impact hierarchy
        self.impact_hierarchy = multiindex_to_nested_dict(
            self.iosystem.index.impact_multiindex
        )

        # Set default impact selections
        self._set_default_impacts()

        self._init_ui()

    def _get_text(self, key, fallback):
        """Get text from general_dict with fallback."""
        return self.general_dict.get(key, fallback)

    def _set_default_impacts(self):
        """Set default impact selections."""
        # Use safe indexing to avoid index errors
        impacts = self.iosystem.impacts
        self.saved_defaults = {}

        # Set defaults only if impacts exist at these indices
        if len(impacts) > 3:
            self.saved_defaults[impacts[3]] = True  # Greenhouse gas emissions
        if len(impacts) > 32:
            self.saved_defaults[impacts[32]] = True  # Water consumption
        if len(impacts) > 125:
            self.saved_defaults[impacts[125]] = True  # Land use
        if len(impacts) > 0:
            self.saved_defaults[impacts[0]] = True  # Value creation
        if len(impacts) > 2:
            self.saved_defaults[impacts[2]] = True  # Labor time

        self.selected_impacts = [k for k, v in self.saved_defaults.items() if v]

    def _init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout(self)

        # Impact selection group
        impact_group = self._create_impact_selection_group()
        layout.addWidget(impact_group)

        # Update button - positioned consistently with other tabs
        self.plot_button = QPushButton(self._get_text("Update Plot", "Update Plot"))
        self.plot_button.clicked.connect(self.update_plot)
        layout.addWidget(self.plot_button)

        # Plot area
        self.canvas = None
        self.plot_area = QVBoxLayout()
        self._create_initial_plot()
        layout.addLayout(self.plot_area)

    def _create_impact_selection_group(self):
        """Create the impact selection group."""
        group = QGroupBox(self._get_text("Select Impacts", "Select Impacts"))
        layout = QVBoxLayout(group)

        self.impact_button = QPushButton()
        self._update_impact_button_text()
        self.impact_button.clicked.connect(self._select_impacts)
        layout.addWidget(self.impact_button)

        group.setMaximumHeight(100)
        return group

    def _update_impact_button_text(self):
        """Update the impact button text with selection count."""
        count = sum(self.saved_defaults.values())
        self.impact_button.setText(
            f"{self._get_text('Selected', 'Selected')} ({count})"
        )

    def _create_initial_plot(self):
        """Create initial placeholder plot."""
        fig = plt.figure()
        ax = fig.add_subplot(111)
        ax.text(0.5, 0.5,
                self._get_text("Please select sectors and regions first", "Please select sectors and regions first"),
                horizontalalignment='center', verticalalignment='center',
                transform=ax.transAxes)
        ax.axis('off')

        self.canvas = FigureCanvas(fig)
        self._setup_canvas_context_menu()
        self.plot_area.addWidget(self.canvas)

    def update_plot(self):
        """Update the plot based on selected impacts."""
        QApplication.setOverrideCursor(Qt.WaitCursor)

        # Remove old canvas
        if self.canvas:
            self.plot_area.removeWidget(self.canvas)
            self.canvas.setParent(None)
            self.canvas.deleteLater()

        try:
            # Generate new plot
            fig = self.ui.supplychain.plot_supplychain_diagram(
                self.selected_impacts,
                size=1,
                lines=True,
                line_width=1,
                line_color="gray",
                text_position="center"
            )

            # Create new canvas
            self.canvas = FigureCanvas(fig)
            self._setup_canvas_context_menu()
            self.plot_area.addWidget(self.canvas)
            self.canvas.draw()

        except Exception as e:
            # Create error plot
            fig = plt.figure()
            ax = fig.add_subplot(111)
            ax.text(0.5, 0.5, f"{self._get_text('Error', 'Error')}: {str(e)}",
                    horizontalalignment='center', verticalalignment='center',
                    transform=ax.transAxes)
            ax.axis('off')
            self.canvas = FigureCanvas(fig)
            self._setup_canvas_context_menu()
            self.plot_area.addWidget(self.canvas)

        QApplication.restoreOverrideCursor()

    def _select_impacts(self):
        """Open dialog for impact selection."""
        dialog = QDialog(self)
        dialog.setWindowTitle(self._get_text("Select Impacts", "Select Impacts"))
        dialog.setMinimumSize(350, 300)
        layout = QVBoxLayout(dialog)

        # Instructions
        layout.addWidget(QLabel(f"{self._get_text('Select Impacts', 'Select Impacts')}:"))

        # Impact tree
        self.impact_tree = QTreeWidget()
        self.impact_tree.setHeaderHidden(True)
        self.impact_tree.setSelectionMode(QTreeWidget.NoSelection)
        self._populate_impact_tree(self.impact_tree, self.impact_hierarchy)
        layout.addWidget(self.impact_tree)

        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_layout = QHBoxLayout()

        reset_button = QPushButton(self._get_text("Reset to Defaults", "Reset to Defaults"))
        reset_button.clicked.connect(lambda: self._reset_defaults_and_close(dialog))
        button_layout.addWidget(reset_button)

        button_layout.addStretch()
        button_layout.addWidget(buttons)
        layout.addLayout(button_layout)

        buttons.accepted.connect(lambda: self._confirm_selection_and_close(dialog))
        buttons.rejected.connect(dialog.reject)

        dialog.exec_()

    def _populate_impact_tree(self, tree, data):
        """Populate the impact tree with hierarchical data."""

        def add_items(parent, data_dict, level=0):
            for key, val in data_dict.items():
                item = QTreeWidgetItem(parent)
                item.setText(0, key)
                item.setData(0, Qt.UserRole, level)
                item.setFlags(item.flags() | Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)

                # Set check state based on saved defaults
                check_state = Qt.Checked if self.saved_defaults.get(key, False) else Qt.Unchecked
                item.setCheckState(0, check_state)

                if isinstance(val, dict) and val:
                    add_items(item, val, level + 1)

        add_items(tree, data)

    def _confirm_selection_and_close(self, dialog):
        """Confirm impact selection and close dialog."""
        new_defaults = {}

        def collect_items(item):
            if item.flags() & Qt.ItemIsUserCheckable:
                new_defaults[item.text(0)] = item.checkState(0) == Qt.Checked
            for i in range(item.childCount()):
                collect_items(item.child(i))

        for i in range(self.impact_tree.topLevelItemCount()):
            collect_items(self.impact_tree.topLevelItem(i))

        self.saved_defaults = new_defaults
        self.selected_impacts = [k for k, v in self.saved_defaults.items() if v]
        self._update_impact_button_text()
        self.update_plot()
        dialog.accept()

    def _reset_defaults_and_close(self, dialog):
        """Reset to default impacts and close dialog."""
        self._set_default_impacts()
        self._update_impact_button_text()
        self.update_plot()
        dialog.accept()

    def _setup_canvas_context_menu(self):
        """Set up context menu for canvas."""
        self.canvas.setContextMenuPolicy(Qt.CustomContextMenu)
        self.canvas.customContextMenuRequested.connect(self._show_context_menu)

    def _show_context_menu(self, pos):
        """Show context menu for saving plot."""
        menu = QMenu(self)
        save_action = menu.addAction(self._get_text("Save plot", "Save plot"))
        action = menu.exec_(self.canvas.mapToGlobal(pos))

        if action == save_action:
            self._save_plot_high_quality()

    def _save_plot_high_quality(self):
        """Save plot with high quality and meaningful filename."""
        default_filename = self._generate_diagram_filename()

        # Setzt den Standardpfad auf den Benutzer-Download-Ordner
        home_dir = os.path.expanduser("~")
        download_dir = os.path.join(home_dir, "Downloads")
        if not os.path.exists(download_dir):
            download_dir = home_dir

        full_default_path = os.path.join(download_dir, default_filename)

        fname, _ = QFileDialog.getSaveFileName(
            self,
            self._get_text("Save plot", "Save plot"),
            full_default_path,
            f"{self._get_text('PNG Files', 'PNG-Dateien')} (*.png);;{self._get_text('PDF Files', 'PDF-Dateien')} (*.pdf);;{self._get_text('SVG Files', 'SVG-Dateien')} (*.svg)"
        )

        if fname:
            try:
                # High quality save settings
                save_kwargs = {
                    'dpi': 600,  # Erhöhte DPI für höhere Qualität
                    'bbox_inches': 'tight',
                    'facecolor': 'white',
                    'edgecolor': 'none',
                    'transparent': False,
                    'pad_inches': 0.1
                }

                self.canvas.figure.savefig(fname, **save_kwargs)

                QMessageBox.information(
                    self,
                    self._get_text("Success", "Erfolg"),
                    f"{self._get_text('Plot saved successfully', 'Grafik erfolgreich gespeichert')}: {os.path.basename(fname)}"
                )
            except Exception as e:
                QMessageBox.warning(
                    self,
                    self._get_text("Error", "Fehler"),
                    f"{self._get_text('Error saving plot', 'Fehler beim Speichern')}: {str(e)}"
                )

    def _generate_diagram_filename(self):
        """Generate meaningful default filename for diagrams."""
        # Basis-Name aus ausgewählten Impacts
        if self.selected_impacts:
            # Nehme ersten Impact als Hauptbezeichner und bereinige ihn
            main_impact = self.selected_impacts[0][:30]  # Kürze auf 30 Zeichen
            main_impact = self._clean_filename(main_impact)
            base_name = f"Lieferkette_{main_impact}"
        else:
            base_name = "Lieferkette_Diagramm"

        # Füge Zeitstempel hinzu
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        return f"{base_name}_{timestamp}.png"

    def _clean_filename(self, text):
        """Clean text for use in filenames."""
        # Ersetze problematische Zeichen
        replacements = {
            ' ': '_',
            '/': '_',
            '\\': '_',
            ':': '_',
            '*': '_',
            '?': '_',
            '"': '_',
            '<': '_',
            '>': '_',
            '|': '_',
            'ä': 'ae',
            'ö': 'oe',
            'ü': 'ue',
            'ß': 'ss',
            'Ä': 'Ae',
            'Ö': 'Oe',
            'Ü': 'Ue'
        }

        for old, new in replacements.items():
            text = text.replace(old, new)

        # Entferne mehrfache Unterstriche
        while '__' in text:
            text = text.replace('__', '_')

        return text.strip('_')


class InfoDialog(QDialog):
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


class MapConfigTab(QWidget):
    """A tab for configuring individual map visualizations."""

    def __init__(self, ui, name=None, parent=None):
        """
        Initialize the MapConfigTab.

        Args:
            ui (UserInterface): Main UI reference.
            name (str, optional): Initial map name.
            parent (QWidget, optional): Parent widget.
        """
        super().__init__(parent)

        self.ui = ui
        self.iosystem = self.ui.iosystem
        self.general_dict = self.iosystem.index.general_dict
        self.name = name or self._get_text("Subcontractors", "Subcontractors")
        self.tab_widget = parent if isinstance(parent, QTabWidget) else None

        # Get world data if available
        if hasattr(self.iosystem.index, 'world'):
            self.world = self.iosystem.index.world
            self.world = self.world.to_crs(epsg=4326)
            self.world_sindex = self.world.sindex
        else:
            self.world = None
            self.world_sindex = None

        self._init_ui()

    def _get_text(self, key, fallback):
        """Get text from general_dict with fallback."""
        return self.general_dict.get(key, fallback)

    def _init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout(self)

        # Map selector
        selector_group = self._create_selector_group()
        layout.addWidget(selector_group)

        # Update button - positioned consistently
        self.update_button = QPushButton(self._get_text("Update Map", "Update Map"))
        self.update_button.clicked.connect(self.update_map)
        layout.addWidget(self.update_button)

        # Map canvas
        self.canvas = None
        self.map_area = QVBoxLayout()
        self._create_initial_map()
        layout.addLayout(self.map_area)

    def _create_selector_group(self):
        """Create the map selector group."""
        group = QGroupBox(self._get_text("Map Type", "Map Type"))
        layout = QVBoxLayout(group)

        self.selector = QComboBox()
        self.selector.addItem(self._get_text("Subcontractors", "Subcontractors"))
        self.selector.insertSeparator(self.selector.count())
        self.selector.addItems(self.iosystem.impacts)
        self.selector.setCurrentText(self.name)
        self.selector.currentTextChanged.connect(self._update_tab_name)
        layout.addWidget(self.selector)

        group.setMaximumHeight(100)
        return group

    def _create_initial_map(self):
        """Create initial placeholder map."""
        fig = plt.figure()
        ax = fig.add_subplot(111)
        ax.text(0.5, 0.5,
                self._get_text("Waiting for update…", "Waiting for update…"),
                horizontalalignment='center', verticalalignment='center',
                transform=ax.transAxes)
        ax.axis('off')

        self.canvas = FigureCanvas(fig)
        self._setup_canvas_context_menu()
        self.map_area.addWidget(self.canvas)

    def update_map(self):
        """Update the map based on selection."""
        QApplication.setOverrideCursor(Qt.WaitCursor)

        # Remove old canvas
        if self.canvas:
            self.map_area.removeWidget(self.canvas)
            self.canvas.setParent(None)
            self.canvas.deleteLater()

        try:
            self.choice = self.selector.currentText()

            if self.choice == self._get_text("Subcontractors", "Subcontractors"):
                fig, world = self.ui.supplychain.plot_worldmap_by_subcontractors(
                    color="Blues",
                    relative=True,
                    return_data=True,
                    title=None
                )
            else:
                fig, world = self.ui.supplychain.plot_worldmap_by_impact(
                    self.choice,
                    return_data=True,
                    title=None
                )

            # Update world data
            self.world = world
            if self.world is not None:
                self.world = self.world.to_crs(epsg=4326)
                self.world_sindex = self.world.sindex

            # Create new canvas
            self.canvas = FigureCanvas(fig)
            self.canvas.mpl_connect('motion_notify_event', self._on_hover)
            self.canvas.mpl_connect('button_press_event', self._on_click)
            self._setup_canvas_context_menu()
            self.map_area.addWidget(self.canvas)
            self.canvas.draw()

        except Exception as e:
            # Create error map
            fig = plt.figure()
            ax = fig.add_subplot(111)
            ax.text(0.5, 0.5, f"{self._get_text('Error', 'Error')}: {str(e)}",
                    horizontalalignment='center', verticalalignment='center',
                    transform=ax.transAxes)
            ax.axis('off')
            self.canvas = FigureCanvas(fig)
            self._setup_canvas_context_menu()
            self.map_area.addWidget(self.canvas)

        QApplication.restoreOverrideCursor()

    def _format_value(self, value):
        """Format value for display with appropriate precision."""
        try:
            val = float(value)
            if abs(val) >= 1000000:
                return f"{val:,.1f}"
            elif abs(val) >= 1000:
                return f"{val:,.2f}"
            elif abs(val) >= 1:
                return f"{val:.3f}"
            elif abs(val) >= 0.001:
                return f"{val:.6f}"
            else:
                return f"{val:.2e}"
        except (ValueError, TypeError):
            return str(value)

    def _on_hover(self, event):
        """Handle mouse hover events on the map."""
        if event.inaxes is None or self.world is None or self.world_sindex is None:
            QToolTip.hideText()
            return

        x, y = event.xdata, event.ydata
        if x is None or y is None:
            QToolTip.hideText()
            return

        pt = Point(x, y)
        possible_idxs = list(self.world_sindex.intersection((x, y, x, y)))

        if not possible_idxs:
            QToolTip.hideText()
            return

        # Find exact intersection
        country = None
        for idx in possible_idxs:
            if self.world.geometry.iloc[idx].contains(pt):
                country = self.world.iloc[idx]
                break

        if country is not None:
            value = country.get("value", 0)
            percentage = country.get("percentage", 0)

            value_str = self._format_value(value)
            percentage_str = self._format_value(percentage)

            text = (
                f'{self._get_text("Region", "Region")}: {country.get("region", "-")}\n'
                f'{self.choice}: {value_str} {country.get("unit", "-")}\n'
                f'{self._get_text("Global share", "Global share")}: {percentage_str} %'
            )

            QToolTip.showText(
                self.canvas.mapToGlobal(event.guiEvent.pos()),
                text,
                widget=self.canvas,
            )
        else:
            QToolTip.hideText()

    def _on_click(self, event):
        """Handle mouse click events on the map."""
        if event.inaxes is None or self.world is None or self.world_sindex is None:
            return

        x, y = event.xdata, event.ydata
        if x is None or y is None:
            return

        pt = Point(x, y)
        possible_idxs = list(self.world_sindex.intersection((x, y, x, y)))

        if not possible_idxs:
            return

        country = None
        for idx in possible_idxs:
            if self.world.geometry.iloc[idx].contains(pt):
                country = self.world.iloc[idx]
                break

        if country is not None:
            dialog = InfoDialog(ui=self.ui, country=country, choice=self.choice, parent=self)
            dialog.exec_()

    def _update_tab_name(self, text):
        """Update the tab name based on selection."""
        if self.tab_widget:
            idx = self.tab_widget.indexOf(self)
            if idx != -1:
                self.tab_widget.setTabText(idx, text)

    def _setup_canvas_context_menu(self):
        """Set up canvas context menu."""
        self.canvas.setContextMenuPolicy(Qt.CustomContextMenu)
        self.canvas.customContextMenuRequested.connect(self._show_context_menu)

    def _show_context_menu(self, pos):
        """Show context menu for saving."""
        menu = QMenu(self)
        save_action = menu.addAction(self._get_text("Save plot", "Save plot"))
        action = menu.exec_(self.canvas.mapToGlobal(pos))

        if action == save_action:
            self._save_map_high_quality()

    def _save_map_high_quality(self):
        """Save map with high quality and meaningful filename."""
        default_filename = self._generate_map_filename()

        # Setzt den Standardpfad auf den Benutzer-Download-Ordner
        home_dir = os.path.expanduser("~")
        download_dir = os.path.join(home_dir, "Downloads")
        if not os.path.exists(download_dir):
            download_dir = home_dir

        full_default_path = os.path.join(download_dir, default_filename)

        fname, _ = QFileDialog.getSaveFileName(
            self,
            self._get_text("Save plot", "Save plot"),
            full_default_path,
            f"{self._get_text('PNG Files', 'PNG-Dateien')} (*.png);;{self._get_text('PDF Files', 'PDF-Dateien')} (*.pdf);;{self._get_text('SVG Files', 'SVG-Dateien')} (*.svg)"
        )

        if fname:
            try:
                save_kwargs = {
                    'dpi': 600,  # Erhöhte DPI für höhere Qualität
                    'bbox_inches': 'tight',
                    'facecolor': 'white',
                    'edgecolor': 'none',
                    'transparent': False,
                    'pad_inches': 0.1
                }

                self.canvas.figure.savefig(fname, **save_kwargs)

                QMessageBox.information(
                    self,
                    self._get_text("Success", "Erfolg"),
                    f"{self._get_text('Map saved successfully', 'Karte erfolgreich gespeichert')}: {os.path.basename(fname)}"
                )
            except Exception as e:
                QMessageBox.warning(
                    self,
                    self._get_text("Error", "Fehler"),
                    f"{self._get_text('Error saving map', 'Fehler beim Speichern der Karte')}: {str(e)}"
                )

    def _generate_map_filename(self):
        """Generate meaningful default filename for maps."""
        # Basis-Name aus ausgewähltem Map-Typ
        base_name = f"Weltkarte_{self._clean_filename(self.choice)}"

        # Füge Zeitstempel hinzu
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        return f"{base_name}_{timestamp}.png"

    def _clean_filename(self, text):
        """Clean text for use in filenames."""
        # Ersetze problematische Zeichen
        replacements = {
            ' ': '_',
            '/': '_',
            '\\': '_',
            ':': '_',
            '*': '_',
            '?': '_',
            '"': '_',
            '<': '_',
            '>': '_',
            '|': '_',
            'ä': 'ae',
            'ö': 'oe',
            'ü': 'ue',
            'ß': 'ss',
            'Ä': 'Ae',
            'Ö': 'Oe',
            'Ü': 'Ue'
        }

        for old, new in replacements.items():
            text = text.replace(old, new)

        # Entferne mehrfache Unterstriche
        while '__' in text:
            text = text.replace('__', '_')

        return text.strip('_')


class WorldMapTab(QWidget):
    """Tab for managing multiple world map views with parallel tabs."""

    def __init__(self, ui, parent=None):
        """
        Initialize the WorldMapTab.

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

        # Create tab widget for multiple maps
        self.map_tabs = QTabWidget()
        self.map_tabs.setTabsClosable(True)
        self.map_tabs.tabCloseRequested.connect(self._on_tab_close_requested)
        self.map_tabs.tabBarClicked.connect(self._on_tab_clicked)

        # Add initial map and "+" tab
        self._add_map_tab()
        self._add_plus_tab()

        layout.addWidget(self.map_tabs)

    def _add_plus_tab(self):
        """Add the "+" tab for creating new maps."""
        plus_widget = QWidget()
        idx = self.map_tabs.addTab(plus_widget, "+")
        self._remove_close_button(idx)

    def _remove_close_button(self, tab_index):
        """Remove the close button for a specific tab."""
        # Remove the close button by setting it to None
        self.map_tabs.tabBar().setTabButton(tab_index, QTabBar.RightSide, None)
        self.map_tabs.tabBar().setTabButton(tab_index, QTabBar.LeftSide, None)

    def _on_tab_clicked(self, index):
        """Handle tab clicks - create new tab if "+" is clicked."""
        if index == self.map_tabs.count() - 1:  # "+" tab clicked
            self._add_map_tab()

    def _on_tab_close_requested(self, index):
        """Handle tab close requests."""
        content_count = self.map_tabs.count() - 1  # Exclude "+" tab

        # Don't allow closing if only one content tab left
        if content_count <= 1:
            return

        # Don't allow closing the "+" tab
        if index == self.map_tabs.count() - 1:
            return

        self.map_tabs.removeTab(index)

    def _add_map_tab(self):
        """Add a new map configuration tab."""
        new_tab = MapConfigTab(self.ui, parent=self.map_tabs)

        # Insert before "+" tab
        insert_at = self.map_tabs.count() - 1
        idx = self.map_tabs.insertTab(insert_at, new_tab, new_tab.name)

        # Set focus to new tab
        self.map_tabs.setCurrentIndex(idx)

        # Ensure the "+" tab doesn't have a close button
        plus_tab_index = self.map_tabs.count() - 1
        if plus_tab_index >= 0 and self.map_tabs.tabText(plus_tab_index) == "+":
            self._remove_close_button(plus_tab_index)