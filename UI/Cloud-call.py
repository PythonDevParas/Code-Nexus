"""
CodeNexus - Cloud-call.py
Module: UI/Cloud-call.py
Description: UI Action handlers, modal dialogs, and event connectors 
             for Paras Box Cloud upload and download workflows.
"""

import os
import sys
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTextEdit, QMessageBox, QProgressBar, QWidget
)
from PyQt6.QtCore import Qt, pyqtSignal

# Ensure parent and Cloud directories are available
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
CLOUD_DIR = os.path.join(PROJECT_ROOT, "Cloud")
if CLOUD_DIR not in sys.path:
    sys.path.insert(0, CLOUD_DIR)

try:
    from PK_cloud_link import PK_CloudLinkManager
    from PK_temp_local_cloud import PK_TempLocalCloud
except ImportError:
    PK_CloudLinkManager = None
    PK_TempLocalCloud = None


class PK_CloudActionDialog(QDialog):
    """
    Modal interface for uploading to or downloading from Paras Box Cloud.
    """
    file_downloaded = pyqtSignal(str, str) # Emits filename, content

    def __init__(self, mode: str = "send", default_filename: str = "", content: str = "", parent=None):
        super().__init__(parent)
        self.mode = mode.lower()  # "send" or "get"
        self.file_content = content
        self.cloud_manager = PK_CloudLinkManager() if PK_CloudLinkManager else None
        self.temp_cloud = PK_TempLocalCloud() if PK_TempLocalCloud else None
        self.worker = None

        self.setWindowTitle("Paras Box Cloud — " + ("Send Code" if self.mode == "send" else "Fetch Code"))
        self.setFixedWidth(460)
        self.init_ui(default_filename)
        self.apply_theme()

    def init_ui(self, default_filename: str):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(18, 18, 18, 18)

        # Header Info
        header_text = (
            "Upload active editor buffer to Paras Box Cloud"
            if self.mode == "send"
            else "Download file from Paras Box Cloud directly into CodeNexus"
        )
        self.info_lbl = QLabel(header_text)
        self.info_lbl.setWordWrap(True)
        layout.addWidget(self.info_lbl)

        # File Input Field
        input_container = QVBoxLayout()
        input_container.setSpacing(4)
        input_title = QLabel("Target Filename:")
        self.filename_input = QLineEdit(default_filename)
        self.filename_input.setPlaceholderText("e.g. main.py, index.html, script.js")
        input_container.addWidget(input_title)
        input_container.addWidget(self.filename_input)
        layout.addLayout(input_container)

        # Progress Indicator (Hidden by default)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0) # Indeterminate spinner style
        self.progress_bar.setFixedHeight(4)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.hide()
        layout.addWidget(self.progress_bar)

        # Status Message Box
        self.status_lbl = QLabel("")
        self.status_lbl.setStyleSheet("color: #a6adc8; font-size: 11px;")
        layout.addWidget(self.status_lbl)

        # Action Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)

        btn_label = "Upload to Cloud" if self.mode == "send" else "Fetch from Cloud"
        self.action_btn = QPushButton(btn_label)
        self.action_btn.clicked.connect(self.execute_action)

        btn_layout.addStretch(1)
        btn_layout.addWidget(self.cancel_btn)
        btn_layout.addWidget(self.action_btn)
        layout.addLayout(btn_layout)

    def apply_theme(self):
        """Catppuccin Mocha / VS Code Dark Theme."""
        self.setStyleSheet("""
            QDialog {
                background-color: #181825;
                color: #cdd6f4;
            }
            QLabel {
                color: #cdd6f4;
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
            }
            QLineEdit {
                background-color: #11111b;
                color: #cdd6f4;
                border: 1px solid #313244;
                border-radius: 4px;
                padding: 6px 10px;
                font-size: 13px;
            }
            QLineEdit:focus {
                border-color: #89b4fa;
            }
            QProgressBar {
                background-color: #313244;
                border-radius: 2px;
            }
            QProgressBar::chunk {
                background-color: #89b4fa;
            }
            QPushButton {
                background-color: #313244;
                color: #cdd6f4;
                border: 1px solid #45475a;
                border-radius: 4px;
                padding: 6px 14px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45475a;
                color: #ffffff;
            }
            QPushButton#primaryAction {
                background-color: #89b4fa;
                color: #11111b;
            }
        """)

    def execute_action(self):
        filename = self.filename_input.text().strip()
        if not filename:
            self.status_lbl.setText("Please enter a valid filename.")
            return

        if not self.cloud_manager:
            self.status_lbl.setText("Cloud subsystem unavailable.")
            return

        self.action_btn.setEnabled(False)
        self.filename_input.setEnabled(False)
        self.progress_bar.show()

        if self.mode == "send":
            self.status_lbl.setText("Connecting to Paras Box Cloud...")
            self.worker = self.cloud_manager.send_file(filename, self.file_content)
            self.worker.upload_finished.connect(self.on_upload_complete)
            self.worker.start()
        else:
            self.status_lbl.setText(f"Requesting '{filename}' from Paras Box Cloud...")
            self.worker = self.cloud_manager.get_file(filename)
            self.worker.fetch_finished.connect(self.on_fetch_complete)
            self.worker.start()

    def on_upload_complete(self, success: bool, message: str):
        self.progress_bar.hide()
        self.action_btn.setEnabled(True)
        self.filename_input.setEnabled(True)

        if success:
            QMessageBox.information(self, "Cloud Upload Successful", message)
            self.accept()
        else:
            # Fallback: Cache into offline queue
            if self.temp_cloud:
                filename = self.filename_input.text().strip()
                self.temp_cloud.queue_offline_cloud_sync(filename, self.file_content)
                message += "\n(File preserved in offline local sync queue)"
            self.status_lbl.setText(message)

    def on_fetch_complete(self, success: bool, payload: str):
        self.progress_bar.hide()
        self.action_btn.setEnabled(True)
        self.filename_input.setEnabled(True)

        if success:
            filename = self.filename_input.text().strip()
            self.file_downloaded.emit(filename, payload)
            self.accept()
        else:
            self.status_lbl.setText(payload)


class PK_CloudCall:
    """
    Direct caller interface to trigger Cloud Send/Get modals from any menu, 
    toolbar, or shortcut in CodeNexus.
    """
    @staticmethod
    def trigger_upload(filename: str, content: str, parent=None):
        """Displays Send Dialog."""
        dialog = PK_CloudActionDialog(mode="send", default_filename=filename, content=content, parent=parent)
        return dialog.exec()

    @staticmethod
    def trigger_download(on_success_callback, parent=None):
        """Displays Download Dialog and hooks content response to a callback."""
        dialog = PK_CloudActionDialog(mode="get", default_filename="", parent=parent)
        dialog.file_downloaded.connect(on_success_callback)
        return dialog.exec()


# ----------------- Quick Standalone Runner -----------------
if __name__ == "__main__":
    from PyQt6.QtWidgets import QApplication
    app = QApplication(sys.argv)
    
    # Test Upload Dialog
    sample_code = "print('Hello from CodeNexus & Paras Box Cloud!')"
    PK_CloudCall.trigger_upload("test_script.py", sample_code)
    
    sys.exit(0)