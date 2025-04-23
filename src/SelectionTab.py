import numpy as np
import pandas as pd

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QGroupBox, QLabel, QPushButton, QSplitter, QTreeWidget,
    QTreeWidgetItem, QScrollArea, QCheckBox,
)
from PyQt5.QtCore import Qt

def multiindex_to_nested_dict(multiindex: pd.MultiIndex) -> dict:
    # Initialize an empty dictionary to store the nested structure.
    root = {}

    # Iterate over each set of keys in the MultiIndex.
    for keys in multiindex:
        # Start from the root of the dictionary for each set of keys.
        current = root
        
        # Iterate through each key in the current level.
        for key in keys:
            # Use setdefault to ensure the key exists and create a new dictionary if not.
            current = current.setdefault(key, {})
    
    # Return the final nested dictionary.
    return root


class SelectionTab(QWidget):
    """
    The SelectionTab class is responsible for managing the selection of regions and sectors 
    in the user interface. It interacts with the underlying database to provide hierarchical 
    views for regions and sectors, and updates the selection accordingly.

    Attributes:
        database (IOSystem): The database instance containing the data.
        ui (UserInterface): The parent UI instance.
        general_dict (dict): General dictionary for UI labels and texts.
        region_hierarchy (dict): Nested dictionary representing the region hierarchy.
        sector_hierarchy (dict): Nested dictionary representing the sector hierarchy by region.
        region_level_names (list): List of region level names.
        sector_level_names (list): List of sector level names.
        region_indices (list): List of selected region indices.
        sector_indices (list): List of selected sector indices.
        indices (list): List of all indices available (default: all 9800 indices).
        inputByIndices (bool): Flag to determine if selection is done by indices or criteria.
    """

    def __init__(self, ui):
        """
        Initializes the SelectionTab with the given database and UI instance.
        
        Args:
            database (IOSystem): The database instance containing the data.
            ui (UserInterface): The parent user interface instance.
        """
        super().__init__()

        # Store references to the database and UI.
        self.ui = ui
        self.database = self.ui.database

        # Retrieve general dictionary for UI texts.
        self.general_dict = self.database.Index.general_dict

        # Convert the multiindices for regions and sectors into nested dictionaries.
        self.region_hierarchy = multiindex_to_nested_dict(self.database.Index.region_multiindex)
        self.sector_hierarchy = multiindex_to_nested_dict(self.database.Index.sector_multiindex_per_region)

        # Get level names for regions and sectors.
        self.region_level_names = list(self.database.Index.region_multiindex.names)
        self.sector_level_names = list(self.database.Index.sector_multiindex_per_region.names)

        # Initialize indices lists (empty initially).
        self.region_indices = []
        self.sector_indices = []

        # By default, all indices are available for selection.
        self.indices = [index for index in range(9800)]

        # By default, selection is done using indices.
        self.inputByIndices = False

        # Initialize the user interface components.
        self.init_ui()
     
    def init_ui(self):
        """
        Initializes the user interface components for the SelectionTab, including 
        the region and sector selection trees, buttons for clearing and selecting all items, 
        and the summary section for displaying the current selection.

        It organizes the layout into a region/sector selection section and a bottom section 
        for applying or resetting the selection.
        """
        layout = QVBoxLayout(self)
        layout.setSpacing(20)  # Set the spacing between widgets

        # Widget containing both region and sector trees
        region_sector_widget = QWidget()
        rs_layout = QHBoxLayout(region_sector_widget)
        rs_layout.setSpacing(20)
        rs_layout.setContentsMargins(0, 0, 0, 0)

        # Helper function to recursively add items to the QTreeWidget
        def add_tree_items(parent, data, level=0):
            """
            Adds hierarchical items to the QTreeWidget from the provided data.
            
            Args:
                parent (QTreeWidget): The parent item to which new items will be added.
                data (dict): The hierarchical data to be added as items.
                level (int): The current depth level in the tree.
            """
            for key, val in data.items():
                item = QTreeWidgetItem(parent)
                item.setText(0, key)
                item.setData(0, Qt.UserRole, level)
                item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
                item.setCheckState(0, Qt.Unchecked)  # Set default state to unchecked
                if isinstance(val, dict) and val:
                    add_tree_items(item, val, level + 1)  # Recursively add child items

        # Region Tree
        region_group = QGroupBox(self.general_dict["Region Selection"])
        region_layout = QVBoxLayout(region_group)
        self.region_tree = QTreeWidget()
        self.region_tree.setHeaderHidden(True)  # Hide header
        self.region_tree.setSelectionMode(QTreeWidget.NoSelection)  # No selection allowed
        add_tree_items(self.region_tree, self.region_hierarchy)  # Populate region tree
        self.region_tree.itemChanged.connect(self.on_region_item_changed)  # Connect item change event
        region_layout.addWidget(self.region_tree)

        # Buttons for region selection (Clear & Select All)
        region_button_layout = QHBoxLayout()
        btn_clear_region = QPushButton(f"{self.general_dict['Clear']} {self.general_dict['Region Selection']}")
        btn_select_all_regions = QPushButton(self.general_dict["Select All Regions"])
        btn_clear_region.clicked.connect(self.clear_region_selection)
        btn_select_all_regions.clicked.connect(self.select_all_regions)
        region_button_layout.addWidget(btn_clear_region)
        region_button_layout.addWidget(btn_select_all_regions)
        region_layout.addLayout(region_button_layout)

        # Sector Tree
        sector_group = QGroupBox(self.general_dict["Sector Selection"])
        sector_layout = QVBoxLayout(sector_group)
        self.sector_tree = QTreeWidget()
        self.sector_tree.setHeaderHidden(True)  # Hide header
        self.sector_tree.setSelectionMode(QTreeWidget.NoSelection)  # No selection allowed
        add_tree_items(self.sector_tree, self.sector_hierarchy)  # Populate sector tree
        self.sector_tree.itemChanged.connect(self.on_sector_item_changed)  # Connect item change event
        sector_layout.addWidget(self.sector_tree)

        # Buttons for sector selection (Clear & Select All)
        sector_button_layout = QHBoxLayout()
        btn_clear_sector = QPushButton(f"{self.general_dict['Clear']} {self.general_dict['Sector Selection']}")
        btn_select_all_sectors = QPushButton(self.general_dict["Select All Sectors"])
        btn_clear_sector.clicked.connect(self.clear_sector_selection)
        btn_select_all_sectors.clicked.connect(self.select_all_sectors)
        sector_button_layout.addWidget(btn_clear_sector)
        sector_button_layout.addWidget(btn_select_all_sectors)
        sector_layout.addLayout(sector_button_layout)

        # Style for buttons (Standardized)
        button_style = "QPushButton { padding: 6px 12px; }"
        for btn in [btn_clear_region, btn_select_all_regions, btn_clear_sector, btn_select_all_sectors]:
            btn.setStyleSheet(button_style)

        # Add region and sector selection groups to layout
        rs_layout.addWidget(region_group)
        rs_layout.addWidget(sector_group)
        layout.addWidget(region_sector_widget)

        # Bottom widget for displaying selection summary and applying/resetting
        bottom_widget = QWidget()
        bottom_layout = QVBoxLayout(bottom_widget)
        bottom_layout.setSpacing(10)
        bottom_layout.setContentsMargins(0, 0, 0, 0)

        # Selection Summary Section
        self.summary_group = QGroupBox(self.general_dict["Selection Summary"])
        summary_layout = QVBoxLayout(self.summary_group)
        self.selection_label = QLabel(self.general_dict["No selection made"])
        self.selection_label.setWordWrap(True)  # Allow text to wrap
        summary_scroll = QScrollArea()
        summary_scroll.setWidgetResizable(True)
        summary_scroll.setWidget(self.selection_label)  # Set scrollable summary
        summary_layout.addWidget(summary_scroll)
        bottom_layout.addWidget(self.summary_group)

        # Apply and Reset Buttons
        btn_layout = QHBoxLayout()
        self.apply_button = QPushButton(self.general_dict["Apply Selection"])
        self.reset_button = QPushButton(self.general_dict["Reset All Selections"])
        self.apply_button.clicked.connect(self.apply_selection)
        self.reset_button.clicked.connect(self.reset_selection)
        btn_layout.addWidget(self.apply_button)
        btn_layout.addWidget(self.reset_button)

        # Style buttons for a consistent look
        for btn in [self.apply_button, self.reset_button]:
            btn.setStyleSheet(button_style)

        bottom_layout.addLayout(btn_layout)

        # Splitter to allow resizing of the selection area and bottom summary
        splitter = QSplitter(Qt.Vertical)
        splitter.addWidget(region_sector_widget)
        splitter.addWidget(bottom_widget)
        splitter.setStretchFactor(0, 1)  # Allow region/sector section to expand
        splitter.setStretchFactor(1, 1)  # Allow bottom section to expand equally
        layout.addWidget(splitter)

    def propagate_down(self, item, state):
        """
        Recursively propagates the given check state down the tree to all child items.
        
        Args:
            item (QTreeWidgetItem): The parent item whose children will be updated.
            state (Qt.CheckState): The state to set for all child items (checked or unchecked).
        """
        # Loop through all child items of the current item
        for i in range(item.childCount()):
            child = item.child(i)  # Get the child item at index i
            child.setCheckState(0, state)  # Set the check state for this child item
            self.propagate_down(child, state)  # Recursively call propagate_down for the child item

    def on_region_item_changed(self, item, column):
        """
        Handles the event when the check state of a region item changes.
        
        This method blocks signals temporarily to prevent infinite loops, 
        propagates the new check state down to all child items of the region tree, 
        and then restores signal handling.
        
        Args:
            item (QTreeWidgetItem): The item whose check state has changed.
            column (int): The column in which the check state change occurred (not used here, but required by the signal).
        """
        # Temporarily block signals to prevent recursive signal triggering
        self.region_tree.blockSignals(True)
        
        # Propagate the new check state to all child items of the current item
        self.propagate_down(item, item.checkState(column))
        
        # Restore signal handling after processing the change
        self.region_tree.blockSignals(False)

    def on_sector_item_changed(self, item, column):
        """
        Handles the event when the check state of a sector item changes.
        
        Similar to the on_region_item_changed method, this method blocks signals temporarily, 
        propagates the new check state down to all child items of the sector tree, 
        and then restores signal handling.
        
        Args:
            item (QTreeWidgetItem): The item whose check state has changed.
            column (int): The column in which the check state change occurred (not used here, but required by the signal).
        """
        # Temporarily block signals to prevent recursive signal triggering
        self.sector_tree.blockSignals(True)
        
        # Propagate the new check state to all child items of the current item
        self.propagate_down(item, item.checkState(column))
        
        # Restore signal handling after processing the change
        self.sector_tree.blockSignals(False)

    def clear_region_selection(self):
        """
        Clears the selection of all items in the region tree.

        This method resets the check state of all items in the region tree to 
        unchecked and propagates the change down to all child items.

        It ensures that the entire region tree is deselected.
        """
        # Get the root item of the region tree (the invisible root)
        root = self.region_tree.invisibleRootItem()
        
        # Loop through all child items of the root item
        for i in range(root.childCount()):
            node = root.child(i)
            
            # Set the check state of each child item to unchecked
            node.setCheckState(0, Qt.Unchecked)
            
            # Propagate the unchecked state down to all child items of the current node
            self.propagate_down(node, Qt.Unchecked)

    def clear_sector_selection(self):
        """
        Clears the selection of all items in the sector tree.

        This method resets the check state of all items in the sector tree to 
        unchecked and propagates the change down to all child items.

        It ensures that the entire sector tree is deselected.
        """
        # Get the root item of the sector tree (the invisible root)
        root = self.sector_tree.invisibleRootItem()
        
        # Loop through all child items of the root item
        for i in range(root.childCount()):
            node = root.child(i)
            
            # Set the check state of each child item to unchecked
            node.setCheckState(0, Qt.Unchecked)
            
            # Propagate the unchecked state down to all child items of the current node
            self.propagate_down(node, Qt.Unchecked)

    def select_all_regions(self):
        """
        Selects all items in the region tree.

        This method sets the check state of all items in the region tree to 
        checked and propagates the change down to all child items.

        It ensures that the entire region tree is selected.
        """
        # Get the root item of the region tree (the invisible root)
        root = self.region_tree.invisibleRootItem()
        
        # Loop through all child items of the root item
        for i in range(root.childCount()):
            node = root.child(i)
            
            # Set the check state of each child item to checked
            node.setCheckState(0, Qt.Checked)
            
            # Propagate the checked state down to all child items of the current node
            self.propagate_down(node, Qt.Checked)

    def select_all_sectors(self):
        """
        Selects all items in the sector tree.

        This method sets the check state of all items in the sector tree to 
        checked and propagates the change down to all child items.

        It ensures that the entire sector tree is selected.
        """
        # Get the root item of the sector tree (the invisible root)
        root = self.sector_tree.invisibleRootItem()
        
        # Loop through all child items of the root item
        for i in range(root.childCount()):
            node = root.child(i)
            
            # Set the check state of each child item to checked
            node.setCheckState(0, Qt.Checked)
            
            # Propagate the checked state down to all child items of the current node
            self.propagate_down(node, Qt.Checked)

    def _collect_highest_level(self, item, result):
        """
        Recursively collects the highest level items (that are checked) from the tree.

        This method checks if an item is checked and if so, it adds it to the result list.
        If the item is not checked, it recursively checks its child items.

        Args:
            item (QTreeWidgetItem): The current item being processed.
            result (list): A list that will store the checked items in the format (item_data, item_text).
        """
        # If the current item is checked, add it to the result list with its data and text
        if item.checkState(0) == Qt.Checked:
            result.append((item.data(0, Qt.UserRole), item.text(0)))
        else:
            # If the item is not checked, recursively process its children
            for i in range(item.childCount()):
                self._collect_highest_level(item.child(i), result)

    def get_checked_regions(self):
        """
        Collects all checked regions from the region tree.

        This method starts at the root of the region tree and recursively collects all
        checked items in the tree.

        Returns:
            list: A list of tuples containing the data and text of each checked region.
        """
        checked = []
        # Get the root item of the region tree
        root = self.region_tree.invisibleRootItem()
        
        # Loop through all child items of the root item and collect checked regions
        for i in range(root.childCount()):
            self._collect_highest_level(root.child(i), checked)
        
        return checked

    def get_checked_sectors(self):
        """
        Collects all checked sectors from the sector tree.

        This method starts at the root of the sector tree and recursively collects all
        checked items in the tree.

        Returns:
            list: A list of tuples containing the data and text of each checked sector.
        """
        checked = []
        # Get the root item of the sector tree
        root = self.sector_tree.invisibleRootItem()
        
        # Loop through all child items of the root item and collect checked sectors
        for i in range(root.childCount()):
            self._collect_highest_level(root.child(i), checked)
        
        return checked

    def apply_selection(self):
        """
        Applies the region and sector selection, updates the indices based on the selections,
        and displays a summary of the selection.

        This method collects the checked regions and sectors, computes their corresponding indices,
        and updates the display with the selection details.
        """
        # Get the selected regions and sectors
        regions = self.get_checked_regions()
        sectors = self.get_checked_sectors()

        # Retrieve multiindex structures for regions and sectors from the database
        mi_r = self.database.Index.region_multiindex
        mi_s = self.database.Index.sector_multiindex_per_region

        # Initialize sets to hold region and sector indices
        region_idx = set()
        sector_idx = set()

        # Process the selected regions and update the region indices
        for level, name in regions:
            # Create a mask to identify the rows that match the selected region
            mask = mi_r.get_level_values(level) == name
            region_idx.update(np.where(mask)[0])  # Add matching indices to region_idx set

        # Process the selected sectors and update the sector indices
        for level, name in sectors:
            # Create a mask to identify the rows that match the selected sector
            mask = mi_s.get_level_values(level) == name
            sector_idx.update(np.where(mask)[0])  # Add matching indices to sector_idx set

        # Sort the indices for regions and sectors
        self.region_indices = sorted(region_idx)
        self.sector_indices = sorted(sector_idx)

        # Prepare strings to display in the selection summary for regions and sectors
        region_strings = [f"{self.region_level_names[level]}: {name}" for level, name in regions]
        sector_strings = [f"{self.sector_level_names[level]}: {name}" for level, name in sectors]

        txt = ""

        # Region selection summary
        txt += f"<b>{self.general_dict['Regions']}:</b><br>"
        if len(self.region_indices) == 0:
            txt += f"{self.general_dict['No regions selected']}.<br><br>"
        elif len(self.region_indices) == len(mi_r):
            txt += f"{self.general_dict['All regions selected (Global view)']}.<br><br>"
        else:
            txt += ", ".join(region_strings)
            txt += f"<br><i>{self.general_dict['Region indices count']}:</i> {len(self.region_indices)}<br><br>"

        # Sector selection summary
        txt += f"<b>{self.general_dict['Sectors']}:</b><br>"
        if len(self.sector_indices) == 0:
            txt += f"{self.general_dict['No sectors selected']}.<br><br>"
        elif len(self.sector_indices) == len(mi_s):
            txt += f"{self.general_dict['All sectors selected (Global view)']}.<br><br>"
        else:
            txt += ", ".join(sector_strings)
            txt += f"<br><i>{self.general_dict['Sector indices count']}:</i> {len(self.sector_indices)}<br><br>"

        # Calculate the indices based on the region and sector selections
        self.indices = []
        if region_strings and sector_strings:
            for region in self.region_indices:
                for sector in self.sector_indices:
                    self.indices.append(int(region) * len(self.database.sectors) + int(sector))
        elif region_strings:
            for region in self.region_indices:
                for sector in range(len(self.database.sectors)):  # All sectors
                    self.indices.append(int(region) * len(self.database.sectors) + int(sector))
        elif sector_strings:
            for region in range(len(self.database.regions)):  # All regions
                for sector in self.sector_indices:
                    self.indices.append(int(region) * len(self.database.sectors) + int(sector))
        else:  # World: include all indices
            self.indices = [index for index in range(9800)]

        # Determine whether the selection is simple (one region and one sector) or more complex
        self.inputByIndices = True
        if len(regions) <= 1 and len(sectors) <= 1:
            self.inputByIndices = False
            self.kwargs = {}

            # If regions are selected, store the selected region in kwargs
            if regions:
                key = self.region_level_names[regions[0][0]]
                value = regions[0][1]
                self.kwargs[key] = value

            # If sectors are selected, store the selected sector in kwargs
            if sectors:
                key = self.sector_level_names[sectors[0][0]]
                value = sectors[0][1]
                self.kwargs[key] = value

        # If the "show indices" setting is active, display the indices count
        if self.ui.settings_tab.is_show_indices_active():
            txt += f"<b>Indices ({len(self.indices)}):</b> {self.indices}<br><br>"

        # Update the label and group title with the selection summary
        self.selection_label.setText(txt)
        self.summary_group.setTitle(self.general_dict["Selection Summary"])

        # Update the supplychain-Object
        self.ui.update_supplychain()

    def reset_selection(self):
        """
        Resets the region and sector selections to unchecked, updates the display to show that
        no selection has been made, and updates the selection summary title.

        This method calls the `clear_region_selection` and `clear_sector_selection` methods 
        to uncheck all items, and then updates the label and title to indicate that no selection
        has been made.
        """
        # Clear all region selections (uncheck all regions)
        self.clear_region_selection()

        # Clear all sector selections (uncheck all sectors)
        self.clear_sector_selection()

        # Update the selection label to indicate that no selection has been made
        self.selection_label.setText(self.general_dict["No selection made"])

        # Update the summary group title to "Selection Summary"
        self.summary_group.setTitle(self.general_dict["Selection Summary"])
