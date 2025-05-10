import matplotlib.pyplot as plt
import pandas as pd
import os
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas

from PyQt5.QtWidgets import (
    QTabWidget, QWidget, QVBoxLayout, QHBoxLayout,  QMenu, QFileDialog, QGraphicsOpacityEffect,
    QGroupBox, QLabel, QPushButton, QSizePolicy, QStackedLayout,
    QTreeWidget, QTreeWidgetItem, QDialogButtonBox, QDialog, QApplication, QComboBox, QTabBar, QToolTip
)
from PyQt5.QtCore import Qt
from shapely.geometry import Point
from PyQt5.QtGui import QPixmap

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
    
    def __init__(self, ui, parent=None):
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
        self.database = self.ui.database
        
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
        self.inner_tab_widget.addTab(DiagramTab(ui=self.ui), self.general_dict["Diagram"])
        self.inner_tab_widget.addTab(WorldMapTab(ui=self.ui), self.general_dict["World Map"])
        #self.inner_tab_widget.addTab(BarChartTab(), self.general_dict["Total"])

        # Add the inner tab widget to the main layout of the visualisation tab.
        layout.addWidget(self.inner_tab_widget)

    
class DiagramTab(QWidget):
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
    
    def __init__(self, ui, parent=None):
        """
        Initializes the DiagramTab with the given database and UI.
        
        Args:
            ui (UserInterface): The parent user interface object.
            parent (QWidget, optional): The parent widget for this tab. Defaults to None.
        """
        super().__init__(parent)
        
        # Set the user interface and database for the table tab.
        self.ui = ui
        self.database = self.ui.database

        # Retrieve the general configuration dictionary from the database.
        self.general_dict = self.database.Index.general_dict
        
        # Convert the MultiIndex of impacts to a nested dictionary.
        self.impact_hierarchy = multiindex_to_nested_dict(self.database.Index.impact_multiindex)
        
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
        self._setup_canvas_context_menu() 
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
        
        # Generate the plot for the supply chain with the selected impacts.
        fig = self.ui.supplychain.plot_supplychain_diagram(
            self.selected_impacts, size=1, lines=True, line_width=1, line_color="gray", text_position="center"
        )
        
        # Create a new canvas for the generated plot and add it to the plot area.
        self.canvas = FigureCanvas(fig)
        self._setup_canvas_context_menu()  
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

    def _setup_canvas_context_menu(self):
        self.canvas.setContextMenuPolicy(Qt.CustomContextMenu)
        self.canvas.customContextMenuRequested.connect(self._show_context_menu)

    def _show_context_menu(self, pos):
        menu = QMenu(self)
        save_action = menu.addAction(self.general_dict["Save plot"])
        action = menu.exec_(self.canvas.mapToGlobal(pos))
        if action == save_action:
            fname, _ = QFileDialog.getSaveFileName(
                self, self.general_dict["Save plot"], "", self.general_dict["PNG-File (*.png)"]
            )
            if fname:
                # Speichern
                self.canvas.figure.savefig(fname)


class InfoDialog(QDialog):
    def __init__(self, ui, country, parent=None):
        super().__init__(parent)
        self.ui = ui
        self.database = self.ui.database

        # Dialog-Grundkonfiguration
        self.setWindowTitle("Detail-Info")
        self.setFixedSize(320, 220)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        # Haupt-Layout: überlagert Hintergrund und Text
        stack = QStackedLayout(self)
        stack.setContentsMargins(0, 0, 0, 0)
        stack.setStackingMode(QStackedLayout.StackAll)

        # Hintergrund: Flagge mit Transparenz
        flag_name = f"{country.get('exiobase','-').lower()}.png"
        flag_path = os.path.join(self.database.data_dir, "flags", flag_name)
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
        # Transparenz-Effekt
        opacity_effect = QGraphicsOpacityEffect(bg_label)
        opacity_effect.setOpacity(0.3)
        bg_label.setGraphicsEffect(opacity_effect)
        stack.addWidget(bg_label)

        # Text-Label: ohne eigenen Hintergrund, nur weiße Schrift mit Schatten
        region = country.get("region", "-")
        value = country.get("value", "-")
        percentage = country.get("percentage", "-")
        text = (
            f"<div style='color: #000; font-size:16px;'>"
            f"<b>{region}</b><br>"
            f"Wert: {value}<br>"
            f"Prozent: {percentage} %"
            f"</div>"
        )
        text_label = QLabel(text, self)
        text_label.setAlignment(Qt.AlignCenter)
        text_label.setWordWrap(True)
        stack.addWidget(text_label)

    def mousePressEvent(self, event):
        self.accept()


