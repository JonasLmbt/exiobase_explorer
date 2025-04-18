import logging

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QGroupBox, QLabel, QComboBox, QCheckBox,
    QTextEdit
)

class QTextEditLogger(logging.Handler):
    """Logging handler that emits logs to a QTextEdit widget."""
    def __init__(self):
        super().__init__()
        self.widget = QTextEdit()
        self.widget.setReadOnly(True)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        self.setFormatter(formatter)

    def emit(self, record):
        msg = self.format(record)
        # Ensure append happens on GUI thread
        self.widget.append(msg)

class SettingsTab(QWidget):
    def __init__(self, database):
        self.database = database
        super().__init__()
        # set up logger
        self.log_handler = QTextEditLogger()
        logging.getLogger().addHandler(self.log_handler)
        logging.getLogger().setLevel(logging.INFO)
        self.get_languages()
        self.get_years()
        self.init_ui()

    def set_parent_ui(self, ui):
        self.ui = ui

    def get_languages(self):
        self.current_language = self.database.language
        self.languages = self.database.Index.languages

    def get_years(self):
        self.current_year = str(self.database.year)
        self.years = ["2022", "2021", "2020", "2019"]

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(20, 20, 20, 20)

        # General Settings in Settings tab
        general_group = QGroupBox("General Settings")
        v = QVBoxLayout(general_group)
        h = QHBoxLayout()

        # Language
        self.language_combo = QComboBox()
        self.language_combo.addItems(self.languages)
        self.language_combo.setCurrentText(self.current_language)
        h.addWidget(QLabel("Language:"))
        h.addWidget(self.language_combo)
        
        
        # Year
        self.year_combo = QComboBox()
        self.year_combo.addItems(self.years)
        self.year_combo.setCurrentText(self.current_year)
        h.addWidget(QLabel("Year:"))
        h.addWidget(self.year_combo)

        # Show Indices
        self.show_indices_checkbox = QCheckBox("Show Indices")
        self.show_indices_checkbox.setChecked(True)  # Set to False later
        h.addWidget(self.show_indices_checkbox)

        # Console
        v.addLayout(h)
        v.addWidget(self.log_handler.widget)

        # Connect signals to handler methods
        self.language_combo.currentTextChanged.connect(self.on_language_changed)
        self.year_combo.currentTextChanged.connect(self.on_year_changed)

        layout.addWidget(general_group)
        layout.addWidget(QLabel("Additional settings..."))

    def on_language_changed(self, text):
        self.current_language = text
        self.database.switch_language(self.current_language)
        self.ui.reload_selection_tab()

    def on_year_changed(self, text):
        self.current_year = text
        self.database.switch_year(int(self.current_year))
        self.database.load()
        self.ui.reload_selection_tab()

    def is_show_indices_active(self):
        return self.show_indices_checkbox.isChecked()
