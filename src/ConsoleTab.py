import sys
import code
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QTextEdit, QPushButton, QHBoxLayout, QLabel
)
from PyQt5.QtCore import Qt, QEvent
from PyQt5.QtGui import QTextCursor

from src.IOSystem import IOSystem
from src.SupplyChain import SupplyChain


class ConsoleTab(QWidget):
    """
    Tab providing an interactive Python console within the application.

    Attributes:
        ui (QWidget): Reference to the main UI to access shared components and translations.
        general_dict (dict): Dictionary containing localized UI text.
        context (dict): The local context (variables/functions) available in the interactive console.
        console (InteractiveConsole): Instance of an interactive Python interpreter.
    """ 
    def __init__(self, context: dict = None, ui=None):
        """
        Initialize the console tab with optional context and reference to UI.

        Args:
            context (dict, optional): Dictionary of predefined variables for the console. Defaults to None.
            ui (QWidget, optional): Reference to the main UI object. Defaults to None.
        """
        super().__init__()

        # Store reference to main UI (used for shared state and translations)
        self.ui = ui

        # Access the translation dictionary from UI
        self.general_dict = self.ui.general_dict

        # Set the execution context for the console; use an empty dict if none provided
        self.context = context or {}

        # Create an instance of the interactive console with the given context
        self.console = code.InteractiveConsole(self.context)

        # Initialize the layout and widgets for this tab
        self.init_ui()

    def init_ui(self):
        """
        Initialize the user interface for the ConsoleTab.

        Sets up the layout with a label, an output text area, an input box,
        and a button to execute Python code within the console context.
        """
        # Create a vertical layout for the entire tab
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # Add a label to indicate the purpose of this tab
        layout.addWidget(QLabel(self.general_dict["Interactive Console"]))

        # Create a read-only text area for output display
        self.output = QTextEdit()
        self.output.setReadOnly(True)
        layout.addWidget(self.output)

        # Horizontal layout to hold the input box and execute button
        input_layout = QHBoxLayout()

        # Input text area for user to enter Python code
        self.input = QTextEdit()
        self.input.setFixedHeight(50)  # Limit height to a single code block
        self.input.installEventFilter(self)  # Enable custom keypress handling (e.g., Shift+Enter)
        input_layout.addWidget(self.input)

        # Button to execute the code written in the input box
        self.execute_button = QPushButton(self.general_dict["Execute"])
        self.execute_button.clicked.connect(self.execute_code)  # Connect button to handler
        input_layout.addWidget(self.execute_button)

        # Add the input layout (input + button) to the main layout
        layout.addLayout(input_layout)

    def eventFilter(self, obj, event):
        """
        Capture and handle specific key events for the input text box.

        Executes the code when the user presses Enter (without Shift),
        while allowing Shift+Enter to insert a new line.
        """
        # Check if the event is a key press on the input field
        if obj is self.input and event.type() == QEvent.KeyPress:
            # If Enter is pressed without Shift, trigger code execution
            if event.key() == Qt.Key_Return and not (event.modifiers() & Qt.ShiftModifier):
                self.execute_button.click()  # Simulate a click on the Execute button
                return True  # Event handled

        # For all other cases, use default event processing
        return super().eventFilter(obj, event)

    def execute_code(self):
        """
        Execute the Python code entered in the input field using an interactive console.

        Captures and redirects stdout/stderr to the output widget and handles multiline input.
        """
        code_string = self.input.toPlainText()  # Get code from input
        self.output.append(f">>> {code_string}")  # Display input code in output
        self.input.clear()  # Clear input field

        try:
            # Redirect standard output and error to the QTextEdit
            old_stdout = sys.stdout
            old_stderr = sys.stderr
            sys.stdout = self._stdout_catcher = StreamCatcher(self.output)
            sys.stderr = self._stdout_catcher

            # Push code to the interactive console and check if more input is needed
            more = self.console.push(code_string)
            if more:
                self.output.append(f"... ({self.general_dict['more input needed']})")  # Indicate incomplete input

        except Exception as e:
            # Display any exception raised during execution
            self.output.append(f"{self.general_dict['Error']}: {str(e)}")

        finally:
            # Restore original stdout and stderr
            sys.stdout = old_stdout
            sys.stderr = old_stderr


class StreamCatcher:
    """
    A custom stream catcher that redirects text output to a QTextEdit widget.
    
    This class allows capturing standard output and error streams (stdout, stderr)
    and displaying them within a QTextEdit widget in the UI.
    """
    def __init__(self, output_widget):
        """
        Initializes the StreamCatcher with the specified output widget.
        
        Args:
            output_widget (QTextEdit): The QTextEdit widget where the captured text will be displayed.
        """
        self.output_widget = output_widget

    def write(self, text):
        """
        Write the captured text to the output widget.
        
        This method is called whenever new text is output to stdout or stderr.
        
        Args:
            text (str): The text to be written to the output widget.
        """
        self.output_widget.moveCursor(QTextCursor.End)  # Move cursor to the end
        self.output_widget.insertPlainText(text)  # Insert the text into the output widget
        self.output_widget.ensureCursorVisible()  # Ensure that the cursor is visible

    def flush(self):
        """
        This method is required for compatibility with file-like objects but is left empty,
        as there is no actual flushing needed for QTextEdit.
        """
        pass

