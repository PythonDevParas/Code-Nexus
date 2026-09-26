"""
CodeNexus - PK_cloud_link.py
Module: Cloud/PK_cloud_link.py
Description: Asynchronous file sync with Paras Box Cloud over direct URL requests.
"""

import os
import requests
from PyQt6.QtCore import QThread, pyqtSignal

DEFAULT_CLOUD_URL = "https://parasboxcloud.ai.studio"
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36 CodeNexus/1.0"
)


class PK_CloudSendWorker(QThread):
    """
    QThread worker to send/save files to Paras Box Cloud without blocking the UI.
    """
    upload_started = pyqtSignal(str)       # Emits filename
    upload_finished = pyqtSignal(bool, str) # Emits success flag and status message

    def __init__(self, filename: str, content: str, cloud_url: str = DEFAULT_CLOUD_URL):
        super().__init__()
        self.filename = filename.strip()
        self.content = content
        self.cloud_url = cloud_url.rstrip("/")

    def run(self):
        if not self.filename:
            self.upload_finished.emit(False, "Filename cannot be empty.")
            return

        self.upload_started.emit(self.filename)
        headers = {
            "User-Agent": DEFAULT_USER_AGENT,
            "Accept": "*/*"
        }
        payload = {
            "filename": self.filename,
            "code": self.content
        }

        try:
            # 1. Attempt primary transmission via standard Form Data
            response = requests.post(
                self.cloud_url,
                data=payload,
                headers=headers,
                timeout=12
            )

            # 2. Fallback to JSON payload if server expects application/json
            if response.status_code in [400, 415]:
                headers["Content-Type"] = "application/json"
                response = requests.post(
                    self.cloud_url,
                    json=payload,
                    headers=headers,
                    timeout=12
                )

            # Check response
            if response.status_code in [200, 201]:
                msg = f"Successfully uploaded '{self.filename}' to Paras Box Cloud."
                self.upload_finished.emit(True, msg)
            else:
                snippet = response.text[:180].replace("\n", " ").strip()
                error_msg = f"Upload failed ({response.status_code}): {snippet or 'Server rejected request'}"
                self.upload_finished.emit(False, error_msg)

        except requests.exceptions.Timeout:
            self.upload_finished.emit(False, "Paras Box Cloud request timed out. Check network connection.")
        except requests.exceptions.RequestException as e:
            self.upload_finished.emit(False, f"Network communication error: {str(e)}")
        except Exception as e:
            self.upload_finished.emit(False, f"Unexpected error during upload: {str(e)}")


class PK_CloudGetWorker(QThread):
    """
    QThread worker to fetch/load files from Paras Box Cloud without blocking the UI.
    """
    fetch_started = pyqtSignal(str)          # Emits filename
    fetch_finished = pyqtSignal(bool, str)   # Emits success flag and file content / error message

    def __init__(self, filename: str, cloud_url: str = DEFAULT_CLOUD_URL):
        super().__init__()
        self.filename = filename.strip()
        self.cloud_url = cloud_url.rstrip("/")

    def run(self):
        if not self.filename:
            self.fetch_finished.emit(False, "Enter a valid filename to fetch.")
            return

        self.fetch_started.emit(self.filename)
        headers = {
            "User-Agent": DEFAULT_USER_AGENT,
            "Accept": "text/plain, application/json, */*"
        }

        try:
            # Attempt 1: Fetch via query param (?file=filename or ?filename=filename)
            params = {"file": self.filename}
            response = requests.get(
                self.cloud_url,
                params=params,
                headers=headers,
                timeout=12
            )

            # Attempt 2: If query param returns 404, try direct file path structure
            if response.status_code == 404:
                direct_url = f"{self.cloud_url}/{self.filename}"
                response = requests.get(direct_url, headers=headers, timeout=12)

            if response.status_code == 200:
                content = response.text
                if not content.strip():
                    self.fetch_finished.emit(False, f"File '{self.filename}' was found but is empty.")
                else:
                    self.fetch_finished.emit(True, content)
            else:
                snippet = response.text[:180].replace("\n", " ").strip()
                error_msg = f"Failed to retrieve '{self.filename}' (HTTP {response.status_code}): {snippet}"
                self.fetch_finished.emit(False, error_msg)

        except requests.exceptions.Timeout:
            self.fetch_finished.emit(False, "Request timed out while contacting Paras Box Cloud.")
        except requests.exceptions.RequestException as e:
            self.fetch_finished.emit(False, f"Network error during fetch: {str(e)}")
        except Exception as e:
            self.fetch_finished.emit(False, f"Unexpected fetch error: {str(e)}")


class PK_CloudLinkManager:
    """
    Controller interface to manage active cloud requests, thread lifecycles,
    and target URLs.
    """
    def __init__(self, cloud_url: str = DEFAULT_CLOUD_URL):
        self.cloud_url = cloud_url
        self.send_worker = None
        self.get_worker = None

    def send_file(self, filename: str, content: str) -> PK_CloudSendWorker:
        """Creates and launches an asynchronous upload worker."""
        if self.send_worker and self.send_worker.isRunning():
            self.send_worker.terminate()
            self.send_worker.wait()

        self.send_worker = PK_CloudSendWorker(filename, content, self.cloud_url)
        return self.send_worker

    def get_file(self, filename: str) -> PK_CloudGetWorker:
        """Creates and launches an asynchronous fetch worker."""
        if self.get_worker and self.get_worker.isRunning():
            self.get_worker.terminate()
            self.get_worker.wait()

        self.get_worker = PK_CloudGetWorker(filename, self.cloud_url)
        return self.get_worker

    def set_cloud_url(self, new_url: str):
        """Update cloud server endpoint."""
        self.cloud_url = new_url.rstrip("/")