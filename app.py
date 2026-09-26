"""
CodeNexus IDE - main.py (Robust Production Engine)
Description: Production desktop IDE window runner using pywebview.
Features:
 - Resilient Stealth Git Pipeline (Non-blocking auth, reliable output)
 - Autonomous Multi-File AI Agent (Sanitized token stream, strict agent parsing)
 - Portable Git Engine auto-detection (Data/git/bin, Data/git/cmd)
 - Cross-Drive Dynamic Execution (No hardcoded paths, sys._MEIPASS aware)
 - 5-Second Centered Animated Splash Screen with Custom Logo
 - Sandboxed Workspace defaulting to Desktop
 - VS Code Style Multi-Tabs & In-App Browser Tab
 - Interactive Terminal piping direct Windows CMD / Stdin
 - Silent Local Cloud Integration via Cloud/PK_temp_local_cloud.py
"""

import os
import sys
import time
import json
import base64
import shutil
import threading
import subprocess
import re
from pathlib import Path
import webview

# 1. डायनामिक बेस डायरेक्टरी (EXE और स्क्रिप्ट दोनों के लिए सुरक्षित)
if getattr(sys, 'frozen', False):
    BASE_DIR = sys._MEIPASS
    APP_EXEC_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    APP_EXEC_DIR = BASE_DIR

# 2. मॉड्यूल्स पाथ्स को लिंक करना
for folder in ["Cloud", "Core", "Link", "UI", "Data", "temp"]:
    p = os.path.join(BASE_DIR, folder)
    if p not in sys.path:
        sys.path.insert(0, p)

DESKTOP_DIR = str(Path.home() / "Desktop")

try:
    import file_Runner
    PK_FileRunner = getattr(file_Runner, "PK_FileRunner", None)
except Exception:
    PK_FileRunner = None

PK_LocalCloudManager = None
try:
    import PK_temp_local_cloud
    if hasattr(PK_temp_local_cloud, "PK_LocalCloudManager"):
        PK_LocalCloudManager = PK_temp_local_cloud.PK_LocalCloudManager
    elif hasattr(PK_temp_local_cloud, "PK_TempLocalCloud"):
        PK_LocalCloudManager = PK_temp_local_cloud.PK_TempLocalCloud
except Exception:
    PK_LocalCloudManager = None

DEFAULT_OPENROUTER_KEY = "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"
DEFAULT_AI_MODEL = "openai/gpt-oss-120b"


def find_app_logo(workspace_dir):
    search_dirs = [
        os.path.join(workspace_dir, "Data", "icons"),
        os.path.join(APP_EXEC_DIR, "Data", "icons"),
        workspace_dir,
        APP_EXEC_DIR
    ]
    icon_path = ""

    for s_dir in search_dirs:
        if os.path.isdir(s_dir):
            for name in ["logo", "mc"]:
                for ext in [".ico", ".png", ".jpg", ".jpeg"]:
                    candidate = os.path.join(s_dir, f"{name}{ext}")
                    if os.path.isfile(candidate):
                        icon_path = candidate
                        break
                if icon_path:
                    break
        if icon_path:
            break

    if icon_path:
        ext = os.path.splitext(icon_path)[1].lower().replace(".", "")
        mime = "image/x-icon" if ext == "ico" else f"image/{ext}"
        try:
            with open(icon_path, "rb") as img_f:
                encoded = base64.b64encode(img_f.read()).decode("utf-8")
            return icon_path, f"data:{mime};base64,{encoded}"
        except Exception:
            return icon_path, ""

    return "", ""


APP_ICON_PATH, APP_LOGO_DATA_URI = find_app_logo(BASE_DIR)


