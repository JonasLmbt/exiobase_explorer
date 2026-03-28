import logging
import os
import re
import sys
import qdarktheme

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QGroupBox, QLabel, QComboBox, QCheckBox,
    QTextEdit, QApplication
)
from PyQt5.QtCore import Qt, pyqtSignal


class QTextEditLogger(logging.Handler):
    """
    A custom logging handler that emits log messages to a QTextEdit widget.
    """

    def __init__(self):
        """Initialize the QTextEditLogger instance."""
        super().__init__()

        # Create QTextEdit widget for log display
        self.widget = QTextEdit()
        self.widget.setReadOnly(True)

        # Set up formatter
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        self.setFormatter(formatter)

    def emit(self, record):
        """Emit the log message to the QTextEdit widget."""
        msg = self.format(record)
        self.widget.append(msg)


class SettingsTab(QWidget):
    """
    SettingsTab widget for displaying and adjusting application settings.
    """

    theme_changed = pyqtSignal(str)

    def __init__(self, ui, log_widget=None, show_indices_state=None, current_theme=None, export_with_background_state=None):
        """
        Initialize the SettingsTab widget.

        Args:
            ui (UserInterface): The UI instance to link to the SettingsTab.
            log_widget (QTextEdit, optional): Logger widget to reuse.
            show_indices_state (bool, optional): Checkbox state to reuse.
            current_theme (str, optional): Name of the current theme for ComboBox selection.
        """
        super().__init__()

        self.ui = ui
        self.iosystem = self.ui.iosystem
        self.general_dict = self.iosystem.index.general_dict
        self._current_theme = current_theme

        # Set up logging
        logger = logging.getLogger()
        # Entferne alle bestehenden QTextEditLogger-Handler
        for handler in list(logger.handlers):
            if isinstance(handler, QTextEditLogger):
                logger.removeHandler(handler)
        if log_widget is not None:
            self.log_handler = QTextEditLogger()
            self.log_handler.widget = log_widget
        else:
            self.log_handler = QTextEditLogger()
        logger.addHandler(self.log_handler)
        logger.setLevel(logging.INFO)

        self._get_languages()
        self._get_years()
        self._get_aggregations()

        self._init_ui(show_indices_state, export_with_background_state)

    def _translate(self, key, fallback):
        """Get text from general_dict with fallback."""
        return self.general_dict.get(key, fallback)

    def _get_languages(self):
        """Fetch available languages from the database."""
        self.current_language = self.iosystem.language
        self.languages = self.iosystem.index.languages

    def _get_aggregations(self):
        """Fetch available aggregations from config/aggregations/ subfolders."""
        self.current_aggregation = getattr(self.iosystem, 'aggregation', 'exiobase')
        self.aggregations = []
        try:
            agg_dir = os.path.join(self.iosystem.config_dir, 'aggregations')
            if os.path.exists(agg_dir):
                self.aggregations = sorted([
                    d for d in os.listdir(agg_dir)
                    if os.path.isdir(os.path.join(agg_dir, d))
                ])
        except Exception as e:
            logging.warning(f"Could not read aggregations directory: {e}")
        if not self.aggregations:
            self.aggregations = [self.current_aggregation]

    def _get_years(self):
        """Fetch available years from available fast databases."""
        self.current_year = str(self.iosystem.year)
        self.years = []

        try:
            years_int = []
            if hasattr(self.iosystem, "available_fast_db_years"):
                years_int = list(self.iosystem.available_fast_db_years() or [])
            self.years = [str(y) for y in sorted(set(years_int), reverse=True)]

            if self.current_year not in self.years:
                self.years.append(self.current_year)
                self.years.sort(reverse=True)

        except Exception as e:
            logging.warning(f"Could not determine available years: {e}")
            if self.current_year not in self.years:
                self.years.append(self.current_year)

    def _init_ui(self, show_indices_state=None, export_with_background_state=None):
        """Initialize the UI components."""
        layout = QVBoxLayout(self)

        general_group = self._create_general_settings_group()
        layout.addWidget(general_group)

        options_group = self._create_options_group(show_indices_state, export_with_background_state)
        layout.addWidget(options_group)

        console_group = QGroupBox(self._translate("Console Output", "Console Output"))
        console_layout = QVBoxLayout(console_group)
        console_layout.addWidget(self.log_handler.widget)
        layout.addWidget(console_group)

    def _create_general_settings_group(self):
        group = QGroupBox(self._translate("General Settings", "General Settings"))
        layout = QHBoxLayout(group)

        language_label = QLabel(f"{self._translate('Language', 'Language')}:")
        self.language_combo = QComboBox()
        self.language_combo.addItems(self.languages)
        self.language_combo.setCurrentText(self.current_language)
        self.language_combo.currentTextChanged.connect(self._on_language_changed)
        layout.addWidget(language_label)
        layout.addWidget(self.language_combo)

        aggregation_label = QLabel(f"{self._translate('Aggregation', 'Aggregation')}:")
        self.aggregation_combo = QComboBox()
        self.aggregation_combo.addItems(self.aggregations)
        self.aggregation_combo.setCurrentText(self.current_aggregation)
        self.aggregation_combo.currentTextChanged.connect(self._on_aggregation_changed)
        layout.addWidget(aggregation_label)
        layout.addWidget(self.aggregation_combo)

        year_label = QLabel(f"{self._translate('Year', 'Year')}:")
        self.year_combo = QComboBox()
        self.year_combo.addItems(self.years)
        self.year_combo.setCurrentText(self.current_year)
        self.year_combo.currentTextChanged.connect(self._on_year_changed)
        layout.addWidget(year_label)
        layout.addWidget(self.year_combo)

        return group

    def _create_options_group(self, show_indices_state=None, export_with_background_state=None):
        group = QGroupBox(self._translate("Options", "Options"))
        layout = QVBoxLayout(group)

        first_row = QHBoxLayout()
        self.show_indices_checkbox = QCheckBox(self._translate("Show Indices", "Show Indices"))
        if show_indices_state is not None:
            self.show_indices_checkbox.setChecked(show_indices_state)
        else:
            self.show_indices_checkbox.setChecked(True)
        first_row.addWidget(self.show_indices_checkbox)
        self.export_with_background_checkbox = QCheckBox(
            self._translate("Export graphics with background", "Export graphics with background")
        )
        if export_with_background_state is not None:
            self.export_with_background_checkbox.setChecked(bool(export_with_background_state))
        else:
            self.export_with_background_checkbox.setChecked(
                bool(getattr(self.ui, "export_graphics_with_background", False))
            )
        self.export_with_background_checkbox.toggled.connect(self._on_export_with_background_toggled)
        first_row.addWidget(self.export_with_background_checkbox)
        self.ui.export_graphics_with_background = bool(self.export_with_background_checkbox.isChecked())
        layout.addLayout(first_row)

        theme_row = QHBoxLayout()

        theme_label = QLabel(f"{self._translate('Theme', 'Theme')}:")
        self.theme_combo = QComboBox()
        self.theme_combo.addItems([
            self._translate("System Default", "System Default"),
            self._translate("Custom Light Mode", "Custom Light Mode"),
            self._translate("Custom Dark Mode", "Custom Dark Mode")
        ])
        # Setze den aktuellen Theme-Namen korrekt
        theme_name = self._get_current_theme_name()
        self.theme_combo.setCurrentText(theme_name)
        self.theme_combo.currentTextChanged.connect(self._on_theme_changed)

        theme_row.addWidget(theme_label)
        theme_row.addWidget(self.theme_combo)
        theme_row.addStretch()

        layout.addLayout(theme_row)

        return group

    def _get_current_theme_name(self):
        # Gibt den Namen für die Theme-ComboBox zurück
        if self._current_theme is not None:
            return self._current_theme
        # Fallback: System Default
        return self._translate("System Default", "System Default")

    def _on_language_changed(self, text):
        try:
            self.current_language = text
            self.iosystem.switch_language(self.current_language)
            self.general_dict = self.iosystem.index.general_dict
            self.ui.reload_tabs()
        except Exception as e:
            logging.error(f"Error changing language: {e}")

    def _on_aggregation_changed(self, text):
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            self.current_aggregation = text
            self.iosystem.switch_aggregation(self.current_aggregation)
            self.ui.reload_tabs()
        except Exception as e:
            logging.error(f"Error changing aggregation: {e}")
        finally:
            QApplication.restoreOverrideCursor()

    def _on_year_changed(self, text):
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            self.current_year = text
            self.iosystem.switch_year(int(self.current_year))
            self.ui.update_supplychain()
        except Exception as e:
            logging.error(f"Error changing year: {e}")
        finally:
            QApplication.restoreOverrideCursor()

    def _on_theme_changed(self, theme_text):
        """Handler for theme change using pyqtdarktheme load_stylesheet."""
        try:
            app = QApplication.instance()
            if app is None:
                return

            if theme_text == self._translate("Custom Dark Mode", "Custom Dark Mode"):
                app.setStyleSheet(qdarktheme.load_stylesheet("dark"))
                logging.info("Applied qdarktheme dark theme")
            elif theme_text == self._translate("Custom Light Mode", "Custom Light Mode"):
                app.setStyleSheet(qdarktheme.load_stylesheet("light"))
                logging.info("Applied qdarktheme light theme")
            else:  # System Default
                app.setStyleSheet("")
                app.setPalette(app.style().standardPalette())
                logging.info("Applied system default theme")
        except Exception as e:
            logging.error(f"Error changing theme: {e}")

    def _on_export_with_background_toggled(self, checked: bool):
        try:
            self.ui.export_graphics_with_background = bool(checked)
        except Exception as e:
            logging.error(f"Error changing export background option: {e}")

    def is_show_indices_active(self):
        return self.show_indices_checkbox.isChecked()

    def is_export_with_background_active(self):
        return self.export_with_background_checkbox.isChecked()
