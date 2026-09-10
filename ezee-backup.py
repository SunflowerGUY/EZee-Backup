import base64
import io
import json
import os
import queue
import subprocess
import sys
import tempfile
import threading
from pathlib import Path

import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
from tkinter import ttk

from PIL import Image, ImageDraw, ImageTk

try:
    import winsound
except ImportError:
    winsound = None

VERSION = "2.5"
APP_NAME = "EZee-Backup"

SPLASH_B64 = (
    """/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAAgGBgcGBQgHBwcJCQgKDBQNDAsLDBkSEw8UHRofHh0aHBwgJC4nICIsIxwcKDcpLDAxNDQ0Hyc5PTgyPC4zNDL/wAALCACTAZEDAREA/8QAHwAAAQUBAQEBAQEAAAAAAAAAAAECAwQFBgcICQoL/8QAtRAAAgEDAwIEAwUFBAQAAAF9AQIDAAQRBRIhMUEGE1FhByJxFDKBkaEII0KxwRVS0fAkM2JyggkKFhcYGRolJicoKSo0NTY3ODk6Q0RFRkdISUpTVFVWV1hZWmNkZWZnaGlqc3R1dnd4eXqDhIWGh4iJipKTlJWWl5iZmqKjpKWmp6ipqrKztLW2t7i5usLDxMXGx8jJytLT1NXW19jZ2uHi4+Tl5ufo6erx8vP09fb3+Pn6/8QAHwEAAwEBAQEBAQEBAQAAAAAAAAECAwQFBgcICQoL/8QAtREAAgECBAQDBAcFBAQAAQJ3AAECAxEEBSExBhJBUQdhcRMiMoEIFEKRobHBCSMzUvAVYnLRChYkNOEl8RcYGRomJygpKjU2Nzg5OkNERUZHSElKU1RVVldYWVpjZGVmZ2hpanN0dXZ3eHl6goOEhYaHiImKkpOUlZaXmJmaoqOkpaanqKmqsrO0tba3uLm6wsPExcbHyMnK0tPU1dbX2Nna4uPk5ebn6Onq8vP09fb3+Pn6/9oADAMBAAIRAxEAPwD5ZoooruOcKK7zT/B2g6Vpy3fjXVrq2u5Vymk2KqbpAdpUyFshDtYnYwBxjnIK1L/avgL/AKJ5/wCVmf8Awrp+rcvxyUX2d7/gnb5nD9eUv4UJSXdWS+Tk1f1V0efUV6D/AGr4C/6J5/5WZ/8ACj+1fAX/AETz/wArM/8AhR7CH/Pxf+Tf/Ih9bq/8+ZffD/5M8+or0H+1fAX/AETz/wArM/8AhR/avgL/AKJ5/wCVmf8Awo9hD/n4v/Jv/kQ+t1f+fMvvh/8AJnn1Feg/2r4C/wCief8AlZn/AMKP7V8Bf9E8/wDKzP8A4Uewh/z8X/k3/wAiH1ur/wA+ZffD/wCTPPqK9B/tXwF/0Tz/AMrM/wDhR/avgL/onn/lZn/wo9hD/n4v/Jv/AJEPrdX/AJ8y++H/AMmefUV6D/avgL/onn/lZn/wo/tXwF/0Tz/ysz/4Uewh/wA/F/5N/wDIh9bq/wDPmX3w/wDkzz6ivQf7V8Bf9E8/8rM/+FH9q+Av+ief+Vmf/Cj2EP8An4v/ACb/AORD63V/58y++H/yZ59RXoP9q+Av+ief+Vmf/Cj+1fAX/RPP/KzP/hR7CH/Pxf8Ak3/yIfW6v/PmX3w/+TPPqK9B/tXwF/0Tz/ysz/4Uf2r4C/6J5/5WZ/8ACj2EP+fi/wDJv/kQ+t1f+fMvvh/8mefUV6D/AGr4C/6J5/5WZ/8ACj+1fAX/AETz/wArM/8AhR7CH/Pxf+Tf/Ih9bq/8+ZffD/5M8+or0H+1fAX/AETz/wArM/8AhR/avgL/AKJ5/wCVmf8Awo9hD/n4v/Jv/kQ+t1f+fMvvh/8AJnn1Feg/2r4C/wCief8AlZn/AMKP7V8Bf9E8/wDKzP8A4Uewh/z8X/k3/wAiH1ur/wA+ZffD/wCTPPqK9B/tXwF/0Tz/AMrM/wDhR/avgL/onn/lZn/wo9hD/n4v/Jv/kQ+t1f+fMvvh/8AJnn1Feg/2r4C/wCief8AlZn/AMKP7V8Bf9E8/wDKzP8A4Uewh/z8X/k3/wAiH1ur/wA+ZffD/wCTPPqK9B/tXwF/0Tz/AMrM/wDhR/avgL/onn/lZn/wo/tXwF/0Tz/ysz/4Uewh/wA/F/5N/wDIh9bq/wDPmX3w/wDkzz6ivQf7V8Bf9E8/8rM/+FH9q+Av+ief+Vmf/Cj2EP8An4v/ACb/AORD63V/58y++H/yZ59RXoP9q+Av+ief+Vmf/Cj+1fAX/RPP/KzP/hR7CH/Pxf8Ak3/yIfW6v/PmX3w/+TPPqK9B/tXwF/0Tz/ysz/4Uf2r4C/6J5/5WZ/8ACj2EP+fi/wDJv/kQ+t1f+fMvvh/8mefUV6D/AGr4C/6J5/5WZ/8ACj+1fAX/AETz/wArM/8AhR7CH/Pxf+Tf/Ih9bq/8+ZffD/5M8+or0H+1fAX/AETz/wArM/8AhR/avgL/AKJ5/wCVmf8Awo9hD/n4v/Jv/kQ+t1f+fMvvh/8AJnn1Feg/2r4C/wCief8AlZn/AMKP7V8Bf9E8/wDKzP8A4Uewh/z8X/k3/wAiH1ur/wA+ZffD/wCTPPqK9B/tXwF/0Tz/AMrM/wDhRJ4X8KeIbV38L6lPp2rHLLpeoOpSViVxHFLwOpKruyzYGdoyaaw3N8E0321X5pA8dya1acoru7NfPlbt6vQ8+op9xDLbzyQTxPFNGxSSN1KsjA4IIPIIPamVzHcncK7z4fWdlpXhfUfGt2iTXcE4s9JQ8hLkruMpUqQSqkMueMqeh2muDr0HW/8Akl3gr/t//wDR4row3u80+sVdet0vwvc4cd7yhS6SlZ+iTk187Wfkzmp5ZZ5nnkeWWRi7u7EszE5JJPUmmUUVznYlYKKKKQBRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAFFFFABRRRQAUUUUAdV4hgt/E3w/k8RyN/xPNHkjhv5WY5uoHO2N2+XBcHC5znCksT8orzyvRPh3/qPFX/YuXn8lrzuuqu+aMJvdrX5dTjwa9nOpSWyd15Jrb0Tvby06BXoOt/8ku8Ff9v/AP6PFefV6Drf/JLvBX/b/wD+jxSofBU9P/bohi/4tH/E/wD0iZy9FFFcx2BRRRQAUUUUAFFFFABV7w+LFtbs01Jc2TzKk53EbUJwW49M5/CqNFNOzE1dWO1g8Hxf2Qpv547G4hncXMjSRg4Z2jjQCSRF6wTsec4K8EVUtvCtmQgutdiid9RurJCkatG/kIjFg7Oo+beFUHAJIyQDkZzeKNce/mvZbtJpplRZPNt43Rtn3TsZSu4f3sZySc5JzBDruqxNGwuy5jmmnHmIr7nmVVlLbgdwYKoIOR+ZrVyp9jnUK3839fd3Ny48JQwWct1Peyw29rJP57GzYTBUFtt+RnAJLXKjGQBgncwxUkfgu18ywhl1pll1K9FrZKtpuD7ooJI3c7xsBFwgIGSPesZvFGts6s92jAF/3ZtzHhkjQqU27Su2KMBcYGwYAqNvEWstd2t2bwma0uzeQN5a/JKfLGQMYxiKMBegC8DrRzU+wKFe3xf19xY8Hwabd3F9bX1k1xIbC6lgfzSqxNHbyyBsD7x3IuMnHXIOeL/AIT0rTbq20pLy0FxJq+qPYeYZGU2yhYvnUAgE5mz82RhOnNc1Y3dxZTNNayeXI0UkJO0H5JEZHHPqrMPx4q5Za9qlnE8VtPHGjgcCCP5SE2blO35W28FlwT1JJpRlFboupCbb5WZlFFFZGwUUUUAFFFFABRRRQAUUUUAdX8O/wDUeKv+xcvP5LXndeifDv8A1Hir/sXLz+S153XTV/gw+f5nHh/95q/9u/kFeg63/wAku8Ff9v8A/wCjxXn1eg63/wAku8Ff9v8A/wCjxRQ+Cp6f+3RDF/xaP+J/+kTOXooormOwKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooA6v4d/wCo8Vf9i5efyWvO69E+Hf8AqPFX/YuXn8lrzuumr/Bh8/zOPD/7zV/7d/IK9B1v/kl3gr/t/wD/AEeK8+r0HW/+SXeCv+3/AP8AR4oofBU9P/bohi/4tH/E/wD0iZy9FFFcx2BRRRQAUUUUAFFFFABXRa/oui6QbW3k1fUJbyW1tLqVF09BGizwxzEK/nZYqsmOVGSO1c7XZ6x4ys9WttMt7+z1uW2s4rOGSz/tn/RZFgiSNtsflfIXVCc5O0sTzQMqap4VgVNOGjX9xdzXdu91LHeQR2gt4cgI7uZWUBucbivGw87xVSLwj4gluZbZbJBKjhFVrmJfOZlDKsWW/ekqykBN2Qy46jOzH43trbxBfatYWOrWz6jA9vdlNUVZFQtG6CF0hXygpjUYww2/LgCrVv8AEy9jaYmPVQouvtNv5Wsyoxbyo4sTtjdMMRRngpzuxgHAWoHM+GNIs9Ti1a5v76ezttNshdO0FsJnfM8UIUKXQdZgc57Ve1nwTqtqzz6eo1Gx2wvFIhRZXWXYFzDuLjDyLG2AQHyuSaXwn4xvdGa8F1catcJPp4sYGttRMEtqomil/duVfaP3W0qAOGNdNc/FuZ2e6i0d11ApbJ573gZZWguIZklmXywZJSIFRn3AEcgDnJqBy8PgndfH8V3Qx2RxOHudx/C5ijAztlatJdS9W4s2f7RJG5raXb+X7goZ8VvJ7OAr9u+j2YBz3pMqiI0U2xHvJHGDdOdo+MyaAo3Dyl5E3syK9E7+Ka2sPcyH5iW0tn6Y0ZX0t7I2yWdr6Dce0MkrgOm3z5hP4/kQdXJ1wV3sXfU3ysFx7K0OBn3d8VV+oVn7j6inrY8D9dw4m4S1ldF3+6SNGp1Dl+5i3o/ZmraV+Rj61xA8QG2B69WAJjGmyrR/""")


