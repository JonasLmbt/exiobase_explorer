import sys
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QTabWidget, QWidget, QVBoxLayout, QHBoxLayout,
    QGroupBox, QLabel, QComboBox, QPushButton, QSplitter, QCheckBox, QScrollArea
)
from PyQt5.QtCore import Qt

class UserInterface(QMainWindow):
    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Exiobase Explorer")
        self.resize(800, 450)

        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)

        central_layout = QVBoxLayout(central_widget)
        central_layout.setContentsMargins(20, 20, 20, 20)
        central_layout.setSpacing(20)

        self.tab_widget = QTabWidget(self)
        self.create_selection_tab()
        central_layout.addWidget(self.tab_widget)

        self._create_menu_bar()
        self.show()

    def create_selection_tab(self):
        selection_tab = QWidget()
        selection_layout = QVBoxLayout(selection_tab)
        selection_layout.setSpacing(20)

        # === General Settings ===
        general_settings_group = QGroupBox("General Settings")
        gen_layout = QHBoxLayout(general_settings_group)
        self.language_combo = QComboBox()
        self.language_combo.addItems(["English", "Deutsch", "Français", "Español"])
        self.year_combo = QComboBox()
        self.year_combo.addItems(["2021", "2022", "2023", "2024"])
        gen_layout.addWidget(QLabel("Language:"))
        gen_layout.addWidget(self.language_combo)
        gen_layout.addWidget(QLabel("Year:"))
        gen_layout.addWidget(self.year_combo)
        selection_layout.addWidget(general_settings_group)

        # === Region/Sector Widget ===
        region_sector_widget = QWidget()
        rs_layout = QHBoxLayout(region_sector_widget)
        rs_layout.setSpacing(20)
        rs_layout.setContentsMargins(0, 0, 0, 0)

        # === Region Selection ===
        region_group = QGroupBox("Region Selection")
        region_layout = QVBoxLayout(region_group)
        region_layout.setContentsMargins(0, 0, 0, 0)
        region_layout.setSpacing(8)

        region_scroll = QScrollArea()
        region_scroll.setWidgetResizable(True)
        region_container = QWidget()
        region_container_layout = QVBoxLayout(region_container)
        region_container_layout.setContentsMargins(0, 0, 0, 0)
        region_container_layout.setSpacing(8)

        regions = [
            "Germany", "France", "Spain", "Italy", "Poland",
            "Netherlands", "Belgium", "Portugal", "Greece", "Austria",
            "Sweden", "Norway", "Finland", "Denmark", "Ireland",
            "Switzerland", "Czech Republic", "Hungary", "Slovakia", "Slovenia",
            "Croatia", "Bulgaria", "Romania", "Estonia", "Latvia",
            "Lithuania", "Luxembourg", "United Kingdom", "USA", "China"
        ]

        self.region_checkboxes = []
        for name in regions:
            cb = QCheckBox(name)
            self.region_checkboxes.append(cb)
            region_container_layout.addWidget(cb)

        region_scroll.setWidget(region_container)
        region_layout.addWidget(region_scroll)

        region_button_layout = QHBoxLayout()
        btn_clear_region = QPushButton("Clear Region Selection")
        btn_clear_region.clicked.connect(self.clear_region_selection)
        btn_select_all_region = QPushButton("Select All Regions")
        btn_select_all_region.clicked.connect(self.select_all_regions)
        region_button_layout.addWidget(btn_clear_region)
        region_button_layout.addWidget(btn_select_all_region)
        region_layout.addLayout(region_button_layout)

        # === Sector Selection ===
        sector_group = QGroupBox("Sector Selection")
        sector_layout = QVBoxLayout(sector_group)
        sector_layout.setContentsMargins(0, 0, 0, 0)
        sector_layout.setSpacing(8)

        sector_scroll = QScrollArea()
        sector_scroll.setWidgetResizable(True)
        sector_container = QWidget()
        sector_container_layout = QVBoxLayout(sector_container)
        sector_container_layout.setContentsMargins(0, 0, 0, 0)
        sector_container_layout.setSpacing(8)

        sectors = [
            "Agriculture", "Forestry", "Fishing", "Mining", "Industry",
            "Energy", "Construction", "Transport", "Retail", "Wholesale",
            "Finance", "Insurance", "Real Estate", "Education", "Healthcare",
            "Social Services", "Public Administration", "Defense", "Tourism", "Media",
            "Telecommunications", "Technology", "Environmental Services", "Waste Management", "Scientific R&D"
        ]

        self.sector_checkboxes = []
        for name in sectors:
            cb = QCheckBox(name)
            self.sector_checkboxes.append(cb)
            sector_container_layout.addWidget(cb)

        sector_scroll.setWidget(sector_container)
        sector_layout.addWidget(sector_scroll)

        sector_button_layout = QHBoxLayout()
        btn_clear_sector = QPushButton("Clear Sector Selection")
        btn_clear_sector.clicked.connect(self.clear_sector_selection)
        btn_select_all_sector = QPushButton("Select All Sectors")
        btn_select_all_sector.clicked.connect(self.select_all_sectors)
        sector_button_layout.addWidget(btn_clear_sector)
        sector_button_layout.addWidget(btn_select_all_sector)
        sector_layout.addLayout(sector_button_layout)

        rs_layout.addWidget(region_group)
        rs_layout.addWidget(sector_group)

        # === Bottom Widget (Summary + Buttons) ===
        bottom_widget = QWidget()
        bottom_layout = QVBoxLayout(bottom_widget)
        bottom_layout.setSpacing(10)
        bottom_layout.setContentsMargins(0, 0, 0, 0)

        self.summary_group = QGroupBox("Selection Summary")
        summary_layout = QVBoxLayout(self.summary_group)
        self.selection_label = QLabel("No selection made...")
        self.selection_label.setWordWrap(True)
        summary_scroll = QScrollArea()
        summary_scroll.setWidgetResizable(True)
        summary_scroll.setWidget(self.selection_label)
        summary_layout.addWidget(summary_scroll)
        bottom_layout.addWidget(self.summary_group)

        btn_layout = QHBoxLayout()
        self.apply_button = QPushButton("Apply Selection")
        self.apply_button.clicked.connect(self.apply_selection)
        self.reset_button = QPushButton("Reset All Selections")
        self.reset_button.clicked.connect(self.reset_selection)
        btn_layout.addWidget(self.apply_button)
        btn_layout.addWidget(self.reset_button)
        bottom_layout.addLayout(btn_layout)

        splitter = QSplitter(Qt.Vertical)
        splitter.setContentsMargins(0, 0, 0, 0)
        splitter.addWidget(region_sector_widget)
        splitter.addWidget(bottom_widget)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)

        selection_layout.addWidget(splitter)
        self.tab_widget.addTab(selection_tab, "Selection")

    def clear_region_selection(self):
        for cb in self.region_checkboxes:
            cb.setChecked(False)
        self.update_summary()

    def select_all_regions(self):
        for cb in self.region_checkboxes:
            cb.setChecked(True)
        self.update_summary()

    def clear_sector_selection(self):
        for cb in self.sector_checkboxes:
            cb.setChecked(False)
        self.update_summary()

    def select_all_sectors(self):
        for cb in self.sector_checkboxes:
            cb.setChecked(True)
        self.update_summary()

    def reset_selection(self):
        self.clear_region_selection()
        self.clear_sector_selection()
        self.selection_label.setText("No selection made...")
        self.summary_group.setTitle("Selection Summary")

    def apply_selection(self):
        lang = self.language_combo.currentText()
        yr = self.year_combo.currentText()
        selected_regions = [cb.text() for cb in self.region_checkboxes if cb.isChecked()]
        selected_sectors = [cb.text() for cb in self.sector_checkboxes if cb.isChecked()]

        all_regions_selected = len(selected_regions) == len(self.region_checkboxes)
        all_sectors_selected = len(selected_sectors) == len(self.sector_checkboxes)

        if all_regions_selected:
            selected_regions = ["(all regions – entire world)"]
        elif not selected_regions:
            selected_regions = ["(no regions selected – entire world)"]

        if all_sectors_selected:
            selected_sectors = ["(all sectors)"]
        elif not selected_sectors:
            selected_sectors = ["(no sectors selected - all sectors)"]

        self.selection_label.setText(
            f"&nbsp;&nbsp;&nbsp;&nbsp;<b>Language:</b> {lang}, <b>Year:</b> {yr}<br>"
            f"&nbsp;&nbsp;&nbsp;&nbsp;<b>Regions:</b> {', '.join(selected_regions)}<br>"
            f"&nbsp;&nbsp;&nbsp;&nbsp;<b>Sectors:</b> {', '.join(selected_sectors)}"
        )
        self.summary_group.setTitle("Selection Summary (saved)")

    def update_summary(self):
        selected_regions = [cb.text() for cb in self.region_checkboxes if cb.isChecked()]
        selected_sectors = [cb.text() for cb in self.sector_checkboxes if cb.isChecked()]

        all_regions_selected = len(selected_regions) == len(self.region_checkboxes)
        all_sectors_selected = len(selected_sectors) == len(self.sector_checkboxes)

        if (not selected_regions or all_regions_selected) and (not selected_sectors or all_sectors_selected):
            self.selection_label.setText("No selection made...")
        else:
            txt = ""
            if selected_regions and not all_regions_selected:
                txt += f"<b>Regions:</b> {', '.join(selected_regions)}<br>"
            if selected_sectors and not all_sectors_selected:
                txt += f"<b>Sectors:</b> {', '.join(selected_sectors)}"
            self.selection_label.setText(txt)

    def _create_menu_bar(self):
        self.menuBar()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = UserInterface()
    sys.exit(app.exec_())
