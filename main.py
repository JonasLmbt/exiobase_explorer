import sys

from src.IOSystem import IOSystem
from src.SupplyChain import SupplyChain
from src.SelectionTab import SelectionTab
from src.SettingsTab import SettingsTab
from src.VisualisationTab import VisualisationTab

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QTabWidget, QWidget, QVBoxLayout,
)

class UserInterface(QMainWindow):
    """
    A class to represent the user interface of the application.
    It initializes the UI and loads the necessary data from the IOSystem.

    Attributes:
        database (IOSystem): An instance of the IOSystem class, used to load the database.
        general_dict (dict): A dictionary containing general configurations from the database.
    """
    
    def __init__(self):
        """
        Initializes the UserInterface class, loads the database,
        copies configurations, and sets up the UI.
        """
        super().__init__()

        # Load the database using IOSystem, with specified year and language.
        self.database = IOSystem(year=2022, language="Deutsch").load()
        
        # Copy the configurations from the database index.
        self.database.Index.copy_configs()
        
        # Store the general dictionary from the database index.
        self.general_dict = self.database.Index.general_dict
        
        # Initialize the user interface.
        self.init_ui()

    def init_ui(self):
        """
        Initializes the user interface elements such as the window title, layout,
        tabs, and menu bar. Also connects the various components (tabs) to the main UI.

        This method sets up the layout, creates tabs for selection, visualisation, 
        and settings, and then displays them in the main window.
        """
        # Set the window title.
        self.setWindowTitle("Exiobase Explorer")
        
        # Resize the main window.
        self.resize(800, 450)
        
        # Create the central widget and set it as the central widget of the main window.
        central = QWidget(self)
        self.setCentralWidget(central)
        
        # Create a vertical layout for the central widget.
        layout = QVBoxLayout(central)
        
        # Set the margins and spacing for the layout.
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        # Create tabs as separate objects.
        self.selection_tab = SelectionTab(self.database, self)
        self.visualisation_tab = VisualisationTab(self.database, self)
        self.settings_tab = SettingsTab(self.database, self)

        # Create a tab widget and add the tabs.
        self.tabs = QTabWidget()
        self.tabs.addTab(self.selection_tab, self.general_dict["Selection"])
        self.tabs.addTab(self.visualisation_tab, self.general_dict["Visualisation"])
        self.tabs.addTab(self.settings_tab, self.general_dict["Settings"])

        # Add the tab widget to the layout.
        layout.addWidget(self.tabs)

        # Create the menu bar.
        self._create_menu_bar()

        # Show the main window with the UI elements.
        self.show()

    def _create_menu_bar(self):
        """
        Creates the menu bar for the application.
        """
        # Initialize the menu bar.
        self.menuBar()
    
    def reload_selection_tab(self):
        """
        Reloads the selection tab by removing the existing tab and inserting a new one.
        
        This method removes the current selection tab at index 0, creates a new instance
        of the `SelectionTab`, and re-inserts it at the same position in the tab widget.
        """
        # Remove the existing selection tab (index 0).
        self.tabs.removeTab(0)
        
        # Create a new instance of the selection tab.
        self.selection_tab = SelectionTab(self.database)
        
        # Re-insert the new selection tab at index 0.
        self.tabs.insertTab(0, self.selection_tab, self.general_dict["Selection"])

    def reload_visualisation_tab(self):
        """
        Reloads the visualisation tab by removing the existing tab and inserting a new one.
        
        This method removes the current visualisation tab at index 1, creates a new instance
        of the `VisualisationTab`, and re-inserts it at the same position in the tab widget.
        """
        # Remove the existing visualisation tab (index 1).
        self.tabs.removeTab(1)
        
        # Create a new instance of the visualisation tab.
        self.visualisation_tab = VisualisationTab(self.database, self)
        
        # Re-insert the new visualisation tab at index 1.
        self.tabs.insertTab(1, self.visualisation_tab, self.general_dict["Visualisation"])

    def reload_settings_tab(self):
        """
        Reloads the settings tab by removing the existing tab and inserting a new one.
        
        This method removes the current settings tab at index 2, creates a new instance
        of the `SettingsTab`, and re-inserts it at the same position in the tab widget.
        """
        # Remove the existing settings tab (index 2).
        self.tabs.removeTab(2)
        
        # Create a new instance of the settings tab.
        self.settings_tab = SettingsTab(self.database)
        
        # Re-insert the new settings tab at index 2.
        self.tabs.insertTab(2, self.settings_tab, self.general_dict["Settings"])

    def reload_tabs(self):
        """
        Reloads all the tabs by updating the general dictionary and reloading each tab.
        
        This method updates the general dictionary from the database and reloads
        each of the tabs (selection, visualisation, and settings).
        """
        # Update the general dictionary from the database.
        self.general_dict = self.database.Index.general_dict
        
        # Reload each tab.
        self.reload_selection_tab()
        self.reload_visualisation_tab()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = UserInterface()
    sys.exit(app.exec_())