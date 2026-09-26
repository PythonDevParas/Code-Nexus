"""
CodeNexus - Termiral-view.py
Module: UI/Termiral-view.py
Description: Multi-session dockable Terminal View panel supporting multiple terminal tabs,
             direct shell access, process control actions, and run output redirection.
"""

import os
import sys
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTabWidget,
    QPushButton, QLabel, QTabBar, QToolButton
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QIcon

# Ensure Core directory is accessible for imports
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
CORE_DIR = os.path.join(PROJECT_ROOT, "Core")
if CORE_DIR not in sys.path:
    sys.path.insert(0, CORE_DIR)

try:
    from Terminal import PK_TerminalWidget
except ImportError:
    # Fallback placeholder if Core/Terminal.py is not yet placed
    PK_TerminalWidget = None


class PK_TerminalViewPanel(QWidget):
    """
    Bottom dock Terminal panel providing multi-tab terminal emulation
    and process execution display for CodeNexus.
    """
    terminal_count_changed = pyqtSignal(int)
    active_directory_changed = pyqtSignal(str)

    def __init__(self, workspace_directory: str = None, parent=None):
        super().__init__(parent)
        self.workspace_directory = workspace_directory or os.getcwd()
        self.session_counter = 1

        self.init_ui()
        self.apply_theme()

        # Open initial default terminal
        self.add_terminal_session()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Top Control Strip
        header_bar = QWidget()
        header_bar.setFixedHeight(32)
        header_layout = QHBoxLayout(header_bar)
        header_layout.setContentsMargins(8, 2, 8, 2)
        header_layout.setSpacing(6)

        title_lbl = QLabel("TERMINAL")
        title_lbl.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        header_layout.addWidget(title_lbl)

        header_layout.addStretch(1)

        # Action Buttons
        self.new_term_btn = QPushButton("+ New")
        self.new_term_btn.setFixedHeight(22)
        self.new_term_btn.setToolTip("Open New Terminal Session")
        self.new_term_btn.clicked.connect(lambda: self.add_terminal_session())
        header_layout.addWidget(self.new_term_btn)

        self.clear_btn = QPushButton("Clear")
        self.clear_btn.setFixedHeight(22)
        self.clear_btn.setToolTip("Clear Active Terminal Output")
        self.clear_btn.clicked.connect(self.clear_active_terminal)
        header_layout.addWidget(self.clear_btn)

        self.kill_btn = QPushButton("Kill")
        self.kill_btn.setFixedHeight(22)
        self.kill_btn.setToolTip("Kill Running Process in Active Terminal")
        self.kill_btn.clicked.connect(self.kill_active_process)
        header_layout.addWidget(self.kill_btn)

        # Tab Widget for Multiple Sessions
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabsClosable(True)
        self.tab_widget.setMovable(True)
        self.tab_widget.tabCloseRequested.connect(self.close_terminal_session)

        main_layout.addWidget(header_bar)
        main_layout.addWidget(self.tab_widget, stretch=1)

    def apply_theme(self):
        """Catppuccin Mocha / VS Code Dark Theme."""
        self.setStyleSheet("""
            QWidget {
                background-color: #181825;
                color: #cdd6f4;
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
            }
            QLabel {
                color: #89b4fa;
                font-size: 11px;
                letter-spacing: 0.5px;
            }
            QPushButton {
                background-color: #313244;
                color: #cdd6f4;
                border: 1px solid #45475a;
                border-radius: 3px;
                padding: 2px 8px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #45475a;
                color: #ffffff;
            }
            QTabWidget::pane {
                border-top: 1px solid #313244;
                background-color: #11111b;
            }
            QTabBar::tab {
                background: #181825;
                color: #a6adc8;
                padding: 4px 12px;
                margin-right: 2px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                font-size: 11px;
            }
            QTabBar::tab:selected {
                background: #1e1e2e;
                color: #89b4fa;
                border-bottom: 2px solid #89b4fa;
            }
            QTabBar::tab:hover {
                background: #313244;
                color: #cdd6f4;
            }
        """)

    def add_terminal_session(self, title: str = None) -> QWidget:
        """
        Spawns a new independent terminal instance tab.
        """
        tab_name = title or f"Terminal {self.session_counter}"
        self.session_counter += 1

        if PK_TerminalWidget:
            terminal_instance = PK_TerminalWidget(working_directory=self.workspace_directory)
        else:
            from PyQt6.QtWidgets import QTextEdit
            terminal_instance = QTextEdit()
            terminal_instance.setReadOnly(True)
            terminal_instance.setText("[Error]: Core/Terminal.py module not detected.")

        index = self.tab_widget.addTab(terminal_instance, tab_name)
        self.tab_widget.setCurrentIndex(index)
        self.terminal_count_changed.emit(self.tab_widget.count())
        return terminal_instance

    def close_terminal_session(self, index: int):
        """Closes and cleans up a terminal tab."""
        if self.tab_widget.count() <= 1:
            # Always keep at least one terminal session open
            self.clear_active_terminal()
            return

        widget = self.tab_widget.widget(index)
        if hasattr(widget, "closeEvent"):
            widget.close()

        self.tab_widget.removeTab(index)
        self.terminal_count_changed.emit(self.tab_widget.count())

    def get_current_terminal(self):
        """Returns the currently active terminal widget."""
        return self.tab_widget.currentWidget()

    def run_command(self, command: str):
        """Pipes a command string into the active terminal instance."""
        current_term = self.get_current_terminal()
        if current_term and hasattr(current_term, "input_field"):
            current_term.input_field.setText(command)
            current_term.send_command()

    def append_output(self, text: str):
        """Directly writes text into the current terminal output window."""
        current_term = self.get_current_terminal()
        if current_term and hasattr(current_term, "append_text"):
            current_term.append_text(text)

    def clear_active_terminal(self):
        """Clears text of the current active session."""
        current_term = self.get_current_terminal()
        if current_term and hasattr(current_term, "clear_terminal"):
            current_term.clear_terminal()

    def kill_active_process(self):
        """Terminates any command currently active in the foreground."""
        current_term = self.get_current_terminal()
        if current_term and hasattr(current_term, "process") and current_term.process:
            if current_term.process.state() == current_term.process.ProcessState.Running:
                current_term.process.kill()
                current_term.append_text("\n[Process terminated by user]\n")
                current_term.init_process()

    def set_workspace_directory(self, new_dir: str):
        """Updates directory across newly spawned and active sessions."""
        if os.path.isdir(new_dir):
            self.workspace_directory = new_dir
            current_term = self.get_current_terminal()
            if current_term and hasattr(current_term, "set_working_directory"):
                current_term.set_working_directory(new_dir)
            self.active_directory_changed.emit(new_dir)


# ----------------- Quick Standalone Runner -----------------
if __name__ == "__main__":
    from PyQt6.QtWidgets import QApplication
    app = QApplication(sys.argv)
    panel = PK_TerminalViewPanel()
    panel.resize(800, 350)
    panel.show()
    sys.exit(app.exec())