import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas

from PyQt5.QtWidgets import (
    QTabWidget, QWidget, QVBoxLayout, 
    QGroupBox, QLabel, QPushButton, 
)

class VisualisationTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        # Inner tab widget (Table, World Map, Bar Chart)
        self.inner_tab_widget = QTabWidget()

        # === Table Tab ===
        table_tab = QWidget()
        table_layout = QVBoxLayout(table_tab)

        impact_group = QGroupBox("Select Impacts")
        impact_layout = QVBoxLayout(impact_group)

        self.impact_button = QPushButton("Select Impacts")
        self.impact_button.clicked.connect(self.select_impacts)
        impact_layout.addWidget(self.impact_button)

        impact_group.setMaximumHeight(100)
        table_layout.addWidget(impact_group)

        # Add Matplotlib figure
        fig, ax = plt.subplots()
        ax.plot([0, 1, 2, 3], [10, 1, 20, 3])
        ax.set_title("Sample Plot")
        canvas = FigureCanvas(fig)
        table_layout.addWidget(canvas)

        # Add tabs to inner QTabWidget
        self.inner_tab_widget.addTab(table_tab, "Table")
        self.inner_tab_widget.addTab(QLabel("This is inner tab 2 content."), "World Map")
        self.inner_tab_widget.addTab(QLabel("This is inner tab 3 content."), "Bar Chart")

        layout.addWidget(self.inner_tab_widget)

    def select_impacts(self):
        print("Select Impacts clicked")