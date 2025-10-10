"""
main.py

This module serves as the entry point for the Exiobase Explorer application.
"""

import sys
import os
import logging

from src.IOSystem import IOSystem
from src.SupplyChain import SupplyChain
from src.GUI.SelectionTab import SelectionTab
from src.GUI.SettingsTab import SettingsTab
from src.GUI.VisualisationTab import VisualisationTab
from src.GUI.ConsoleTab import ConsoleTab

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QTabWidget, QWidget, QVBoxLayout, QDesktopWidget,
)

from PyQt5.QtGui import QIcon
from PyQt5.QtCore import Qt

# Configure logging for clear output
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)


class UserInterface(QMainWindow):
    """
    Main user interface class for the Exiobase Explorer application.

    This class manages the primary window, tabs, and core functionality of the application.
    It initializes the database connection, creates the user interface elements, and handles
    theme management based on system preferences.

    Attributes:
        iosystem (IOSystem): Database interface instance
        supplychain (SupplyChain): Supply chain analysis instance
        general_dict (Dict[str, Any]): General configuration dictionary
        tabs (QTabWidget): Main tab widget container
        selection_tab (SelectionTab): Data selection interface tab
        visualisation_tab (VisualisationTab): Data visualization tab
        settings_tab (SettingsTab): Application settings tab
        console_tab (ConsoleTab): Console interface tab
    """

    # Class constants for better maintainability
    DEFAULT_YEAR = 2022
    DEFAULT_LANGUAGE = "Deutsch"
    WINDOW_TITLE = "Exiobase Explorer"
    ICON_PATH = os.path.join("data", "exiobase_logo_2.png")  # Change to path of newest icon

    # Tab indices for consistent reference
    SELECTION_TAB_INDEX = 0
    VISUALISATION_TAB_INDEX = 1
    CONSOLE_TAB_INDEX = 2
    SETTINGS_TAB_INDEX = 3

    def __init__(self) -> None:
        """
        Initialize the UserInterface class.

        Sets up the database connection, initializes the supply chain,
        and creates the user interface elements.
        """
        super().__init__()
        logger.info("Initializing UserInterface")

        # Initialize core components
        self._initialize_database()
        self._initialize_supplychain()

        # Setup user interface
        self._setup_ui()

        logger.info("UserInterface initialization completed")

    def _initialize_database(self) -> None:
        """Initialize the database connection and load configurations."""
        try:
            logger.info(f"Loading database with year={self.DEFAULT_YEAR}, language={self.DEFAULT_LANGUAGE}")
            self.iosystem = IOSystem(year=self.DEFAULT_YEAR, language=self.DEFAULT_LANGUAGE).load()

            # Update configurations
            self.iosystem.index.copy_configs(output=False)
            self.general_dict = self.iosystem.index.general_dict

            logger.info("Database loaded and configured successfully")
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise

    def _initialize_supplychain(self) -> None:
        """Initialize the supply chain analysis component."""
        try:
            self.supplychain = SupplyChain(iosystem=self.iosystem)
            logger.info("SupplyChain initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize SupplyChain: {e}")
            raise

    def _setup_ui(self) -> None:
        """Set up the main user interface components."""
        self._configure_main_window()
        self._create_central_widget()
        self._create_tabs()
        self._create_menu_bar()

        # Show the window
        self.show()
        logger.info("User interface setup completed")
    
    def _translate(self, key: str, fallback: str) -> str:
        """Return localized string; always cast to str to avoid non-str labels."""
        val = self.general_dict.get(key, fallback)
        if val is None:
            return str(fallback)
        return str(val)

    def _configure_main_window(self) -> None:
        """Configure the main window properties with flexible sizing."""
        self.setWindowTitle(self.WINDOW_TITLE)

        # Set window icon
        icon_path = os.path.normpath(os.path.join(os.path.dirname(__file__), self.ICON_PATH))
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        else:
            logger.warning(f"Icon file not found: {icon_path}")

        # Set flexible window sizing
        screen = QDesktopWidget().availableGeometry()

        # Calculate initial size as percentage of screen
        initial_width = int(screen.width() * 0.8)  # Increased from 0.7 to 0.8
        initial_height = int(screen.height() * 0.8)  # Increased from 0.7 to 0.8

        # Set reasonable minimum sizes but allow full screen
        min_width = min(800, screen.width() - 50)   # Reduced margin from 100 to 50
        min_height = min(600, screen.height() - 50)  # Reduced margin from 100 to 50

        # Set size constraints - allow full screen
        self.setMinimumSize(min_width, min_height)
        # Remove maximum size constraint to allowfullscreen
        # self.setMaximumSize(screen.width(), screen.height())

        # Set initial size
        self.resize(initial_width, initial_height)

        # Center the window
        self._center_window()

    def _center_window(self) -> None:
        """Center the window on the screen."""
        screen = QDesktopWidget().availableGeometry()
        window_geometry = self.frameGeometry()

        # Calculate center position
        center_x = screen.center().x() - window_geometry.width() // 2
        center_y = screen.center().y() - window_geometry.height() // 2

        # Ensure window stays within screen bounds
        center_x = max(0, min(center_x, screen.width() - window_geometry.width()))
        center_y = max(0, min(center_y, screen.height() - window_geometry.height()))

        self.move(center_x, center_y)

    def _create_central_widget(self) -> None:
        """Create and configure the central widget with layout."""
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)

        # Create main layout with flexible margins
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(10, 15, 10, 10)  # Reduced margins for more space
        layout.setSpacing(5)  # Reduced spacing

        # Store layout reference
        self._main_layout = layout

    def _create_tabs(self) -> None:
        """Create and configure all application tabs."""
        try:
            # Initialize tab instances
            self.selection_tab = SelectionTab(self)
            self.visualisation_tab = VisualisationTab(self)
            self.settings_tab = SettingsTab(self)
            self.console_tab = ConsoleTab(context={"ui": self}, ui=self)

            # Create tab widget
            self.tabs = QTabWidget()

            # Allow tabs to be more flexible in size
            self.tabs.setUsesScrollButtons(True)
            self.tabs.setElideMode(Qt.ElideNone)  # Don't elide tab text
    
            # Add tabs in order
            self.tabs.addTab(self.selection_tab, self._translate("Selection", "Selection"))
            self.tabs.addTab(self.visualisation_tab, self._translate("Visualisation", "Visualisation"))
            self.tabs.addTab(self.console_tab, self._translate("Console", "Console"))
            self.tabs.addTab(self.settings_tab, self._translate("Settings", "Settings"))

            # Add tabs to main layout
            self._main_layout.addWidget(self.tabs)

            logger.info("All tabs created and configured successfully")
        except Exception as e:
            logger.error(f"Failed to create tabs: {e}")
            raise

    def _create_menu_bar(self) -> None:
        """Create the application menu bar."""
        try:
            menu_bar = self.menuBar()
            logger.info("Menu bar created successfully")
        except Exception as e:
            logger.error(f"Failed to create menu bar: {e}")
            raise

    def reload_selection_tab(self) -> None:
        """Reload the selection tab with a new instance."""
        try:
            logger.info("Reloading selection tab")

            # Remove existing tab
            self.tabs.removeTab(self.SELECTION_TAB_INDEX)

            # Create new instance
            self.selection_tab = SelectionTab(self)

            # Insert at correct position
            self.tabs.insertTab(
                self.SELECTION_TAB_INDEX,
                self.selection_tab,
                self._translate("Selection", "Selection")
            )

            logger.info("Selection tab reloaded successfully")
        except Exception as e:
            logger.error(f"Failed to reload selection tab: {e}")
            raise

    def reload_visualisation_tab(self) -> None:
        """Reload the visualisation tab with a new instance."""
        try:
            logger.info("Reloading visualisation tab")

            # Remove existing tab
            self.tabs.removeTab(self.VISUALISATION_TAB_INDEX)

            # Create new instance
            self.visualisation_tab = VisualisationTab(self)

            # Insert at correct position
            self.tabs.insertTab(
                self.VISUALISATION_TAB_INDEX,
                self.visualisation_tab,
                self._translate("Visualisation", "Visualisation")
            )

            logger.info("Visualisation tab reloaded successfully")
        except Exception as e:
            logger.error(f"Failed to reload visualisation tab: {e}")
            raise

    def reload_console_tab(self) -> None:
        """Reload the console tab with a new instance."""
        try:
            logger.info("Reloading console tab")

            # Remove existing tab
            self.tabs.removeTab(self.CONSOLE_TAB_INDEX)

            # Create new instance
            self.console_tab = ConsoleTab(context={"ui": self}, ui=self)

            # Insert at correct position
            self.tabs.insertTab(
                self.CONSOLE_TAB_INDEX,
                self.console_tab,
                self._translate("Console", "Console")
            )

            logger.info("Console tab reloaded successfully")
        except Exception as e:
            logger.error(f"Failed to reload console tab: {e}")
            raise

    def reload_settings_tab(self) -> None:
        """Reload the settings tab with a new instance, preserving logger, checkbox state, theme and tab focus."""
        try:
            logger.info("Reloading settings tab")
            # Sicherung des Logger-Widgets und des Checkbox-Status
            log_widget = None
            show_indices_state = None
            if hasattr(self.settings_tab, 'log_handler'):
                log_widget = getattr(self.settings_tab.log_handler, 'widget', None)
            if hasattr(self.settings_tab, 'show_indices_checkbox'):
                show_indices_state = self.settings_tab.show_indices_checkbox.isChecked()
            # Aktuellen Tab-Index sichern
            current_tab_index = self.tabs.currentIndex()
            # Aktuelles Theme ermitteln
            theme_name = self.settings_tab.theme_combo.currentText() if hasattr(self.settings_tab, 'theme_combo') else self.general_dict.get("System Default", "System Default")
            # Tab entfernen
            self.tabs.removeTab(self.SETTINGS_TAB_INDEX)
            # Neue Instanz erzeugen
            self.settings_tab = SettingsTab(self, log_widget=log_widget, show_indices_state=show_indices_state, current_theme=theme_name)
            # Tab wieder einfügen
            self.tabs.insertTab(
                self.SETTINGS_TAB_INDEX,
                self.settings_tab,
                self._translate("Settings", "Settings")
            )
            # Tab-Fokus wiederherstellen, falls vorher SettingsTab aktiv war
            if current_tab_index == self.SETTINGS_TAB_INDEX:
                self.tabs.setCurrentIndex(self.SETTINGS_TAB_INDEX)
            else:
                self.tabs.setCurrentIndex(current_tab_index)
            logger.info("Settings tab reloaded successfully")
        except Exception as e:
            logger.error(f"Failed to reload settings tab: {e}")
            raise

    def reload_tabs(self) -> None:
        """
        Reload all tabs and update configurations.
        """
        try:
            logger.info("Reloading all tabs")

            # Update general dictionary
            self.general_dict = self.iosystem.index.general_dict

            # Reload all tabs
            self.reload_selection_tab()
            self.reload_visualisation_tab()
            self.reload_console_tab()
            self.reload_settings_tab()

            logger.info("All tabs reloaded successfully")
        except Exception as e:
            logger.error(f"Failed to reload tabs: {e}")
            raise

    def update_supplychain(self) -> None:
        """
        Update the supply chain analysis based on current selection criteria.
        """
        try:
            logger.info("Updating supply chain analysis")

            # Show wait cursor
            QApplication.setOverrideCursor(Qt.WaitCursor)

            try:
                # Determine input method
                if hasattr(self.selection_tab, 'inputByIndices') and self.selection_tab.inputByIndices:
                    logger.info("Creating SupplyChain using indices")
                    self.supplychain = SupplyChain(self.iosystem, indices=self.selection_tab.indices)
                else:
                    logger.info("Creating SupplyChain using keyword arguments")
                    self.supplychain = SupplyChain(self.iosystem, **self.selection_tab.kwargs)

                logger.info("Supply chain updated successfully")

            finally:
                # Always restore cursor
                QApplication.restoreOverrideCursor()

        except Exception as e:
            logger.error(f"Failed to update supply chain: {e}")
            QApplication.restoreOverrideCursor()
            raise

    def resizeEvent(self, event):
        """Handle window resize events to maintain proper layout."""
        super().resizeEvent(event)
        # Remove size constraints that were preventing fullscreen
        # The window can now resize freely


def main() -> int:
    """
    Main application entry point.

    Creates the QApplication instance, initializes the main window,
    and starts the event loop.

    Returns:
        int: Application exit code
    """
    try:
        logger.info("Starting Exiobase Explorer application")

        # Create QApplication instance
        app = QApplication(sys.argv)

        # Set application metadata
        app.setApplicationName("Exiobase Explorer")
        app.setApplicationVersion("1.0")
        app.setOrganizationName("Exiobase Team")

        # Enable high DPI support
        app.setAttribute(Qt.AA_EnableHighDpiScaling, True)
        app.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

        # Create main window
        window = UserInterface()

        # Start event loop
        exit_code = app.exec_()

        logger.info(f"Application exiting with code: {exit_code}")
        return exit_code

    except Exception as e:
        logger.critical(f"Critical error in main application: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())