import logging
import os
import re

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
        super().__init__()
        self.database = database
        self.general_dict = self.database.Index.general_dict

        # Set up logger
        self.log_handler = QTextEditLogger()
        logging.getLogger().addHandler(self.log_handler)
        logging.getLogger().setLevel(logging.INFO)

        # Fetch languages and years
        self.get_languages()
        self.get_years()
        
        # Initialize UI components
        self.init_ui()

    def set_parent_ui(self, ui):
        """Set the parent UI (for refreshing other tabs)."""
        self.ui = ui

    def get_languages(self):
        """Fetch available languages from the database."""
        self.current_language = self.database.language
        self.languages = self.database.Index.languages

    def get_years(self):
        """Fetch available years from filenames in the specified directory."""
        self.current_year = str(self.database.year)
        self.years = []
        pattern = re.compile(r"Fast_IOT_(\d{4})_pxp")
        for filename in os.listdir(self.database.fast_dir):
            match = pattern.match(filename)
            if match:
                self.years.append(match.group(1))

    def init_ui(self):
        """Initialize the UI components for settings tab."""
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(20, 20, 20, 20)

        # General Settings Group
        general_group = QGroupBox(self.general_dict["General Settings"])
        v = QVBoxLayout(general_group)
        h = QHBoxLayout()

        # Language ComboBox
        self.language_combo = QComboBox()
        self.language_combo.addItems(self.languages)
        self.language_combo.setCurrentText(self.current_language)
        h.addWidget(QLabel(f"{self.general_dict['Language']}:"))
        h.addWidget(self.language_combo)

        # Year ComboBox
        self.year_combo = QComboBox()
        self.year_combo.addItems(self.years)
        self.year_combo.setCurrentText(self.current_year)
        h.addWidget(QLabel(f"{self.general_dict['Year']}:"))
        h.addWidget(self.year_combo)

        # Show Indices Checkbox
        self.show_indices_checkbox = QCheckBox(self.general_dict["Show Indices"])
        self.show_indices_checkbox.setChecked(True)  # Set to False later if needed
        h.addWidget(self.show_indices_checkbox)

        # Console Output
        v.addLayout(h)
        v.addWidget(self.log_handler.widget)

        # Add general group to main layout
        layout.addWidget(general_group)

        # Connect signals to handler methods
        self.language_combo.currentTextChanged.connect(self.on_language_changed)
        self.year_combo.currentTextChanged.connect(self.on_year_changed)

    def on_language_changed(self, text):
        """Handles language change event."""
        self.current_language = text
        self.database.switch_language(self.current_language)
        self.general_dict = self.database.Index.general_dict  # Update dictionary with new language

        # Reload tabs to reflect language changes
        self.ui.reload_tabs()

    def on_year_changed(self, text):
        """Handles year change event."""
        self.current_year = text
        self.database.switch_year(int(self.current_year))
        self.database.load()  # Load data for the selected year

        # Reload tabs to reflect the year change
        self.ui.reload_tabs()

    def is_show_indices_active(self):
        """Returns whether 'Show Indices' checkbox is active."""
        return self.show_indices_checkbox.isChecked()
