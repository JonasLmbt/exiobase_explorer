import numpy as np
import pandas as pd

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QGroupBox, QLabel, QPushButton, QSplitter, QTreeWidget,
    QTreeWidgetItem, QScrollArea, QCheckBox,
)
from PyQt5.QtCore import Qt

def multiindex_to_nested_dict(multiindex: pd.MultiIndex) -> dict:
    root = {}
    for keys in multiindex:
        current = root
        for key in keys:
            current = current.setdefault(key, {})
    return root

class SelectionTab(QWidget):
    def __init__(self, database):
        super().__init__()
        self.database = database
        self.region_hierarchy = multiindex_to_nested_dict(database.Index.region_multiindex)
        self.sector_hierarchy = multiindex_to_nested_dict(database.Index.sector_multiindex_per_region)
        self.region_level_names = list(database.Index.region_multiindex.names)
        self.sector_level_names = list(database.Index.sector_multiindex_per_region.names)
        self.region_indices = []
        self.sector_indices = []
        self.indices = []
        self.init_ui()
    
    def set_parent_ui(self, ui):
        self.ui = ui

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(20)

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

        # Region tree
        region_group = QGroupBox("Region Selection")
        region_layout = QVBoxLayout(region_group)
        self.region_tree = QTreeWidget()
        self.region_tree.setHeaderHidden(True)
        self.region_tree.setSelectionMode(QTreeWidget.NoSelection)  # Keine Auswahl möglich
        add_tree_items(self.region_tree, self.region_hierarchy)
        self.region_tree.itemChanged.connect(self.on_region_item_changed)
        region_layout.addWidget(self.region_tree)

        region_button_layout = QHBoxLayout()
        btn_clear_region = QPushButton("Clear Region Selection")
        btn_select_all_regions = QPushButton("Select All Regions")
        btn_clear_region.clicked.connect(self.clear_region_selection)
        btn_select_all_regions.clicked.connect(self.select_all_regions)
        region_button_layout.addWidget(btn_clear_region)
        region_button_layout.addWidget(btn_select_all_regions)
        region_layout.addLayout(region_button_layout)

        # Sector tree
        sector_group = QGroupBox("Sector Selection")
        sector_layout = QVBoxLayout(sector_group)
        self.sector_tree = QTreeWidget()
        self.sector_tree.setHeaderHidden(True)
        self.sector_tree.setSelectionMode(QTreeWidget.NoSelection)  # Keine Auswahl möglich
        add_tree_items(self.sector_tree, self.sector_hierarchy)
        self.sector_tree.itemChanged.connect(self.on_sector_item_changed)
        sector_layout.addWidget(self.sector_tree)

        sector_button_layout = QHBoxLayout()
        btn_clear_sector = QPushButton("Clear Sector Selection")
        btn_select_all_sectors = QPushButton("Select All Sectors")
        btn_clear_sector.clicked.connect(self.clear_sector_selection)
        btn_select_all_sectors.clicked.connect(self.select_all_sectors)
        sector_button_layout.addWidget(btn_clear_sector)
        sector_button_layout.addWidget(btn_select_all_sectors)
        sector_layout.addLayout(sector_button_layout)

        # Standard Button Style
        button_style = "QPushButton { padding: 6px 12px; }"
        for btn in [btn_clear_region, btn_select_all_regions, btn_clear_sector, btn_select_all_sectors]:
            btn.setStyleSheet(button_style)

        rs_layout.addWidget(region_group)
        rs_layout.addWidget(sector_group)
        layout.addWidget(region_sector_widget)

        # Bottom widget for summary and apply/reset
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
        self.reset_button = QPushButton("Reset All Selections")
        self.apply_button.clicked.connect(self.apply_selection)
        self.reset_button.clicked.connect(self.reset_selection)
        btn_layout.addWidget(self.apply_button)
        btn_layout.addWidget(self.reset_button)

        for btn in [self.apply_button, self.reset_button]:
            btn.setStyleSheet(button_style)

        bottom_layout.addLayout(btn_layout)

        # Splitter for resizing
        splitter = QSplitter(Qt.Vertical)
        splitter.addWidget(region_sector_widget)
        splitter.addWidget(bottom_widget)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)
        layout.addWidget(splitter)

    def propagate_down(self, item, state):
        for i in range(item.childCount()):
            child = item.child(i)
            child.setCheckState(0, state)
            self.propagate_down(child, state)

    def on_region_item_changed(self, item, column):
        self.region_tree.blockSignals(True)
        self.propagate_down(item, item.checkState(column))
        self.region_tree.blockSignals(False)

    def on_sector_item_changed(self, item, column):
        self.sector_tree.blockSignals(True)
        self.propagate_down(item, item.checkState(column))
        self.sector_tree.blockSignals(False)

    def clear_region_selection(self):
        root = self.region_tree.invisibleRootItem()
        for i in range(root.childCount()):
            node = root.child(i)
            node.setCheckState(0, Qt.Unchecked)
            self.propagate_down(node, Qt.Unchecked)

    def clear_sector_selection(self):
        root = self.sector_tree.invisibleRootItem()
        for i in range(root.childCount()):
            node = root.child(i)
            node.setCheckState(0, Qt.Unchecked)
            self.propagate_down(node, Qt.Unchecked)

    def select_all_regions(self):
        root = self.region_tree.invisibleRootItem()
        for i in range(root.childCount()):
            node = root.child(i)
            node.setCheckState(0, Qt.Checked)
            self.propagate_down(node, Qt.Checked)

    def select_all_sectors(self):
        root = self.sector_tree.invisibleRootItem()
        for i in range(root.childCount()):
            node = root.child(i)
            node.setCheckState(0, Qt.Checked)
            self.propagate_down(node, Qt.Checked)

    def _collect_highest_level(self, item, result):
        if item.checkState(0) == Qt.Checked:
            result.append((item.data(0, Qt.UserRole), item.text(0)))
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
        regions = self.get_checked_regions()
        sectors = self.get_checked_sectors()
        mi_r = self.database.Index.region_multiindex
        mi_s = self.database.Index.sector_multiindex_per_region
        region_idx = set()
        for level, name in regions:
            mask = mi_r.get_level_values(level) == name
            region_idx.update(np.where(mask)[0])
        sector_idx = set()
        for level, name in sectors:
            mask = mi_s.get_level_values(level) == name
            sector_idx.update(np.where(mask)[0])
        self.region_indices = sorted(region_idx)
        self.sector_indices = sorted(sector_idx)
        region_strings = [f"{self.region_level_names[level]}: {name}" for level, name in regions]
        sector_strings = [f"{self.sector_level_names[level]}: {name}" for level, name in sectors]
        
        txt = ""
        
        # Handle region selection summary
        txt += "<b>Regions:</b><br>"
        if len(self.region_indices) == 0:
            txt += "No regions selected.<br><br>"
        elif len(self.region_indices) == len(mi_r):
            txt += "All regions selected (Global view).<br><br>"
        else:
            txt += ", ".join(region_strings)
            txt += f"<br><i>Region indices count:</i> {len(self.region_indices)}<br><br>"

        # Handle sector selection summary
        txt += "<b>Sectors:</b><br>"
        if len(self.sector_indices) == 0:
            txt += "No sectors selected.<br><br>"
        elif len(self.sector_indices) == len(mi_s):
            txt += "All sectors selected (Global view).<br><br>"
        else:
            txt += ", ".join(sector_strings)
            txt += f"<br><i>Sector indices count:</i> {len(self.sector_indices)}<br><br>"

        # Calculate indices
        self.indices = []
        if region_strings and sector_strings:
            for region in self.region_indices:
                for sector in self.sector_indices:
                    self.indices.append(int(region) * len(self.database.sectors) + int(sector))
        elif region_strings:
            for region in self.region_indices:
                for sector in range(len(self.database.sectors)): # All sectors
                    self.indices.append(int(region) * len(self.database.sectors) + int(sector))
        elif sector_strings:
            for region in range(len(self.database.regions)): # All regions
                for sector in self.sector_indices:
                    self.indices.append(int(region) * len(self.database.sectors) + int(sector))
        else: # World
            self.indices = [index for index in range(9800)]

        # Handle indices display if checkbox is checked
        if self.ui.settings_tab.is_show_indices_active():
            txt += f"<b>Indices ({len(self.indices)}):</b> {self.indices}<br><br>"

        self.selection_label.setText(txt)
        self.summary_group.setTitle("Selection Summary (saved)")

    def reset_selection(self):
        self.clear_region_selection()
        self.clear_sector_selection()
        self.selection_label.setText("No selection made")
        self.summary_group.setTitle("Selection Summary")