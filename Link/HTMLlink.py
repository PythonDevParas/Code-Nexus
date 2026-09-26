"""
CodeNexus - HTMLlink.py
Module: Link/HTMLlink.py
Description: Web preview runtime linker, embedded local HTTP web server,
             dynamic port allocator, and external browser dispatcher.
"""

import os
import sys
import socket
import webbrowser
from http.server import SimpleHTTPRequestHandler
from socketserver import TCPServer
from PyQt6.QtCore import QObject, QThread, pyqtSignal


class PK_ReusableTCPServer(TCPServer):
    """TCPServer that allows instant port reuse after shutdown."""
    allow_reuse_address = True


class PK_LocalWebServerThread(QThread):
    """
    Asynchronous QThread running Python's built-in HTTP server
    to serve local HTML projects without blocking the CodeNexus UI.
    """
    server_started = pyqtSignal(int, str)   # port, host_url
    server_error = pyqtSignal(str)

    def __init__(self, root_directory: str, preferred_port: int = 8000):
        super().__init__()
        self.root_directory = os.path.abspath(root_directory)
        self.preferred_port = preferred_port
        self.httpd = None
        self._is_running = False

    def find_free_port(self, starting_port: int) -> int:
        """Finds the next available local port starting from preferred_port."""
        port = starting_port
        while port < 65535:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                if s.connect_ex(("127.0.0.1", port)) != 0:
                    return port
                port += 1
        return starting_port

    def run(self):
        allocated_port = self.find_free_port(self.preferred_port)

        class CustomDirHandler(SimpleHTTPRequestHandler):
            def __init__(handler_self, *args, **kwargs):
                super().__init__(*args, directory=self.root_directory, **kwargs)

            def log_message(handler_self, format, *args):
                # Suppress noisy standard HTTP access logs in console
                pass

        try:
            self.httpd = PK_ReusableTCPServer(("127.0.0.1", allocated_port), CustomDirHandler)
            self._is_running = True
            host_url = f"http://127.0.0.1:{allocated_port}"
            self.server_started.emit(allocated_port, host_url)
            self.httpd.serve_forever()
        except Exception as e:
            self.server_error.emit(f"Web server failed to start: {str(e)}")
        finally:
            self._is_running = False

    def stop(self):
        """Clean shutdown of the socket server."""
        if self.httpd:
            self.httpd.shutdown()
            self.httpd.server_close()
        self._is_running = False
        self.wait(1000)


class PK_HTMLLink(QObject):
    """
    Manager interface bridging HTML files to local preview servers
    and external browser dispatchers.
    """
    preview_ready = pyqtSignal(str)     # Full URL to preview
    server_stopped = pyqtSignal()
    status_changed = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.active_server_thread = None
        self.current_root_dir = ""
        self.current_url = ""

    def start_live_server(self, target_path: str, port: int = 8000) -> str:
        """
        Starts or restarts the local web server rooted at the target file's directory.
        Returns the generated URL.
        """
        if os.path.isfile(target_path):
            serve_dir = os.path.dirname(os.path.abspath(target_path))
            file_name = os.path.basename(target_path)
        elif os.path.isdir(target_path):
            serve_dir = os.path.abspath(target_path)
            file_name = "index.html"
        else:
            serve_dir = os.getcwd()
            file_name = "index.html"

        # If already running for this directory, reuse existing server
        if (
            self.active_server_thread 
            and self.active_server_thread.isRunning() 
            and self.current_root_dir == serve_dir
        ):
            target_url = f"{self.current_url}/{file_name}"
            self.preview_ready.emit(target_url)
            return target_url

        self.stop_server()

        self.current_root_dir = serve_dir
        self.active_server_thread = PK_LocalWebServerThread(serve_dir, preferred_port=port)
        self.active_server_thread.server_started.connect(
            lambda p, url: self._on_server_started(url, file_name)
        )
        self.active_server_thread.server_error.connect(
            lambda err: self.status_changed.emit(f"Server Error: {err}")
        )
        self.active_server_thread.start()
        return ""

    def _on_server_started(self, base_url: str, entry_file: str):
        self.current_url = base_url
        full_url = f"{base_url}/{entry_file}"
        self.status_changed.emit(f"Live server running at {base_url}")
        self.preview_ready.emit(full_url)

    def open_in_system_browser(self, target_url: str = None):
        """Launches the preview URL inside Chrome/Edge/Firefox."""
        url_to_open = target_url or self.current_url
        if url_to_open:
            webbrowser.open(url_to_open)

    def stop_server(self):
        """Stops the active web server instance."""
        if self.active_server_thread and self.active_server_thread.isRunning():
            self.active_server_thread.stop()
            self.active_server_thread = None
            self.current_url = ""
            self.server_stopped.emit()
            self.status_changed.emit("Web server stopped.")


# ----------------- Quick Standalone Runner -----------------
if __name__ == "__main__":
    from PyQt6.QtCore import QCoreApplication
    app = QCoreApplication(sys.argv)

    link = PK_HTMLLink()
    link.preview_ready.connect(lambda url: print(f"Preview URL Available: {url}"))
    link.status_changed.connect(lambda status: print(f"[HTML Link]: {status}"))

    # Test server in current working directory
    link.start_live_server(os.getcwd())

    from PyQt6.QtCore import QTimer
    QTimer.singleShot(3000, lambda: (link.stop_server(), app.quit()))
    sys.exit(app.exec())