USER_LOGO_B64 = ""


def decode_base64_jpeg(data: str) -> Image.Image:
    img_bytes = base64.b64decode(data)
    return Image.open(io.BytesIO(img_bytes)).convert("RGBA")


def exe_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def bundled_asset_path(name: str) -> Path:
    bundle_dir = Path(getattr(sys, "_MEIPASS", exe_dir()))
    return bundle_dir / name


def job_file_path(base_dir: Path | None = None) -> Path:
    target_dir = Path(base_dir) if base_dir is not None else exe_dir()
    return target_dir / "ezee_backup_jobs.json"


def load_jobs(path: str | Path | None = None) -> list:
    target = Path(path) if path is not None else job_file_path()
    if not target.exists():
        return []
    try:
        with target.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        if isinstance(data, list):
            jobs = data
        elif isinstance(data, dict) and isinstance(data.get("jobs"), list):
            jobs = data["jobs"]
        else:
            return []

        migrated = False
        for job in jobs:
            if "include_subfolders" not in job:
                job["include_subfolders"] = True
                migrated = True
        if migrated:
            try:
                save_jobs(jobs, target)
            except OSError:
                pass
        return jobs
    except (json.JSONDecodeError, OSError):
        return []


def save_jobs(jobs: list, path: str | Path | None = None) -> Path:
    target = Path(path) if path is not None else job_file_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    groups = {}
    for job in jobs:
        group = str(job.get("group", "")).strip()
        if group:
            groups.setdefault(group, []).append(job.get("name", "Untitled"))
    data = {"version": 2, "groups": groups, "jobs": jobs}
    with target.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2)
    return target


def build_robocopy_command(source: str, destination: str, mode: str, verbose: bool = False, include_subfolders: bool = True):
    source_norm = str(source).strip().rstrip('\\/')
    dest_norm = str(destination).strip().rstrip('\\/')
    mode_name = (mode or "backup").lower()

    options = ["/R:2", "/W:2", "/COPY:DAT", "/FFT", "/DST"]
    if mode_name == "sync":
        options = ["/MIR", "/R:2", "/W:2", "/COPY:DAT", "/FFT", "/DST"]
    elif mode_name in {"move", "transfer"}:
        options = (["/E"] if include_subfolders else []) + ["/MOV", "/COPY:DAT", "/FFT", "/DST", "/R:2", "/W:2"]
    elif mode_name == "compare":
        options = ["/L"] + (["/E"] if include_subfolders else []) + ["/COPY:DAT", "/FFT", "/DST", "/R:2", "/W:2"]
    else:
        options = (["/E"] if include_subfolders else []) + ["/COPY:DAT", "/FFT", "/DST", "/R:2", "/W:2"]

    if verbose:
        options.append("/V")

    command = ["robocopy", source_norm, dest_norm, *options]
    return command


def has_valid_folder_pair(source: str, destination: str) -> bool:
    return bool(str(source).strip()) and bool(str(destination).strip())


def folder_dialog_initialdir(folder: str) -> str | None:
    candidate = str(folder).strip()
    return candidate if candidate and os.path.isdir(candidate) else None


def icon_key_for_filename(filename: str) -> str:
    suffix = Path(filename).suffix.lower()
    if suffix in {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".svg"}:
        return "image"
    if suffix in {".mp4", ".mkv", ".avi", ".mov", ".wmv", ".webm"}:
        return "video"
    if suffix in {".zip", ".7z", ".rar", ".tar", ".gz"}:
        return "archive"
    if suffix in {".exe", ".msi", ".bat", ".cmd", ".ps1"}:
        return "application"
    return "file"


def is_successful_robocopy_exit_code(code: int) -> bool:
    return 0 <= code <= 7


def play_completion_chime():
    if winsound is None:
        return

    def chime():
        try:
            sound_path = bundled_asset_path("EZ-guitar.wav")
            if sound_path.exists():
                winsound.PlaySound(str(sound_path), winsound.SND_FILENAME | winsound.SND_ASYNC)
            else:
                winsound.PlaySound("Tada", winsound.SND_ALIAS | winsound.SND_ASYNC)
        except (RuntimeError, OSError):
            try:
                winsound.PlaySound("Tada", winsound.SND_ALIAS | winsound.SND_ASYNC)
            except (RuntimeError, OSError):
                pass

    threading.Thread(target=chime, daemon=True).start()


def play_error_sound():
    if winsound is None:
        return

    def sound():
        try:
            sound_path = bundled_asset_path("EZ-error.wav")
            if sound_path.exists():
                winsound.PlaySound(str(sound_path), winsound.SND_FILENAME | winsound.SND_ASYNC)
            else:
                winsound.PlaySound("SystemHand", winsound.SND_ALIAS | winsound.SND_ASYNC)
        except (RuntimeError, OSError):
            try:
                winsound.PlaySound("SystemHand", winsound.SND_ALIAS | winsound.SND_ASYNC)
            except (RuntimeError, OSError):
                pass

    threading.Thread(target=sound, daemon=True).start()


def jobs_for_sidebar_selection(jobs: list, kind: str, value: str) -> list:
    if kind == "job":
        return [jobs[int(value)]]
    if kind == "group":
        return [job for job in jobs if str(job.get("group", "")).strip() == value]
    return []


class ToolTip:
    def __init__(self, widget, text: str):
        self.widget = widget
        self.text = text
        self.tip_window = None
        self.after_id = None
        widget.bind("<Enter>", self._schedule, add="+")
        widget.bind("<Leave>", self._hide, add="+")
        widget.bind("<ButtonPress>", self._hide, add="+")

    def _schedule(self, _event=None):
        self._hide()
        self.after_id = self.widget.after(500, self._show)

    def _show(self):
        if self.tip_window is not None or not self.widget.winfo_exists():
            return
        x = self.widget.winfo_rootx() + self.widget.winfo_width() + 6
        y = self.widget.winfo_rooty() + self.widget.winfo_height() // 2
        self.tip_window = tk.Toplevel(self.widget)
        self.tip_window.wm_overrideredirect(True)
        self.tip_window.wm_geometry(f"+{x}+{y}")
        tk.Label(
            self.tip_window,
            text=self.text,
            bg="#0f172a",
            fg="#e2e8f0",
            relief="solid",
            borderwidth=1,
            padx=6,
            pady=3,
        ).pack()

    def _hide(self, _event=None):
        if self.after_id is not None:
            self.widget.after_cancel(self.after_id)
            self.after_id = None
        if self.tip_window is not None:
            self.tip_window.destroy()
            self.tip_window = None


