"""
CodeNexus - AuraNexus_link.py
Module: Link/AuraNexus_link.py
Description: Aura Nexus project connector, runtime module resolver, 
             dynamic component loader, and remote manifest synchronization bridge.
"""

import os
import sys
import importlib
import json
import requests
from PyQt6.QtCore import QObject, QThread, pyqtSignal

DEFAULT_AURA_NEXUS_ENDPOINT = "https://raw.githubusercontent.com/PythonDevParas/Aura-Nexus/main/manifest.json"


class PK_AuraSyncWorker(QThread):
    """
    Background worker to query remote Aura Nexus releases and component definitions.
    """
    sync_finished = pyqtSignal(bool, dict, str)  # success, manifest_data, message

    def __init__(self, endpoint_url: str = DEFAULT_AURA_NEXUS_ENDPOINT):
        super().__init__()
        self.endpoint_url = endpoint_url

    def run(self):
        headers = {
            "User-Agent": "CodeNexus-AuraBridge/1.0"
        }
        try:
            response = requests.get(self.endpoint_url, headers=headers, timeout=10)
            if response.status_code == 200:
                try:
                    data = response.json()
                    self.sync_finished.emit(True, data, "Aura Nexus manifest fetched successfully.")
                except json.JSONDecodeError:
                    self.sync_finished.emit(False, {}, "Failed to parse remote JSON manifest.")
            else:
                self.sync_finished.emit(
                    False, {}, f"Server returned status {response.status_code}"
                )
        except requests.exceptions.RequestException as e:
            self.sync_finished.emit(False, {}, f"Network connection error: {str(e)}")
        except Exception as e:
            self.sync_finished.emit(False, {}, f"Unexpected sync error: {str(e)}")


class PK_AuraNexusLink(QObject):
    """
    Controller connecting CodeNexus workspaces with Aura Nexus runtime dependencies and utilities.
    """
    connection_status_changed = pyqtSignal(bool, str) # is_connected, details
    plugin_loaded = pyqtSignal(str)                   # plugin_name
    error_occurred = pyqtSignal(str)

    def __init__(self, workspace_root: str = None, parent=None):
        super().__init__(parent)
        self.workspace_root = workspace_root or os.getcwd()
        self.is_aura_detected = False
        self.loaded_modules = {}
        self.sync_worker = None

        self.detect_local_aura_nexus()

    def detect_local_aura_nexus(self) -> bool:
        """
        Scans workspace directory, parent folders, and PYTHONPATH for Aura Nexus sources.
        """
        candidate_paths = [
            os.path.join(self.workspace_root, "Aura-Nexus"),
            os.path.join(self.workspace_root, "aura_nexus"),
            os.path.join(os.path.dirname(self.workspace_root), "Aura-Nexus"),
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "Aura-Nexus")
        ]

        for path in candidate_paths:
            resolved_path = os.path.abspath(path)
            if os.path.isdir(resolved_path):
                if resolved_path not in sys.path:
                    sys.path.insert(0, resolved_path)
                self.is_aura_detected = True
                self.connection_status_changed.emit(True, f"Local Aura Nexus linked at: {resolved_path}")
                return True

        # Check if already installed globally as a package
        try:
            importlib.import_module("aura_nexus")
            self.is_aura_detected = True
            self.connection_status_changed.emit(True, "Aura Nexus detected in global Python environment.")
            return True
        except ImportError:
            pass

        self.is_aura_detected = False
        self.connection_status_changed.emit(False, "Aura Nexus runtime not detected locally.")
        return False

    def load_component(self, module_name: str):
        """
        Dynamically imports an Aura Nexus sub-module or plugin hook safely.
        """
        if not self.is_aura_detected:
            self.detect_local_aura_nexus()

        try:
            mod = importlib.import_module(module_name)
            self.loaded_modules[module_name] = mod
            self.plugin_loaded.emit(module_name)
            return mod
        except Exception as e:
            self.error_occurred.emit(f"Failed to load Aura module '{module_name}': {str(e)}")
            return None

    def execute_hook(self, module_name: str, function_name: str, *args, **kwargs):
        """
        Executes a callable hook from an Aura Nexus module.
        """
        mod = self.loaded_modules.get(module_name) or self.load_component(module_name)
        if not mod:
            return None

        func = getattr(mod, function_name, None)
        if callable(func):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                self.error_occurred.emit(f"Error executing '{function_name}' in {module_name}: {str(e)}")
                return None
        else:
            self.error_occurred.emit(f"Hook '{function_name}' not found in {module_name}")
            return None

    def check_remote_manifest(self, custom_endpoint: str = None) -> PK_AuraSyncWorker:
        """
        Spawns a thread to inspect remote updates or dependencies from GitHub/Aura Nexus CDN.
        """
        if self.sync_worker and self.sync_worker.isRunning():
            self.sync_worker.wait()

        endpoint = custom_endpoint or DEFAULT_AURA_NEXUS_ENDPOINT
        self.sync_worker = PK_AuraSyncWorker(endpoint)
        return self.sync_worker


# ----------------- Quick Standalone Runner -----------------
if __name__ == "__main__":
    from PyQt6.QtCore import QCoreApplication
    app = QCoreApplication(sys.argv)

    bridge = PK_AuraNexusLink()
    bridge.connection_status_changed.connect(
        lambda status, msg: print(f"[Aura Nexus Status]: {msg} (Active: {status})")
    )
    bridge.error_occurred.connect(lambda err: print(f"[Error]: {err}", file=sys.stderr))

    print("Checking local environment...")
    detected = bridge.detect_local_aura_nexus()

    # Test Manifest Fetch
    print("Testing remote manifest bridge...")
    worker = bridge.check_remote_manifest()
    worker.sync_finished.connect(
        lambda success, data, msg: (print(f"Result: {msg}"), app.quit())
    )
    worker.start()

    sys.exit(app.exec())