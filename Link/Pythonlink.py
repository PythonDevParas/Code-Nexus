"""
CodeNexus - PythonLink.py
Module: Link/PythonLink.py
Description: Python Environment Manager, Virtual Environment Switcher,
             pip package introspector, and pre-execution compiler bridge.
"""

import os
import sys
import shutil
import subprocess
from PyQt6.QtCore import QObject, QThread, pyqtSignal


class PK_PackageInspectorWorker(QThread):
    """
    Asynchronously queries installed packages using pip list without freezing the GUI.
    """
    packages_loaded = pyqtSignal(list)   # Emits list of (pkg_name, version)
    error_occurred = pyqtSignal(str)

    def __init__(self, python_executable: str):
        super().__init__()
        self.python_executable = python_executable

    def run(self):
        try:
            result = subprocess.run(
                [self.python_executable, "-m", "pip", "list", "--format=json"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=12
            )
            if result.returncode == 0:
                import json
                packages = json.loads(result.stdout)
                formatted = [(pkg["name"], pkg["version"]) for pkg in packages]
                self.packages_loaded.emit(formatted)
            else:
                self.error_occurred.emit(f"pip error: {result.stderr.strip()}")
        except Exception as e:
            self.error_occurred.emit(f"Failed to inspect packages: {str(e)}")


class PK_PythonLink(QObject):
    """
    Core connector bridging CodeNexus to the local Python environment,
    virtual environments, and runtime tooling.
    """
    environment_changed = pyqtSignal(str, str)  # interpreter_path, python_version
    syntax_checked = pyqtSignal(bool, str)       # is_valid, details_or_error

    def __init__(self, custom_interpreter: str = None, parent=None):
        super().__init__(parent)
        self.active_interpreter = custom_interpreter or sys.executable
        self.installed_packages = []
        self._inspector_thread = None

    def get_interpreter(self) -> str:
        """Returns the absolute path to the active Python executable."""
        return self.active_interpreter

    def get_version_info(self) -> str:
        """Returns detailed Python version string of the active interpreter."""
        try:
            res = subprocess.run(
                [self.active_interpreter, "--version"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=4
            )
            return (res.stdout or res.stderr).strip()
        except Exception:
            return f"Python {sys.version.split()[0]}"

    def set_interpreter(self, path: str) -> bool:
        """
        Validates and sets a new Python interpreter (e.g. from a .venv or conda).
        """
        if not os.path.isfile(path):
            return False

        try:
            res = subprocess.run(
                [path, "-c", "import sys; print(sys.executable)"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=4
            )
            if res.returncode == 0:
                self.active_interpreter = os.path.abspath(path)
                version_str = self.get_version_info()
                self.environment_changed.emit(self.active_interpreter, version_str)
                return True
        except Exception:
            pass

        return False

    def auto_detect_environments(self, workspace_root: str = None) -> list[dict]:
        """
        Scans current workspace and common system locations for Python environments.
        """
        discovered = []

        # 1. Current Running Interpreter
        discovered.append({
            "name": "Current CodeNexus Runtime",
            "path": sys.executable,
            "type": "System"
        })

        # 2. Check for local .venv or venv inside workspace
        if workspace_root and os.path.isdir(workspace_root):
            candidate_folders = [".venv", "venv", "env", ".env"]
            for folder in candidate_folders:
                env_path = os.path.join(workspace_root, folder)
                if sys.platform == "win32":
                    py_exe = os.path.join(env_path, "Scripts", "python.exe")
                else:
                    py_exe = os.path.join(env_path, "bin", "python")

                if os.path.isfile(py_exe):
                    discovered.append({
                        "name": f"Workspace Virtualenv ({folder})",
                        "path": py_exe,
                        "type": "Virtualenv"
                    })

        # 3. Check for Global Python installations on Windows
        if sys.platform == "win32":
            py_launcher = shutil.which("py")
            if py_launcher:
                discovered.append({
                    "name": "Windows Python Launcher (py)",
                    "path": py_launcher,
                    "type": "Global"
                })

        return discovered

    def validate_syntax(self, file_path: str) -> tuple[bool, str]:
        """
        Uses py_compile to check Python file for syntax issues without executing it.
        """
        import py_compile
        try:
            py_compile.compile(file_path, doraise=True)
            self.syntax_checked.emit(True, "Syntax valid.")
            return True, "Syntax valid."
        except py_compile.PyCompileError as err:
            err_msg = str(err).strip()
            self.syntax_checked.emit(False, err_msg)
            return False, err_msg
        except Exception as e:
            self.syntax_checked.emit(False, str(e))
            return False, str(e)

    def fetch_installed_packages(self) -> PK_PackageInspectorWorker:
        """
        Spawns background worker to list all installed packages via pip.
        """
        if self._inspector_thread and self._inspector_thread.isRunning():
            self._inspector_thread.wait()

        self._inspector_thread = PK_PackageInspectorWorker(self.active_interpreter)
        return self._inspector_thread

    def install_package(self, package_name: str) -> subprocess.Popen:
        """
        Installs a package into the active interpreter environment asynchronously.
        """
        cmd = [self.active_interpreter, "-m", "pip", "install", package_name]
        return subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)


# ----------------- Quick Standalone Runner -----------------
if __name__ == "__main__":
    link = PK_PythonLink()
    print("Active Interpreter:", link.get_interpreter())
    print("Version Info:", link.get_version_info())
    print("Detected Environments:", link.auto_detect_environments(os.getcwd()))