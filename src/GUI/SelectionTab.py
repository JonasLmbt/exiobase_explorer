import numpy as np
import pandas as pd

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QGroupBox, QLabel, QPushButton, QSplitter, QTreeWidget,
    QTreeWidgetItem, QScrollArea, QSizePolicy
)
from PyQt5.QtCore import Qt


def multiindex_to_nested_dict(multiindex: pd.MultiIndex) -> dict:
    """Convert a MultiIndex to a nested dictionary structure."""
    root = {}
    for keys in multiindex:
        current = root
        for key in keys:
            current = current.setdefault(key, {})
    return root


class SelectionTab(QWidget):
    """
    The SelectionTab class manages the selection of regions and sectors.
    """

    def __init__(self, ui):
        """
        Initialize the SelectionTab.

        Args:
            ui (UserInterface): The parent user interface instance.
        """
        super().__init__()

        # Store references
        self.ui = ui
        self.iosystem = self.ui.iosystem
        self.general_dict = self.iosystem.index.general_dict

        # Convert multiindices to nested dictionaries
        self.region_hierarchy = multiindex_to_nested_dict(self.iosystem.index.region_multiindex)
        self.sector_hierarchy = multiindex_to_nested_dict(self.iosystem.index.sector_multiindex_per_region)

        # Get level names
        self.region_level_names = list(self.iosystem.index.region_multiindex.names)
        self.sector_level_names = list(self.iosystem.index.sector_multiindex_per_region.names)

        # Initialize indices lists
        self.region_indices = []
        self.sector_indices = []
        self.indices = list(range(9800))  # Default: all indices
        self.inputByIndices = False
        self.kwargs = {}

        # Initialize UI
        self.init_ui()

    def _translate(self, key, fallback):
        """Get text from general_dict with fallback."""
        return self.general_dict.get(key, fallback)

    def init_ui(self):
        """Initialize the user interface components."""
        layout = QVBoxLayout(self)

        # Create main splitter for flexible layout
        main_splitter = QSplitter(Qt.Vertical)

        # Top section: Region and Sector selection with horizontal splitter
        selection_splitter = QSplitter(Qt.Horizontal)

        # Region selection
        region_widget = self._create_region_widget()
        selection_splitter.addWidget(region_widget)

        # Sector selection
        sector_widget = self._create_sector_widget()
        selection_splitter.addWidget(sector_widget)

        # Set equal initial sizes for region and sector selection
        selection_splitter.setSizes([400, 400])
        selection_splitter.setStretchFactor(0, 1)
        selection_splitter.setStretchFactor(1, 1)

        main_splitter.addWidget(selection_splitter)

        # Bottom section: Summary
        summary_widget = self._create_summary_widget()
        main_splitter.addWidget(summary_widget)

        # Set stretch factors (selection area gets more space than summary)
        main_splitter.setStretchFactor(0, 3)
        main_splitter.setStretchFactor(1, 1)

        layout.addWidget(main_splitter)

    def _create_region_widget(self):
        """Create the region selection widget."""
        region_group = QGroupBox(self._translate("Region Selection", "Region Selection"))
        layout = QVBoxLayout(region_group)

        # Region tree with scroll area for long lists
        self.region_tree = QTreeWidget()
        self.region_tree.setHeaderHidden(True)
        self.region_tree.setSelectionMode(QTreeWidget.NoSelection)

        # Set size policy to allow flexible resizing
        self.region_tree.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self._populate_tree(self.region_tree, self.region_hierarchy, collapsed=True)
        self.region_tree.itemChanged.connect(self._on_region_item_changed)
        layout.addWidget(self.region_tree)

        # Region buttons
        button_layout = QHBoxLayout()
        clear_btn = QPushButton(self._translate("Clear", "Clear"))
        select_all_btn = QPushButton(self._translate("Select All", "Select All"))
        clear_btn.clicked.connect(self.clear_region_selection)
        select_all_btn.clicked.connect(self.select_all_regions)

        # Set reasonable button sizes
        clear_btn.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        select_all_btn.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)

        button_layout.addWidget(clear_btn)
        button_layout.addWidget(select_all_btn)
        layout.addLayout(button_layout)

        return region_group

    def _create_sector_widget(self):
        """Create the sector selection widget."""
        sector_group = QGroupBox(self._translate("Sector Selection", "Sector Selection"))
        layout = QVBoxLayout(sector_group)

        # Sector tree with scroll area for long lists
        self.sector_tree = QTreeWidget()
        self.sector_tree.setHeaderHidden(True)
        self.sector_tree.setSelectionMode(QTreeWidget.NoSelection)

        # Set size policy to allow flexible resizing
        self.sector_tree.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self._populate_tree(self.sector_tree, self.sector_hierarchy, collapsed=True)
        self.sector_tree.itemChanged.connect(self._on_sector_item_changed)
        layout.addWidget(self.sector_tree)

        # Sector buttons
        button_layout = QHBoxLayout()
        clear_btn = QPushButton(self._translate("Clear", "Clear"))
        select_all_btn = QPushButton(self._translate("Select All", "Select All"))
        clear_btn.clicked.connect(self.clear_sector_selection)
        select_all_btn.clicked.connect(self.select_all_sectors)

        # Set reasonable button sizes
        clear_btn.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        select_all_btn.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)

        button_layout.addWidget(clear_btn)
        button_layout.addWidget(select_all_btn)
        layout.addLayout(button_layout)

        return sector_group

    def _create_summary_widget(self):
        """Create the selection summary widget."""
        self.summary_group = QGroupBox(self._translate("Selection Summary", "Selection Summary"))
        layout = QVBoxLayout(self.summary_group)

        # Summary label in scroll area for long text
        self.selection_label = QLabel(self._translate("No selection made", "No selection made"))
        self.selection_label.setWordWrap(True)
        self.selection_label.setAlignment(Qt.AlignTop)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self.selection_label)
        layout.addWidget(scroll)

        # Action buttons
        button_layout = QHBoxLayout()
        self.apply_button = QPushButton(self._translate("Apply Selection", "Apply Selection"))
        self.reset_button = QPushButton(self._translate("Reset All Selections", "Reset All Selections"))

        # Set button size policies
        self.apply_button.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        self.reset_button.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)

        self.apply_button.clicked.connect(self.apply_selection)
        self.reset_button.clicked.connect(self.reset_selection)
        button_layout.addWidget(self.apply_button)
        button_layout.addWidget(self.reset_button)
        layout.addLayout(button_layout)

        return self.summary_group

    def _populate_tree(self, tree, data, collapsed=False):
        """Populate tree widget with hierarchical data."""

        def add_items(parent, data_dict, level=0):
            for key, val in data_dict.items():
                item = QTreeWidgetItem(parent)
                item.setText(0, key)
                item.setData(0, Qt.UserRole, level)
                item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
                item.setCheckState(0, Qt.Unchecked)
                if isinstance(val, dict) and val:
                    add_items(item, val, level + 1)

        add_items(tree, data)

        # Set initial expansion state
        if collapsed:
            tree.collapseAll()
        else:
            # Expand first level by default for better UX
            tree.expandToDepth(0)

    def _propagate_down(self, item, state):
        """Propagate check state down to all children."""
        for i in range(item.childCount()):
            child = item.child(i)
            child.setCheckState(0, state)
            self._propagate_down(child, state)

    def _on_region_item_changed(self, item, column):
        """Handle region item check state change."""
        self.region_tree.blockSignals(True)
        self._propagate_down(item, item.checkState(column))
        self.region_tree.blockSignals(False)

    def _on_sector_item_changed(self, item, column):
        """Handle sector item check state change."""
        self.sector_tree.blockSignals(True)
        self._propagate_down(item, item.checkState(column))
        self.sector_tree.blockSignals(False)

    def clear_region_selection(self):
        """Clear all region selections."""
        root = self.region_tree.invisibleRootItem()
        for i in range(root.childCount()):
            node = root.child(i)
            node.setCheckState(0, Qt.Unchecked)
            self._propagate_down(node, Qt.Unchecked)

    def clear_sector_selection(self):
        """Clear all sector selections."""
        root = self.sector_tree.invisibleRootItem()
        for i in range(root.childCount()):
            node = root.child(i)
            node.setCheckState(0, Qt.Unchecked)
            self._propagate_down(node, Qt.Unchecked)

    def select_all_regions(self):
        """Select all regions."""
        root = self.region_tree.invisibleRootItem()
        for i in range(root.childCount()):
            node = root.child(i)
            node.setCheckState(0, Qt.Checked)
            self._propagate_down(node, Qt.Checked)

    def select_all_sectors(self):
        """Select all sectors."""
        root = self.sector_tree.invisibleRootItem()
        for i in range(root.childCount()):
            node = root.child(i)
            node.setCheckState(0, Qt.Checked)
            self._propagate_down(node, Qt.Checked)

    def _collect_checked_items(self, item, result):
        """Recursively collect checked items."""
        if item.checkState(0) == Qt.Checked:
            result.append((item.data(0, Qt.UserRole), item.text(0)))
        else:
            for i in range(item.childCount()):
                self._collect_checked_items(item.child(i), result)

    def get_checked_regions(self):
        """Get all checked regions."""
        checked = []
        root = self.region_tree.invisibleRootItem()
        for i in range(root.childCount()):
            self._collect_checked_items(root.child(i), checked)
        return checked

    def get_checked_sectors(self):
        """Get all checked sectors."""
        checked = []
        root = self.sector_tree.invisibleRootItem()
        for i in range(root.childCount()):
            self._collect_checked_items(root.child(i), checked)
        return checked

    def apply_selection(self):
        """Apply the current selection and update indices."""
        regions = self.get_checked_regions()
        sectors = self.get_checked_sectors()

        # Get multiindex structures
        mi_r = self.iosystem.index.region_multiindex
        mi_s = self.iosystem.index.sector_multiindex_per_region

        # Calculate indices
        region_idx = set()
        sector_idx = set()

        for level, name in regions:
            mask = mi_r.get_level_values(level) == name
            region_idx.update(np.where(mask)[0])

        for level, name in sectors:
            mask = mi_s.get_level_values(level) == name
            sector_idx.update(np.where(mask)[0])

        self.region_indices = sorted(region_idx)
        self.sector_indices = sorted(sector_idx)

        # Build summary text
        region_strings = [f"{self.region_level_names[level]}: {name}" for level, name in regions]
        sector_strings = [f"{self.sector_level_names[level]}: {name}" for level, name in sectors]

        summary_text = self._build_summary_text(region_strings, sector_strings)
        self.selection_label.setText(summary_text)

        # Calculate final indices
        self._calculate_indices(region_strings, sector_strings, regions, sectors)

        # Update supplychain
        self.ui.update_supplychain()

    def _build_summary_text(self, region_strings, sector_strings):
        """Build the summary text for display."""
        text = f"<b>{self._translate('Regions', 'Regions')}:</b><br>"

        if not self.region_indices:
            text += f"{self._translate('No regions selected', 'No regions selected')}.<br><br>"
        elif len(self.region_indices) == len(self.iosystem.index.region_multiindex):
            text += f"{self._translate('All regions selected (Global view)', 'All regions selected (Global view)')}.<br><br>"
        else:
            # Limit display length for very long lists
            display_regions = region_strings[:10]  # Show first 10
            text += ", ".join(display_regions)
            if len(region_strings) > 10:
                text += f", ... {self._translate('and', 'and')} {len(region_strings) - 10} {self._translate('more', 'more')}"
            text += f"<br><i>{self._translate('Count', 'Count')}:</i> {len(self.region_indices)}<br><br>"

        text += f"<b>{self._translate('Sectors', 'Sectors')}:</b><br>"

        if not self.sector_indices:
            text += f"{self._translate('No sectors selected', 'No sectors selected')}.<br><br>"
        elif len(self.sector_indices) == len(self.iosystem.index.sector_multiindex_per_region):
            text += f"{self._translate('All sectors selected (Global view)', 'All sectors selected (Global view)')}.<br><br>"
        else:
            # Limit display length for very long lists
            display_sectors = sector_strings[:10]  # Show first 10
            text += ", ".join(display_sectors)
            if len(sector_strings) > 10:
                text += f", ... {self._translate('and', 'and')} {len(sector_strings) - 10} {self._translate('more', 'more')}"
            text += f"<br><i>{self._translate('Count', 'Count')}:</i> {len(self.sector_indices)}<br><br>"

        return text

    def _calculate_indices(self, region_strings, sector_strings, regions, sectors):
        """Calculate the final indices based on selections."""
        self.indices = []

        if region_strings and sector_strings:
            for region in self.region_indices:
                for sector in self.sector_indices:
                    self.indices.append(int(region) * len(self.iosystem.sectors) + int(sector))
        elif region_strings:
            for region in self.region_indices:
                for sector in range(len(self.iosystem.sectors)):
                    self.indices.append(int(region) * len(self.iosystem.sectors) + int(sector))
        elif sector_strings:
            for region in range(len(self.iosystem.regions)):
                for sector in self.sector_indices:
                    self.indices.append(int(region) * len(self.iosystem.sectors) + int(sector))
        else:
            self.indices = list(range(9800))

        # Determine input method
        self.inputByIndices = True
        if len(regions) <= 1 and len(sectors) <= 1:
            self.inputByIndices = False
            self.kwargs = {}

            if regions:
                key = self.region_level_names[regions[0][0]]
                value = regions[0][1]
                self.kwargs[key] = value

            if sectors:
                key = self.sector_level_names[sectors[0][0]]
                value = sectors[0][1]
                self.kwargs[key] = value

    def reset_selection(self):
        """Reset all selections."""
        self.clear_region_selection()
        self.clear_sector_selection()
        self.selection_label.setText(self._translate("No selection made", "No selection made"))
        self.summary_group.setTitle(self._translate("Selection Summary", "Selection Summary"))
