import sys
import logging

from src.IOSystem import IOSystem
from src.SupplyChain import SupplyChain
from src.SelectionTab import SelectionTab
from src.SettingsTab import SettingsTab
from src.VisualisationTab import VisualisationTab

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QTabWidget, QWidget, QVBoxLayout, QHBoxLayout,
    QGroupBox, QLabel, QComboBox, QPushButton, QSplitter, QTreeWidget,
    QTreeWidgetItem, QScrollArea, QTextEdit
)
from PyQt5.QtCore import Qt


class UserInterface(QMainWindow):
    def __init__(self):
        super().__init__()
        # load database without logging UI
        self.database = IOSystem(year=2022, language="german").load()
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Exiobase Explorer")
        self.resize(800,450)
        central = QWidget(self)
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(20,20,20,20)
        layout.setSpacing(20)
        self.tab_widget = QTabWidget(self)
        # Add tabs as separate objects
        self.selection_tab = SelectionTab(self.database)
        self.settings_tab = SettingsTab()
        self.visualisation_tab = VisualisationTab()
        self.tab_widget.addTab(self.selection_tab, "Selection")
        self.tab_widget.addTab(self.settings_tab, "Settings")
        self.tab_widget.addTab(self.visualisation_tab, "Visualisation")
        layout.addWidget(self.tab_widget)
        self._create_menu_bar()
        self.show()

    def _create_menu_bar(self):
        self.menuBar()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = UserInterface()
    sys.exit(app.exec_())