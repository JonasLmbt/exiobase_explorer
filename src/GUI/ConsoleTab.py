import sys
import code
import io
from contextlib import redirect_stdout, redirect_stderr
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QTextEdit, QPushButton, QHBoxLayout,
    QLabel, QApplication, QGroupBox, QSplitter, QSizePolicy
)
from PyQt5.QtCore import Qt, QEvent
from PyQt5.QtGui import QTextCursor, QFont


class ConsoleTab(QWidget):
    """
    Tab providing an interactive Python console within the application.
    """

    def __init__(self, context: dict = None, ui=None):
        """
        Initialize the console tab.

        Args:
            context (dict, optional): Dictionary of predefined variables for the console.
            ui (QWidget, optional): Reference to the main UI object.
        """
        super().__init__()

        # Store references
        self.ui = ui
        self.general_dict = self.ui.general_dict if ui and hasattr(ui, 'general_dict') else {}

        # Set execution context
        self.context = context or {}

        # Create interactive console instance
        self.console = code.InteractiveConsole(self.context)

        # Track multi-line input
        self.multiline_buffer = []
        self.in_multiline = False

        # Initialize UI
        self._init_ui()

    def _get_text(self, key, fallback):
        """Get text from general_dict with fallback."""
        return self.general_dict.get(key, fallback)

    def _init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout(self)

        # Console description
        description_group = QGroupBox(self._get_text("Interactive Console", "Interactive Console"))
        description_layout = QVBoxLayout(description_group)
        # Improved user instruction
        description_layout.addWidget(
            QLabel(self._get_text("Enter Python code below. Press <b>Enter</b> to execute, use <b>Shift+Enter</b> for a new line within a multi-line statement.",
                                  "Enter Python code below. Press <b>Enter</b> to execute, use <b>Shift+Enter</b> for a new line within a multi-line statement."))
        )
        layout.addWidget(description_group)

        # Create splitter for resizable areas
        splitter = QSplitter(Qt.Vertical)

        # Output area
        output_widget = self._create_output_widget()
        splitter.addWidget(output_widget)

        # Input area
        input_widget = self._create_input_widget()
        splitter.addWidget(input_widget)

        # Set stretch factors (output gets more space)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 1)

        layout.addWidget(splitter)

    def _create_output_widget(self):
        """Create the output display widget."""
        output_group = QGroupBox(self._get_text("Output", "Output"))
        output_layout = QVBoxLayout(output_group)

        self.output = QTextEdit()
        self.output.setReadOnly(True)

        # Set larger monospace font for better readability
        font = QFont("Consolas", 12)
        if not font.exactMatch():
            font = QFont("Courier New", 12)
        self.output.setFont(font)

        # Set minimum height but allow resizing
        self.output.setMinimumHeight(80)

        output_layout.addWidget(self.output)

        # Clear button
        clear_button = QPushButton(self._get_text("Clear Output", "Clear Output"))
        clear_button.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        clear_button.clicked.connect(self.clear_output)
        output_layout.addWidget(clear_button)

        return output_group

    def _create_input_widget(self):
        """Create the input area widget."""
        input_group = QGroupBox(self._get_text("Input", "Input"))
        input_layout = QVBoxLayout(input_group)

        # Input text area
        self.input = QTextEdit()
        self.input.setMinimumHeight(80)

        # Set larger monospace font for input as well
        font = QFont("Consolas", 12)
        if not font.exactMatch():
            font = QFont("Courier New", 12)
        self.input.setFont(font)

        self.input.installEventFilter(self)
        input_layout.addWidget(self.input)

        # Execute button
        self.execute_button = QPushButton(self._get_text("Execute", "Execute"))
        self.execute_button.clicked.connect(self.execute_code)
        # Apply consistent size policy
        self.execute_button.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        input_layout.addWidget(self.execute_button)

        return input_group

    def eventFilter(self, obj, event):
        """Handle key events for the input field."""
        if obj is self.input and event.type() == QEvent.KeyPress:
            # Execute on Enter (without Shift)
            if event.key() == Qt.Key_Return and not (event.modifiers() & Qt.ShiftModifier):
                self.execute_button.click()
                return True

        return super().eventFilter(obj, event)

    def execute_code(self):
        """Execute the Python code entered in the input field."""
        QApplication.setOverrideCursor(Qt.WaitCursor)

        code_string = self.input.toPlainText().strip()

        if not code_string:
            QApplication.restoreOverrideCursor()
            return

        # Display the input with proper prompt
        if self.in_multiline:
            self.output.append(f"... {code_string}")
        else:
            self.output.append(f">>> {code_string}")

        self.input.clear()

        try:
            # Handle multi-line input
            self.multiline_buffer.append(code_string)
            full_code = '\n'.join(self.multiline_buffer)

            # Check if more input is needed
            try:
                # Try to compile the code
                compile(full_code, '<console>', 'exec')
                # If compilation succeeds, we have complete code
                more_needed = False
            except SyntaxError as e:
                if "unexpected EOF while parsing" in str(e) or "EOF while scanning" in str(e):
                    # More input needed
                    more_needed = True
                else:
                    # Real syntax error
                    more_needed = False
            except:
                # Other compilation errors
                more_needed = False

            if more_needed:
                self.in_multiline = True
                self.output.append("...")  # Indicate continuation
            else:
                # Execute the complete code
                self._execute_complete_code(full_code)
                self.multiline_buffer = []
                self.in_multiline = False

        except Exception as e:
            self.output.append(f"Error: {str(e)}")
            self.multiline_buffer = []
            self.in_multiline = False

        finally:
            QApplication.restoreOverrideCursor()

    def _execute_complete_code(self, code_string):
        """Execute complete, ready-to-run code."""
        # Capture stdout and stderr
        stdout_capture = io.StringIO()
        stderr_capture = io.StringIO()

        try:
            # Execute in the console's namespace
            with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
                # Use exec for multiple statements
                try:
                    # First try to eval (for expressions that return values)
                    result = eval(code_string, self.console.locals)
                    if result is not None:
                        print(result)
                except SyntaxError:
                    # If eval fails, use exec (for statements)
                    exec(code_string, self.console.locals)

            # Get captured output
            stdout_content = stdout_capture.getvalue()
            stderr_content = stderr_capture.getvalue()

            # Display output
            if stdout_content:
                # Remove trailing newline to avoid double spacing
                self.output.append(stdout_content.rstrip('\n'))

            if stderr_content:
                self.output.append(f"Error: {stderr_content.rstrip()}")

        except Exception as e:
            self.output.append(f"Error: {str(e)}")

        # Ensure cursor is visible
        self.output.ensureCursorVisible()

    def clear_output(self):
        """Clear the output area."""
        self.output.clear()
        self.multiline_buffer = []
        self.in_multiline = False

        # Add welcome message
        welcome_msg = self._get_text("Python Console - Ready", "Python Console - Ready")
        self.output.append(welcome_msg)
        self.output.append("=" * 40)


class StreamCatcher:
    """
    A custom stream catcher that redirects text output to a QTextEdit widget.
    This class is kept for compatibility but is not used in the improved version.
    """

    def __init__(self, output_widget):
        """
        Initialize the StreamCatcher.

        Args:
            output_widget (QTextEdit): The QTextEdit widget for text display.
        """
        self.output_widget = output_widget

    def write(self, text):
        """Write captured text to the output widget."""
        self.output_widget.moveCursor(QTextCursor.End)
        self.output_widget.insertPlainText(text)
        self.output_widget.ensureCursorVisible()

    def flush(self):
        """Flush method for file-like object compatibility."""
        pass