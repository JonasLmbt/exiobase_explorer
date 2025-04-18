import sys
from src.IOSystem import IOSystem
from src.SupplyChain import SupplyChain

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QTabWidget, QWidget, QVBoxLayout, QHBoxLayout,
    QGroupBox, QLabel, QComboBox, QPushButton, QSplitter, QTreeWidget,
    QTreeWidgetItem, QScrollArea, QSizePolicy
)
from PyQt5.QtCore import Qt

# Load database
database = IOSystem(year=2022, language="german").load()


def multiindex_to_nested_dict(multiindex: pd.MultiIndex) -> dict:
    root = {}
    for keys in multiindex:
        current = root
        for key in keys:
            current = current.setdefault(key, {})
    return root


class UserInterface(QMainWindow):
    def __init__(self):
        super().__init__()
        self.region_hierarchy = multiindex_to_nested_dict(
            database.Index.region_multiindex
        )
        self.sector_hierarchy = multiindex_to_nested_dict(
            database.Index.sector_multiindex_per_region
        )
        self.region_level_names = list(database.Index.region_multiindex.names)
        self.sector_level_names = list(database.Index.sector_multiindex_per_region.names)
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Exiobase Explorer")
        self.resize(800, 450)

        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)

        central_layout = QVBoxLayout(central_widget)
        central_layout.setContentsMargins(20, 20, 20, 20)
        central_layout.setSpacing(20)

        self.tab_widget = QTabWidget(self)
        self.create_selection_tab()
        self.create_additional_tab()
        central_layout.addWidget(self.tab_widget)

        self._create_menu_bar()
        self.show()

    def create_selection_tab(self):
        selection_tab = QWidget()
        selection_layout = QVBoxLayout(selection_tab)
        selection_layout.setSpacing(20)

        # === General Settings ===
        general_settings_group = QGroupBox("General Settings")
        gen_layout = QHBoxLayout(general_settings_group)
        self.language_combo = QComboBox()
        self.language_combo.addItems(["English", "Deutsch", "Français", "Español"])
        self.year_combo = QComboBox()
        self.year_combo.addItems(["2021", "2022", "2023", "2024"])
        gen_layout.addWidget(QLabel("Language:"))
        gen_layout.addWidget(self.language_combo)
        gen_layout.addWidget(QLabel("Year:"))
        gen_layout.addWidget(self.year_combo)
        selection_layout.addWidget(general_settings_group)

        # === Region/Sector Widget ===
        region_sector_widget = QWidget()
        rs_layout = QHBoxLayout(region_sector_widget)
        rs_layout.setSpacing(20)
        rs_layout.setContentsMargins(0, 0, 0, 0)

        def add_tree_items(parent, data, level=0):
            for key, val in data.items():
                item = QTreeWidgetItem(parent)
                item.setText(0, key)
                item.setData(0, Qt.UserRole, level)
                item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
                item.setCheckState(0, Qt.Unchecked)
                if isinstance(val, dict) and val:
                    add_tree_items(item, val, level + 1)

        # Region Tree
        region_group = QGroupBox("Region Selection")
        region_layout = QVBoxLayout(region_group)
        self.region_tree = QTreeWidget()
        self.region_tree.setHeaderHidden(True)
        self.region_tree.setSelectionMode(QTreeWidget.NoSelection)
        add_tree_items(self.region_tree, self.region_hierarchy)
        self.region_tree.itemChanged.connect(self.on_region_item_changed)
        region_layout.addWidget(self.region_tree)

        # Region Button Layout
        region_button_row = QWidget()
        region_button_layout = QHBoxLayout(region_button_row)
        region_button_layout.setContentsMargins(0, 0, 0, 0)
        region_button_layout.setSpacing(10)

        btn_select_all_region = QPushButton("Select All Regions")
        btn_clear_region = QPushButton("Clear Region Selection")
        btn_select_all_region.clicked.connect(self.select_all_regions)
        btn_clear_region.clicked.connect(self.clear_region_selection)

        for btn in [btn_select_all_region, btn_clear_region]:
            btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            region_button_layout.addWidget(btn)

        region_layout.addWidget(region_button_row)

        # Sector Tree
        sector_group = QGroupBox("Sector Selection")
        sector_layout = QVBoxLayout(sector_group)
        self.sector_tree = QTreeWidget()
        self.sector_tree.setHeaderHidden(True)
        self.sector_tree.setSelectionMode(QTreeWidget.NoSelection)
        add_tree_items(self.sector_tree, self.sector_hierarchy)
        self.sector_tree.itemChanged.connect(self.on_sector_item_changed)
        sector_layout.addWidget(self.sector_tree)

        # Sector Button Layout
        sector_button_row = QWidget()
        sector_button_layout = QHBoxLayout(sector_button_row)
        sector_button_layout.setContentsMargins(0, 0, 0, 0)
        sector_button_layout.setSpacing(10)

        btn_select_all_sector = QPushButton("Select All Sectors")
        btn_clear_sector = QPushButton("Clear Sector Selection")
        btn_select_all_sector.clicked.connect(self.select_all_sectors)
        btn_clear_sector.clicked.connect(self.clear_sector_selection)

        for btn in [btn_select_all_sector, btn_clear_sector]:
            btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            sector_button_layout.addWidget(btn)

        sector_layout.addWidget(sector_button_row)

        rs_layout.addWidget(region_group)
        rs_layout.addWidget(sector_group)

        # === Bottom Widget ===
        bottom_widget = QWidget()
        bottom_layout = QVBoxLayout(bottom_widget)
        bottom_layout.setSpacing(10)
        bottom_layout.setContentsMargins(0, 0, 0, 0)

        self.summary_group = QGroupBox("Selection Summary")
        summary_layout = QVBoxLayout(self.summary_group)
        self.selection_label = QLabel("No selection made")
        self.selection_label.setWordWrap(True)
        summary_scroll = QScrollArea()
        summary_scroll.setWidgetResizable(True)
        summary_scroll.setWidget(self.selection_label)
        summary_layout.addWidget(summary_scroll)
        bottom_layout.addWidget(self.summary_group)

        btn_layout = QHBoxLayout()
        self.apply_button = QPushButton("Apply Selection")
        self.apply_button.clicked.connect(self.apply_selection)
        self.reset_button = QPushButton("Reset All Selections")
        self.reset_button.clicked.connect(self.reset_selection)
        btn_layout.addWidget(self.apply_button)
        btn_layout.addWidget(self.reset_button)
        bottom_layout.addLayout(btn_layout)

        splitter = QSplitter(Qt.Vertical)
        splitter.setContentsMargins(0, 0, 0, 0)
        splitter.addWidget(region_sector_widget)
        splitter.addWidget(bottom_widget)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)

        selection_layout.addWidget(splitter)
        self.tab_widget.addTab(selection_tab, "Selection")

    def create_additional_tab(self):
        additional_tab = QWidget()
        additional_layout = QVBoxLayout(additional_tab)

        inner_tab_widget = QTabWidget()

        # Matplotlib Integration in "Table" tab
        table_tab = QWidget()
        table_layout = QVBoxLayout(table_tab)

        fig, ax = plt.subplots()
        ax.plot([0, 1, 2, 3], [10, 1, 20, 3])
        ax.set_title("Sample Plot")

        from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
        canvas = FigureCanvas(fig)
        table_layout.addWidget(canvas)

        inner_tab_widget.addTab(table_tab, "Table")
        inner_tab_widget.addTab(QLabel("This is inner tab 2 content."), "World Map")

        additional_layout.addWidget(inner_tab_widget)
        self.tab_widget.addTab(additional_tab, "Visualization")

    def propagate_down(self, item, state):
        for i in range(item.childCount()):
            child = item.child(i)
            child.setCheckState(0, state)
            self.propagate_down(child, state)

    def on_region_item_changed(self, item, column):
        state = item.checkState(column)
        self.region_tree.blockSignals(True)
        self.propagate_down(item, state)
        self.region_tree.blockSignals(False)
        self.update_summary()

    def on_sector_item_changed(self, item, column):
        state = item.checkState(column)
        self.sector_tree.blockSignals(True)
        self.propagate_down(item, state)
        self.sector_tree.blockSignals(False)
        self.update_summary()

    def clear_region_selection(self):
        root = self.region_tree.invisibleRootItem()
        for i in range(root.childCount()):
            parent = root.child(i)
            parent.setCheckState(0, Qt.Unchecked)
            self.propagate_down(parent, Qt.Unchecked)
        self.update_summary()

    def clear_sector_selection(self):
        root = self.sector_tree.invisibleRootItem()
        for i in range(root.childCount()):
            parent = root.child(i)
            parent.setCheckState(0, Qt.Unchecked)
            self.propagate_down(parent, Qt.Unchecked)
        self.update_summary()

    def _collect_highest_level(self, item, result):
        if item.checkState(0) == Qt.Checked:
            level = item.data(0, Qt.UserRole)
            name = item.text(0)
            result.append((level, name))
        else:
            for i in range(item.childCount()):
                self._collect_highest_level(item.child(i), result)

    def get_checked_regions(self):
        checked = []
        root = self.region_tree.invisibleRootItem()
        for i in range(root.childCount()):
            self._collect_highest_level(root.child(i), checked)
        return checked

    def get_checked_sectors(self):
        checked = []
        root = self.sector_tree.invisibleRootItem()
        for i in range(root.childCount()):
            self._collect_highest_level(root.child(i), checked)
        return checked

    def apply_selection(self):
        lang = self.language_combo.currentText()
        yr = self.year_combo.currentText()
        regions = self.get_checked_regions()
        sectors = self.get_checked_sectors()
        region_strings = [f"{self.region_level_names[level]}: {name}" for level, name in regions]
        sector_strings = [f"{self.sector_level_names[level]}: {name}" for level, name in sectors]

        if not regions:
            region_strings = ["The whole world will be considered."]
        elif len(regions) == len(self.region_hierarchy):
            region_strings = ["All regions selected, will consider the entire region set."]

        if not sectors:
            sector_strings = ["All sectors will be used."]
        elif len(sectors) == len(self.sector_hierarchy):
            sector_strings = ["All sectors selected, will consider the entire sector set."]

        summary_text = (
            f"Language: {lang}\nYear: {yr}\n\n"
            f"Regions:\n" + "\n".join(region_strings) + "\n\n"
            f"Sectors:\n" + "\n".join(sector_strings)
        )
        self.selection_label.setText(summary_text)

    def reset_selection(self):
        self.clear_region_selection()
        self.clear_sector_selection()
        self.language_combo.setCurrentIndex(0)
        self.year_combo.setCurrentIndex(0)
        self.selection_label.setText("No selection made")

    def update_summary(self):
        self.apply_selection()

    def select_all_regions(self):
        root = self.region_tree.invisibleRootItem()
        for i in range(root.childCount()):
            parent = root.child(i)
            parent.setCheckState(0, Qt.Checked)
            self.propagate_down(parent, Qt.Checked)
        self.update_summary()

    def select_all_sectors(self):
        root = self.sector_tree.invisibleRootItem()
        for i in range(root.childCount()):
            parent = root.child(i)
            parent.setCheckState(0, Qt.Checked)
            self.propagate_down(parent, Qt.Checked)
        self.update_summary()

    def _create_menu_bar(self):
        pass


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = UserInterface()
    sys.exit(app.exec_())
