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
    root = {}
    for keys in multiindex:
        current = root
        for key in keys:
            current = current.setdefault(key, {})
    return root

class VisualisationTab(QWidget):
    def __init__(self, database, ui, parent=None):
        super().__init__(parent)
        self.ui = ui
        self.database = database  
        self.general_dict = self.database.Index.general_dict
        self._init_ui()  # UI wird nach der Initialisierung des Attributs aufgerufen

    def _init_ui(self):
        layout = QVBoxLayout(self)

        # Inner tab widget (Table, World Map, Bar Chart)
        self.inner_tab_widget = QTabWidget()

        # Add tabs to inner QTabWidget using new classes
        self.inner_tab_widget.addTab(TableTab(self.database, ui=self.ui), self.general_dict["Supply Chain Analysis"])
        self.inner_tab_widget.addTab(WorldMapTab(), self.general_dict["World Map"])
        self.inner_tab_widget.addTab(BarChartTab(), self.general_dict["Total"])

        layout.addWidget(self.inner_tab_widget)
    



class TableTab(QWidget):
    def __init__(self, database, ui, parent=None):
        super().__init__(parent)
        self.ui = ui
        self.database = database
        self.general_dict = self.database.Index.general_dict
        self.impact_hierarchy = multiindex_to_nested_dict(database.Index.impact_multiindex)
        
        # Set the default values for impacts (Dummy data as standard)
        self.saved_defaults = {
            self.database.impacts[3]: True, # Treibhausgasemissionen
            self.database.impacts[32]: True, # Wasserverbrauch
            self.database.impacts[125]: True, # Landnutzung
            self.database.impacts[0]: True, # Wertschöpfung
            self.database.impacts[2]: True # Arbeitszeit
        }
        self.selected_impacts = [k for k, v in self.saved_defaults.items() if v]
        
        layout = QVBoxLayout(self)

        impact_group = QGroupBox(self.general_dict["Select Impacts"])
        impact_layout = QVBoxLayout(impact_group)

        self.impact_button = QPushButton(self.general_dict["Select Impacts"])
        self.impact_button.setText(f"{self.general_dict['Selected']} ({sum(self.saved_defaults.values())})")
        self.impact_button.clicked.connect(self.select_impacts)
        impact_layout.addWidget(self.impact_button)

        impact_group.setMaximumHeight(100)
        layout.addWidget(impact_group)

        self.canvas = None
        self.plot_area = QVBoxLayout()
        layout.addLayout(self.plot_area)

        self.plot_button = QPushButton(self.general_dict["Update Plot"])
        self.plot_button.clicked.connect(self.update_plot)
        layout.addWidget(self.plot_button)

        self.setLayout(layout)

    def set_parent_ui(self, ui):
        """Set the parent UI (for refreshing other tabs)."""
        self.ui = ui

    def update_plot(self):
        QApplication.setOverrideCursor(Qt.WaitCursor)
        if self.canvas:
            self.plot_area.removeWidget(self.canvas)
            self.canvas.setParent(None)
            self.canvas.deleteLater()  

        if self.ui.selection_tab.inputByIndices:
            supplychain = SupplyChain(self.database, indices=self.ui.selection_tab.indices)
        else:  
            supplychain = SupplyChain(self.database, **self.ui.selection_tab.kwargs)
        fig = supplychain.plot_supply_chain(self.selected_impacts, size=1, lines=True, line_width=1, line_color="gray", text_position="center")
        self.canvas = FigureCanvas(fig)
        self.plot_area.addWidget(self.canvas)
        self.canvas.draw()  
        QApplication.restoreOverrideCursor()


    def select_impacts(self):
        current_selection = self.saved_defaults.copy()
        previous_defaults = self.saved_defaults.copy()
        dialog = QDialog(self)
        dialog.setWindowTitle(self.general_dict["Select Impacts"])
        dialog.setMinimumSize(350, 300)
        layout = QVBoxLayout(dialog)

        layout.addWidget(QLabel(f"{self.general_dict['Select Impacts']}:"))

        def add_tree_items(parent, data, level=0):
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