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
    def __init__(self):
        super().__init__()
        self.database = IOSystem(year=2022, language="Deutsch").load()
        self.database.Index.copy_configs()
        self.general_dict = self.database.Index.general_dict
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Exiobase Explorer")
        self.resize(800,450)
        central = QWidget(self)
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(20,20,20,20)
        layout.setSpacing(20)

        # Add tabs as separate objects
        self.selection_tab = SelectionTab(self.database)
        self.visualisation_tab = VisualisationTab(self.database, self)
        self.settings_tab = SettingsTab(self.database)

        # Connects tabs
        self.set_parent()

        # Show tabs
        self.tabs = QTabWidget()
        self.tabs.addTab(self.selection_tab, self.general_dict["Selection"])
        self.tabs.addTab(self.visualisation_tab, self.general_dict["Visualisation"])
        self.tabs.addTab(self.settings_tab, self.general_dict["Settings"])

        layout.addWidget(self.tabs)
        self._create_menu_bar()
        self.show()

    def _create_menu_bar(self):
        self.menuBar()
    
    def set_parent(self):
        self.settings_tab.set_parent_ui(self)
        self.selection_tab.set_parent_ui(self)

    def reload_selection_tab(self):
        self.tabs.removeTab(0)
        self.selection_tab = SelectionTab(self.database)
        self.tabs.insertTab(0, self.selection_tab, self.general_dict["Selection"])
        self.set_parent()

    def reload_visualisation_tab(self):
        self.tabs.removeTab(1)
        self.visualisation_tab = VisualisationTab(self.database, self)
        self.tabs.insertTab(1, self.visualisation_tab, self.general_dict["Visualisation"])
        self.set_parent()

    def reload_settings_tab(self):
        self.tabs.removeTab(2)
        self.settings_tab = SettingsTab(self.database)
        self.tabs.insertTab(2, self.settings_tab, self.general_dict["Settings"])
        self.set_parent()

    def reload_tabs(self):
        self.general_dict = self.database.Index.general_dict
        self.reload_selection_tab()
        self.reload_visualisation_tab()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = UserInterface()
    sys.exit(app.exec_())