import matplotlib.pyplot as plt
from src.SupplyChain import SupplyChain
import pandas as pd
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from PyQt5.QtWidgets import QSizePolicy

from PyQt5.QtWidgets import (
    QTabWidget, QWidget, QVBoxLayout, QHBoxLayout,
    QGroupBox, QLabel, QPushButton, 
    QTreeWidget, QTreeWidgetItem, QDialogButtonBox, QDialog, QApplication
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

class VisualisationTab(QWidget):
    """
    A class to represent the visualisation tab in the user interface.

    This class initializes the visualisation tab, which is a widget that allows
    users to interact with and view the visualisation of the data from the database.

    Attributes:
        ui (UserInterface): The main UI object, which the tab interacts with.
        database (IOSystem): The database from which the data for visualisation is fetched.
        general_dict (dict): A dictionary containing general configurations for the visualisation.
    """
    
    def __init__(self, database, ui, parent=None):
        """
        Initializes the VisualisationTab with the given database and UI.
        
        Args:
            database (IOSystem): The database object containing the data for visualisation.
            ui (UserInterface): The parent user interface object.
            parent (QWidget, optional): The parent widget for this tab. Defaults to None.
        """
        super().__init__(parent)
        
        # Set the user interface and database for the visualisation tab.
        self.ui = ui
        self.database = database
        
        # Retrieve the general configuration dictionary from the database.
        self.general_dict = self.database.Index.general_dict
        
        # Initialize the user interface for the tab.
        self._init_ui()

    def _init_ui(self):
        """
        Initializes the user interface for the visualisation tab.

        This method sets up the layout and adds an inner tab widget to the visualisation
        tab, which contains three sub-tabs: Table, World Map, and Bar Chart. Each sub-tab 
        is associated with a different class that handles the respective visualisation.

        The general dictionary from the database is used to set the tab labels.
        """
        # Create a vertical layout for the visualisation tab.
        layout = QVBoxLayout(self)

        # Create the inner tab widget, which will contain sub-tabs (Table, World Map, Bar Chart).
        self.inner_tab_widget = QTabWidget()

        # Add sub-tabs to the inner tab widget using new classes.
        self.inner_tab_widget.addTab(SupplyChainAnalysis(self.database, ui=self.ui), self.general_dict["Supply Chain Analysis"])
        self.inner_tab_widget.addTab(WorldMapTab(), self.general_dict["World Map"])
        self.inner_tab_widget.addTab(BarChartTab(), self.general_dict["Total"])

        # Add the inner tab widget to the main layout of the visualisation tab.
        layout.addWidget(self.inner_tab_widget)

    
class SupplyChainAnalysis(QWidget):
    """
    A class to represent the supply chain analysis in the visualisation section.

    This class initializes the table tab where users can select impact categories,
    view impacts, and update the plot based on the selected impacts. It allows users 
    to interact with different impact categories like greenhouse gas emissions, water 
    usage, land use, value creation, and labor time.

    Attributes:
        ui (UserInterface): The main UI object, which the tab interacts with.
        database (IOSystem): The database from which the data is fetched.
        general_dict (dict): A dictionary containing general configurations for the tab.
        impact_hierarchy (dict): A nested dictionary representing the impact hierarchy.
        saved_defaults (dict): Default values for selected impacts.
        selected_impacts (list): A list of selected impact categories.
        canvas (matplotlib.Axes): The canvas for the plot (initially None).
        plot_area (QVBoxLayout): Layout for the plot area.
        impact_button (QPushButton): Button to select impact categories.
        plot_button (QPushButton): Button to update the plot.
    """
    
    def __init__(self, database, ui, parent=None):
        """
        Initializes the SupplyChainAnalysis with the given database and UI.
        
        Args:
            database (IOSystem): The database object containing the data.
            ui (UserInterface): The parent user interface object.
            parent (QWidget, optional): The parent widget for this tab. Defaults to None.
        """
        super().__init__(parent)
        
        # Set the user interface and database for the table tab.
        self.ui = ui
        self.database = database
        
        # Retrieve the general configuration dictionary from the database.
        self.general_dict = self.database.Index.general_dict
        
        # Convert the MultiIndex of impacts to a nested dictionary.
        self.impact_hierarchy = multiindex_to_nested_dict(database.Index.impact_multiindex)
        
        # Set the default values for impacts (Dummy data as standard).
        self.saved_defaults = {
            self.database.impacts[3]: True,  # Greenhouse gas emissions
            self.database.impacts[32]: True, # Water consumption
            self.database.impacts[125]: True, # Land use
            self.database.impacts[0]: True,  # Value creation
            self.database.impacts[2]: True   # Labor time
        }

        # Select the impacts that are marked as True in the defaults.
        self.selected_impacts = [k for k, v in self.saved_defaults.items() if v]
        
        # Set up the layout for the table tab.
        layout = QVBoxLayout(self)

        # Create the impact selection group box and button.
        impact_group = QGroupBox(self.general_dict["Select Impacts"])
        impact_layout = QVBoxLayout(impact_group)

        # Create the impact selection button that shows the number of selected impacts.
        self.impact_button = QPushButton(self.general_dict["Select Impacts"])
        self.impact_button.setText(f"{self.general_dict['Selected']} ({sum(self.saved_defaults.values())})")
        self.impact_button.clicked.connect(self.select_impacts)  # Connect the button to the selection method.
        impact_layout.addWidget(self.impact_button)

        # Set a maximum height for the impact selection group and add it to the layout.
        impact_group.setMaximumHeight(100)
        layout.addWidget(impact_group)

        # Set up the plot area and button for updating the plot.
        self.canvas = None
        self.plot_area = QVBoxLayout()
        layout.addLayout(self.plot_area)
        
        # Add dummy plot to display initial message
        self.fig_dummy = plt.figure()
        self.ax_dummy = self.fig_dummy.add_subplot(111)
        self.ax_dummy.text(0.5, 0.5, self.general_dict["Please select sectors and regions first"],
                      horizontalalignment='center', verticalalignment='center',
                      transform=self.ax_dummy.transAxes)
        self.ax_dummy.axis('off')
        self.canvas = FigureCanvas(self.fig_dummy)
        self.plot_area.addWidget(self.canvas)

        self.plot_button = QPushButton(self.general_dict["Update Plot"])
        self.plot_button.clicked.connect(self.update_plot)  # Connect the button to the update plot method.
        layout.addWidget(self.plot_button)

        # Set the layout for this tab.
        self.setLayout(layout)

    def update_plot(self):
        """
        Updates the plot in the TableTab based on the selected impacts and the current input.

        This method handles updating the plot area with the new plot based on the
        user’s selection. It sets a wait cursor while the plot is being updated and
        restores the default cursor once the process is complete. It removes the 
        previous canvas if it exists and adds a new one.

        The plot is generated using the `SupplyChain` class and is customized with
        various settings, such as line color, line width, and text position.
        """
        # Set the cursor to a wait cursor while the plot is being updated.
        QApplication.setOverrideCursor(Qt.WaitCursor)
        
        # Remove the previous plot canvas if it exists and delete it.
        if self.canvas:
            self.plot_area.removeWidget(self.canvas)
            self.canvas.setParent(None)
            self.canvas.deleteLater()  # Free memory by deleting the old canvas.

        # Determine the input method based on the user's selection in the interface.
        if self.ui.selection_tab.inputByIndices:
            # Create a SupplyChain object using indices from the selection tab.
            supplychain = SupplyChain(self.database, indices=self.ui.selection_tab.indices)
        else:
            # Create a SupplyChain object using the keyword arguments from the selection tab.
            supplychain = SupplyChain(self.database, **self.ui.selection_tab.kwargs)
        
        # Generate the plot for the supply chain with the selected impacts.
        fig = supplychain.plot_supply_chain(
            self.selected_impacts, size=1, lines=True, line_width=1, line_color="gray", text_position="center"
        )
        
        # Create a new canvas for the generated plot and add it to the plot area.
        self.canvas = FigureCanvas(fig)
        self.plot_area.addWidget(self.canvas)
        
        # Draw the canvas to display the plot.
        self.canvas.draw()
        
        # Restore the default cursor after the plot has been updated.
        QApplication.restoreOverrideCursor()

    def select_impacts(self):
        """
        Opens a dialog for the user to select or deselect impacts from a hierarchical list.

        The impacts are displayed in a tree structure, allowing the user to check or uncheck impacts at
        various levels of the hierarchy. The selected impacts are updated based on user input.
        """
        dialog = QDialog(self)
        dialog.setWindowTitle(self.general_dict["Select Impacts"])
        dialog.setMinimumSize(350, 300)
        layout = QVBoxLayout(dialog)

        layout.addWidget(QLabel(f"{self.general_dict['Select Impacts']}:"))

        def add_tree_items(parent, data, level=0):
            """
            Recursively adds items to the tree widget. If the data is a dictionary, it creates nested items.
            If the data is a list, it creates items for each list element. Each item is checkable.

            Args:
                parent (QTreeWidgetItem): The parent item to add the current items to.
                data (dict): The data to be added, either a dictionary or a list.
                level (int): The current level of the hierarchy, used for nesting items.
            """
            for key, val in data.items():
                item = QTreeWidgetItem(parent)
                item.setText(0, key)
                item.setData(0, Qt.UserRole, level)
                item.setFlags(item.flags() | Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
                check_state = Qt.Checked if self.saved_defaults.get(key, False) else Qt.Unchecked
                item.setCheckState(0, check_state)
                if isinstance(val, dict) and val:
                    add_tree_items(item, val, level + 1)
                elif isinstance(val, list):
                    for item_name in val:
                        impact_item = QTreeWidgetItem(parent)
                        impact_item.setText(0, item_name)
                        impact_item.setFlags(impact_item.flags() | Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
                        check_state = Qt.Checked if self.saved_defaults.get(item_name, False) else Qt.Unchecked
                        impact_item.setCheckState(0, check_state)

        self.impact_tree = QTreeWidget()
        self.impact_tree.setHeaderHidden(True)
        self.impact_tree.setSelectionMode(QTreeWidget.NoSelection)
        add_tree_items(self.impact_tree, self.impact_hierarchy)

        layout.addWidget(self.impact_tree)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)

        def get_all_children(parent):
            return [parent.child(i) for i in range(parent.childCount())]

        def get_all_items_recursively(item):
            items = []
            for i in range(item.childCount()):
                child = item.child(i)
                items.append(child)
                items.extend(get_all_items_recursively(child))
            return items

        def confirm():
            new_defaults = {}
            def collect_items_recursively(item):
                if item.flags() & Qt.ItemIsUserCheckable:
                    new_defaults[item.text(0)] = item.checkState(0) == Qt.Checked
                for i in range(item.childCount()):
                    collect_items_recursively(item.child(i))

            for i in range(self.impact_tree.topLevelItemCount()):
                collect_items_recursively(self.impact_tree.topLevelItem(i))

            self.saved_defaults = new_defaults
            self.selected_impacts = [k for k, v in self.saved_defaults.items() if v]
            self.impact_button.setText(f"{self.general_dict['Selected']} ({sum(self.saved_defaults.values())})")
            self.update_plot()  # Update plot after confirming selection
            dialog.accept()

        def reset_to_defaults():
            self.saved_defaults = {
                self.database.impacts[3]: True, 
                self.database.impacts[32]: True, 
                self.database.impacts[125]: True, 
                self.database.impacts[0]: True, 
                self.database.impacts[2]: True
            }
            self.selected_impacts = [k for k, v in self.saved_defaults.items() if v]
            self.impact_button.setText(f"{self.general_dict['Selected']} ({sum(self.saved_defaults.values())})")
            self.update_plot()  # Update plot after resetting defaults
            dialog.accept()

        buttons.accepted.connect(confirm)
        buttons.rejected.connect(dialog.reject)

        button_layout = QHBoxLayout()

        reset_button = QPushButton(self.general_dict["Reset to Defaults"])
        reset_button.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        reset_button.clicked.connect(reset_to_defaults)
        button_layout.addWidget(reset_button)

        button_layout.addStretch()
        button_layout.addWidget(buttons)

        layout.addLayout(button_layout)

        dialog.exec_()


class WorldMapTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("This is inner tab 2 content."))


class BarChartTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("This is inner tab 3 content."))