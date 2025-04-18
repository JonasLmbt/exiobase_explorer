import sys
import logging

from src.IOSystem import IOSystem
from src.SupplyChain import SupplyChain
from src.SelectionTab import SelectionTab
from src.SettingsTab import SettingsTab
from src.VisualisationTab import VisualisationTab

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QTabWidget, QWidget, QVBoxLayout, QHBoxLayout
)


class UserInterface(QMainWindow):
    def __init__(self):
        super().__init__()
        self.database = IOSystem(year=2022, language="Deutsch").load()
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
        self.visualisation_tab = VisualisationTab(self.database)
        self.settings_tab = SettingsTab(self.database)

        # Show tabs
        self.tabs = QTabWidget()
        self.tabs.addTab(self.selection_tab, "Selection")
        self.tabs.addTab(self.visualisation_tab, "Visualisation")
        self.tabs.addTab(self.settings_tab, "Settings")

        # Connects tabs
        self.settings_tab.set_parent_ui(self)
        self.selection_tab.set_parent_ui(self)

        layout.addWidget(self.tabs)
        self._create_menu_bar()
        self.show()

    def _create_menu_bar(self):
        self.menuBar()
    
    def reload_selection_tab(self):
        logging.info("SelectionTab wird neu erstellt...")
        # Entferne alten Tab (Index kann sich ändern, evtl. dynamisch abfragen!)
        self.tabs.removeTab(0)
        # Erstelle neuen SelectionTab
        self.selection_tab = SelectionTab(self.database)
        self.tabs.insertTab(0, self.selection_tab, "Selection")

    def reload_visualisation_tab(self):
        logging.info("VisualisationTab wird neu erstellt...")
        # Entferne alten Tab (Index kann sich ändern, evtl. dynamisch abfragen!)
        self.tabs.removeTab(1)
        # Erstelle neuen SelectionTab
        self.visualisation_tab = SelectionTab(self.database)
        self.tabs.insertTab(1, self.visualisation_tab, "Selection")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = UserInterface()
    sys.exit(app.exec_())