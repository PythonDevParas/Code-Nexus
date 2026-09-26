"""
CodeNexus - PK_temp_local_cloud.py
Module: Cloud/PK_temp_local_cloud.py
Description: Silent local storage acting as "Cloud" inside C:\\Users\\<Username>\\Code Nexus Local Cloud
"""

import os
import sys
import shutil
from pathlib import Path


class PK_LocalCloudManager:
    """
    Manages silent local-cloud synchronization in the user's home directory.
    Target Directory: C:\Users\<Username>\Code Nexus Local Cloud
    """
    def __init__(self):
        user_home = Path.home()
        self.cloud_root = user_home / "Code Nexus Local Cloud"
        self._ensure_storage()

    def _ensure_storage(self):
        """Creates the directory quietly if it does not exist."""
        try:
            self.cloud_root.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass

    def upload_file(self, filename: str, content: str) -> dict:
        """Saves file into the local cloud silently."""
        self._ensure_storage()
        clean_name = os.path.basename(filename.strip())
        target_path = self.cloud_root / clean_name

        try:
            with open(target_path, "w", encoding="utf-8", errors="replace") as f:
                f.write(content)
            return {
                "success": True,
                "message": f"'{clean_name}' successfully synced to Cloud Storage.",
                "path": str(target_path)
            }
        except Exception as e:
            return {"success": False, "message": f"Cloud Sync Failed: {str(e)}"}

    def download_file(self, filename: str) -> dict:
        """Fetches file from the local cloud."""
        self._ensure_storage()
        clean_name = os.path.basename(filename.strip())
        target_path = self.cloud_root / clean_name

        if not target_path.is_file():
            return {
                "success": False,
                "message": f"File '{clean_name}' not found in Cloud Storage."
            }

        try:
            with open(target_path, "r", encoding="utf-8", errors="replace") as f:
                data = f.read()
            return {
                "success": True,
                "filename": clean_name,
                "content": data
            }
        except Exception as e:
            return {"success": False, "message": f"Failed reading from Cloud: {str(e)}"}

    def list_cloud_files(self) -> list:
        """Returns list of all files synced in cloud."""
        self._ensure_storage()
        try:
            return [f.name for f in self.cloud_root.iterdir() if f.is_file()]
        except Exception:
            return []

    def flush_cloud(self) -> dict:
        """Deletes all synced cloud files completely."""
        self._ensure_storage()
        try:
            file_count = 0
            for item in self.cloud_root.iterdir():
                if item.is_file():
                    item.unlink()
                    file_count += 1
                elif item.is_dir():
                    shutil.rmtree(item)
                    file_count += 1
            return {
                "success": True,
                "message": f"Cloud flushed completely. ({file_count} items purged)"
            }
        except Exception as e:
            return {"success": False, "message": f"Failed to flush cloud: {str(e)}"}