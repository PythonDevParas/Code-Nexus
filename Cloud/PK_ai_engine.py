"""
CodeNexus - PK_ai_engine.py
Module: Cloud/PK_ai_engine.py
Description: Asynchronous streaming AI engine powered by OpenRouter API (openai/gpt-oss-120b).
"""

import json
import requests
from PyQt6.QtCore import QThread, pyqtSignal

# Default API Configuration
DEFAULT_API_URL = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_MODEL = "openai/gpt-oss-120b"
DEFAULT_API_KEY = "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"


class PK_AIStreamWorker(QThread):
    """
    QThread worker that streams token-by-token completions from OpenRouter
    without freezing the CodeNexus Qt UI.
    """
    chunk_received = pyqtSignal(str)   # Emitted on every incoming token/word
    started_stream = pyqtSignal()      # Emitted when HTTP connection succeeds
    finished = pyqtSignal()            # Emitted when streaming is complete
    error_occurred = pyqtSignal(str)   # Emitted on network/API failure

    def __init__(
        self,
        prompt: str,
        code_context: str = "",
        conversation_history: list = None,
        api_key: str = DEFAULT_API_KEY,
        model: str = DEFAULT_MODEL,
        api_url: str = DEFAULT_API_URL
    ):
        super().__init__()
        self.prompt = prompt.strip()
        self.code_context = code_context.strip()
        self.conversation_history = conversation_history or []
        self.api_key = api_key or DEFAULT_API_KEY
        self.model = model or DEFAULT_MODEL
        self.api_url = api_url or DEFAULT_API_URL
        self._is_cancelled = False

    def cancel(self):
        """Allows UI to abort the generation midway."""
        self._is_cancelled = True

    def run(self):
        if not self.prompt and not self.code_context:
            self.error_occurred.emit("Empty prompt or context provided.")
            self.finished.emit()
            return

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": "https://parasboxcloud.ai.studio",
            "X-Title": "CodeNexus AI IDLE",
            "Content-Type": "application/json"
        }

        system_instruction = (
            "You are CodeNexus Copilot, a high-performance AI coding assistant inside CodeNexus IDE. "
            "Provide clean, well-formatted, production-ready code with explanations. "
            "When analyzing or refactoring, refer directly to the user's provided code context."
        )

        messages = [{"role": "system", "content": system_instruction}]

        # Append previous conversation turns if provided
        for msg in self.conversation_history:
            messages.append(msg)

        # Build current user message with attached active file context
        user_message_content = ""
        if self.code_context:
            user_message_content += (
                f"--- CURRENT ACTIVE CODE CONTEXT ---\n"
                f"```\n{self.code_context}\n```\n\n"
            )
        user_message_content += f"User Request: {self.prompt}"
        messages.append({"role": "user", "content": user_message_content})

        payload = {
            "model": self.model,
            "messages": messages,
            "stream": True,
            "temperature": 0.3
        }

        try:
            response = requests.post(
                self.api_url,
                headers=headers,
                json=payload,
                stream=True,
                timeout=30
            )

            if response.status_code != 200:
                self.error_occurred.emit(
                    f"API Error ({response.status_code}): {response.text[:200]}"
                )
                self.finished.emit()
                return

            self.started_stream.emit()

            # Process Server-Sent Events (SSE) stream
            for raw_line in response.iter_lines():
                if self._is_cancelled:
                    break

                if raw_line:
                    line = raw_line.decode("utf-8").strip()
                    if not line.startswith("data:"):
                        continue

                    data_payload = line[5:].strip()
                    if data_payload == "[DONE]":
                        break

                    try:
                        parsed = json.loads(data_payload)
                        choices = parsed.get("choices", [])
                        if choices:
                            delta = choices[0].get("delta", {})
                            token = delta.get("content", "")
                            if token:
                                self.chunk_received.emit(token)
                    except json.JSONDecodeError:
                        continue

        except requests.exceptions.Timeout:
            self.error_occurred.emit("Request timed out. Please check your internet connection.")
        except requests.exceptions.RequestException as exc:
            self.error_occurred.emit(f"Network error: {str(exc)}")
        except Exception as exc:
            self.error_occurred.emit(f"Unexpected error: {str(exc)}")
        finally:
            self.finished.emit()


class PK_AIEngine:
    """
    Manager interface used by UI components to spawn, monitor,
    and cancel AI requests.
    """
    def __init__(self, api_key: str = DEFAULT_API_KEY, model: str = DEFAULT_MODEL):
        self.api_key = api_key
        self.model = model
        self.history = []
        self.current_worker = None

    def query_stream(self, prompt: str, code_context: str = "") -> PK_AIStreamWorker:
        """
        Creates and returns a new AI streaming worker.
        Connect to worker signals: chunk_received, finished, error_occurred.
        """
        if self.current_worker and self.current_worker.isRunning():
            self.current_worker.cancel()
            self.current_worker.wait()

        self.current_worker = PK_AIStreamWorker(
            prompt=prompt,
            code_context=code_context,
            conversation_history=self.history,
            api_key=self.api_key,
            model=self.model
        )
        return self.current_worker

    def record_turn(self, user_text: str, ai_response_text: str):
        """Preserves back-and-forth chat context across queries."""
        self.history.append({"role": "user", "content": user_text})
        self.history.append({"role": "assistant", "content": ai_response_text})
        # Keep sliding window to avoid token overflows
        if len(self.history) > 10:
            self.history = self.history[-10:]

    def clear_history(self):
        """Resets the context window."""
        self.history.clear()