from src.IOSystem import IOSystem
from src.SupplyChain import SupplyChain

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

import sys
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QTabWidget, QWidget, QVBoxLayout, QHBoxLayout,
    QGroupBox, QLabel, QComboBox, QPushButton, QSplitter, QTreeWidget,
    QTreeWidgetItem, QScrollArea
)
from PyQt5.QtCore import Qt

database = IOSystem(year=2022, language="german").load()

def multiindex_to_nested_dict(multiindex: pd.MultiIndex) -> dict:
    """Convert a MultiIndex to a nested dictionary for hierarchical QTreeWidget use."""
    root = {}
    for keys in multiindex:
        current = root
        for key in keys:
            current = current.setdefault(key, {})
    return root

sector_hierarchy = multiindex_to_nested_dict(database.Index.sector_multiindex_per_region)
region_hierarchy = multiindex_to_nested_dict(database.Index.region_multiindex)

class UserInterface(QMainWindow):
    def __init__(self):
        super().__init__()
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

        # Helper: recurisve add for nested dict
        def add_tree_items(parent, data):
            for key, val in data.items():
                item = QTreeWidgetItem(parent)
                item.setText(0, key)
                item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
                item.setCheckState(0, Qt.Unchecked)
                if isinstance(val, dict) and val:
                    add_tree_items(item, val)

        # Region Selection with QTreeWidget via nested dict
        region_group = QGroupBox("Region Selection")
        region_layout = QVBoxLayout(region_group)
        self.region_tree = QTreeWidget()
        self.region_tree.setHeaderHidden(True)

        # Nested dict for regions
        add_tree_items(self.region_tree, region_hierarchy)
        self.region_tree.itemChanged.connect(self.on_region_item_changed)

        region_layout.addWidget(self.region_tree)
        btn_clear_region = QPushButton("Clear Region Selection")
        btn_clear_region.clicked.connect(self.clear_region_selection)
        region_layout.addWidget(btn_clear_region)

        # Sector Selection with hierarchical QTreeWidget
        sector_group = QGroupBox("Sector Selection")
        sector_layout = QVBoxLayout(sector_group)
        self.sector_tree = QTreeWidget()
        self.sector_tree.setHeaderHidden(True)

        # Nested dict for sectors
        add_tree_items(self.sector_tree, sector_hierarchy)
        self.sector_tree.itemChanged.connect(self.on_sector_item_changed)

        sector_layout.addWidget(self.sector_tree)
        btn_clear_sector = QPushButton("Clear Sector Selection")
        btn_clear_sector.clicked.connect(self.clear_sector_selection)
        sector_layout.addWidget(btn_clear_sector)

        rs_layout.addWidget(region_group)
        rs_layout.addWidget(sector_group)

        # === Bottom Widget (Summary + Buttons) ===
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

    def get_checked_regions(self):
        checked = []
        root = self.region_tree.invisibleRootItem()
        for i in range(root.childCount()):
            cont = root.child(i)
            self._collect_checked(cont, checked)
        return checked

    def get_checked_sectors(self):
        checked = []
        root = self.sector_tree.invisibleRootItem()
        for i in range(root.childCount()):
            sect = root.child(i)
            self._collect_checked(sect, checked)
        return checked

    def _collect_checked(self, item, result_list):
        # only leaf nodes
        if item.childCount() == 0 and item.checkState(0) == Qt.Checked:
            result_list.append(item.text(0))
        for i in range(item.childCount()):
            self._collect_checked(item.child(i), result_list)

    def apply_selection(self):
        lang = self.language_combo.currentText()
        yr = self.year_combo.currentText()
        regions = self.get_checked_regions()
        sectors = self.get_checked_sectors()
        self.selection_label.setText(
            f"Selection applied!<br><b>Language:</b> {lang}, <b>Year:</b> {yr}<br>"
            f"<b>Regions:</b> {', '.join(regions)}<br>"
            f"<b>Sectors:</b> {', '.join(sectors)}"
        )
        self.summary_group.setTitle("Selection Summary (saved)")

    def reset_selection(self):
        self.clear_region_selection()
        self.clear_sector_selection()
        self.selection_label.setText("No selection made")
        self.summary_group.setTitle("Selection Summary")

    def update_summary(self):
        regions = self.get_checked_regions()
        sectors = self.get_checked_sectors()
        if not regions and not sectors:
            self.selection_label.setText("No selection made")
        else:
            txt = ""
            if regions:
                txt += f"<b>Regions:</b> {', '.join(regions)}<br>"
            if sectors:
                txt += f"<b>Sectors:</b> {', '.join(sectors)}"
            self.selection_label.setText(txt)

    def _create_menu_bar(self):
        self.menuBar()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = UserInterface()
    sys.exit(app.exec_())
