"""
CodeNexus - AI-call.py
Module: UI/AI-call.py
Description: Action dispatcher, key manager, and SSE streaming bridge connecting
             CodeNexus editor buffers to OpenRouter (openai/gpt-oss-120b).
"""

import os
import sys
import json
import requests
from PyQt6.QtCore import QObject, QThread, pyqtSignal

# Ensure project root is in path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


class PK_AIStreamWorker(QThread):
    """
    Background worker that handles Server-Sent Events (SSE) streaming
    from OpenRouter without locking the GUI or WebEngine.
    """
    stream_started = pyqtSignal()
    token_received = pyqtSignal(str)
    stream_finished = pyqtSignal(str)   # Full accumulated text
    error_occurred = pyqtSignal(str)

    def __init__(self, api_key: str, prompt: str, code_context: str = "", model: str = "openai/gpt-oss-120b"):
        super().__init__()
        self.api_key = api_key
        self.prompt = prompt
        self.code_context = code_context
        self.model = model
        self.is_cancelled = False
        self.accumulated_text = ""

    def run(self):
        if not self.api_key:
            self.error_occurred.emit("OpenRouter API key is missing. Set it in settings or config.")
            return

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://parasboxcloud.ai.studio",
            "X-Title": "CodeNexus IDE"
        }

        full_user_content = self.prompt
        if self.code_context.strip():
            full_user_content = f"```\n{self.code_context}\n```\n\nTask: {self.prompt}"

        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are CodeNexus Copilot, an expert AI programming assistant. "
                        "Write clean, idiomatic, and robust code. Keep prose concise and directly actionable."
                    )
                },
                {"role": "user", "content": full_user_content}
            ],
            "stream": True
        }

        self.stream_started.emit()

        try:
            response = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json=payload,
                stream=True,
                timeout=30
            )

            if response.status_code != 200:
                try:
                    err_json = response.json()
                    err_msg = err_json.get("error", {}).get("message", response.text)
                except Exception:
                    err_msg = response.text
                self.error_occurred.emit(f"OpenRouter Error ({response.status_code}): {err_msg}")
                return

            for line in response.iter_lines(decode_unicode=True):
                if self.is_cancelled:
                    break

                if not line:
                    continue

                line_clean = line.strip()
                if line_clean == "data: [DONE]":
                    break

                if line_clean.startswith("data: "):
                    raw_data = line_clean[6:].strip()
                    try:
                        chunk = json.loads(raw_data)
                        choices = chunk.get("choices", [])
                        if choices:
                            delta = choices[0].get("delta", {})
                            token = delta.get("content", "")
                            if token:
                                self.accumulated_text += token
                                self.token_received.emit(token)
                    except Exception:
                        continue

            self.stream_finished.emit(self.accumulated_text)

        except requests.exceptions.Timeout:
            self.error_occurred.emit("AI request timed out after 30 seconds.")
        except requests.exceptions.RequestException as e:
            self.error_occurred.emit(f"Network error: {str(e)}")
        except Exception as e:
            self.error_occurred.emit(f"Unexpected AI error: {str(e)}")

    def cancel(self):
        self.is_cancelled = True


class PK_AICall(QObject):
    """
    High-level API dispatcher for AI Copilot actions, key persistence,
    and prompt engineering templates.
    """
    stream_started = pyqtSignal()
    token_received = pyqtSignal(str)
    stream_finished = pyqtSignal(str)
    error_occurred = pyqtSignal(str)

    def __init__(self, workspace_dir: str = None, parent=None):
        super().__init__(parent)
        self.workspace_dir = workspace_dir or PROJECT_ROOT
        self.active_worker = None

    # --- API Key Resolution & Persistence ---

    def get_api_key(self) -> str:
        """Resolves API key from environment variable or Data/ai_config.json."""
        env_key = os.environ.get("OPENROUTER_API_KEY", "").strip()
        if env_key:
            return env_key

        config_path = os.path.join(self.workspace_dir, "Data", "ai_config.json")
        if os.path.isfile(config_path):
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return data.get("openrouter_api_key", "").strip()
            except Exception:
                pass
        return ""

    def save_api_key(self, api_key: str) -> bool:
        """Saves API key to Data/ai_config.json."""
        data_dir = os.path.join(self.workspace_dir, "Data")
        os.makedirs(data_dir, exist_ok=True)
        config_path = os.path.join(data_dir, "ai_config.json")
        try:
            cfg = {}
            if os.path.isfile(config_path):
                try:
                    with open(config_path, "r", encoding="utf-8") as f:
                        cfg = json.load(f)
                except Exception:
                    pass
            cfg["openrouter_api_key"] = api_key.strip()
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(cfg, f, indent=2)
            return True
        except Exception:
            return False

    # --- Core Dispatcher ---

    def execute_query(self, prompt: str, code_context: str = ""):
        """Dispatches an asynchronous query with optional code context."""
        api_key = self.get_api_key()
        if not api_key:
            self.error_occurred.emit("API key missing. Save your OpenRouter key to continue.")
            return

        self.cancel_active_stream()

        self.active_worker = PK_AIStreamWorker(
            api_key=api_key,
            prompt=prompt,
            code_context=code_context
        )
        self.active_worker.stream_started.connect(self.stream_started.emit)
        self.active_worker.token_received.connect(self.token_received.emit)
        self.active_worker.stream_finished.connect(self.stream_finished.emit)
        self.active_worker.error_occurred.connect(self.error_occurred.emit)
        self.active_worker.start()

    # --- Preset Code Workflows ---

    def explain_code(self, code_snippet: str, language: str = "python"):
        prompt = (
            f"Explain the logic, purpose, potential edge cases, and performance considerations "
            f"of this {language} snippet clearly and concisely."
        )
        self.execute_query(prompt, code_snippet)

    def refactor_code(self, code_snippet: str, instructions: str = "Optimize and improve readability"):
        prompt = (
            f"Refactor the provided code according to this instruction: '{instructions}'. "
            f"Output the improved code in markdown blocks followed by a concise summary of changes."
        )
        self.execute_query(prompt, code_snippet)

    def generate_tests(self, code_snippet: str, language: str = "python"):
        prompt = (
            f"Write a comprehensive unit test suite for this {language} code covering normal cases, "
            f"boundary inputs, and error handling."
        )
        self.execute_query(prompt, code_snippet)

    def fix_traceback(self, code_snippet: str, error_traceback: str):
        prompt = (
            f"The following code raised an error:\n"
            f"--- ERROR TRACEBACK ---\n{error_traceback}\n------------------------\n"
            f"Diagnose the root cause and provide the patched code snippet."
        )
        self.execute_query(prompt, code_snippet)

    def cancel_active_stream(self):
        if self.active_worker and self.active_worker.isRunning():
            self.active_worker.cancel()
            self.active_worker.wait(1000)
            self.active_worker = None


# ----------------- Quick Standalone Test -----------------
if __name__ == "__main__":
    from PyQt6.QtCore import QCoreApplication
    app = QCoreApplication(sys.argv)

    caller = PK_AICall()
    caller.token_received.connect(lambda t: print(t, end="", flush=True))
    caller.error_occurred.connect(lambda e: (print(f"\n[Error]: {e}"), app.quit()))
    caller.stream_finished.connect(lambda full: (print("\n[Done]"), app.quit()))

    print("Checking API key...")
    if not caller.get_api_key():
        print("Notice: No API key saved in Data/ai_config.json or OPENROUTER_API_KEY env.")
    else:
        print("Dispatching test query...")
        caller.explain_code("def add(a: int, b: int) -> int:\n    return a + b", "python")

    sys.exit(app.exec())