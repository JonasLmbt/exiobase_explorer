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
        layout = QVBoxLayout(self)
        layout.setSpacing(20)  # Set spacing between widgets
        layout.setContentsMargins(20, 20, 20, 20)  # Set margins around the layout

        # General Settings Group
        general_group = QGroupBox(self.general_dict["General Settings"])  # Group box for general settings
        v = QVBoxLayout(general_group)  # Vertical layout for the group box
        h = QHBoxLayout()  # Horizontal layout for individual settings

        # Language ComboBox
        self.language_combo = QComboBox()  # ComboBox for language selection
        self.language_combo.addItems(self.languages)  # Populate with available languages
        self.language_combo.setCurrentText(self.current_language)  # Set the current language
        h.addWidget(QLabel(f"{self.general_dict['Language']}:"))  # Label for language selection
        h.addWidget(self.language_combo)  # Add the combo box to the horizontal layout

        # Year ComboBox
        self.year_combo = QComboBox()  # ComboBox for year selection
        self.year_combo.addItems(self.years)  # Populate with available years
        self.year_combo.setCurrentText(self.current_year)  # Set the current year
        h.addWidget(QLabel(f"{self.general_dict['Year']}:"))  # Label for year selection
        h.addWidget(self.year_combo)  # Add the combo box to the horizontal layout

        # Show Indices Checkbox
        self.show_indices_checkbox = QCheckBox(self.general_dict["Show Indices"])  # Checkbox for showing indices
        self.show_indices_checkbox.setChecked(True)  # Default checked state, can be set to False later if needed
        h.addWidget(self.show_indices_checkbox)  # Add the checkbox to the horizontal layout

        # Console Output Section (log handler widget)
        v.addLayout(h)  # Add the horizontal layout to the vertical layout
        v.addWidget(self.log_handler.widget)  # Add the logging widget to the layout

        # Add the general settings group to the main layout
        layout.addWidget(general_group)

        # Connect signals to handler methods
        self.language_combo.currentTextChanged.connect(self.on_language_changed)  # Signal for language change
        self.year_combo.currentTextChanged.connect(self.on_year_changed)  # Signal for year change

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

        # Switch year in the database and reload data for the selected year
        self.database.switch_year(int(self.current_year))
        self.database.load()  # Reload data for the selected year

        # Restore the cursor after processing is complete
        QApplication.restoreOverrideCursor()

    def is_show_indices_active(self):
        """Returns whether 'Show Indices' checkbox is active."""
        return self.show_indices_checkbox.isChecked()