class MapConfigTab(QWidget):
    """
    A tab for configuring the map visualization in the application.

    Attributes:
        ui (UserInterface): Reference to the main UI object.
        database (IOSystem): The database instance containing data for maps.
        general_dict (dict): Dictionary of localized UI labels and texts.
        name (str): The current selection name for the map (defaults to 'Subcontractors').
        tab_widget (QTabWidget or None): Parent tab widget if provided.
    """
    def __init__(self, ui, name=None, parent=None):
        """
        Initialize the MapConfigTab.

        Args:
            ui (UserInterface): Main UI reference for accessing shared state.
            name (str, optional): Initial map selection name. Defaults to localized 'Subcontractors'.
            parent (QWidget, optional): Parent widget, may be a QTabWidget to attach to. Defaults to None.
        """
        super().__init__(parent)

        # Store references to UI, database, and localized text dictionary
        self.ui = ui
        self.database = self.ui.database
        self.general_dict = self.database.Index.general_dict

        # Determine initial map selection name
        self.name = name or self.general_dict["Subcontractors"]

        # If parent is a QTabWidget, keep reference to rename tab dynamically
        self.tab_widget = parent if isinstance(parent, QTabWidget) else None

        # Statt GeoJSON: dein gemergtes GeoDataFrame übernehmen
        self.world = self.database.Index.world
        self.world = self.world.to_crs(epsg=4326)
        self.world_sindex = self.world.sindex

        # Main layout for the tab
        layout = QVBoxLayout(self)

        # 1) Dropdown selector for map categories or impacts
        self.selector = QComboBox()
        # Add default option for subcontractors
        self.selector.addItem(self.general_dict["Subcontractors"])
        # Insert a separator before listing all available impacts
        self.selector.insertSeparator(self.selector.count())
        # Add all impact options from the database
        self.selector.addItems(self.database.impacts)
        # Set the current text to the provided name
        self.selector.setCurrentText(self.name)
        layout.addWidget(self.selector)

        # 2) Update button to refresh the map based on selection
        btn = QPushButton(self.general_dict["Update Map"])
        btn.clicked.connect(self.update_map)  # Connect button click to update handler
        layout.addWidget(btn)

        # 3) Placeholder for the map canvas; initially empty
        self.canvas = None
        self._empty_canvas(layout)  # Call method to insert an empty placeholder

        # Change the tab name dynamically when selection changes
        self.selector.currentTextChanged.connect(
            lambda text: self._update_tab_name(text)
        )

    def _empty_canvas(self, layout):
        """
        Draws an empty placeholder map canvas with a waiting message.

        Args:
            layout (QLayout): The layout to which the placeholder canvas will be added.
        """
        # Create a new matplotlib figure
        fig = plt.figure()
        ax = fig.add_subplot(111)

        # Add centered waiting text to the plot
        ax.text(
            0.5, 0.5,
            self.general_dict["Waiting for update…"],
            horizontalalignment='center',
            verticalalignment='center',
            transform=ax.transAxes
        )

        # Hide axis lines and ticks for a clean placeholder
        ax.axis('off')

        # Embed the figure into a FigureCanvas and add it to the layout
        self.canvas = FigureCanvas(fig)
        self.canvas.mpl_connect('motion_notify_event', self._on_hover)
        self._setup_canvas_context_menu()
        layout.addWidget(self.canvas)

    def update_map(self):
        """
        Updates the map canvas based on the selected impact or subcontractors.
        Clears the existing canvas and replaces it with a new plot.
        """
        # Set the cursor to a waiting state during the update process
        QApplication.setOverrideCursor(Qt.WaitCursor)

        # Remove the old canvas widget from the layout and memory
        parent_layout = self.layout()
        parent_layout.removeWidget(self.canvas)
        self.canvas.setParent(None)
        self.canvas.deleteLater()

        # Determine which map to draw based on current selection
        choice = self.selector.currentText()
        if choice == self.general_dict["Subcontractors"]:
            fig, world = self.ui.supplychain.plot_worldmap_by_subcontractors(color="Blues", relative=True, return_data=True)
        else:
            fig, world = self.ui.supplychain.plot_worldmap_by_impact(choice, return_data=True)

        self.world = world
        self.world = self.world.to_crs(epsg=4326)
        self.world_sindex = self.world.sindex

        # Create and display the new canvas with the selected map
        self.canvas = FigureCanvas(fig)
        self.canvas.mpl_connect('motion_notify_event', self._on_hover)
        self.canvas.mpl_connect('button_press_event', self._on_click)
        self._setup_canvas_context_menu()
        parent_layout.addWidget(self.canvas)
        self.canvas.draw()

        # Restore the cursor to its normal state
        QApplication.restoreOverrideCursor()

    def _on_hover(self, event):
        if event.inaxes is None:
            QToolTip.hideText()
            return

        # Datenkoordinaten
        x, y = event.xdata, event.ydata
        pt = Point(x, y)
        # Zuerst Bounding-Box-Filter via SpatialIndex
        possible_idxs = list(self.world_sindex.intersection((x, y, x, y)))
        if not possible_idxs:
            QToolTip.hideText()
            return

        # Genaue contains-Abfrage
        country = None
        for idx in possible_idxs:
            if self.world.geometry.iloc[idx].contains(pt):
                country = self.world.iloc[idx]
                break

        if country is not None:
            region = country.get("region", "-")
            value = country.get("value", "-")
            percentage = country.get("percentage", "-")

            text = (
                f"Region:    {region}\n"
                f"Wert:  {round(value, 2)}\n"
                f"Prozentwert.:    {round(percentage, 1)} %"
            )

            QToolTip.showText(
                self.canvas.mapToGlobal(event.guiEvent.pos()),
                text,
                widget=self.canvas,
            )
        else:
            QToolTip.hideText()

    def _on_click(self, event):
        """Wird bei Mausklick im Canvas aufgerufen – zeigt Info-Dialog an."""
        if event.inaxes is None:
            return

        x, y = event.xdata, event.ydata
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
            dialog = InfoDialog(ui=self.ui, country=country, parent=self)
            dialog.exec_()

    def _update_tab_name(self, text):
        """
        Updates the name of the tab to reflect the current selection.

        Args:
            text (str): The new name to set as the tab label.
        """
        # Ensure the tab widget exists and update the label of the current tab
        if self.tab_widget:
            idx = self.tab_widget.indexOf(self)
            if idx != -1:
                self.tab_widget.setTabText(idx, text)

    def _setup_canvas_context_menu(self):
        self.canvas.setContextMenuPolicy(Qt.CustomContextMenu)
        self.canvas.customContextMenuRequested.connect(self._show_context_menu)

    def _show_context_menu(self, pos):
        menu = QMenu(self)
        save_action = menu.addAction(self.general_dict["Save plot"])
        action = menu.exec_(self.canvas.mapToGlobal(pos))
        if action == save_action:
            fname, _ = QFileDialog.getSaveFileName(
                self, self.general_dict["Save plot"], "", self.general_dict["PNG-File (*.png)"]
            )
            if fname:
                self.canvas.figure.savefig(fname)


