import logging
import os
import re

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QGroupBox, QLabel, QComboBox, QCheckBox,
    QTextEdit, QApplication
)

from PyQt5.QtCore import Qt

class QTextEditLogger(logging.Handler):
    """
    A custom logging handler that emits log messages to a QTextEdit widget.
    This handler formats the log messages and appends them to the QTextEdit.
    """
    def __init__(self):
        """
        Initializes the QTextEditLogger instance and sets up the QTextEdit widget
        to display log messages.
        """
        # Initialize the base Handler class
        super().__init__()

        # Create a QTextEdit widget to display the log messages
        self.widget = QTextEdit()
        self.widget.setReadOnly(True)  # Set QTextEdit to read-only so users can't modify the logs

        # Set up the formatter for the log messages (including timestamp, level, and message)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        self.setFormatter(formatter)  # Apply the formatter to this handler

    def emit(self, record):
        """
        Emit the log message to the QTextEdit widget.
        
        This method formats the log record and appends the formatted message
        to the QTextEdit widget.
        """
        # Format the log record into a string
        msg = self.format(record)

        # Append the formatted message to the QTextEdit widget (on the GUI thread)
        self.widget.append(msg)


class SettingsTab(QWidget):
    """
    SettingsTab widget for displaying and adjusting application settings.
    This widget handles logging setup, fetching languages, years, and UI initialization.
    """
    def __init__(self, database, ui):
        """
        Initializes the SettingsTab widget.

        :param database: The database instance containing data for the settings.
        :param ui: The UI instance to link to the SettingsTab.
        """
        super().__init__()
        
        # Store references to the database and UI for later use
        self.database = database
        self.ui = ui
        
        # Access the general dictionary from the database for UI labels and text
        self.general_dict = self.database.Index.general_dict

        # Set up logging to capture logs in a QTextEdit widget
        self.log_handler = QTextEditLogger()  # Custom log handler to output to QTextEdit
        logging.getLogger().addHandler(self.log_handler)  # Add the custom log handler to the logger
        logging.getLogger().setLevel(logging.INFO)  # Set the logging level to INFO

        # Fetch available languages and years from the database
        self.get_languages()  # Method to retrieve languages
        self.get_years()  # Method to retrieve years
        
        # Initialize UI components such as buttons, labels, and other widgets
        self.init_ui()  # Method to initialize the UI

    def get_languages(self):
        """
        Fetch available languages from the database.
        This method retrieves the current language and all available languages
        from the database index.
        """
        # Set the current language from the database
        self.current_language = self.database.language
        
        # Retrieve all available languages from the database index
        self.languages = self.database.Index.languages

    def get_years(self):
        """
        Fetch available years from filenames in the specified directory.
        This method scans the directory for filenames matching a pattern
        and extracts the years from them.
        """
        # Set the current year from the database
        self.current_year = str(self.database.year)
        
        # Initialize an empty list to store the years
        self.years = []
        
        # Define the regular expression pattern to match filenames of the form "Fast_IOT_YYYY_pxp"
        pattern = re.compile(r"Fast_IOT_(\d{4})_pxp")
        
        # Iterate through the files in the specified directory
        for filename in os.listdir(self.database.fast_dir):
            match = pattern.match(filename)  # Try to match the pattern with the filename
            if match:
                # If a match is found, extract the year and append it to the years list
                self.years.append(match.group(1))

    def init_ui(self):
        """
        Initialize the UI components for the settings tab.
        This method sets up the layout, UI components, and connects necessary signals.
        """
        # Main vertical layout for the settings tab
        self.layout = QVBoxLayout(self)
        self.layout.setSpacing(20)  # Set spacing between widgets
        self.layout.setContentsMargins(20, 20, 20, 20)  # Set margins around the layout

        # Language and Year Group
        self.lang_year_group = QGroupBox(self.general_dict["General Settings"])
        self.lang_year_layout = QHBoxLayout(self.lang_year_group)
        self.lang_year_layout.setContentsMargins(10, 10, 10, 10)

        self.language_combo = QComboBox()
        self.language_combo.addItems(self.languages)
        self.language_combo.setCurrentText(self.current_language)
        self.language_label = QLabel(f"{self.general_dict['Language']}:")
        self.lang_year_layout.addWidget(self.language_label)
        self.lang_year_layout.addWidget(self.language_combo)

        self.year_combo = QComboBox()
        self.year_combo.addItems(self.years)
        self.year_combo.setCurrentText(self.current_year)
        self.year_label = QLabel(f"{self.general_dict['Year']}:")
        self.lang_year_layout.addWidget(self.year_label)
        self.lang_year_layout.addWidget(self.year_combo)

        self.layout.addWidget(self.lang_year_group)

        # Indices Options Group with a simple label
        self.options_group = QGroupBox(self.general_dict["Options"])
        self.options_layout = QHBoxLayout(self.options_group)
        self.options_layout.setContentsMargins(10, 10, 10, 10)

        self.show_indices_checkbox = QCheckBox(self.general_dict["Show Indices"])
        self.show_indices_checkbox.setChecked(True)
        self.options_layout.addWidget(self.show_indices_checkbox)

        self.darkmode_checkbox = QCheckBox("Darkmode")
        self.darkmode_checkbox.setChecked(False)  
        self.darkmode_checkbox.stateChanged.connect(self.on_darkmode_changed)
        self.options_layout.addWidget(self.darkmode_checkbox)

        self.layout.addWidget(self.options_group)

        # Console Output Section (log handler widget)
        self.layout.addWidget(self.log_handler.widget)

        # Connect signals to handler methods
        self.language_combo.currentTextChanged.connect(self.on_language_changed)  # Signal for language change
        self.year_combo.currentTextChanged.connect(self.on_year_changed)  # Signal for year change

        # Lightmode
        self.on_darkmode_changed(Qt.Unchecked, output=False)

    def on_language_changed(self, text):
        """
        Handler method for changing the language.
        Updates the current language, switches the language in the database,
        and reloads the tabs to reflect the changes.
        """
        # Update the current language
        self.current_language = text

        # Switch language in the database
        self.database.switch_language(self.current_language)

        # Update the general dictionary with the new language
        self.general_dict = self.database.Index.general_dict

        # Reload the UI tabs to reflect the language changes
        self.ui.reload_tabs()

        # Change the language of the Settings-Tab without reloading
        self.lang_year_group.setTitle(self.general_dict["General Settings"])
        self.language_label.setText(f"{self.general_dict['Language']}:")
        self.year_label.setText(f"{self.general_dict['Year']}:")

        self.options_group.setTitle(self.general_dict["Options"])
        self.show_indices_checkbox.setText(self.general_dict["Show Indices"])

        self.ui.tabs.setTabText(3, self.general_dict["Settings"])

    def on_year_changed(self, text):
        """
        Handler method for changing the year.
        Sets the cursor to a wait state, updates the selected year in the database,
        reloads the data for the new year, and restores the cursor.
        """
        # Set the cursor to a wait state (to indicate processing)
        QApplication.setOverrideCursor(Qt.WaitCursor)

        # Update the current year
        self.current_year = text
        logging.info(f"Switching to year {self.current_year}...")

        # Switch year in the database and reload data for the selected year
        self.database.switch_year(int(self.current_year))
        self.database.load()  # Reload data for the selected year

        # Restore the cursor after processing is complete
        QApplication.restoreOverrideCursor()

    def is_show_indices_active(self):
        """Returns whether 'Show Indices' checkbox is active."""
        return self.show_indices_checkbox.isChecked()

    def on_darkmode_changed(self, state, output=True):
        QApplication.setOverrideCursor(Qt.WaitCursor)
        if state == Qt.Checked:
            if output:
                logging.info(f"Enabled Darkmode.")
            QApplication.instance().setStyleSheet(self.ui.DARKMODE_STYLE)
        else:
            if output:
                logging.info(f"Disabled Darkmode.")
            QApplication.instance().setStyleSheet(self.ui.LIGHTMODE_STYLE)  
        QApplication.restoreOverrideCursor()