SPLASH_HTML = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Initializing CodeNexus IDE</title>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; user-select: none; }}
    body {{
      display: flex; flex-direction: column; justify-content: center; align-items: center;
      height: 100vh; width: 100vw; overflow: hidden; background-color: #11111b; color: #cdd6f4;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }}
    .logo-box {{
      width: 100px; height: 100px; margin-bottom: 20px;
      display: flex; justify-content: center; align-items: center;
      border-radius: 20px; background: #181825; border: 1px solid #313244;
      box-shadow: 0 0 35px rgba(137, 180, 250, 0.25);
      animation: pulseLogo 2s infinite alternate ease-in-out;
    }}
    .logo-box img {{
      width: 68px; height: 68px; object-fit: contain;
    }}
    @keyframes pulseLogo {{
      0% {{ transform: scale(0.97); box-shadow: 0 0 20px rgba(137, 180, 250, 0.2); }}
      100% {{ transform: scale(1.03); box-shadow: 0 0 40px rgba(137, 180, 250, 0.45); }}
    }}
    .title {{
      font-size: 22px; font-weight: 800; letter-spacing: 1.2px; color: #89b4fa;
      margin-bottom: 6px; text-shadow: 0 0 10px rgba(137, 180, 250, 0.3);
    }}
    .status-text {{
      font-size: 13px; color: #a6adc8; margin-bottom: 22px; letter-spacing: 0.5px;
    }}
    .progress-bar-container {{
      width: 260px; height: 5px; background: #1e1e2e; border-radius: 6px;
      overflow: hidden; border: 1px solid #313244;
    }}
    .progress-bar-fill {{
      height: 100%; width: 0%; background: linear-gradient(90deg, #89b4fa, #a6e3a1);
      border-radius: 6px;
      animation: loadFill 4.8s cubic-bezier(0.1, 0.8, 0.2, 1) forwards;
    }}
    @keyframes loadFill {{
      0% {{ width: 0%; }}
      40% {{ width: 55%; }}
      80% {{ width: 85%; }}
      100% {{ width: 100%; }}
    }}
  </style>
</head>
<body>
  <div class="logo-box">
    <img src="{APP_LOGO_DATA_URI}" alt="Logo">
  </div>
  <div class="title">CODENEXUS IDE</div>
  <div class="status-text">Initializing CodeNexus IDE...</div>
  <div class="progress-bar-container">
    <div class="progress-bar-fill"></div>
  </div>
</body>
</html>
"""


class CodeNexusAPI:
    def __init__(self):
        self._window = None
        self.workspace_dir = DESKTOP_DIR if os.path.isdir(DESKTOP_DIR) else BASE_DIR
        self.active_file_path = ""
        self.open_buffers = {}
        self.runner = PK_FileRunner(default_cwd=self.workspace_dir) if PK_FileRunner else None
        self.local_cloud = PK_LocalCloudManager() if PK_LocalCloudManager else None
        
        self.active_process = None
        self.process_lock = threading.Lock()

    def set_window(self, window):
        self._window = window

    def get_app_logo(self):
        return APP_LOGO_DATA_URI

    # --- 1. Workspace & Shallow Explorer ---
    def get_workspace_tree(self):
        return self._build_directory_shallow(self.workspace_dir)

    def get_folder_children(self, folder_path):
        if not os.path.isdir(folder_path):
            return []
        items = []
        try:
            entries = sorted(os.listdir(folder_path))
            for entry in entries:
                if entry in [".git", "__pycache__", ".venv", "venv", ".idea", "$RECYCLE.BIN"]:
                    continue
                full_path = os.path.join(folder_path, entry)
                if os.path.isdir(full_path):
                    items.append({"name": entry, "path": full_path, "type": "folder"})
                else:
                    items.append({"name": entry, "path": full_path, "type": "file"})
        except Exception:
            pass
        return items

    def _build_directory_shallow(self, path):
        root_name = os.path.basename(path) or path
        result = {"name": root_name, "path": path, "type": "folder", "children": []}
        try:
            entries = sorted(os.listdir(path))
            for entry in entries:
                if entry in [".git", "__pycache__", ".venv", "venv", ".idea", "$RECYCLE.BIN"]:
                    continue
                full_path = os.path.join(path, entry)
                if os.path.isdir(full_path):
                    result["children"].append({
                        "name": entry,
                        "path": full_path,
                        "type": "folder",
                        "children": []
                    })
                else:
                    result["children"].append({
                        "name": entry,
                        "path": full_path,
                        "type": "file"
                    })
        except Exception:
            pass
        return result

    def open_file_dialog(self):
        if not self._window:
            return {"error": "Window not initialized"}

        file_types = ('Source Files (*.py;*.html;*.htm;*.js;*.css;*.json;*.nx;*.txt;*.md)', 'All files (*.*)')
        result = self._window.create_file_dialog(webview.OPEN_DIALOG, allow_multiple=False, file_types=file_types)
        
        if result and len(result) > 0:
            target_path = result[0]
            parent_dir = os.path.dirname(os.path.abspath(target_path))
            if os.path.isdir(parent_dir):
                self.workspace_dir = parent_dir
                if self.runner:
                    self.runner.default_cwd = self.workspace_dir

            file_res = self.open_file(target_path)
            file_res["workspace_changed"] = True
            return file_res
        return {"cancelled": True}

    def open_file(self, file_path):
        if not os.path.isfile(file_path):
            return {"error": "Target file does not exist on disk."}

        self.active_file_path = file_path
        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()

            self.open_buffers[file_path] = content
            ext = os.path.splitext(file_path)[1].lower()
            lang_map = {
                ".py": "python", ".pyw": "python", ".js": "javascript",
                ".html": "html", ".htm": "html", ".css": "css",
                ".json": "json", ".cpp": "cpp", ".c": "c",
                ".md": "markdown", ".bat": "bat", ".nx": "plaintext"
            }
            language = lang_map.get(ext, "plaintext")

            return {
                "success": True,
                "path": file_path,
                "filename": os.path.basename(file_path),
                "content": content,
                "language": language
            }
        except Exception as e:
            return {"error": f"Failed reading file: {str(e)}"}

    def save_file(self, file_path, content):
        target_path = file_path or self.active_file_path
        if not target_path:
            return {"error": "No target file specified."}

        try:
            os.makedirs(os.path.dirname(os.path.abspath(target_path)), exist_ok=True)
            with open(target_path, "w", encoding="utf-8") as f:
                f.write(content)
            self.active_file_path = target_path
            self.open_buffers[target_path] = content
            return {"success": True, "message": f"Saved {os.path.basename(target_path)}"}
        except Exception as e:
            return {"error": f"Save failed: {str(e)}"}

    def create_new_file(self, target_dir, file_name):
        dest_dir = target_dir if (target_dir and os.path.isdir(target_dir)) else self.workspace_dir
        clean_name = os.path.basename(file_name.strip())
        if not clean_name:
            return {"success": False, "message": "File name cannot be empty."}

        target_file = os.path.join(dest_dir, clean_name)
        if os.path.exists(target_file):
            return {"success": False, "message": f"File '{clean_name}' already exists."}

        try:
            with open(target_file, "w", encoding="utf-8") as f:
                f.write("")
            return {"success": True, "path": target_file, "filename": clean_name}
        except Exception as e:
            return {"success": False, "message": f"Failed creating file: {str(e)}"}

    def create_new_folder(self, target_dir, folder_name):
        dest_dir = target_dir if (target_dir and os.path.isdir(target_dir)) else self.workspace_dir
        clean_name = os.path.basename(folder_name.strip())
        if not clean_name:
            return {"success": False, "message": "Folder name cannot be empty."}

        target_folder = os.path.join(dest_dir, clean_name)
        if os.path.exists(target_folder):
            return {"success": False, "message": f"Folder '{clean_name}' already exists."}

        try:
            os.makedirs(target_folder, exist_ok=True)
            return {"success": True, "path": target_folder, "foldername": clean_name}
        except Exception as e:
            return {"success": False, "message": f"Failed creating folder: {str(e)}"}

    def rename_item(self, target_path, new_name):
        if not os.path.exists(target_path):
            return {"success": False, "message": "Item does not exist on disk."}
        if os.path.abspath(target_path) == os.path.abspath(self.workspace_dir):
            return {"success": False, "message": "Cannot rename root workspace directory."}

        clean_name = os.path.basename(new_name.strip())
        if not clean_name:
            return {"success": False, "message": "New name cannot be empty."}

        parent_dir = os.path.dirname(target_path)
        dest_path = os.path.join(parent_dir, clean_name)

        if os.path.exists(dest_path):
            return {"success": False, "message": f"An item named '{clean_name}' already exists."}

        try:
            os.rename(target_path, dest_path)
            if self.active_file_path == target_path:
                self.active_file_path = dest_path

            return {
                "success": True,
                "old_path": target_path,
                "new_path": dest_path,
                "new_name": clean_name
            }
        except Exception as e:
            return {"success": False, "message": f"Rename failed: {str(e)}"}

    def delete_item(self, target_path):
        if not os.path.exists(target_path):
            return {"success": False, "message": "Item does not exist."}
        if os.path.abspath(target_path) == os.path.abspath(self.workspace_dir):
            return {"success": False, "message": "Cannot delete root workspace directory."}

        try:
            if os.path.isdir(target_path):
                shutil.rmtree(target_path)
            else:
                os.remove(target_path)
            return {"success": True, "message": f"Deleted {os.path.basename(target_path)}"}
        except Exception as e:
            return {"success": False, "message": f"Delete failed: {str(e)}"}

    # --- 2. Interactive Execution & Windows CMD Pipe ---
    def run_file(self, file_path, content):
        target_path = file_path or self.active_file_path
        if not target_path:
            target_path = os.path.join(self.workspace_dir, "temp_run.py")

        save_res = self.save_file(target_path, content)
        if "error" in save_res:
            return {"success": False, "output": save_res["error"]}

        if self.runner and hasattr(self.runner, "check_file"):
            inspection = self.runner.check_file(target_path, content)
            type_key = inspection.get("type_key", "UNKNOWN")
            file_type_name = inspection.get("file_type", "File")

            if not inspection.get("is_valid", True):
                return {
                    "success": False,
                    "output": f"=== PRE-EXECUTION CHECK FAILED [{file_type_name}] ===\n{inspection.get('report', '')}\n\nExecution aborted."
                }

            if type_key == "HTML":
                target_url = "file:///" + target_path.replace("\\", "/")
                escaped_url = json.dumps(target_url)
                self._window.evaluate_js(f"openInBrowserTab({escaped_url}, 'HTML Preview');")
                return {
                    "success": True,
                    "output": f"=== HTML VALIDATED ===\n{inspection.get('report', '')}\nOpened preview in internal Browser Tab."
                }

        self.stop_active_process()

        def _reader_thread(pipe):
            try:
                for line in iter(pipe.readline, ''):
                    if line:
                        escaped = json.dumps(line)
                        self._window.evaluate_js(f"appendTerminalChunk({escaped});")
                pipe.close()
            except Exception:
                pass

        def _monitor_thread(proc):
            proc.wait()
            ret_code = proc.returncode
            status_text = f"\n[Process completed with exit code {ret_code}]\n"
            escaped = json.dumps(status_text)
            self._window.evaluate_js(f"onProcessFinished({escaped});")
            with self.process_lock:
                self.active_process = None

        working_dir = os.path.dirname(os.path.abspath(target_path))
        cmd = [sys.executable, "-u", target_path]

        try:
            startupinfo = None
            creationflags = 0
            if sys.platform == "win32":
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                creationflags = 0x08000000  # CREATE_NO_WINDOW

            with self.process_lock:
                self.active_process = subprocess.Popen(
                    cmd,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    bufsize=1,
                    cwd=working_dir,
                    encoding="utf-8",
                    errors="replace",
                    startupinfo=startupinfo,
                    creationflags=creationflags
                )

            t_out = threading.Thread(target=_reader_thread, args=(self.active_process.stdout,), daemon=True)
            t_err = threading.Thread(target=_reader_thread, args=(self.active_process.stderr,), daemon=True)
            t_mon = threading.Thread(target=_monitor_thread, args=(self.active_process,), daemon=True)

            t_out.start()
            t_err.start()
            t_mon.start()

            return {"success": True, "output": f"=== Execution Started: {os.path.basename(target_path)} ===\n"}
        except Exception as e:
            return {"success": False, "output": f"[Execution Start Failed]: {str(e)}"}

    def send_terminal_input(self, user_input):
        raw_cmd = user_input.strip()
        if not raw_cmd:
            return {"success": True}

        with self.process_lock:
            if self.active_process and self.active_process.poll() is None:
                try:
                    self.active_process.stdin.write(user_input + "\n")
                    self.active_process.stdin.flush()
                    return {"success": True, "type": "stdin"}
                except Exception as e:
                    return {"success": False, "message": f"Input error: {str(e)}"}

        def _run_cmd_worker(cmd_str):
            try:
                startupinfo = None
                creationflags = 0
                if sys.platform == "win32":
                    startupinfo = subprocess.STARTUPINFO()
                    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                    creationflags = 0x08000000

                proc = subprocess.run(
                    cmd_str,
                    shell=True,
                    capture_output=True,
                    text=True,
                    cwd=self.workspace_dir,
                    encoding="utf-8",
                    errors="replace",
                    timeout=30,
                    startupinfo=startupinfo,
                    creationflags=creationflags
                )
                output = proc.stdout
                if proc.stderr:
                    output += "\n" + proc.stderr
                if not output:
                    output = "[Command executed successfully with no output]"
                escaped = json.dumps(output + "\n")
                self._window.evaluate_js(f"appendTerminalChunk({escaped});")
            except subprocess.TimeoutExpired:
                self._window.evaluate_js("appendTerminalChunk('\\n[Command Timed Out after 30s]\\n');")
            except Exception as ex:
                escaped_err = json.dumps(f"\n[CMD Error]: {str(ex)}\n")
                self._window.evaluate_js(f"appendTerminalChunk({escaped_err});")

        threading.Thread(target=_run_cmd_worker, args=(raw_cmd,), daemon=True).start()
        return {"success": True, "type": "cmd", "message": f"[Command Sent to CMD]: {raw_cmd}"}

    def stop_active_process(self):
        with self.process_lock:
            if self.active_process and self.active_process.poll() is None:
                try:
                    self.active_process.terminate()
                    threading.Timer(1.0, self._force_kill_process, [self.active_process]).start()
                    return {"success": True, "message": "Process stopped."}
                except Exception as e:
                    return {"success": False, "message": str(e)}
        return {"success": True, "message": "No process running."}

    def _force_kill_process(self, proc):
        try:
            if proc.poll() is None:
                proc.kill()
        except Exception:
            pass

    # --- 3. PK_temp_local_cloud Integration ---
    def cloud_upload(self, filename, content):
        if not self.local_cloud:
            return {"success": False, "message": "PK_temp_local_cloud module is not loaded."}
        fname = filename or os.path.basename(self.active_file_path) or "cloud_file.txt"
        if hasattr(self.local_cloud, "upload_file"):
            return self.local_cloud.upload_file(fname, content)
        elif hasattr(self.local_cloud, "save_file"):
            return self.local_cloud.save_file(fname, content)
        return {"success": False, "message": "Upload method missing in PK_temp_local_cloud."}

    def cloud_download(self, filename):
        if not self.local_cloud:
            return {"success": False, "message": "PK_temp_local_cloud module is not loaded."}
        if hasattr(self.local_cloud, "download_file"):
            return self.local_cloud.download_file(filename)
        elif hasattr(self.local_cloud, "get_file"):
            return self.local_cloud.get_file(filename)
        return {"success": False, "message": "Download method missing in PK_temp_local_cloud."}

    def cloud_flush(self):
        if not self.local_cloud:
            return {"success": False, "message": "PK_temp_local_cloud module is not loaded."}
        if hasattr(self.local_cloud, "flush_cloud"):
            return self.local_cloud.flush_cloud()
        elif hasattr(self.local_cloud, "clear_all"):
            return self.local_cloud.clear_all()
        return {"success": False, "message": "Flush method missing in PK_temp_local_cloud."}

    # --- 4. Stealth Git Deployer Engine ---
    def _find_git_binary(self):
        portable_paths = [
            os.path.join(APP_EXEC_DIR, "Data", "git", "bin", "git.exe"),
            os.path.join(APP_EXEC_DIR, "Data", "git", "cmd", "git.exe"),
            os.path.join(APP_EXEC_DIR, "Data", "git", "git.exe"),
            os.path.join(APP_EXEC_DIR, "Data", ".git", "bin", "git.exe"),
            os.path.join(APP_EXEC_DIR, "Data", ".git", "cmd", "git.exe"),
            os.path.join(BASE_DIR, "Data", "git", "bin", "git.exe"),
            os.path.join(BASE_DIR, "Data", "git", "cmd", "git.exe"),
            os.path.join(BASE_DIR, "Data", "git", "git.exe"),
        ]
        for p in portable_paths:
            if os.path.isfile(p):
                return p
        
        system_git = shutil.which("git")
        if system_git:
            return system_git

        return "git"

    def deploy_to_github(self, repo_url, commit_message):
        repo_url = repo_url.strip()
        commit_message = commit_message.strip() or "Auto deploy via CodeNexus IDE"

        if not repo_url:
            return {"success": False, "message": "Repository link cannot be empty!"}

        git_bin = self._find_git_binary()
        ws_dir = self.workspace_dir

        def _deploy_worker():
            def log_term(text):
                escaped = json.dumps(text + "\n")
                self._window.evaluate_js(f"appendTerminalChunk({escaped});")

            log_term("\n==============================================")
            log_term("🚀 [CodeNexus Deployer] Starting Silent Pipeline...")
            log_term(f"📂 Workspace: {ws_dir}")
            log_term(f"🔗 Target Repo: {repo_url}")
            log_term(f"📝 Commit: \"{commit_message}\"")
            log_term("==============================================")

            env = os.environ.copy()
            env["GIT_TERMINAL_PROMPT"] = "0"  # बैकग्राउंड में यूजर प्रॉम्प्ट से लटकने से रोके

            def run_git_stealth(args, allow_fail=False):
                cmd = [git_bin] + args
                try:
                    startupinfo = None
                    creationflags = 0
                    if sys.platform == "win32":
                        startupinfo = subprocess.STARTUPINFO()
                        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                        creationflags = 0x08000000

                    res = subprocess.run(
                        cmd,
                        cwd=ws_dir,
                        capture_output=True,
                        text=True,
                        encoding="utf-8",
                        errors="replace",
                        env=env,
                        startupinfo=startupinfo,
                        creationflags=creationflags
                    )
                    out = res.stdout.strip()
                    err = res.stderr.strip()
                    if out:
                        log_term(f"  {out}")
                    if err and res.returncode != 0 and not allow_fail:
                        log_term(f"  ⚠️ [Git Notice]: {err}")
                    return res.returncode == 0
                except Exception as ex:
                    log_term(f"  ❌ Execution Error '{' '.join(args)}': {str(ex)}")
                    return False

            dot_git = os.path.join(ws_dir, ".git")
            if not os.path.isdir(dot_git):
                log_term("Step 1/6: Initializing Git repository...")
                run_git_stealth(["init"])
            else:
                log_term("Step 1/6: Repository already initialized.")

            run_git_stealth(["config", "user.name", "CodeNexus Dev"], allow_fail=True)
            run_git_stealth(["config", "user.email", "dev@codenexus.local"], allow_fail=True)

            log_term("Step 2/6: Staging files (git add -A)...")
            run_git_stealth(["add", "-A"])

            log_term("Step 3/6: Committing changes...")
            run_git_stealth(["commit", "-m", commit_message], allow_fail=True)

            log_term("Step 4/6: Setting branch 'main'...")
            run_git_stealth(["branch", "-M", "main"])

            log_term("Step 5/6: Setting remote origin URL...")
            run_git_stealth(["remote", "remove", "origin"], allow_fail=True)
            run_git_stealth(["remote", "add", "origin", repo_url])

            log_term("Step 6/6: Pushing to GitHub...")
            success = run_git_stealth(["push", "-u", "origin", "main", "--force"])

            if success:
                log_term("\n🎉 SUCCESS: Code successfully pushed to GitHub!")
                self._window.evaluate_js("onDeployComplete(true, 'Successfully pushed to GitHub!');")
            else:
                log_term("\n❌ PUSH FAILED: Ensure repo URL is valid and token/credentials have write access.")
                self._window.evaluate_js("onDeployComplete(false, 'Git push failed. See terminal for details.');")

        threading.Thread(target=_deploy_worker, daemon=True).start()
        return {"success": True, "message": "Deployment initiated silently in background."}

    # --- 5. Clean Autonomous AI Agent Operations Engine ---
    def execute_ai_agent_ops(self, actions_json_str):
        try:
            cleaned_json = actions_json_str.strip()
            actions = json.loads(cleaned_json)
        except Exception as e:
            return {"success": False, "error": f"JSON Parse Failed: {str(e)}"}

        results = []
        files_to_open_or_refresh = []

        for act in actions:
            action_type = act.get("action", "").lower().strip()
            rel_path = act.get("path", "").strip()
            content = act.get("content", "")

            if not rel_path:
                continue

            full_path = os.path.normpath(os.path.join(self.workspace_dir, rel_path))

            if not full_path.startswith(os.path.normpath(self.workspace_dir)):
                results.append({"action": action_type, "path": rel_path, "success": False, "error": "Path out of bounds."})
                continue

            try:
                if action_type in ["create_file", "write_file", "edit_file", "fix_file"]:
                    os.makedirs(os.path.dirname(full_path), exist_ok=True)
                    with open(full_path, "w", encoding="utf-8") as f:
                        f.write(content)
                    self.open_buffers[full_path] = content
                    files_to_open_or_refresh.append({
                        "path": full_path,
                        "filename": os.path.basename(full_path),
                        "content": content
                    })
                    results.append({"action": action_type, "path": rel_path, "success": True})

                elif action_type == "create_folder":
                    os.makedirs(full_path, exist_ok=True)
                    results.append({"action": action_type, "path": rel_path, "success": True})

                elif action_type == "delete_file":
                    if os.path.isfile(full_path):
                        os.remove(full_path)
                        self.open_buffers.pop(full_path, None)
                        results.append({"action": action_type, "path": rel_path, "success": True})
                    else:
                        results.append({"action": action_type, "path": rel_path, "success": False, "error": "File not found."})

                elif action_type == "delete_folder":
                    if os.path.isdir(full_path):
                        shutil.rmtree(full_path)
                        results.append({"action": action_type, "path": rel_path, "success": True})
                    else:
                        results.append({"action": action_type, "path": rel_path, "success": False, "error": "Folder not found."})
                else:
                    results.append({"action": action_type, "path": rel_path, "success": False, "error": f"Unknown action: {action_type}"})

            except Exception as ex:
                results.append({"action": action_type, "path": rel_path, "success": False, "error": str(ex)})

        return {
            "success": True,
            "results": results,
            "synced_files": files_to_open_or_refresh
        }

    def get_ai_key(self):
        env_key = os.environ.get("OPENROUTER_API_KEY", "").strip()
        if env_key:
            return env_key

        config_path = os.path.join(APP_EXEC_DIR, "Data", "ai_config.json")
        if not os.path.isfile(config_path):
            config_path = os.path.join(BASE_DIR, "Data", "ai_config.json")

        if os.path.isfile(config_path):
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    k = json.load(f).get("openrouter_api_key", "").strip()
                    if k:
                        return k
            except Exception:
                pass
        return DEFAULT_OPENROUTER_KEY

    def save_ai_key(self, key):
        data_dir = os.path.join(APP_EXEC_DIR, "Data")
        os.makedirs(data_dir, exist_ok=True)
        config_path = os.path.join(data_dir, "ai_config.json")
        try:
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump({"openrouter_api_key": key.strip(), "default_model": DEFAULT_AI_MODEL}, f, indent=2)
            return {"success": True, "message": "API key stored in Data/ai_config.json"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    def ask_ai_stream(self, prompt, code_context=""):
        api_key = self.get_ai_key()
        if not api_key:
            self._window.evaluate_js("onAIError('OpenRouter API Key not set! Set your key in settings.');")
            return {"status": "missing_key"}

        def _worker():
            import requests

            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://parasboxcloud.ai.studio",
                "X-Title": "CodeNexus IDE"
            }

            system_instruction = (
                "You are CodeNexus Copilot, an autonomous developer AI.\n"
                "Provide a clean, human-readable explanation first.\n"
                "If the user asks to create, edit, write, delete, or fix files/folders, append an action block at the VERY END formatted strictly as:\n"
                "```codenexus-agent\n"
                "[\n"
                "  {\"action\": \"create_file\" | \"write_file\" | \"edit_file\" | \"fix_file\", \"path\": \"relative/path.py\", \"content\": \"...clean content...\"},\n"
                "  {\"action\": \"create_folder\", \"path\": \"relative/folder\"},\n"
                "  {\"action\": \"delete_file\", \"path\": \"relative/file.txt\"},\n"
                "  {\"action\": \"delete_folder\", \"path\": \"relative/folder\"}\n"
                "]\n"
                "```\n"
                "Do NOT output broken characters or raw escaped junk outside this block."
            )

            full_prompt = f"```\n{code_context}\n```\n\nTask: {prompt}" if code_context.strip() else prompt

            payload = {
                "model": DEFAULT_AI_MODEL,
                "messages": [
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": full_prompt}
                ],
                "stream": True
            }

            try:
                self._window.evaluate_js("onAIStreamStart();")
                response = requests.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers=headers,
                    json=payload,
                    stream=True,
                    timeout=55
                )

                if response.status_code != 200:
                    try:
                        err_detail = response.json().get("error", {}).get("message", response.text)
                    except Exception:
                        err_detail = response.text
                    err_msg = json.dumps(f"API Error ({response.status_code}): {err_detail}")
                    self._window.evaluate_js(f"onAIError({err_msg});")
                    return

                for raw_line in response.iter_lines(decode_unicode=True):
                    if not raw_line:
                        continue
                    line = raw_line.strip()
                    if line == "data: [DONE]":
                        break
                    if line.startswith("data: "):
                        data_str = line[6:].strip()
                        if not data_str:
                            continue
                        try:
                            chunk = json.loads(data_str)
                            choices = chunk.get("choices", [])
                            if choices and len(choices) > 0:
                                delta = choices[0].get("delta", {})
                                token = delta.get("content", None)
                                if token and isinstance(token, str):
                                    sanitized_token = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', token)
                                    escaped_token = json.dumps(sanitized_token)
                                    self._window.evaluate_js(f"onAIChunkReceived({escaped_token});")
                        except Exception:
                            continue

                self._window.evaluate_js("onAIStreamFinished();")

            except requests.exceptions.Timeout:
                self._window.evaluate_js("onAIError('AI request timed out after 55 seconds.');")
            except Exception as e:
                self._window.evaluate_js(f"onAIError({json.dumps(str(e))});")

        threading.Thread(target=_worker, daemon=True).start()
        return {"status": "started"}


# =============================================================================
# Monaco Single-Page Application (HTML / CSS / JS)
# =============================================================================
HTML_SHELL = r"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>CodeNexus IDE</title>
  <link id="dynamic-favicon" rel="shortcut icon" href="">
  <link rel="stylesheet" data-name="vs/editor/editor.main" href="https://cdnjs.cloudflare.com/ajax/libs/monaco-editor/0.45.0/min/vs/editor/editor.main.min.css">
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; user-select: none; transition: background-color 0.15s ease, border-color 0.15s ease; }
    body { display: flex; height: 100vh; width: 100vw; overflow: hidden; background-color: #11111b; color: #cdd6f4; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
    .brand-container { display: flex; align-items: center; gap: 7px; }
    #app-logo-img { width: 18px; height: 18px; object-fit: contain; border-radius: 3px; display: none; }
    
    /* Left: Explorer */
    #sidebar { width: 250px; min-width: 200px; height: 100%; background-color: #181825; border-right: 1px solid #313244; display: flex; flex-direction: column; position: relative; }
    .panel-header { padding: 9px 12px; font-size: 11px; font-weight: bold; letter-spacing: 0.8px; color: #89b4fa; border-bottom: 1px solid #313244; display: flex; justify-content: space-between; align-items: center; }
    #file-tree { flex: 1; overflow-y: auto; padding: 5px 0; }
    
    .tree-row { display: flex; align-items: center; padding: 4px 6px; font-size: 13px; cursor: pointer; margin: 1px 4px; border-radius: 4px; }
    .tree-row:hover { background-color: #313244; }
    .tree-row.active { background-color: #45475a; color: #ffffff; box-shadow: inset 2px 0 0 #89b4fa; }

    .folder-toggle { display: inline-block; width: 16px; font-size: 10px; color: #89b4fa; cursor: pointer; text-align: center; margin-right: 2px; }
    .folder-toggle:hover { color: #f9e2af; }
    .folder-children { display: block; }
    .folder-children.collapsed { display: none !important; }
    
    /* Center: Work Area */
    #main-area { flex: 1; display: flex; flex-direction: column; height: 100%; border-right: 1px solid #313244; overflow: hidden; }
    #toolbar { height: 40px; background-color: #181825; border-bottom: 1px solid #313244; display: flex; align-items: center; padding: 0 10px; gap: 6px; }
    .tool-btn { background-color: #313244; color: #cdd6f4; border: 1px solid #45475a; padding: 5px 12px; border-radius: 5px; font-size: 11px; cursor: pointer; font-weight: bold; }
    .tool-btn:hover { background-color: #45475a; color: #ffffff; }
    .tool-btn.run { background-color: #a6e3a1; color: #11111b; border: none; }
    .tool-btn.open { background-color: #fab387; color: #11111b; border: none; }
    .tool-btn.stop { background-color: #f38ba8; color: #11111b; border: none; display: none; }
    
    /* 1-Click GitHub Deploy Button */
    .tool-btn.deploy-btn {
      background: linear-gradient(135deg, #cba6f7, #f5c2e7); color: #11111b; border: none; margin-left: auto;
    }
    .tool-btn.deploy-btn:hover { filter: brightness(1.1); transform: translateY(-1px); }

    /* Dedicated Cloud Menu Button */
    .tool-btn.cloud-menu-btn {
      background-color: #89b4fa; color: #11111b; border: none; position: relative;
    }
    .tool-btn.cloud-menu-btn:hover { background-color: #b4befe; }

    /* Cloud Dropdown Menu */
    #cloud-dropdown {
      position: absolute; right: 340px; top: 44px; background: #1e1e2e; border: 1px solid #45475a;
      border-radius: 6px; box-shadow: 0 6px 16px rgba(0,0,0,0.6); z-index: 1000; display: none; min-width: 220px; padding: 5px 0; }
    .cloud-dropdown-item {
      padding: 8px 14px; font-size: 12px; color: #cdd6f4; cursor: pointer; display: flex; align-items: center; gap: 8px; }
    .cloud-dropdown-item:hover { background: #313244; color: #89b4fa; }
    .cloud-dropdown-item.danger:hover { background: #f38ba8; color: #11111b; }
    .cloud-divider { height: 1px; background: #313244; margin: 4px 0; }

    /* GitHub Deploy Modal */
    #deploy-modal {
      position: fixed; top: 0; left: 0; width: 100vw; height: 100vh; background: rgba(0, 0, 0, 0.65);
      backdrop-filter: blur(3px); z-index: 2000; display: none; justify-content: center; align-items: center; }
    .deploy-dialog {
      width: 440px; background: #181825; border: 1px solid #89b4fa; border-radius: 8px;
      box-shadow: 0 10px 30px rgba(0,0,0,0.7); padding: 18px 20px; display: flex; flex-direction: column; gap: 12px; }
    .deploy-dialog h3 { font-size: 15px; color: #cba6f7; display: flex; align-items: center; gap: 8px; }
    .deploy-dialog label { font-size: 11px; color: #a6adc8; font-weight: bold; }
    .deploy-input {
      width: 100%; background: #11111b; border: 1px solid #313244; color: #cdd6f4;
      padding: 8px 10px; font-size: 12px; border-radius: 4px; outline: none; }
    .deploy-input:focus { border-color: #cba6f7; }
    .deploy-dialog-footer { display: flex; justify-content: flex-end; gap: 8px; margin-top: 8px; }

    /* Multi-Tab Bar */
    #tab-bar {
      height: 35px; background-color: #11111b; border-bottom: 1px solid #313244;
      display: flex; align-items: center; overflow-x: auto; overflow-y: hidden; }
    #tab-bar::-webkit-scrollbar { height: 3px; }
    #tab-bar::-webkit-scrollbar-thumb { background: #313244; }

    .tab-item {
      display: flex; align-items: center; gap: 8px; padding: 0 12px; height: 100%;
      background-color: #181825; color: #a6adc8; border-right: 1px solid #313244;
      font-size: 12px; cursor: pointer; white-space: nowrap; user-select: none; }
    .tab-item:hover { background-color: #1e1e2e; color: #cdd6f4; }
    .tab-item.active {
      background-color: #1e1e2e; color: #89b4fa; border-top: 2px solid #89b4fa; font-weight: bold; }
    .tab-close-btn { font-size: 13px; color: #6c7086; border-radius: 50%; padding: 0 3px; }
    .tab-close-btn:hover { background-color: #45475a; color: #f38ba8; }

    /* Content Area */
    #content-viewport { flex: 1; width: 100%; position: relative; }
    #editor-container { position: absolute; top:0; left:0; width: 100%; height: 100%; }
    
    #browser-container {
      position: absolute; top:0; left:0; width: 100%; height: 100%;
      display: none; flex-direction: column; background: #fff; z-index: 10; }
    #browser-toolbar {
      height: 36px; background-color: #181825; border-bottom: 1px solid #313244;
      display: flex; align-items: center; padding: 0 8px; gap: 6px; }
    #browser-url-input {
      flex: 1; background: #11111b; border: 1px solid #313244; color: #cdd6f4;
      padding: 4px 8px; font-size: 12px; border-radius: 4px; outline: none; }
    #browser-frame { flex: 1; width: 100%; border: none; background: #ffffff; }

    /* Terminal */
    #terminal-panel { height: 210px; background-color: #11111b; border-top: 1px solid #313244; display: flex; flex-direction: column; }
    #terminal-header { padding: 5px 12px; background-color: #181825; font-size: 11px; color: #89b4fa; font-weight: bold; border-bottom: 1px solid #313244; display: flex; justify-content: space-between; align-items: center; }
    #terminal-output {
      flex: 1; padding: 8px 12px; font-family: 'Consolas', monospace; font-size: 12px;
      color: #a6adc8; overflow-y: auto; white-space: pre-wrap; line-height: 1.4; }
    .terminal-link {
      color: #89b4fa !important; text-decoration: underline !important; cursor: pointer !important; font-weight: bold; }
    .terminal-link:hover { color: #f9e2af !important; }

    #terminal-input-bar { display: flex; padding: 6px 8px; background-color: #181825; border-top: 1px solid #313244; gap: 6px; }
    #term-input { flex: 1; background: #11111b; border: 1px solid #313244; color: #a6e3a1; padding: 6px 12px; font-family: 'Consolas', monospace; font-size: 12px; border-radius: 4px; outline: none; }
    #term-input:focus { border-color: #a6e3a1; }

    /* Right: AI Copilot */
    #ai-sidebar { width: 340px; min-width: 280px; height: 100%; background-color: #181825; display: flex; flex-direction: column; }
    .ai-actions { display: flex; gap: 5px; padding: 6px; border-bottom: 1px solid #313244; }
    .ai-action-btn { flex: 1; background: #313244; color: #cdd6f4; border: 1px solid #45475a; padding: 5px; font-size: 11px; border-radius: 4px; cursor: pointer; }
    .ai-action-btn:hover { background: #45475a; color: #fff; }
    #ai-messages { flex: 1; padding: 10px; overflow-y: auto; font-family: 'Consolas', monospace; font-size: 12px; color: #cdd6f4; white-space: pre-wrap; line-height: 1.45; }
    .ai-cursor { display: inline-block; width: 6px; height: 14px; background: #89b4fa; margin-left: 2px; animation: cursorBlink 0.7s infinite alternate; vertical-align: middle; }
    @keyframes cursorBlink { 0% { opacity: 0; } 100% { opacity: 1; } }
    #ai-input-area { padding: 8px; border-top: 1px solid #313244; display: flex; gap: 6px; }
    #ai-prompt { flex: 1; background: #11111b; border: 1px solid #313244; color: #cdd6f4; padding: 6px 10px; border-radius: 4px; font-size: 12px; outline: none; }
    #ai-prompt:focus { border-color: #89b4fa; }

    .agent-report-card {
      margin-top: 8px; background: #11111b; border: 1px solid #89b4fa; border-radius: 6px; padding: 8px 10px; }
    .agent-badge {
      display: inline-block; font-size: 10px; font-weight: bold; padding: 2px 6px; border-radius: 3px; margin: 2px 0; }
    .agent-badge.create { background: #a6e3a1; color: #11111b; }
    .agent-badge.edit { background: #f9e2af; color: #11111b; }
    .agent-badge.delete { background: #f38ba8; color: #11111b; }

    /* Context Menu */
    #context-menu {
      position: fixed; display: none; background-color: #1e1e2e; border: 1px solid #45475a;
      border-radius: 6px; box-shadow: 0 4px 12px rgba(0,0,0,0.5); z-index: 1000; min-width: 150px; padding: 4px 0; }
    .ctx-item { padding: 6px 14px; font-size: 12px; color: #cdd6f4; cursor: pointer; display: flex; align-items: center; gap: 8px; }
    .ctx-item:hover { background-color: #89b4fa; color: #11111b; font-weight: bold; }
    .ctx-separator { height: 1px; background-color: #313244; margin: 4px 0; }
  </style>
</head>
<body onclick="hideAllPopups(event)">
  <!-- Left: Explorer -->
  <div id="sidebar">
    <div class="panel-header">
      <div class="brand-container"><img id="app-logo-img" alt="Logo"><span>EXPLORER</span></div>
      <div style="display:flex; gap:6px;">
        <span style="cursor:pointer;" title="New File" onclick="promptNewFileRoot()">+📄</span>
        <span style="cursor:pointer;" title="New Folder" onclick="promptNewFolderRoot()">+📁</span>
        <span style="cursor:pointer;" title="Refresh" onclick="loadWorkspace()">⟳</span>
      </div>
    </div>
    <div id="file-tree" oncontextmenu="handleEmptyAreaContextMenu(event)">Loading workspace...</div>
  </div>

  <!-- Center: Main Workspace -->
  <div id="main-area">
    <div id="toolbar">
      <button class="tool-btn open" onclick="triggerOpenFile()">📂 Open</button>
      <button class="tool-btn run" id="run-btn" onclick="runActiveFile()">▶ Run</button>
      <button class="tool-btn stop" id="stop-btn" onclick="stopActiveFile()">⏹ Stop</button>
      <button class="tool-btn" onclick="saveActiveFile()">Save</button>
      
      <!-- 1-Click Zero-Config GitHub Deploy Button -->
      <button class="tool-btn deploy-btn" onclick="openDeployModal()">🚀 Deploy to GitHub</button>

      <!-- Dedicated Cloud Menu Button -->
      <button class="tool-btn cloud-menu-btn" onclick="toggleCloudMenu(event)">☁ Cloud ▾</button>
    </div>

    <!-- Multi-File Tabs Bar -->
    <div id="tab-bar"></div>

    <!-- Content Viewport -->
    <div id="content-viewport">
      <div id="editor-container"></div>

      <!-- In-built Browser View -->
      <div id="browser-container">
        <div id="browser-toolbar">
          <button class="tool-btn" onclick="reloadBrowserFrame()">⟳</button>
          <input type="text" id="browser-url-input" placeholder="http://localhost:5000" onkeydown="if(event.key==='Enter') navigateBrowser(this.value)">
          <button class="tool-btn" onclick="navigateBrowser(document.getElementById('browser-url-input').value)">Go</button>
          <button class="tool-btn flush" onclick="closeBrowserView()">✕ Close Browser</button>
        </div>
        <iframe id="browser-frame" src="about:blank"></iframe>
      </div>
    </div>

    <!-- Terminal -->
    <div id="terminal-panel">
      <div id="terminal-header">
        <span>TERMINAL & DIRECT WINDOWS CMD</span>
        <span style="cursor:pointer; color:#a6adc8;" onclick="clearTerminal()">Clear</span>
      </div>
      <div id="terminal-output">CodeNexus Ready. Type command, run a file, or deploy to GitHub with 1-click.</div>
      <div id="terminal-input-bar">
        <input type="text" id="term-input" placeholder="Type Windows Command or Script Stdin..." onkeydown="if(event.key==='Enter') submitTerminalInput()">
        <button class="tool-btn" onclick="submitTerminalInput()">Send to CMD</button>
      </div>
    </div>
  </div>

  <!-- Right: AI Copilot -->
  <div id="ai-sidebar">
    <div class="panel-header">
      <span>🤖 AI COPILOT & AGENT</span>
      <div style="display:flex; gap: 8px;">
        <span style="cursor:pointer;" onclick="configureAPIKey()">⚙ Key</span>
        <span style="cursor:pointer;" onclick="clearAIChat()">⟲ Clear</span>
      </div>
    </div>
    <div class="ai-actions">
      <button class="ai-action-btn" onclick="triggerAI('Fix bugs and rewrite this code cleanly.')">Fix Code</button>
      <button class="ai-action-btn" onclick="triggerAI('Refactor this file and create unit tests in tests/test_core.py')">Tests & Refactor</button>
      <button class="ai-action-btn" onclick="triggerAI('Explain this project structure and file connections.')">Analyze</button>
    </div>
    <div id="ai-messages">Ready for prompts. (AI can create, write, edit, delete, and fix multiple files on your workspace)</div>
    <div style="padding: 4px 8px; background: #11111b; border-top: 1px solid #313244;">
      <button id="insert-code-btn" class="tool-btn" style="width: 100%; display: none;" onclick="insertExtractedCode()">⎘ Insert Code to Editor</button>
    </div>
    <div id="ai-input-area">
      <input type="text" id="ai-prompt" placeholder="Ask AI to write, edit, fix, or delete files..." onkeydown="if(event.key==='Enter') submitCustomAI()">
      <button class="tool-btn" onclick="submitCustomAI()">Send</button>
    </div>
  </div>

  <!-- GitHub Deploy Modal Dialog -->
  <div id="deploy-modal" onclick="closeDeployModal(event)">
    <div class="deploy-dialog" onclick="event.stopPropagation()">
      <h3>🚀 Deploy Workspace to GitHub</h3>
      
      <div>
        <label>GIVE THE REPOSITORY LINK HERE:</label>
        <input type="text" id="deploy-repo-url" class="deploy-input" placeholder="https://github.com/YourUsername/your-repo.git">
      </div>

      <div>
        <label>WRITE YOUR COMMIT HERE:</label>
        <input type="text" id="deploy-commit-msg" class="deploy-input" placeholder="e.g. Initial commit from CodeNexus IDE">
      </div>

      <div class="deploy-dialog-footer">
        <button class="tool-btn" onclick="closeDeployModal()">Cancel</button>
        <button class="tool-btn deploy-btn" id="confirm-deploy-btn" onclick="submitGitHubDeploy()">Deploy Now ⚡</button>
      </div>
    </div>
  </div>

  <!-- Cloud Dropdown Menu -->
  <div id="cloud-dropdown">
    <div class="cloud-dropdown-item" onclick="uploadCloud()">⬆ Upload Active File to Cloud</div>
    <div class="cloud-dropdown-item" onclick="downloadCloud()">⬇ Fetch File from Cloud</div>
    <div class="cloud-divider"></div>
    <div class="cloud-dropdown-item danger" onclick="flushCloud()">🗑 Delete Everything from Cloud</div>
  </div>

  <!-- Context Menu -->
  <div id="context-menu">
    <div class="ctx-item" onclick="onContextNewFile()">📄 New File...</div>
    <div class="ctx-item" onclick="onContextNewFolder()">📁 New Folder...</div>
    <div class="ctx-separator"></div>
    <div class="ctx-item" onclick="onContextRename()">✏ Rename (F2)</div>
    <div class="ctx-item" onclick="onContextDelete()">🗑 Delete</div>
    <div class="ctx-separator"></div>
    <div class="ctx-item" onclick="loadWorkspace()">⟳ Refresh</div>
  </div>

  <!-- Monaco AMD Loader -->
  <script src="https://cdnjs.cloudflare.com/ajax/libs/monaco-editor/0.45.0/min/vs/loader.min.js"></script>
  <script>
    let editor = null;
    let activeFilePath = "";
    let activeLanguage = "python";
    let currentAIResponse = "";
    let contextTarget = { path: "", type: "folder" };
    let openTabs = new Map();
    let isBrowserTabActive = false;
    let liveStreamTarget = null;
    let liveCursor = null;

    function initMonaco() {
      try {
        require.config({ paths: { 'vs': 'https://cdnjs.cloudflare.com/ajax/libs/monaco-editor/0.45.0/min/vs' } });
        require(['vs/editor/editor.main'], function () {
          editor = monaco.editor.create(document.getElementById('editor-container'), {
            value: '# Welcome to CodeNexus AI IDE\nprint("CodeNexus Production Engine Ready")\n',
            language: 'python',
            theme: 'vs-dark',
            automaticLayout: true,
            fontSize: 14
          });

          editor.onDidChangeModelContent(() => {
            if (activeFilePath && openTabs.has(activeFilePath)) {
              openTabs.get(activeFilePath).content = editor.getValue();
            }
          });

          if (window.pywebview && window.pywebview.api) {
            startApp();
          } else {
            window.addEventListener('pywebviewready', startApp);
          }
        });
      } catch(err) {
        console.error("Monaco Load Error:", err);
      }
    }

    function startApp() {
      loadAppLogo();
      loadWorkspace();
    }

    window.addEventListener('DOMContentLoaded', initMonaco);

    window.addEventListener('keydown', function (e) {
      if (e.key === 'F2') {
        if (contextTarget && contextTarget.path) {
          onContextRename();
        } else if (activeFilePath) {
          contextTarget = { path: activeFilePath, type: 'file' };
          onContextRename();
        }
      }
    });

    function loadAppLogo() {
      if (!window.pywebview || !window.pywebview.api) return;
      window.pywebview.api.get_app_logo().then(dataUri => {
        if (dataUri) {
          const logoEl = document.getElementById('app-logo-img');
          if (logoEl) { logoEl.src = dataUri; logoEl.style.display = 'inline-block'; }
          const fav = document.getElementById('dynamic-favicon');
          if (fav) fav.href = dataUri;
        }
      });
    }

    // --- Tab Management System ---
    function renderTabs() {
      const tabBar = document.getElementById('tab-bar');
      tabBar.innerHTML = '';

      openTabs.forEach((tabData, path) => {
        const tabEl = document.createElement('div');
        tabEl.className = 'tab-item' + (activeFilePath === path && !isBrowserTabActive ? ' active' : '');
        
        const label = document.createElement('span');
        label.innerText = '📄 ' + tabData.filename;
        
        const closeBtn = document.createElement('span');
        closeBtn.className = 'tab-close-btn';
        closeBtn.innerText = '×';
        closeBtn.onclick = (e) => closeTab(e, path);

        tabEl.appendChild(label);
        tabEl.appendChild(closeBtn);
        tabEl.onclick = () => switchToFileTab(path);
        tabBar.appendChild(tabEl);
      });

      if (document.getElementById('browser-container').style.display === 'flex') {
        const browserTabEl = document.createElement('div');
        browserTabEl.className = 'tab-item' + (isBrowserTabActive ? ' active' : '');
        browserTabEl.innerHTML = `<span>🌐 Browser</span>`;
        const closeBtn = document.createElement('span');
        closeBtn.className = 'tab-close-btn';
        closeBtn.innerText = '×';
        closeBtn.onclick = (e) => closeBrowserView(e);
        browserTabEl.appendChild(closeBtn);
        browserTabEl.onclick = () => switchToBrowserTab();
        tabBar.appendChild(browserTabEl);
      }
    }

    function switchToFileTab(path) {
      if (!openTabs.has(path)) return;
      isBrowserTabActive = false;
      document.getElementById('browser-container').style.display = 'none';
      document.getElementById('editor-container').style.display = 'block';

      activeFilePath = path;
      const tabData = openTabs.get(path);
      activeLanguage = tabData.language;

      if (!tabData.model) {
        tabData.model = monaco.editor.createModel(tabData.content, tabData.language);
      }
      editor.setModel(tabData.model);
      renderTabs();
    }

    function closeTab(e, path) {
      if (e) e.stopPropagation();
      if (!openTabs.has(path)) return;

      const tabData = openTabs.get(path);
      if (tabData.model) tabData.model.dispose();
      openTabs.delete(path);

      if (activeFilePath === path) {
        if (openTabs.size > 0) {
          const nextPath = openTabs.keys().next().value;
          switchToFileTab(nextPath);
        } else {
          activeFilePath = "";
          editor.setValue("");
          renderTabs();
        }
      } else {
        renderTabs();
      }
    }

    // --- In-App Browser Tab Integration ---
    function openInBrowserTab(url, title) {
      isBrowserTabActive = true;
      const browserContainer = document.getElementById('browser-container');
      const editorContainer = document.getElementById('editor-container');
      const urlInput = document.getElementById('browser-url-input');
      const frame = document.getElementById('browser-frame');

      editorContainer.style.display = 'none';
      browserContainer.style.display = 'flex';

      urlInput.value = url;
      frame.src = url;
      renderTabs();
    }

    function switchToBrowserTab() {
      isBrowserTabActive = true;
      document.getElementById('editor-container').style.display = 'none';
      document.getElementById('browser-container').style.display = 'flex';
      renderTabs();
    }

    function closeBrowserView(e) {
      if (e) e.stopPropagation();
      isBrowserTabActive = false;
      document.getElementById('browser-container').style.display = 'none';
      document.getElementById('editor-container').style.display = 'block';
      document.getElementById('browser-frame').src = 'about:blank';

      if (activeFilePath && openTabs.has(activeFilePath)) {
        switchToFileTab(activeFilePath);
      } else {
        renderTabs();
      }
    }

    function navigateBrowser(url) {
      if (!url.startsWith('http://') && !url.startsWith('https://') && !url.startsWith('file:///')) {
        url = 'http://' + url;
      }
      document.getElementById('browser-url-input').value = url;
      document.getElementById('browser-frame').src = url;
    }

    function reloadBrowserFrame() {
      const frame = document.getElementById('browser-frame');
      frame.src = frame.src;
    }

    // --- Open File Dialog ---
    function triggerOpenFile() {
      if (!window.pywebview || !window.pywebview.api) return;
      window.pywebview.api.open_file_dialog().then(res => {
        if (res && res.success) {
          addFileToTabsAndOpen(res.path, res.filename, res.content, res.language);
          appendTerminal("Opened file: " + res.path);
          if (res.workspace_changed) {
            loadWorkspace();
          }
        } else if (res && res.error) {
          alert(res.error);
        }
      });
    }

    function addFileToTabsAndOpen(path, filename, content, language) {
      if (!openTabs.has(path)) {
        const model = monaco.editor.createModel(content, language);
        openTabs.set(path, { filename, content, language, model });
      } else {
        openTabs.get(path).content = content;
        if (openTabs.get(path).model) {
          openTabs.get(path).model.setValue(content);
        }
      }
      switchToFileTab(path);
    }

    function openFile(path) {
      if (openTabs.has(path)) {
        switchToFileTab(path);
        return;
      }
      window.pywebview.api.open_file(path).then(res => {
        if (res.error) { alert(res.error); return; }
        addFileToTabsAndOpen(res.path, res.filename, res.content, res.language);
      });
    }

    function saveActiveFile() {
      if (!activeFilePath) return;
      const code = editor.getValue();
      window.pywebview.api.save_file(activeFilePath, code).then(res => {
        appendTerminal(res.message || res.error);
      });
    }

    // --- Explorer Tree Methods ---
    function loadWorkspace() {
      if (!window.pywebview || !window.pywebview.api) return;
      window.pywebview.api.get_workspace_tree().then(tree => {
        const root = document.getElementById('file-tree');
        root.innerHTML = '';
        renderTree(tree, root, 0);
      }).catch(err => {
        document.getElementById('file-tree').innerText = "Failed loading explorer: " + err;
      });
    }

    function renderTree(node, container, depth) {
      if (!node.children) return;

      node.children.forEach(child => {
        if (child.type === 'folder') {
          const folderRow = document.createElement('div');
          folderRow.className = 'tree-row';
          folderRow.style.paddingLeft = (depth * 14 + 6) + 'px';

          const arrow = document.createElement('span');
          arrow.className = 'folder-toggle';
          arrow.innerHTML = '▶';

          const label = document.createElement('span');
          label.innerHTML = '📁 ' + child.name;

          folderRow.appendChild(arrow);
          folderRow.appendChild(label);

          const childrenContainer = document.createElement('div');
          childrenContainer.className = 'folder-children collapsed';
          childrenContainer.setAttribute('data-loaded', 'false');

          const toggleFolder = (e) => {
            if (e) e.stopPropagation();
            if (childrenContainer.classList.contains('collapsed')) {
              if (childrenContainer.getAttribute('data-loaded') === 'false') {
                window.pywebview.api.get_folder_children(child.path).then(items => {
                  childrenContainer.innerHTML = '';
                  renderTree({ children: items }, childrenContainer, depth + 1);
                  childrenContainer.setAttribute('data-loaded', 'true');
                  childrenContainer.classList.remove('collapsed');
                  arrow.innerHTML = '▼';
                });
              } else {
                childrenContainer.classList.remove('collapsed');
                arrow.innerHTML = '▼';
              }
            } else {
              childrenContainer.classList.add('collapsed');
              arrow.innerHTML = '▶';
            }
          };

          arrow.onclick = toggleFolder;
          folderRow.onclick = (e) => {
            highlightTreeItem(folderRow, child.path, 'folder');
            toggleFolder(e);
          };

          folderRow.oncontextmenu = (e) => {
            highlightTreeItem(folderRow, child.path, 'folder');
            showContextMenu(e, child.path, 'folder');
          };

          container.appendChild(folderRow);
          container.appendChild(childrenContainer);

        } else {
          const fileRow = document.createElement('div');
          fileRow.className = 'tree-row';
          fileRow.style.paddingLeft = (depth * 14 + 22) + 'px';
          fileRow.innerHTML = '📄 ' + child.name;

          fileRow.onclick = () => {
            highlightTreeItem(fileRow, child.path, 'file');
            openFile(child.path);
          };

          fileRow.oncontextmenu = (e) => {
            highlightTreeItem(fileRow, child.path, 'file');
            showContextMenu(e, child.path, 'file');
          };

          container.appendChild(fileRow);
        }
      });
    }

    function highlightTreeItem(el, path, type) {
      document.querySelectorAll('.tree-row').forEach(i => i.classList.remove('active'));
      el.classList.add('active');
      contextTarget = { path: path, type: type };
    }

    function showContextMenu(e, path, type) {
      e.preventDefault();
      e.stopPropagation();
      contextTarget = { path: path, type: type };
      const menu = document.getElementById('context-menu');
      menu.style.display = 'block';
      menu.style.left = e.clientX + 'px';
      menu.style.top = e.clientY + 'px';
    }

    function handleEmptyAreaContextMenu(e) {
      e.preventDefault();
      contextTarget = { path: "", type: "folder" };
      const menu = document.getElementById('context-menu');
      menu.style.display = 'block';
      menu.style.left = e.clientX + 'px';
      menu.style.top = e.clientY + 'px';
    }

    // --- Dedicated Cloud Menu Toggle ---
    function toggleCloudMenu(e) {
      e.stopPropagation();
      const drop = document.getElementById('cloud-dropdown');
      drop.style.display = (drop.style.display === 'block') ? 'none' : 'block';
    }

    function hideAllPopups(e) {
      document.getElementById('context-menu').style.display = 'none';
      document.getElementById('cloud-dropdown').style.display = 'none';
    }

    // --- 1-Click GitHub Deploy Modal Handlers ---
    function openDeployModal() {
      document.getElementById('deploy-modal').style.display = 'flex';
      document.getElementById('deploy-repo-url').focus();
    }

    function closeDeployModal(e) {
      document.getElementById('deploy-modal').style.display = 'none';
    }

    function submitGitHubDeploy() {
      const repoUrl = document.getElementById('deploy-repo-url').value.trim();
      const commitMsg = document.getElementById('deploy-commit-msg').value.trim();

      if (!repoUrl) {
        alert("Please provide the repository link!");
        return;
      }

      const btn = document.getElementById('confirm-deploy-btn');
      btn.innerText = "Deploying... ⏳";
      btn.disabled = true;

      window.pywebview.api.deploy_to_github(repoUrl, commitMsg).then(res => {
        closeDeployModal();
        btn.innerText = "Deploy Now ⚡";
        btn.disabled = false;
        appendTerminal("\n[GitHub Deployer]: " + res.message);
      });
    }

    function onDeployComplete(success, message) {
      if (success) {
        alert("🚀 Project successfully pushed and deployed to GitHub!");
      } else {
        alert("⚠️ GitHub Push Notice: " + message);
      }
    }

    function onContextNewFile() {
      const targetDir = (contextTarget.type === 'file') ? contextTarget.path.substring(0, contextTarget.path.lastIndexOf(/[\\\/]/)) : contextTarget.path;
      const fname = prompt("Enter new file name (e.g. script.py, index.html):");
      if (!fname) return;

      window.pywebview.api.create_new_file(targetDir, fname).then(res => {
        if (res.success) {
          loadWorkspace();
          openFile(res.path);
        } else {
          alert(res.message);
        }
      });
    }

    function onContextNewFolder() {
      const targetDir = (contextTarget.type === 'file') ? contextTarget.path.substring(0, contextTarget.path.lastIndexOf(/[\\\/]/)) : contextTarget.path;
      const folderName = prompt("Enter new folder name:");
      if (!folderName) return;

      window.pywebview.api.create_new_folder(targetDir, folderName).then(res => {
        if (res.success) {
          loadWorkspace();
        } else {
          alert(res.message);
        }
      });
    }

    function onContextRename() {
      if (!contextTarget.path) return;
      const oldName = contextTarget.path.split(/[\\\/]/).pop();
      const newName = prompt("Rename to:", oldName);
      if (!newName || newName.trim() === "" || newName.trim() === oldName) return;

      window.pywebview.api.rename_item(contextTarget.path, newName.trim()).then(res => {
        if (res.success) {
          if (openTabs.has(res.old_path)) {
            const data = openTabs.get(res.old_path);
            data.filename = res.new_name;
            openTabs.delete(res.old_path);
            openTabs.set(res.new_path, data);
            if (activeFilePath === res.old_path) activeFilePath = res.new_path;
            renderTabs();
          }
          loadWorkspace();
          appendTerminal("Renamed: " + oldName + " -> " + res.new_name);
        } else {
          alert(res.message);
        }
      });
    }

    function onContextDelete() {
      if (!contextTarget.path) return;
      const itemName = contextTarget.path.split(/[\\\/]/).pop();
      if (confirm("Are you sure you want to permanently delete '" + itemName + "'?")) {
        window.pywebview.api.delete_item(contextTarget.path).then(res => {
          if (res.success) {
            if (openTabs.has(contextTarget.path)) {
              closeTab(null, contextTarget.path);
            }
            loadWorkspace();
          } else {
            alert(res.message);
          }
        });
      }
    }

    function promptNewFileRoot() {
      contextTarget = { path: "", type: "folder" };
      onContextNewFile();
    }

    function promptNewFolderRoot() {
      contextTarget = { path: "", type: "folder" };
      onContextNewFolder();
    }

    // --- Subprocess Execution & Direct CMD ---
    function runActiveFile() {
      appendTerminal("\nStarting: " + (activeFilePath || "Buffer") + "...");
      document.getElementById('stop-btn').style.display = 'inline-block';
      window.pywebview.api.run_file(activeFilePath, editor.getValue()).then(res => {
        if (res.output) appendTerminal(res.output);
      });
    }

    function stopActiveFile() {
      window.pywebview.api.stop_active_process().then(res => {
        appendTerminal("\n[User Interrupted Process]");
        document.getElementById('stop-btn').style.display = 'none';
      });
    }

    function submitTerminalInput() {
      const input = document.getElementById('term-input');
      const val = input.value;
      if (!val || val.trim() === "") return;
      input.value = "";
      
      appendTerminal(">> " + val);

      window.pywebview.api.send_terminal_input(val).then(res => {
        if (res && res.message) {
          appendTerminal(res.message);
        }
      });
    }

    function formatTerminalLinks(text) {
      const urlRegex = /(https?:\/\/[^\s]+|localhost:[0-9]+|127\.0\.0\.1:[0-9]+)/gi;
      return text.replace(urlRegex, function(url) {
        let fullUrl = url;
        if (!fullUrl.startsWith('http://') && !fullUrl.startsWith('https://')) {
          fullUrl = 'http://' + fullUrl;
        }
        return `<span class="terminal-link" onclick="openInBrowserTab('${fullUrl}')">${url}</span>`;
      });
    }

    function appendTerminalChunk(chunk) {
      const term = document.getElementById('terminal-output');
      const span = document.createElement('span');
      span.innerHTML = formatTerminalLinks(chunk);
      term.appendChild(span);
      term.scrollTop = term.scrollHeight;
    }

    function onProcessFinished(statusMessage) {
      appendTerminal(statusMessage);
      document.getElementById('stop-btn').style.display = 'none';
    }

    function clearTerminal() {
      document.getElementById('terminal-output').innerText = "";
    }

    function appendTerminal(text) {
      const term = document.getElementById('terminal-output');
      const div = document.createElement('div');
      div.innerHTML = formatTerminalLinks(text);
      term.appendChild(div);
      term.scrollTop = term.scrollHeight;
    }

    // --- Silent Local Cloud Functions ---
    function uploadCloud() {
      const code = editor.getValue();
      const fname = prompt("Save file to Cloud Storage as:", activeFilePath.split(/[\\\/]/).pop() || "code.py");
      if (!fname) return;
      window.pywebview.api.cloud_upload(fname, code).then(res => {
        appendTerminal("[Cloud]: " + res.message);
        alert(res.message);
      });
    }

    function downloadCloud() {
      const fname = prompt("Fetch file from Cloud Storage (filename):");
      if (!fname) return;
      window.pywebview.api.cloud_download(fname).then(res => {
        if (res.success) {
          addFileToTabsAndOpen(fname, res.filename, res.content, "python");
          appendTerminal("[Cloud]: Successfully loaded " + res.filename);
        } else {
          alert(res.message);
        }
      });
    }

    function flushCloud() {
      if (confirm("Are you sure you want to delete everything from Cloud Storage?")) {
        window.pywebview.api.cloud_flush().then(res => {
          appendTerminal("[Cloud Purge]: " + res.message);
          alert(res.message);
        });
      }
    }

    // --- AI Copilot (Clean Token Stream & Agent Operations) ---
    function configureAPIKey() {
      const key = prompt("Enter OpenRouter Key (sk-or-v1-...):");
      if (key) window.pywebview.api.save_ai_key(key).then(r => alert(r.message));
    }

    function triggerAI(p) {
      let sel = "";
      if (editor) {
        sel = editor.getModel().getValueInRange(editor.getSelection()) || editor.getValue();
      }

      const aiBox = document.getElementById('ai-messages');
      const block = document.createElement('div');
      block.style.marginTop = "10px";
      block.style.paddingTop = "8px";
      block.style.borderTop = "1px solid #313244";

      const titleEl = document.createElement('div');
      titleEl.style.color = "#89b4fa";
      titleEl.style.fontWeight = "bold";
      titleEl.innerText = "▶ " + p;

      const responseEl = document.createElement('div');
      responseEl.style.marginTop = "4px";
      responseEl.innerHTML = "<span style='color:#a6e3a1;'>⚡ Copilot: </span>";

      liveStreamTarget = document.createElement('span');
      liveStreamTarget.style.whiteSpace = "pre-wrap";
      
      liveCursor = document.createElement('span');
      liveCursor.className = "ai-cursor";

      responseEl.appendChild(liveStreamTarget);
      responseEl.appendChild(liveCursor);

      block.appendChild(titleEl);
      block.appendChild(responseEl);
      aiBox.appendChild(block);

      currentAIResponse = "";
      document.getElementById('insert-code-btn').style.display = 'none';

      window.pywebview.api.ask_ai_stream(p, sel);
    }

    function submitCustomAI() {
      const val = document.getElementById('ai-prompt').value.trim();
      if (!val) return;
      document.getElementById('ai-prompt').value = "";
      triggerAI(val);
    }

    function onAIStreamStart() {
      const aiBox = document.getElementById('ai-messages');
      aiBox.scrollTop = aiBox.scrollHeight;
    }

    function onAIChunkReceived(token) {
      if (typeof token !== "string" || !token) return;
      currentAIResponse += token;
      
      if (liveStreamTarget) {
        if (!currentAIResponse.includes("```codenexus-agent")) {
          liveStreamTarget.textContent = currentAIResponse;
        } else {
          const cleanPart = currentAIResponse.split("```codenexus-agent")[0];
          liveStreamTarget.textContent = cleanPart.trim();
        }
      }
      const aiBox = document.getElementById('ai-messages');
      aiBox.scrollTop = aiBox.scrollHeight;
    }

    function onAIStreamFinished() {
      if (liveCursor) {
        liveCursor.remove();
        liveCursor = null;
      }

      if (currentAIResponse.includes("```codenexus-agent")) {
        try {
          const match = currentAIResponse.match(/```codenexus-agent([\s\S]*?)```/);
          if (match && match[1]) {
            const rawJson = match[1].trim();
            window.pywebview.api.execute_ai_agent_ops(rawJson).then(res => {
              if (res && res.success) {
                renderAgentReport(res.results, res.synced_files);
                loadWorkspace();
              }
            });
          }
        } catch(e) {
          console.error("Agent execution error:", e);
        }
      }

      if (currentAIResponse.includes("```") && !currentAIResponse.includes("```codenexus-agent")) {
        document.getElementById('insert-code-btn').style.display = 'block';
      }

      const aiBox = document.getElementById('ai-messages');
      aiBox.scrollTop = aiBox.scrollHeight;
    }

    function renderAgentReport(results, syncedFiles) {
      const aiBox = document.getElementById('ai-messages');
      const card = document.createElement('div');
      card.className = "agent-report-card";
      
      let html = "<b style='color:#a6e3a1;'>⚡ CodeNexus Agent Changes Executed:</b><br>";
      results.forEach(r => {
        let badgeClass = "edit";
        if (r.action.includes("create")) badgeClass = "create";
        if (r.action.includes("delete")) badgeClass = "delete";
        
        let status = r.success ? "✓" : `✗ (${r.error})`;
        html += `<span class='agent-badge ${badgeClass}'>${r.action.toUpperCase()}</span> <span style='font-size:11px;'>${r.path} - ${status}</span><br>`;
      });
      card.innerHTML = html;
      aiBox.appendChild(card);

      if (syncedFiles && syncedFiles.length > 0) {
        syncedFiles.forEach(file => {
          addFileToTabsAndOpen(file.path, file.filename, file.content, "python");
        });
      }
    }

    function onAIError(err) {
      if (liveCursor) {
        liveCursor.remove();
        liveCursor = null;
      }
      const aiBox = document.getElementById('ai-messages');
      const errBox = document.createElement('div');
      errBox.style.color = "#f38ba8";
      errBox.style.marginTop = "4px";
      errBox.innerText = "[Error]: " + err;
      aiBox.appendChild(errBox);
      aiBox.scrollTop = aiBox.scrollHeight;
    }

    function insertExtractedCode() {
      if (!editor || !currentAIResponse.includes("```")) return;
      const parts = currentAIResponse.split("```");
      if (parts.length >= 3) {
        let snippet = parts[1];
        const firstNewline = snippet.indexOf("\n");
        if (firstNewline !== -1) {
          snippet = snippet.substring(firstNewline + 1);
        }

        const selection = editor.getSelection();
        const op = {
          range: selection,
          text: snippet,
          forceMoveMarkers: true
        };
        editor.executeEdits("codenexus-copilot", [op]);
        editor.focus();
      }
    }

    function clearAIChat() {
      document.getElementById('ai-messages').innerText = "Chat cleared. Ready.";
      document.getElementById('insert-code-btn').style.display = 'none';
      currentAIResponse = "";
      liveStreamTarget = null;
      liveCursor = null;
    }
  </script>
</body>
</html>
"""


def set_windows_taskbar_icon(icon_path):
    if sys.platform == "win32" and icon_path and os.path.exists(icon_path):
        try:
            import ctypes
            myappid = "parastech.codenexus.ide.1.0"
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
        except Exception:
            pass


def main():
    if APP_ICON_PATH:
        set_windows_taskbar_icon(APP_ICON_PATH)

    splash_w = 540
    splash_h = 350
    screen_x = 0
    screen_y = 0

    try:
        screens = webview.screens
        if screens and len(screens) > 0:
            primary = screens[0]
            screen_x = int((primary.width - splash_w) / 2)
            screen_y = int((primary.height - splash_h) / 2)
    except Exception:
        pass

    # 1. 5-Second Centered Splash Screen
    splash_window = webview.create_window(
        title="Initializing CodeNexus IDE",
        html=SPLASH_HTML,
        width=splash_w,
        height=splash_h,
        x=screen_x if screen_x > 0 else None,
        y=screen_y if screen_y > 0 else None,
        frameless=True,
        easy_drag=True,
        on_top=True,
        background_color="#11111b"
    )

    def _splash_timer():
        time.sleep(5.0)

        api = CodeNexusAPI()
        main_window = webview.create_window(
            title="CodeNexus AI IDE",
            html=HTML_SHELL,
            js_api=api,
            width=1380,
            height=850,
            background_color="#11111b"
        )
        api.set_window(main_window)
        splash_window.destroy()

    threading.Thread(target=_splash_timer, daemon=True).start()
    webview.start(debug=False)


if __name__ == "__main__":
    main()
