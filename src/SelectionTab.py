import numpy as np
import pandas as pd

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QGroupBox, QLabel, QPushButton, QSplitter, QTreeWidget,
    QTreeWidgetItem, QScrollArea, 
)
from PyQt5.QtCore import Qt

def multiindex_to_nested_dict(multiindex: pd.MultiIndex) -> dict:
    """Convert a MultiIndex to a nested dictionary for hierarchical QTreeWidget use."""
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
        self.region_hierarchy = multiindex_to_nested_dict(
            database.Index.region_multiindex
        )
        self.sector_hierarchy = multiindex_to_nested_dict(
            database.Index.sector_multiindex_per_region
        )
        self.region_level_names = list(database.Index.region_multiindex.names)
        self.sector_level_names = list(database.Index.sector_multiindex_per_region.names)
        self.region_indices = []
        self.sector_indices = []
        self.indices = []
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(20)

        # Region and Sector Selection
        region_sector_widget = QWidget()
        rs_layout = QHBoxLayout(region_sector_widget)
        rs_layout.setSpacing(20)
        rs_layout.setContentsMargins(0, 0, 0, 0)

        # Helper to add tree
        def add_tree_items(parent, data, level=0):
            for key, val in data.items():
                item = QTreeWidgetItem(parent)
                item.setText(0, key)
                item.setData(0, Qt.UserRole, level)
                item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
                item.setCheckState(0, Qt.Unchecked)
                if isinstance(val, dict) and val:
                    add_tree_items(item, val, level+1)

        # Region Tree
        region_group = QGroupBox("Region Selection")
        region_layout = QVBoxLayout(region_group)
        self.region_tree = QTreeWidget()
        self.region_tree.setHeaderHidden(True)
        add_tree_items(self.region_tree, self.region_hierarchy)
        self.region_tree.itemChanged.connect(self.on_region_item_changed)
        region_layout.addWidget(self.region_tree)
        btn_clear_region = QPushButton("Clear Region Selection")
        btn_clear_region.clicked.connect(self.clear_region_selection)
        region_layout.addWidget(btn_clear_region)

        # Sector Tree
        sector_group = QGroupBox("Sector Selection")
        sector_layout = QVBoxLayout(sector_group)
        self.sector_tree = QTreeWidget()
        self.sector_tree.setHeaderHidden(True)
        add_tree_items(self.sector_tree, self.sector_hierarchy)
        self.sector_tree.itemChanged.connect(self.on_sector_item_changed)
        sector_layout.addWidget(self.sector_tree)
        btn_clear_sector = QPushButton("Clear Sector Selection")
        btn_clear_sector.clicked.connect(self.clear_sector_selection)
        sector_layout.addWidget(btn_clear_sector)

        rs_layout.addWidget(region_group)
        rs_layout.addWidget(sector_group)
        layout.addWidget(region_sector_widget)

        # Bottom summary and buttons
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
        splitter.addWidget(region_sector_widget)
        splitter.addWidget(bottom_widget)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)
        layout.addWidget(splitter)

    # Tree selection propagation and summary logic
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
        for level,name in regions:
            mask = mi_r.get_level_values(level)==name
            region_idx.update(np.where(mask)[0])
        sector_idx = set()
        for level,name in sectors:
            mask = mi_s.get_level_values(level)==name
            sector_idx.update(np.where(mask)[0])
        self.region_indices = sorted(region_idx)
        self.sector_indices = sorted(sector_idx)
        # build summary text
        region_strings = [f"{self.region_level_names[level]}: {name}" for level, name in regions]
        sector_strings = [f"{self.sector_level_names[level]}: {name}" for level, name in sectors]
        txt = f"Selection applied!"  
        if region_strings:
            txt += "<br>" + ", ".join(region_strings)
            txt += f"<br><i>Region indices count:</i> {len(self.region_indices)}"
        if sector_strings:
            txt += "<br>" + ", ".join(sector_strings)
            txt += f"<br><i>Sector indices count:</i> {len(self.sector_indices)}"
        if region_strings and sector_strings:
            self.indices = []
            for region in self.region_indices:
                for sector in self.sector_indices:
                    self.indices.append(int(region)*200+int(sector))
            txt += f"<br><b>Indices ({len(self.indices)}):</b> {self.indices}"
        self.selection_label.setText(txt)
        self.summary_group.setTitle("Selection Summary (saved)")

    def reset_selection(self):
        self.clear_region_selection()
        self.clear_sector_selection()
        self.selection_label.setText("No selection made")
        self.summary_group.setTitle("Selection Summary")