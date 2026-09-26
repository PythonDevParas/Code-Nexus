"""
CodeNexus - AI-UI.py
Module: UI/AI-UI.py
Description: AI Copilot sidebar interface featuring real-time token streaming,
             quick action triggers, context attachment, and code insertion tools.
"""

import os
import sys
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit,
    QLineEdit, QPushButton, QLabel, QScrollArea,
    QFrame, QSplitter
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QTextCursor

# Ensure current and UI folders are linked
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

try:
    from PK_ai_call import PK_AICall  # or AI-call.py based on local file naming
except ImportError:
    try:
        import importlib
        ai_call_mod = importlib.import_module("AI-call")
        PK_AICall = getattr(ai_call_mod, "PK_AICall")
    except Exception:
        PK_AICall = None


class PK_AICopilotWidget(QWidget):
    """
    Dedicated AI Copilot sidebar widget for CodeNexus.
    """
    insert_code_requested = pyqtSignal(str)  # Emitted to insert code into active editor tab
    context_requested = pyqtSignal()         # Requests active file context from main window

    def __init__(self, parent=None):
        super().__init__(parent)
        self.ai_bridge = PK_AICall() if PK_AICall else None
        self.active_code_context = ""
        self.latest_code_block = ""

        self.init_ui()
        self.apply_theme()
        self.bind_signals()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        # Top Header Bar
        header = QHBoxLayout()
        header.setSpacing(6)
        title = QLabel("🤖 CODENEXUS COPILOT")
        title.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        
        self.clear_btn = QPushButton("Clear")
        self.clear_btn.setFixedHeight(22)
        self.clear_btn.clicked.connect(self.clear_chat)

        header.addWidget(title)
        header.addStretch(1)
        header.addWidget(self.clear_btn)
        layout.addLayout(header)

        # Quick Action Toolbar
        quick_actions = QHBoxLayout()
        quick_actions.setSpacing(4)

        self.explain_btn = QPushButton("Explain")
        self.explain_btn.clicked.connect(self.trigger_explain)
        
        self.refactor_btn = QPushButton("Refactor")
        self.refactor_btn.clicked.connect(self.trigger_refactor)

        self.tests_btn = QPushButton("Tests")
        self.tests_btn.clicked.connect(self.trigger_tests)

        quick_actions.addWidget(self.explain_btn)
        quick_actions.addWidget(self.refactor_btn)
        quick_actions.addWidget(self.tests_btn)
        layout.addLayout(quick_actions)

        # Context Indicator
        self.context_label = QLabel("No active code attached")
        self.context_label.setStyleSheet("color: #6c7086; font-size: 11px;")
        layout.addWidget(self.context_label)

        # Chat Stream Display Area
        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        self.chat_display.setFont(QFont("Consolas", 10))
        layout.addWidget(self.chat_display, stretch=1)

        # Insert to Editor Action Bar
        action_strip = QHBoxLayout()
        self.insert_btn = QPushButton("⎘ Insert Solution to Editor")
        self.insert_btn.setEnabled(False)
        self.insert_btn.clicked.connect(self.insert_code_to_editor)
        action_strip.addWidget(self.insert_btn)
        layout.addLayout(action_strip)

        # Prompt Input Bar
        input_box = QHBoxLayout()
        input_box.setSpacing(4)

        self.prompt_input = QLineEdit()
        self.prompt_input.setPlaceholderText("Ask AI or request code changes...")
        self.prompt_input.returnPressed.connect(self.submit_prompt)

        self.send_btn = QPushButton("Send")
        self.send_btn.clicked.connect(self.submit_prompt)

        input_box.addWidget(self.prompt_input, stretch=1)
        input_box.addWidget(self.send_btn)
        layout.addLayout(input_box)

    def apply_theme(self):
        """Catppuccin Mocha / VS Code Dark Sidebar Theme."""
        self.setStyleSheet("""
            QWidget {
                background-color: #181825;
                color: #cdd6f4;
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
            }
            QLabel {
                color: #89b4fa;
            }
            QTextEdit {
                background-color: #11111b;
                color: #cdd6f4;
                border: 1px solid #313244;
                border-radius: 4px;
                padding: 6px;
                font-family: 'Consolas', 'Courier New', monospace;
            }
            QLineEdit {
                background-color: #1e1e2e;
                color: #cdd6f4;
                border: 1px solid #313244;
                border-radius: 4px;
                padding: 5px 8px;
            }
            QLineEdit:focus {
                border-color: #89b4fa;
            }
            QPushButton {
                background-color: #313244;
                color: #cdd6f4;
                border: 1px solid #45475a;
                border-radius: 3px;
                padding: 3px 8px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #45475a;
                color: #ffffff;
            }
            QPushButton:disabled {
                background-color: #1e1e2e;
                color: #585b70;
                border-color: #313244;
            }
        """)

    def bind_signals(self):
        if not self.ai_bridge:
            self.chat_display.append("⚠ AI subsystem module unavailable.\n")
            return

        self.ai_bridge.stream_started.connect(self.on_stream_start)
        self.ai_bridge.token_received.connect(self.on_token_received)
        self.ai_bridge.stream_finished.connect(self.on_stream_finished)
        self.ai_bridge.error_occurred.connect(self.on_stream_error)

    def set_active_code_context(self, code_snippet: str, file_name: str = ""):
        """Sets code context to forward with the next prompt."""
        self.active_code_context = code_snippet.strip()
        if self.active_code_context:
            display_title = file_name or "active selection"
            lines_count = len(self.active_code_context.splitlines())
            self.context_label.setText(f"📎 Attached: {display_title} ({lines_count} lines)")
            self.context_label.setStyleSheet("color: #a6e3a1; font-size: 11px;")
        else:
            self.context_label.setText("No active code attached")
            self.context_label.setStyleSheet("color: #6c7086; font-size: 11px;")

    def submit_prompt(self):
        prompt = self.prompt_input.text().strip()
        if not prompt or not self.ai_bridge:
            return

        self.prompt_input.clear()
        self.append_message("User", prompt)
        self.ai_bridge.execute_custom_query(prompt, self.active_code_context)

    def trigger_explain(self):
        if not self.active_code_context:
            self.append_message("System", "Select or open code first to explain.")
            return
        self.append_message("User", "Explain this code.")
        self.ai_bridge.explain_code(self.active_code_context)

    def trigger_refactor(self):
        if not self.active_code_context:
            self.append_message("System", "Select or open code first to refactor.")
            return
        self.append_message("User", "Refactor and optimize this code.")
        self.ai_bridge.refactor_code(self.active_code_context)

    def trigger_tests(self):
        if not self.active_code_context:
            self.append_message("System", "Select or open code first to write tests.")
            return
        self.append_message("User", "Generate unit tests for this code.")
        self.ai_bridge.generate_tests(self.active_code_context)

    def on_stream_start(self):
        self.send_btn.setEnabled(False)
        self.insert_btn.setEnabled(False)
        self.append_message("AI", "")

    def on_token_received(self, token: str):
        cursor = self.chat_display.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.chat_display.setTextCursor(cursor)
        self.chat_display.insertPlainText(token)
        self.chat_display.ensureCursorVisible()

    def on_stream_finished(self, full_text: str):
        self.send_btn.setEnabled(True)
        cursor = self.chat_display.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.chat_display.setTextCursor(cursor)
        self.chat_display.insertPlainText("\n\n")

        # Extract code blocks ```code``` if present
        if "```" in full_text:
            parts = full_text.split("```")
            if len(parts) >= 3:
                extracted = parts[1]
                # Strip language prefix if present (e.g., 'python\n')
                lines = extracted.split("\n", 1)
                self.latest_code_block = lines[1] if len(lines) > 1 else extracted
                self.insert_btn.setEnabled(True)

    def on_stream_error(self, err_msg: str):
        self.send_btn.setEnabled(True)
        self.append_message("Error", err_msg)

    def append_message(self, sender: str, text: str):
        cursor = self.chat_display.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.chat_display.setTextCursor(cursor)

        if sender == "User":
            prefix = f"\n▶ You:\n{text}\n"
        elif sender == "AI":
            prefix = f"⚡ CodeNexus Copilot:\n"
        elif sender == "Error":
            prefix = f"\n⚠ Error: {text}\n\n"
        else:
            prefix = f"\n[{sender}]: {text}\n\n"

        self.chat_display.insertPlainText(prefix)
        self.chat_display.ensureCursorVisible()

    def insert_code_to_editor(self):
        """Sends extracted response code to the editor."""
        if self.latest_code_block:
            self.insert_code_requested.emit(self.latest_code_block)

    def clear_chat(self):
        self.chat_display.clear()
        if self.ai_bridge and self.ai_bridge.ai_engine:
            self.ai_bridge.ai_engine.clear_history()


# ----------------- Quick Standalone Runner -----------------
if __name__ == "__main__":
    from PyQt6.QtWidgets import QApplication
    app = QApplication(sys.argv)
    copilot = PK_AICopilotWidget()
    copilot.resize(360, 600)
    copilot.set_active_code_context("def square(x):\n    return x * x", "math_utils.py")
    copilot.show()
    sys.exit(app.exec())