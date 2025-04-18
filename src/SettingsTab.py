import logging

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QGroupBox, QLabel, QComboBox, 
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
    def __init__(self):
        super().__init__()
        # set up logger
        self.log_handler = QTextEditLogger()
        logging.getLogger().addHandler(self.log_handler)
        logging.getLogger().setLevel(logging.INFO)
        self.current_language = "English"
        self.current_year = "2021"
        self.init_ui()

    def get_languages(self):
        self.current_language = "exiobase"
        pass

    def get_years(self):
        pass

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(20, 20, 20, 20)

        # General Settings in Settings tab
        general_group = QGroupBox("General Settings")
        v = QVBoxLayout(general_group)
        h = QHBoxLayout()
        self.language_combo = QComboBox()
        self.language_combo.addItems(["English", "Deutsch", "Français", "Español"])
        self.year_combo = QComboBox()
        self.year_combo.addItems(["2021", "2022", "2023", "2024"])
        h.addWidget(QLabel("Language:"))
        h.addWidget(self.language_combo)
        h.addWidget(QLabel("Year:"))
        h.addWidget(self.year_combo)
        v.addLayout(h)
        v.addWidget(self.log_handler.widget)

        # Connect signals to handler methods
        self.language_combo.currentTextChanged.connect(self.on_language_changed)
        self.year_combo.currentTextChanged.connect(self.on_year_changed)

        layout.addWidget(general_group)
        layout.addWidget(QLabel("Additional settings..."))

    def on_language_changed(self, text):
        self.current_language = text
        print(f"Language changed to {text}")

    def on_year_changed(self, text):
        self.current_year = text
        print(f"Year changed to {text}")