class WorldMapTab(QWidget):
    """
    A tab widget for managing multiple world map views using individual tabs.

    Attributes:
        ui (UserInterface): Reference to the main UI for access to shared data.
        database (IOSystem): Reference to the application's data source.
        map_tabs (QTabWidget): Tab widget to host multiple map configuration tabs.
    """
    def __init__(self, ui, parent=None):
        """
        Initializes the world map tab interface with dynamic sub-tabs for maps.

        Args:
            ui (UserInterface): The main UI object providing shared state and access.
            parent (QWidget, optional): Optional parent widget for hierarchy. Defaults to None.
        """
        super().__init__(parent)
        self.ui = ui
        self.database = self.ui.database

        # Create vertical layout for the entire tab
        layout = QVBoxLayout(self)

        # 1) QTabWidget setup to manage map config tabs
        self.map_tabs = QTabWidget()
        self.map_tabs.setTabsClosable(True)  # Enable close buttons on tabs
        self.map_tabs.tabCloseRequested.connect(self.on_tab_close_requested)
        self.map_tabs.tabBarClicked.connect(self.on_tab_clicked)

        # Apply custom styling to close buttons if needed (placeholder for stylesheet)
        self.map_tabs.setStyleSheet(f"""""")

        # 2) Add first map config tab and a "+" tab for creating new tabs
        self.add_map_tab()      # Adds an initial configurable map tab
        self._add_plus_tab()    # Adds a special "+" tab to open new tabs

        # Add the tab widget to the layout
        layout.addWidget(self.map_tabs)

    def _add_plus_tab(self):
        """
        Adds a special "+" tab at the end of the tab bar that acts as a button to create new tabs.
        This tab cannot be closed and is visually distinguished by its '+' label.
        """
        # Create an empty widget to serve as the "+" tab content (never shown)
        plus_widget = QWidget()

        # Add it as a new tab labeled "+" and store its index
        idx = self.map_tabs.addTab(plus_widget, "+")

        # Disable the close button specifically for the "+" tab
        self.map_tabs.tabBar().setTabButton(idx, QTabBar.RightSide, None)

    def on_tab_clicked(self, index):
        """
        Handles clicks on the tab bar.
        If the '+' tab is clicked (last tab), a new map configuration tab is added.
        
        Args:
            index (int): Index of the clicked tab.
        """
        # If the clicked tab is the '+' tab (last one), create a new MapConfigTab
        if index == self.map_tabs.count() - 1:
            self.add_map_tab()

    def on_tab_close_requested(self, index):
        """
        Handles the request to close a tab.
        Prevents closing the last content tab or the '+' tab.

        Args:
            index (int): Index of the tab to be closed.
        """
        # Total number of actual content tabs (excluding the '+' tab)
        content_count = self.map_tabs.count() - 1

        # Do not allow closing if there's only one content tab left
        if content_count <= 1:
            return

        # Prevent closing the '+' tab at the end
        if index == self.map_tabs.count() - 1:
            return

        # Remove the selected tab
        self.map_tabs.removeTab(index)

    def add_map_tab(self):
        """
        Adds a new MapConfigTab to the QTabWidget before the '+' tab.
        Automatically switches focus to the newly added tab.
        """
        # Create a new map configuration tab, passing the UI and tab widget as parent
        new_tab = MapConfigTab(self.ui, parent=self.map_tabs)

        # Insert the new tab just before the '+' tab (always the last one)
        insert_at = self.map_tabs.count() - 1
        idx = self.map_tabs.insertTab(insert_at, new_tab, new_tab.name)

        # Set focus to the newly added tab
        self.map_tabs.setCurrentIndex(idx)


class BarChartTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("This is inner tab 3 content."))