class SplashScreen(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title(f"{APP_NAME} - Welcome")
        self.configure(bg="#0b1020")
        self.geometry("460x650")
        self.resizable(False, False)
        self.transient(parent)
        self.attributes("-topmost", True)

        try:
            if USER_LOGO_B64:
                payload = decode_base64_jpeg(USER_LOGO_B64)
            else:
                payload = Image.open(bundled_asset_path("EZeeBACK Logo.jpg")).convert("RGBA")
            payload.thumbnail((300, 300), Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(payload)
            self.image = photo
            logo = tk.Label(self, image=photo, bg="#0b1020", borderwidth=0)
            logo.pack(pady=(24, 12))
        except Exception:
            logo = tk.Label(self, text=APP_NAME, font=("Segoe UI", 24, "bold"), bg="#0b1020", fg="#e2e8f0")
            logo.pack(pady=(80, 35))

        tk.Label(self, text=APP_NAME, font=("Segoe UI", 22, "bold"), bg="#0b1020", fg="#e2e8f0").pack()
        tk.Label(self, text=f"Version {VERSION}", font=("Segoe UI", 12), bg="#0b1020", fg="#38bdf8").pack(pady=(2, 16))
        tk.Label(
            self,
            text="Developed by Adrian Newington\nas a Vibe Coding Project\nusing Python and Google Code Assist AI\n\nGithub.com/SunflowerGUY",
            font=("Segoe UI", 10),
            justify="center",
            bg="#0b1020",
            fg="#cbd5e1",
        ).pack()

        button = tk.Button(
            self,
            text="Click to Start",
            command=self.close,
            bg="#38bdf8",
            fg="#0f172a",
            activebackground="#7dd3fc",
            font=("Segoe UI", 11, "bold"),
            relief="flat",
            padx=8,
            pady=8,
        )
        button.pack(pady=(22, 20))

        self.protocol("WM_DELETE_WINDOW", self.close)
        self.update_idletasks()
        parent.update()
        x = parent.winfo_rootx() + (parent.winfo_width() - self.winfo_width()) // 2
        y = parent.winfo_rooty() + (parent.winfo_height() - self.winfo_height()) // 2 - 30
        self.geometry(f"+{x}+{y}")

    def close(self):
        try:
            self.grab_release()
        except tk.TclError:
            pass
        self.destroy()
        self.master.deiconify()
        self.master.lift()
        self.master.focus_force()


class EZeeBackupApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"{APP_NAME} - Version {VERSION}")
        self.geometry("980x850")
        self.minsize(900, 760)
        self.configure(bg="#0b1020")
        try:
            self.iconbitmap(str(bundled_asset_path("ezee-backup.ico")))
        except tk.TclError:
            pass
        self.protocol("WM_DELETE_WINDOW", self.destroy)

        menu_bar = tk.Menu(self)
        self.config(menu=menu_bar)

        file_menu = tk.Menu(menu_bar, tearoff=0)
        file_menu.add_command(label="Exit", command=self.destroy, accelerator="Ctrl+Q")
        menu_bar.add_cascade(label="File", menu=file_menu, underline=0)

        edit_menu = tk.Menu(menu_bar, tearoff=0)
        edit_menu.add_command(label="Save Job", command=self.save_current_job)
        edit_menu.add_command(label="Delete Job", command=self.delete_current_job)
        edit_menu.add_separator()
        edit_menu.add_command(label="Save Changes", command=self.save_job_changes, accelerator="Ctrl+S", state=tk.DISABLED)
        edit_menu.add_command(label="Forget Changes", command=self.forget_changes, state=tk.DISABLED)
        self.edit_menu = edit_menu
        menu_bar.add_cascade(label="Edit", menu=edit_menu, underline=0)

        help_menu = tk.Menu(menu_bar, tearoff=0)
        help_menu.add_command(label="About", command=self.open_about)
        help_menu.add_command(label="Backup Mode Info", command=self.open_backup_info)
        menu_bar.add_cascade(label="Help", menu=help_menu, underline=0)

        self.bind_all("<Control-s>", lambda event: self.save_job_changes())
        self.bind_all("<Control-q>", lambda event: self.destroy())

        self.source_var = tk.StringVar()
        self.destination_var = tk.StringVar()
        self.mode_var = tk.StringVar(value="backup")
        self.include_subfolders_var = tk.BooleanVar(value=True)
        self.log_mode_var = tk.StringVar(value="Simple")
        self._loading_job = False
        self._profile_modified = False
        self.source_var.trace_add("write", self._profile_field_changed)
        self.destination_var.trace_add("write", self._profile_field_changed)
        self.mode_var.trace_add("write", self._profile_field_changed)
        self.include_subfolders_var.trace_add("write", self._profile_field_changed)
        self.active_process = None
        self.process_paused = False
        self.operation_aborted = False
        self.status_var = tk.StringVar(value="Ready")
        self.activity_animation_id = None
        self.activity_position = 0
        self.activity_direction = 1
        self.pending_jobs = []
        self.batch_job_names = []

        self.jobs = load_jobs(job_file_path())
        self._build_ui()
        self._center_window()

    def _center_window(self):
        self.update_idletasks()
        width = max(self.winfo_reqwidth(), 980)
        height = max(self.winfo_reqheight(), 850)
        usable_height = max(0, self.winfo_screenheight() - 48)
        x = max(0, (self.winfo_screenwidth() - width) // 2)
        y = max(0, (usable_height - height) // 2)
        self.geometry(f"{width}x{height}+{x}+{y}")

    def _build_ui(self):
        self._create_file_icons()
        top = tk.Frame(self, bg="#0b1020", padx=18, pady=2)
        top.pack(fill="x")

        title_row = tk.Frame(top, bg="#0b1020")
        title_row.pack(fill="x")
        try:
            logo_image = Image.open(bundled_asset_path("EZeeBACK Logo.jpg")).convert("RGBA")
            logo_image.thumbnail((34, 34), Image.Resampling.LANCZOS)
            self.title_logo = ImageTk.PhotoImage(logo_image)
            tk.Label(title_row, image=self.title_logo, bg="#0b1020", borderwidth=0).pack(side="left", padx=(0, 8))
        except (OSError, tk.TclError):
            pass
        title = tk.Label(title_row, text=f"{APP_NAME}", font=("Segoe UI", 20, "bold"), fg="#e2e8f0", bg="#0b1020")
        title.pack(side="left")
        subtitle = tk.Label(title_row, text=f"Version {VERSION}", font=("Segoe UI", 9), fg="#7dd3fc", bg="#0b1020")
        subtitle.pack(side="left", padx=(10, 0), pady=(6, 0))
        action_row = tk.Frame(title_row, bg="#0b1020")
        action_row.pack(side="right")
        tk.Button(
            action_row,
            text="About",
            command=self.open_about,
            bg="#1f2937",
            fg="#e2e8f0",
            activebackground="#334155",
            activeforeground="#ffffff",
            relief="flat",
            font=("Segoe UI", 10, "bold"),
            padx=12,
        ).pack(side="left", padx=(0, 8))
        tk.Button(
            action_row,
            text="Exit",
            command=self.destroy,
            bg="#7f1d1d",
            fg="#ffffff",
            activebackground="#b91c1c",
            activeforeground="#ffffff",
            relief="flat",
            font=("Segoe UI", 10, "bold"),
            padx=12,
        ).pack(side="left")

        workspace = tk.Frame(self, bg="#0b1020")
        workspace.pack(fill="both", expand=True, padx=18, pady=(2, 4))
        sidebar = tk.LabelFrame(workspace, text="Groups & Jobs", bg="#111827", fg="#e2e8f0", padx=8, pady=4)
        sidebar.configure(width=300)
        sidebar.pack_propagate(False)
        sidebar.pack(side="left", fill="y", padx=(0, 10))
        sidebar_view = tk.Frame(sidebar, bg="#111827")
        sidebar_view.pack(fill="both", expand=True)
        sidebar_tree_style = ttk.Style(self)
        sidebar_tree_style.configure("Sidebar.Treeview", font=("Segoe UI", 10, "bold"))
        self.job_tree = ttk.Treeview(sidebar_view, style="Sidebar.Treeview", show="tree", selectmode="browse", height=22)
        sidebar_scrollbar = ttk.Scrollbar(sidebar_view, orient="vertical", command=self.job_tree.yview)
        self.job_tree.configure(yscrollcommand=sidebar_scrollbar.set)
        self.job_tree.pack(side="left", fill="both", expand=True)
        sidebar_scrollbar.pack(side="right", fill="y")
        self.job_tree.tag_configure("backup", foreground="#3f8f5f", font=("Segoe UI", 10, "bold"))
        self.job_tree.tag_configure("sync", foreground="#ef4444", font=("Segoe UI", 10, "bold"))
        self.job_tree.tag_configure("move", foreground="#3b82f6", font=("Segoe UI", 10, "bold"))
        self.job_tree.tag_configure("compare", foreground="#a855f7", font=("Segoe UI", 10, "bold"))
        self.job_tree.bind("<<TreeviewSelect>>", self._select_sidebar_item)
        self.job_tree.bind("<Button-3>", self._show_job_context_menu)
        form = tk.LabelFrame(workspace, text="Backup Settings", bg="#111827", fg="#e2e8f0", padx=12, pady=4, borderwidth=2, relief="groove")
        form.pack(side="left", fill="both", expand=True)

        self.job_profile_label = tk.Label(
            form,
            text="Showing Job Profile: ",
            anchor="w",
            bg="#111827",
            fg="#f97316",
            font=("Segoe UI", 11, "bold"),
        )
        self.job_profile_label.pack(fill="x", pady=(0, 3))

        row = tk.Frame(form, bg="#111827")
        row.pack(fill="x", pady=3)
        tk.Label(row, text="Source Folder", width=18, anchor="w", bg="#111827", fg="#cbd5e1", font=("Segoe UI", 10, "bold")).pack(side="left")
        source_entry = tk.Entry(row, textvariable=self.source_var, width=1, bg="#ffffff", fg="#111827", insertbackground="#111827", relief="solid", borderwidth=1)
        source_entry.pack(side="left", fill="x", expand=True, padx=(8, 10), ipady=3)
        tk.Button(row, text="Browse", command=self.browse_source, bg="#1f2937", fg="#e2e8f0", activebackground="#334155", activeforeground="#ffffff", relief="flat", font=("Segoe UI", 10, "bold"), padx=12).pack(side="left")
        self.include_subfolders_checkbutton = tk.Checkbutton(
            row,
            text="Include Sub Folders",
            variable=self.include_subfolders_var,
            bg="#111827",
            fg="#e2e8f0",
            activebackground="#111827",
            activeforeground="#ffffff",
            selectcolor="#0f172a",
            font=("Segoe UI", 10),
            command=self._include_subfolders_changed,
        )
        self.include_subfolders_checkbutton.pack(side="left", padx=(12, 0))

        row2 = tk.Frame(form, bg="#111827")
        row2.pack(fill="x", pady=3)
        tk.Label(row2, text="Destination Folder", width=18, anchor="w", bg="#111827", fg="#cbd5e1", font=("Segoe UI", 10, "bold")).pack(side="left")
        destination_entry = tk.Entry(row2, textvariable=self.destination_var, width=1, bg="#ffffff", fg="#111827", insertbackground="#111827", relief="solid", borderwidth=1)
        destination_entry.pack(side="left", fill="x", expand=True, padx=(8, 10), ipady=3)
        tk.Button(row2, text="Browse", command=self.browse_destination, bg="#1f2937", fg="#e2e8f0", activebackground="#334155", activeforeground="#ffffff", relief="flat", font=("Segoe UI", 10, "bold"), padx=12).pack(side="left")
        destination_spacer = tk.Frame(row2, width=self.include_subfolders_checkbutton.winfo_reqwidth(), height=1, bg="#111827")
        destination_spacer.pack_propagate(False)
        destination_spacer.pack(side="left", padx=(12, 0))

        jobs_frame = tk.Frame(form, bg="#111827")
        jobs_frame.pack(fill="x", pady=(2, 2))
        job_row = tk.Frame(jobs_frame, bg="#111827")
        job_row.pack(fill="x")
        tk.Label(job_row, text="Job:", bg="#111827", fg="#cbd5e1").pack(side="left", padx=(0, 8))
        self.job_name = tk.StringVar(value="Daily Backup")
        self.job_name.trace_add("write", self._update_job_profile_label)
        self._update_job_profile_label()
        tk.Button(job_row, text="Save Job...", command=self.save_current_job, bg="#1f2937", fg="#e2e8f0", relief="flat", font=("Segoe UI", 10, "bold"), padx=10).pack(side="left")
        tk.Button(job_row, text="Delete Job", command=self.delete_current_job, bg="#1f2937", fg="#e2e8f0", relief="flat", font=("Segoe UI", 10, "bold"), padx=10).pack(side="left", padx=(8, 0))
        self.save_changes_button = tk.Button(
            job_row,
            text="Save Changes",
            command=self.save_job_changes,
            bg="#1f2937",
            fg="#ffffff",
            activeforeground="#ffffff",
            state=tk.DISABLED,
            relief="flat",
            font=("Segoe UI", 10, "bold"),
            padx=10,
        )
        self.save_changes_button.pack(side="left", padx=(8, 0))
        self.forget_changes_button = tk.Button(
            job_row,
            text="Forget Changes",
            command=self.forget_changes,
            bg="#1f2937",
            fg="#ffffff",
            activeforeground="#ffffff",
            state=tk.DISABLED,
            relief="flat",
            font=("Segoe UI", 10, "bold"),
            padx=10,
        )
        self.forget_changes_button.pack(side="left", padx=(8, 0))
        self.refresh_jobs_list()

        folder_views = tk.Frame(form, bg="#111827")
        folder_views.pack(fill="both", expand=True, pady=(3, 2))
        self.source_tree = self._create_folder_view(folder_views, "Source Folder")
        self.destination_tree = self._create_folder_view(folder_views, "Destination Folder")

        controls = tk.Frame(form, bg="#111827")
        controls.pack(fill="x", pady=3)

        mode_container = tk.LabelFrame(controls, text="", bg="#111827", fg="#e2e8f0", padx=8, pady=6, borderwidth=2, relief="solid")
        mode_container.configure(highlightbackground="#0041a3", highlightcolor="#0041a3", highlightthickness=2)
        mode_container.pack(side="left", fill="y")

        mode_frame = tk.Frame(mode_container, bg="#111827")
        mode_frame.pack(side="left")
        mode_colors = {"backup": "#00ff00", "sync": "#ff3333", "move": "#00c3ff", "compare": "#e400ff"}
        for label, value in [("Backup", "backup"), ("Mirror", "sync"), ("Move", "move"), ("Compare", "compare")]:
            tk.Radiobutton(
                mode_frame,
                text=label,
                variable=self.mode_var,
                value=value,
                command=self._mode_changed,
                bg="#111827",
                fg=mode_colors[value],
                activeforeground=mode_colors[value],
                selectcolor="#0f172a",
                activebackground="#111827",
                font=("Segoe UI", 10, "bold"),
            ).pack(side="left", padx=(0, 16))

        self.backup_info_image = ImageTk.PhotoImage(
            Image.open(bundled_asset_path("backup-info.png")).resize((32, 32), Image.Resampling.LANCZOS)
        )
        backup_info_button = tk.Button(
            mode_frame,
            image=self.backup_info_image,
            command=self.open_backup_info,
            bg="#111827",
            activebackground="#334155",
            relief="flat",
            borderwidth=0,
            highlightthickness=0,
            padx=2,
            pady=2,
            cursor="hand2",
            takefocus=True,
        )
        backup_info_button.pack(side="left", padx=(0, 4))
        ToolTip(backup_info_button, "Backup Info")

        checks = tk.Frame(controls, bg="#111827")
        checks.pack(side="left", padx=(18, 0), pady=6)
        tk.Label(checks, text="Log:", bg="#111827", fg="#cbd5e1", font=("Segoe UI", 10, "bold")).pack(side="left", padx=(8, 4))
        self.log_mode_selector = ttk.Combobox(checks, textvariable=self.log_mode_var, values=("Simple", "Verbose", "No Logs"), state="readonly", width=10)
        self.log_mode_selector.pack(side="left", padx=(0, 8))

        action_group = tk.Frame(controls, bg="#111827")
        action_group.pack(side="right")
        tk.Button(
            action_group,
            text="Refresh Folders",
            command=self.refresh_folder_views,
            bg="#0060ff",
            fg="#ffffff",
            activebackground="#004ecc",
            activeforeground="#ffffff",
            font=("Segoe UI", 10, "bold"),
            padx=8,
            pady=8,
            relief="flat",
            width=14,
        ).pack(side="left", padx=(0, 10))
        tk.Button(
            action_group,
            text="RUN",
            command=self.run_backup,
            bg="#ff3600",
            fg="#ffffff",
            activebackground="#d92d00",
            activeforeground="#ffffff",
            font=("Segoe UI", 10, "bold"),
            padx=8,
            pady=8,
            relief="flat",
            width=8,
        )
        self.run_button = action_group.winfo_children()[-1]
        self.run_button.pack(side="left")
        self.pause_button = tk.Button(action_group, text="Pause", command=self.toggle_pause, bg="#5b4a2f", fg="#000000", disabledforeground="#000000", activebackground="#f59e0b", activeforeground="#ffffff", relief="flat", font=("Segoe UI", 10, "bold"), padx=12, pady=8, state="disabled")
        self.pause_button.pack(side="left", padx=(10, 0))
        self.abort_button = tk.Button(action_group, text="Abort", command=self.abort_operation, bg="#5f3030", fg="#000000", disabledforeground="#000000", activebackground="#ef4444", activeforeground="#ffffff", relief="flat", font=("Segoe UI", 10, "bold"), padx=12, pady=8, state="disabled")
        self.abort_button.pack(side="left", padx=(8, 0))
        self.activity_spinner = tk.Canvas(controls, bg="#374151", width=80, height=10, highlightthickness=0, bd=0)
        self.activity_spinner.pack(side="right", padx=(0, 8))
        self.activity_spinner.create_rectangle(0, 0, 80, 10, fill="#3f8f5f", outline="")
        tk.Label(controls, textvariable=self.status_var, width=10, anchor="center", bg="#111827", fg="#cbd5e1", font=("Segoe UI", 10, "bold")).pack(side="right", padx=(0, 8))

        log_frame = tk.LabelFrame(self, text="Activity Log", bg="#111827", fg="#e2e8f0", padx=10, pady=10)
        log_frame.pack(fill="both", expand=True, padx=18, pady=(0, 10))

        log_view = tk.Frame(log_frame, bg="#020817")
        log_view.pack(fill="both", expand=True)
        self.log_widget = tk.Text(log_view, height=8, bg="#020817", fg="#dbeafe", insertbackground="#e2e8f0", padx=8, pady=8)
        self.log_widget.tag_configure("job_report", foreground="#ffff00")
        log_scrollbar = ttk.Scrollbar(log_view, orient="vertical", command=self.log_widget.yview)
        self.log_widget.configure(yscrollcommand=log_scrollbar.set)
        self.log_widget.pack(side="left", fill="both", expand=True)
        log_scrollbar.pack(side="right", fill="y")
        self.log_widget.insert("end", "EZee-Backup ready.\n")
        self.log_widget.insert("end", "Use Right-Click to copy Log Files.\n", "job_report")
        self.log_widget.see("end")
        self.log_widget.bind("<Button-3>", self._show_log_context_menu)

    def _show_log_context_menu(self, event=None):
        menu = tk.Menu(self, tearoff=0)
        menu.add_command(label="Copy Selected", command=self._copy_selected_log_text)
        menu.add_command(label="Copy Logs", command=self._copy_logs_to_clipboard)
        menu.add_command(label="Copy Logs and Launch NOTEPAD", command=self._copy_logs_and_launch_notepad)
        menu.add_separator()
        menu.add_command(label="Clear Log", command=self._clear_log)
        menu.tk_popup(event.x_root, event.y_root)

    def _copy_selected_log_text(self):
        selected = self.log_widget.get(tk.SEL_FIRST, tk.SEL_LAST) if self.log_widget.tag_ranges(tk.SEL) else ""
        if not selected:
            return
        self.clipboard_clear()
        self.clipboard_append(selected)

    def _copy_logs_to_clipboard(self):
        log_text = self.log_widget.get("1.0", "end").rstrip()
        self.clipboard_clear()
        self.clipboard_append(log_text)

    def _copy_logs_and_launch_notepad(self):
        log_text = self.log_widget.get("1.0", "end").rstrip()
        self.clipboard_clear()
        self.clipboard_append(log_text)

        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                suffix=".txt",
                prefix="ezee-backup-logs-",
                encoding="utf-8",
                delete=False,
            ) as log_file:
                log_file.write(log_text)
                log_path = log_file.name
            subprocess.Popen(["notepad.exe", log_path])
        except OSError as exc:
            messagebox.showerror("Notepad", f"Unable to launch Notepad:\n{exc}", parent=self)

    def _clear_log(self):
        self.log_widget.delete("1.0", "end")
        self.log_widget.insert("end", "EZee-Backup ready.\n")
        self.log_widget.see("end")

    def _set_operation_controls(self, running):
        self.run_button.configure(state="disabled" if running else "normal")
        self.pause_button.configure(state="normal" if running else "disabled")
        self.abort_button.configure(state="normal" if running else "disabled")
        if running:
            self.status_var.set("Working")
            self._start_activity_animation(reset=True)
        else:
            self.status_var.set("Ready")
            self._stop_activity_animation()
        if running:
            self.pause_button.configure(bg="#b45309", fg="#ffffff")
            self.abort_button.configure(bg="#b91c1c", fg="#ffffff")
        else:
            self.pause_button.configure(bg="#5b4a2f", fg="#000000")
            self.abort_button.configure(bg="#5f3030", fg="#000000")

    def _start_activity_animation(self, reset=False):
        if self.activity_animation_id is not None:
            return
        if reset:
            self.activity_position = 0
            self.activity_direction = 1
        self._animate_activity_indicator()

    def _pause_activity_animation(self):
        if self.activity_animation_id is not None:
            self.after_cancel(self.activity_animation_id)
            self.activity_animation_id = None

    def _animate_activity_indicator(self):
        self.activity_spinner.delete("all")
        self.activity_spinner.create_rectangle(0, 0, 80, 10, fill="#374151", outline="")
        self.activity_spinner.create_rectangle(self.activity_position, 0, self.activity_position + 24, 10, fill="#f59e0b", outline="")
        next_position = self.activity_position + self.activity_direction * 2
        if next_position < 0 or next_position > 56:
            self.activity_direction *= -1
            next_position = self.activity_position + self.activity_direction * 2
        self.activity_position = next_position
        self.activity_animation_id = self.after(70, self._animate_activity_indicator)

    def _stop_activity_animation(self):
        if self.activity_animation_id is not None:
            self.after_cancel(self.activity_animation_id)
            self.activity_animation_id = None
        self.activity_spinner.delete("all")
        self.activity_spinner.create_rectangle(0, 0, 80, 10, fill="#3f8f5f", outline="")

    def _set_process_paused(self, process, paused):
        if os.name != "nt":
            raise OSError("Process pause is only supported on Windows.")
        import ctypes

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        handle = kernel32.OpenProcess(0x0800, False, process.pid)
        if not handle:
            raise ctypes.WinError(ctypes.get_last_error())
        try:
            function_name = "NtSuspendProcess" if paused else "NtResumeProcess"
            function = ctypes.WinDLL("ntdll").__getattr__(function_name)
            status = function(handle)
            if status != 0:
                raise OSError(f"Unable to {'pause' if paused else 'resume'} the backup process.")
        finally:
            kernel32.CloseHandle(handle)

    def toggle_pause(self):
        process = self.active_process
        if process is None or process.poll() is not None:
            return False
        paused = not self.process_paused
        try:
            self._set_process_paused(process, paused)
        except OSError as exc:
            self._log(f"Unable to {'pause' if paused else 'resume'} operation: {exc}")
            return False
        self.process_paused = paused
        self.pause_button.configure(text="Resume" if paused else "Pause")
        if paused:
            self._pause_activity_animation()
        else:
            self._start_activity_animation()
        self._log("Operation paused." if paused else "Operation resumed.")
        return True

    def abort_operation(self):
        process = self.active_process
        if process is None or process.poll() is not None:
            return
        paused_before_abort = self.process_paused
        if not paused_before_abort and not self.toggle_pause():
            return
        if not messagebox.askyesno("Abort operation", "Abort the current backup operation?", parent=self):
            if not paused_before_abort:
                self.toggle_pause()
            return
        self.operation_aborted = True
        try:
            process.terminate()
            self._log("Abort requested. Waiting for Robocopy to stop...")
        except OSError as exc:
            self._log(f"Unable to abort operation: {exc}")

    def _create_folder_view(self, parent, title):
        panel = tk.Frame(parent, bg="#111827")
        panel.pack(side="left", fill="both", expand=True, padx=(0, 8))
        tk.Label(panel, text=title, anchor="w", bg="#111827", fg="#e2e8f0", font=("Segoe UI", 10, "bold")).pack(fill="x", pady=(0, 4))

        view_frame = tk.Frame(panel, bg="#111827")
        view_frame.pack(fill="both", expand=True)
        tree = ttk.Treeview(view_frame, columns=("size",), show="tree headings", height=12)
        tree.heading("#0", text="Name")
        tree.heading("size", text="Size")
        tree.column("#0", anchor="w", width=280, stretch=True)
        tree.column("size", anchor="e", width=100, stretch=False)
        tree._file_icons = self.file_icons
        tree._folder_paths = {}
        tree._loaded_folders = set()
        tree.bind("<<TreeviewOpen>>", self._expand_folder_item)
        scrollbar = ttk.Scrollbar(view_frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        return tree

    def _create_file_icons(self):
        colors = {
            "folder": (245, 185, 55),
            "file": (148, 163, 184),
            "image": (45, 180, 145),
            "video": (217, 92, 92),
            "archive": (164, 125, 219),
            "application": (75, 145, 210),
        }
        self.file_icons = {}
        for key, color in colors.items():
            image = Image.new("RGBA", (20, 20), (0, 0, 0, 0))
            draw = ImageDraw.Draw(image)
            if key == "folder":
                draw.polygon([(2, 5), (8, 5), (10, 7), (18, 7), (18, 17), (2, 17)], fill=color)
                draw.line([(2, 5), (8, 5), (10, 7), (18, 7)], fill=(255, 220, 115), width=1)
            else:
                draw.polygon([(4, 2), (13, 2), (17, 6), (17, 18), (4, 18)], fill=color)
                draw.polygon([(13, 2), (13, 6), (17, 6)], fill=(226, 232, 240))
                draw.line([(7, 10), (14, 10)], fill=(255, 255, 255), width=1)
                draw.line([(7, 13), (14, 13)], fill=(255, 255, 255), width=1)
            self.file_icons[key] = ImageTk.PhotoImage(image)

    def _populate_folder_view(self, tree, folder, include_subfolders=True):
        tree.delete(*tree.get_children())
        tree._folder_paths = {}
        tree._loaded_folders = set()
        tree._include_subfolders = include_subfolders
        path = Path(folder.strip()) if folder.strip() else None
        if path is None:
            return
        self._insert_folder_entries(tree, "", path)

    def _insert_folder_entries(self, tree, parent, path):
        try:
            entries = sorted(os.scandir(path), key=lambda entry: (not entry.is_dir(follow_symlinks=False), entry.name.lower()))
            for entry in entries:
                is_directory = entry.is_dir(follow_symlinks=False)
                if is_directory and not tree._include_subfolders:
                    continue
                if is_directory:
                    item_id = tree.insert(
                        parent,
                        "end",
                        text=f"{entry.name}/",
                        image=tree._file_icons["folder"],
                        values=("<DIR>",),
                    )
                    tree._folder_paths[item_id] = Path(entry.path)
                    tree.insert(item_id, "end", text="")
                else:
                    try:
                        size = f"{entry.stat(follow_symlinks=False).st_size:,}"
                    except OSError:
                        size = "?"
                    tree.insert(
                        parent,
                        "end",
                        text=entry.name,
                        image=tree._file_icons[icon_key_for_filename(entry.name)],
                        values=(size,),
                    )
            tree._loaded_folders.add(str(path))
        except (OSError, PermissionError):
            tree.insert(parent, "end", text="Unable to read folder", values=("",))

    def _expand_folder_item(self, event):
        tree = event.widget
        item_id = tree.focus()
        path = tree._folder_paths.get(item_id)
        if path is None or str(path) in tree._loaded_folders:
            return
        tree.delete(*tree.get_children(item_id))
        self._insert_folder_entries(tree, item_id, path)

    def _include_subfolders_changed(self):
        self.refresh_folder_views()
        self._profile_field_changed()

    def refresh_folder_views(self):
        include_subfolders = self.include_subfolders_var.get()
        self._populate_folder_view(
            self.source_tree,
            self.source_var.get(),
            include_subfolders=include_subfolders,
        )
        self._populate_folder_view(
            self.destination_tree,
            self.destination_var.get(),
            include_subfolders=include_subfolders,
        )

    def browse_source(self):
        folder = filedialog.askdirectory(
            title="Select Source Folder",
            initialdir=folder_dialog_initialdir(self.source_var.get()),
        )
        if folder:
            self.source_var.set(folder)
            self.refresh_folder_views()

    def browse_destination(self):
        folder = filedialog.askdirectory(
            title="Select Destination Folder",
            initialdir=folder_dialog_initialdir(self.destination_var.get()),
        )
        if folder:
            self.destination_var.set(folder)
            self.refresh_folder_views()

    def open_about(self):
        if getattr(self, "about_window", None) is not None and self.about_window.winfo_exists():
            self.about_window.lift()
            self.about_window.focus_force()
            return
        self.about_window = SplashScreen(self)

    def _update_job_profile_label(self, *_args):
        name = self.job_name.get().strip() or "Untitled"
        self.job_profile_label.config(text=f"Showing Job Profile: {name}")

    def open_backup_info(self):
        if getattr(self, "backup_info_window", None) is not None and self.backup_info_window.winfo_exists():
            self.backup_info_window.lift()
            self.backup_info_window.focus_force()
            return

        dialog = tk.Toplevel(self)
        self.backup_info_window = dialog
        dialog.title("Backup Info")
        dialog.configure(bg="#111827")
        dialog.resizable(False, False)
        dialog.transient(self)

        content = tk.Frame(dialog, bg="#111827", padx=18, pady=16)
        content.pack(fill="both", expand=True)
        tk.Label(
            content,
            text="Backup modes",
            font=("Segoe UI", 12, "bold"),
            bg="#111827",
            fg="#e2e8f0",
        ).pack(anchor="w", pady=(0, 12))

        explanations = (
            ("BACKUP", "Copies new and changed files to the destination."),
            ("MIRROR", "Makes the destination mirror the source, including deletions."),
            ("MOVE", "Copies files to the destination and removes them from the source."),
            ("COMPARE", "Lists what would be copied without changing either folder."),
        )
        for mode, explanation in explanations:
            row = tk.Frame(content, bg="#111827")
            row.pack(fill="x", pady=2)
            tk.Label(
                row,
                text=f"{mode}: ",
                font=("Segoe UI", 10, "bold"),
                bg="#111827",
                fg="#e2e8f0",
            ).pack(side="left")
            tk.Label(
                row,
                text=explanation,
                font=("Segoe UI", 10),
                bg="#111827",
                fg="#cbd5e1",
            ).pack(side="left")

        tk.Button(
            content,
            text="OK",
            command=dialog.destroy,
            bg="#1f2937",
            fg="#e2e8f0",
            activebackground="#334155",
            activeforeground="#ffffff",
            relief="flat",
            font=("Segoe UI", 10, "bold"),
            padx=16,
        ).pack(anchor="e", pady=(14, 0))

        dialog.protocol("WM_DELETE_WINDOW", dialog.destroy)
        dialog.update_idletasks()
        x = self.winfo_rootx() + (self.winfo_width() - dialog.winfo_width()) // 2
        y = self.winfo_rooty() + (self.winfo_height() - dialog.winfo_height()) // 2
        dialog.geometry(f"+{x}+{y}")
        dialog.grab_set()
        dialog.focus_force()

    def _log(self, message, tag=None):
        self.log_widget.insert("end", f"{message}\n", tag)
        self.log_widget.see("end")
        self.update_idletasks()

    def _should_log_line(self, text: str) -> bool:
        stripped = text.strip()
        if not stripped:
            return False
        if stripped.endswith("%"):
            try:
                float(stripped[:-1])
                return False
            except ValueError:
                pass
        return True

    def _normalize_log_line(self, text: str) -> str:
        text = text.replace("\t", " ").lstrip()
        if text.startswith("Total") and "Copied" in text and "Skipped" in text:
            return f"{' ' * 13}{text}"
        return text

    def _stream_process_output(self, process, output_queue, log_mode):
        try:
            if process.stdout is not None:
                for line in iter(process.stdout.readline, ""):
                    text = line.rstrip()
                    normalized = self._normalize_log_line(text)
                    if log_mode != "No Logs" and self._should_log_line(normalized):
                        output_queue.put(normalized)
            if process.stderr is not None:
                for line in iter(process.stderr.readline, ""):
                    text = line.rstrip()
                    normalized = self._normalize_log_line(text)
                    if log_mode != "No Logs" and self._should_log_line(normalized):
                        output_queue.put(normalized)
        except Exception as exc:
            output_queue.put(f"Stream error: {exc}")

    def _drain_output_queue(self, output_queue):
        lines = []
        while len(lines) < 1000:
            try:
                lines.append(output_queue.get_nowait())
            except queue.Empty:
                break
        if lines:
            self.log_widget.insert("end", "\n".join(lines) + "\n")
            self.log_widget.see("end")
            self.update_idletasks()

    def _poll_process(self, process, output_thread, output_queue, final_message):
        self._drain_output_queue(output_queue)
        if process.poll() is None or output_thread.is_alive() or not output_queue.empty():
            self.after(100, lambda: self._poll_process(process, output_thread, output_queue, final_message))
            return

        code = process.returncode
        aborted = self.operation_aborted
        self.active_process = None
        self.process_paused = False
        self.operation_aborted = False
        self.pause_button.configure(text="Pause")
        self._set_operation_controls(False)
        self._log(f"Operation aborted with exit code {code}." if aborted else final_message.format(code=code))
        if self.pending_jobs and not aborted:
            self.after_idle(self._run_next_job)
        else:
            self._log_job_batch_report()
            self.pending_jobs = []
            if aborted or not is_successful_robocopy_exit_code(code):
                play_error_sound()
            else:
                play_completion_chime()

    def _log_job_batch_report(self):
        if not self.batch_job_names:
            return
        count = len(self.batch_job_names)
        self._log(f"Backup report: {count} JOB{'s' if count != 1 else ''} run.", "job_report")
        for name in self.batch_job_names:
            self._log(f"  JOB profile: {name}", "job_report")
        self.batch_job_names = []

    def refresh_jobs_list(self):
        self.job_tree.delete(*self.job_tree.get_children())
        groups = {}
        for index, job in enumerate(self.jobs):
            group = str(job.get("group", "")).strip()
            groups.setdefault(group, []).append((index, job))
        all_jobs = self.job_tree.insert("", "end", text="All Jobs", values=("all", ""), open=True)
        for index, job in enumerate(self.jobs):
            mode = str(job.get("mode", "backup")).lower()
            self.job_tree.insert(all_jobs, "end", text=job.get("name", "Untitled"), values=("job", index), tags=(mode,))
        for group, members in groups.items():
            if not group:
                continue
            parent = self.job_tree.insert("", "end", text=group, values=("group", group), open=True)
            for index, job in members:
                mode = str(job.get("mode", "backup")).lower()
                self.job_tree.insert(parent, "end", text=job.get("name", "Untitled"), values=("job", index), tags=(mode,))
        children = self.job_tree.get_children()
        if children:
            first_job = self.job_tree.get_children(children[0])
            self.job_tree.selection_set(first_job[0] if first_job else children[0])

    def _selected_sidebar_item(self):
        selected = self.job_tree.selection()
        if not selected:
            return None
        kind, value = self.job_tree.item(selected[0]).get("values", (None, None))
        return kind, value

    def _set_profile_modified(self, modified):
        self._profile_modified = modified
        if hasattr(self, "save_changes_button"):
            save_color = "#ffff00" if modified else "#ffffff"
            self.save_changes_button.configure(
                fg=save_color,
                activeforeground=save_color,
                state=tk.NORMAL if modified else tk.DISABLED,
            )
        if hasattr(self, "edit_menu"):
            menu_state = tk.NORMAL if modified else tk.DISABLED
            self.edit_menu.entryconfigure("Save Changes", state=menu_state)
            self.edit_menu.entryconfigure("Forget Changes", state=menu_state)
        if hasattr(self, "forget_changes_button"):
            forget_color = "#ffa500" if modified else "#ffffff"
            self.forget_changes_button.configure(
                fg=forget_color,
                activeforeground=forget_color,
                state=tk.NORMAL if modified else tk.DISABLED,
            )

    def _profile_field_changed(self, *_args):
        if self._loading_job:
            return
        selected = self._selected_sidebar_item()
        if selected and selected[0] == "job":
            self._set_profile_modified(True)

    def _select_sidebar_item(self, _event=None):
        selected = self._selected_sidebar_item()
        if not selected:
            return
        if selected[0] == "job":
            self.load_selected_job(int(selected[1]))
        else:
            self._set_profile_modified(False)
            self.source_var.set("")
            self.destination_var.set("")
            self.refresh_folder_views()
            if selected[0] == "group":
                job_count = len(jobs_for_sidebar_selection(self.jobs, "group", selected[1]))
                self.job_profile_label.config(
                    text=f"A Group Profile is selected with {job_count} Jobs"
                )
            elif selected[0] == "all":
                self.job_profile_label.config(text=f"All Jobs is selected with {len(self.jobs)} Jobs")
            else:
                self._update_job_profile_label()

    def _show_job_context_menu(self, event):
        item_id = self.job_tree.identify_row(event.y)
        if not item_id:
            return
        self.job_tree.selection_set(item_id)
        selected = self._selected_sidebar_item()
        if not selected:
            return
        menu = tk.Menu(self, tearoff=0)
        menu.add_command(
            label="Rename",
            command=lambda: self.rename_sidebar_item(selected[0], selected[1]),
            state=tk.DISABLED if selected[0] == "all" else tk.NORMAL,
        )
        if selected[0] == "job":
            parent_id = self.job_tree.parent(item_id)
            parent_kind = self.job_tree.item(parent_id).get("values", (None, None))[0]
            menu.add_command(label="Duplicate", command=lambda: self.duplicate_job(int(selected[1])))
            menu.add_command(
                label="Add to Group",
                command=lambda: self.add_job_to_group(int(selected[1]), event.x_root, event.y_root),
            )
            menu.add_command(
                label="Remove from Group",
                command=lambda: self.remove_job_from_group(int(selected[1])),
                state=tk.DISABLED if parent_kind == "all" else tk.NORMAL,
            )
        elif selected[0] == "group":
            menu.add_command(label="Delete Group", command=lambda: self.delete_group(selected[1]))
        menu.tk_popup(event.x_root, event.y_root)

    def _load_initial_job(self):
        selected = self._selected_sidebar_item()
        if selected and selected[0] == "job":
            self.load_selected_job(int(selected[1]))

    def save_current_job(self):
        if not has_valid_folder_pair(self.source_var.get(), self.destination_var.get()):
            messagebox.showerror("Missing folders", "Please choose both a source and destination folder before saving a job.")
            return
        name = simpledialog.askstring(
            "Save Job",
            "Job name:",
            initialvalue=self.job_name.get().strip() or "New Job",
            parent=self,
        )
        if not name or not name.strip():
            return
        name = name.strip()
        self.job_name.set(name)
        job = {
            "name": name,
            "source": self.source_var.get(),
            "destination": self.destination_var.get(),
            "mode": self.mode_var.get(),
            "include_subfolders": self.include_subfolders_var.get(),
        }
        existing = [item for item in self.jobs if item.get("name") != name]
        old_job = next((item for item in self.jobs if item.get("name") == name), None)
        if old_job and old_job.get("group"):
            job["group"] = old_job["group"]
        existing.append(job)
        self.jobs = existing
        save_jobs(self.jobs, job_file_path())
        self._set_profile_modified(False)
        self.refresh_jobs_list()
        self._log(f"Saved job: {name}")

    def save_job_changes(self):
        selected = self._selected_sidebar_item()
        if not selected or selected[0] != "job":
            messagebox.showwarning("No job selected", "Select a job before saving changes.")
            return
        if not has_valid_folder_pair(self.source_var.get(), self.destination_var.get()):
            messagebox.showerror("Missing folders", "Please choose both a source and destination folder before saving changes.")
            return
        index = int(selected[1])
        job = self.jobs[index]
        job.update(
            source=self.source_var.get(),
            destination=self.destination_var.get(),
            mode=self.mode_var.get(),
            include_subfolders=self.include_subfolders_var.get(),
        )
        save_jobs(self.jobs, job_file_path())
        self._set_profile_modified(False)
        self.refresh_jobs_list()
        self._log(f"Saved changes to job: {job.get('name', 'Untitled')}")

    def forget_changes(self):
        self.jobs = load_jobs(job_file_path())
        self._set_profile_modified(False)
        self.refresh_jobs_list()
        self._load_initial_job()
        self._log("Forgot unsaved changes and reloaded JOB profiles.")

    def _mode_changed(self):
        selected = self._selected_sidebar_item()
        if selected and selected[0] == "job":
            index = int(selected[1])
            mode = self.mode_var.get()
            self.jobs[index]["mode"] = mode
            self._update_sidebar_job_mode(index, mode)
            self._set_profile_modified(True)

    def _update_sidebar_job_mode(self, index, mode):
        for item_id in self.job_tree.get_children(""):
            descendants = self.job_tree.get_children(item_id)
            for child_id in descendants:
                values = self.job_tree.item(child_id).get("values", ())
                if len(values) >= 2 and values[0] == "job" and int(values[1]) == index:
                    self.job_tree.item(child_id, tags=(mode,))

    def delete_current_job(self):
        selected = self._selected_sidebar_item()
        if selected and selected[0] == "group":
            return
        if not selected or selected[0] != "job":
            messagebox.showwarning("No job selected", "Select a job before deleting.")
            return
        index = int(selected[1])
        job = self.jobs[index]
        if not messagebox.askyesno("Delete Job", f"Delete job '{job.get('name', 'Untitled')}'?", parent=self):
            return
        self.jobs.pop(index)
        save_jobs(self.jobs, job_file_path())
        self.refresh_jobs_list()
        self._log(f"Deleted job: {job.get('name', 'Untitled')}")

    def load_selected_job(self, index=None):
        if index is None:
            selected = self._selected_sidebar_item()
            index = int(selected[1]) if selected and selected[0] == "job" else -1
        if index < 0:
            messagebox.showwarning("No job selected", "Select a job before loading.")
            return
        job = self.jobs[index]
        self._loading_job = True
        try:
            self.job_name.set(job.get("name", ""))
            self.source_var.set(job.get("source", ""))
            self.destination_var.set(job.get("destination", ""))
            self.include_subfolders_var.set(job.get("include_subfolders", True))
            saved_mode = job.get("mode", "backup")
            self.mode_var.set("move" if saved_mode == "transfer" else saved_mode)
            self.refresh_folder_views()
        finally:
            self._loading_job = False
        self._set_profile_modified(False)
        self._log(f"Loaded job: {job.get('name', 'Unnamed')}")

    def add_job_to_group(self, index, x_root=None, y_root=None):
        job = self.jobs[index]
        group = self._select_group_for_job(job.get("group", ""), x_root, y_root)
        if not group or not group.strip():
            return
        job["group"] = group.strip()
        save_jobs(self.jobs, job_file_path())
        self.refresh_jobs_list()
        self._log(f"Added job '{job.get('name', 'Untitled')}' to group '{job['group']}'.")

    def duplicate_job(self, index):
        source_job = self.jobs[index]
        source_name = str(source_job.get("name", "Untitled"))
        duplicate_name = f"{source_name} Copy"
        suffix = 2
        existing_names = {str(job.get("name", "")).strip().casefold() for job in self.jobs}
        while duplicate_name.strip().casefold() in existing_names:
            duplicate_name = f"{source_name} Copy {suffix}"
            suffix += 1
        new_name = simpledialog.askstring("Duplicate Job", "New job name:", initialvalue=duplicate_name, parent=self)
        if not new_name or not new_name.strip():
            return
        duplicated_job = source_job.copy()
        duplicated_job["name"] = new_name.strip()
        self.jobs.insert(index + 1, duplicated_job)
        save_jobs(self.jobs, job_file_path())
        self.refresh_jobs_list()
        self._log(f"Duplicated job '{source_name}' as '{duplicated_job['name']}'.")

    def _select_group_for_job(self, current_group="", x_root=None, y_root=None):
        groups = sorted({str(job.get("group", "")).strip() for job in self.jobs if str(job.get("group", "")).strip()})
        create_new_group = "Create New Group"
        choices = groups + [create_new_group]
        dialog = tk.Toplevel(self)
        dialog.title("Add to Group")
        dialog.configure(bg="#111827")
        dialog.resizable(False, False)
        dialog.transient(self)

        tk.Label(dialog, text="Choose a group:", bg="#111827", fg="#e2e8f0", font=("Segoe UI", 10, "bold")).pack(
            padx=18, pady=(16, 6), anchor="w"
        )
        group_var = tk.StringVar(value=current_group if current_group in groups else create_new_group)
        group_menu = ttk.Combobox(dialog, textvariable=group_var, values=choices, state="readonly", width=30)
        group_menu.pack(padx=18, pady=(0, 14))

        result = {"group": None}

        def confirm():
            selected_group = group_var.get()
            if selected_group == create_new_group:
                selected_group = simpledialog.askstring("Create New Group", "Group name:", parent=self)
            result["group"] = selected_group
            dialog.destroy()

        buttons = tk.Frame(dialog, bg="#111827")
        buttons.pack(fill="x", padx=18, pady=(0, 16))
        tk.Button(
            buttons,
            text="Cancel",
            command=dialog.destroy,
            bg="#1f2937",
            fg="#e2e8f0",
            activebackground="#334155",
            activeforeground="#ffffff",
            relief="flat",
            font=("Segoe UI", 10, "bold"),
            padx=12,
        ).pack(side="right")
        tk.Button(
            buttons,
            text="Add",
            command=confirm,
            bg="#38bdf8",
            fg="#0f172a",
            activebackground="#7dd3fc",
            relief="flat",
            font=("Segoe UI", 10, "bold"),
            padx=12,
        ).pack(side="right", padx=(0, 8))
        dialog.protocol("WM_DELETE_WINDOW", dialog.destroy)
        dialog.update_idletasks()
        if x_root is not None and y_root is not None:
            dialog.geometry(f"+{int(x_root)}+{int(y_root)}")
        dialog.grab_set()
        self.wait_window(dialog)
        return result["group"]

    def remove_job_from_group(self, index):
        job = self.jobs[index]
        group = str(job.get("group", "")).strip()
        if not group:
            return
        job.pop("group", None)
        save_jobs(self.jobs, job_file_path())
        self.refresh_jobs_list()
        self._log(f"Removed job '{job.get('name', 'Untitled')}' from group '{group}'.")

    def rename_sidebar_item(self, kind, value):
        if kind == "all":
            return
        if kind == "job":
            index = int(value)
            job = self.jobs[index]
            old_name = job.get("name", "Untitled")
            new_name = simpledialog.askstring("Rename Job", "New name:", initialvalue=old_name, parent=self)
            if not new_name or not new_name.strip():
                return
            new_name = new_name.strip()
            job["name"] = new_name
            if self._selected_sidebar_item() == ("job", value):
                self.job_name.set(new_name)
            log_message = f"Renamed job '{old_name}' to '{new_name}'."
        elif kind == "group":
            old_name = str(value)
            new_name = simpledialog.askstring("Rename Group", "New name:", initialvalue=old_name, parent=self)
            if not new_name or not new_name.strip():
                return
            new_name = new_name.strip()
            for job in self.jobs:
                if str(job.get("group", "")).strip() == old_name:
                    job["group"] = new_name
            log_message = f"Renamed group '{old_name}' to '{new_name}'."
        else:
            return
        save_jobs(self.jobs, job_file_path())
        self.refresh_jobs_list()
        self._log(log_message)

    def delete_group(self, group_name):
        group_name = str(group_name).strip()
        if not group_name:
            return
        if not messagebox.askyesno(
            "Delete Group",
            f"Delete group '{group_name}'? Jobs in this group will be moved to All Jobs.",
            parent=self,
        ):
            return
        for job in self.jobs:
            if str(job.get("group", "")).strip() == group_name:
                job.pop("group", None)
        save_jobs(self.jobs, job_file_path())
        self.refresh_jobs_list()
        self._log(f"Deleted group '{group_name}'.")

    def _jobs_for_selection(self):
        selected = self._selected_sidebar_item()
        if not selected:
            return []
        return jobs_for_sidebar_selection(self.jobs, selected[0], selected[1])

    def _run_next_job(self):
        if not self.pending_jobs:
            return
        job = self.pending_jobs.pop(0)
        self.batch_job_names.append(str(job.get("name", "Untitled")))
        self.source_var.set(job.get("source", ""))
        self.destination_var.set(job.get("destination", ""))
        self.include_subfolders_var.set(job.get("include_subfolders", True))
        self.mode_var.set("move" if job.get("mode", "backup") == "transfer" else job.get("mode", "backup"))
        self.job_name.set(job.get("name", ""))
        self.refresh_folder_views()
        self.run_backup(from_queue=True)

    def run_backup(self, from_queue=False):
        selected = self._selected_sidebar_item()
        if selected and selected[0] == "all" and not from_queue:
            messagebox.showinfo("Select a job or group", "Select an individual job or a group before running a backup.", parent=self)
            return
        selected_jobs = self._jobs_for_selection()
        if selected_jobs and not from_queue:
            self.pending_jobs = list(selected_jobs)
            self.batch_job_names = []
            self._run_next_job()
            return
        self.refresh_folder_views()

        source = self.source_var.get().strip()
        destination = self.destination_var.get().strip()
        if not has_valid_folder_pair(source, destination):
            play_error_sound()
            messagebox.showerror("Missing folders", "Please choose a source and destination folder.")
            return

        mode = self.mode_var.get()
        log_mode = self.log_mode_var.get()
        verbose = log_mode == "Verbose"

        if mode == "move":
            confirmed = messagebox.askyesno(
                "Confirm Move Operation",
                "Move will remove each file from the source after it is copied successfully.\n\nDo you want to continue?",
                parent=self,
            )
            if not confirmed:
                self._log("Move operation cancelled.")
                return

        command = build_robocopy_command(
            source,
            destination,
            mode,
            verbose=verbose,
            include_subfolders=self.include_subfolders_var.get(),
        )
        self._log(f"Running: {' '.join(command)}")

        try:
            creationflags = 0
            if os.name == "nt":
                creationflags = subprocess.CREATE_NO_WINDOW

            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                shell=False,
                creationflags=creationflags,
            )
            output_queue = queue.Queue()
            output_thread = threading.Thread(target=self._stream_process_output, args=(process, output_queue, log_mode), daemon=True)
            self.active_process = process
            self.process_paused = False
            self.operation_aborted = False
            self._set_operation_controls(True)
            output_thread.start()
            self.after(100, lambda: self._poll_process(process, output_thread, output_queue, "Operation complete with exit code {code}."))
        except FileNotFoundError:
            self._set_operation_controls(False)
            self._log("Robocopy was not found. This app requires a Windows system with ROBOCOPY available.")
            play_error_sound()
            messagebox.showerror("ROBOCOPY missing", "Robocopy is not available on this system.")
        except Exception as exc:
            self._set_operation_controls(False)
            self._log(f"Unexpected error: {exc}")
            play_error_sound()
            messagebox.showerror("Backup Failed", str(exc))


def main():
    app = EZeeBackupApp()
    splash = SplashScreen(app)
    app.wait_window(splash)
    app.mainloop()


if __name__ == "__main__":
    main()
