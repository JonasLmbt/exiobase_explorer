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
    def __init__(self, context: dict = None, ui=None):
        super().__init__()
        self.ui = ui
        self.general_dict = self.ui.general_dict
        self.context = context or {}
        self.console = code.InteractiveConsole(self.context)

        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        layout.addWidget(QLabel(self.general_dict["Interactive Console"]))

        self.output = QTextEdit()
        self.output.setReadOnly(True)
        layout.addWidget(self.output)

        input_layout = QHBoxLayout()
        self.input = QTextEdit()
        self.input.setFixedHeight(50)
        self.input.installEventFilter(self)
        input_layout.addWidget(self.input)

        self.execute_button = QPushButton(self.general_dict["Execute"])
        self.execute_button.clicked.connect(self.execute_code)
        input_layout.addWidget(self.execute_button)

        layout.addLayout(input_layout)

    def eventFilter(self, obj, event):
        if obj is self.input and event.type() == QEvent.KeyPress:
            if event.key() == Qt.Key_Return and not (event.modifiers() & Qt.ShiftModifier):
                self.execute_button.click()
                return True 
        return super().eventFilter(obj, event)


    def execute_code(self):
        code_string = self.input.toPlainText()
        self.output.append(f">>> {code_string}")
        self.input.clear()

        try:
            old_stdout = sys.stdout
            old_stderr = sys.stderr
            sys.stdout = self._stdout_catcher = StreamCatcher(self.output)
            sys.stderr = self._stdout_catcher

            more = self.console.push(code_string)
            if more:
                self.output.append(f"... ({self.general_dict['more input needed']})")

        except Exception as e:
            self.output.append(f"{self.general_dict['Error']}: {str(e)}")
        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr

class StreamCatcher:
    def __init__(self, output_widget):
        self.output_widget = output_widget

    def write(self, text):
        self.output_widget.moveCursor(QTextCursor.End)
        self.output_widget.insertPlainText(text)
        self.output_widget.ensureCursorVisible()

    def flush(self):
        pass
