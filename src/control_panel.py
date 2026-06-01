from __future__ import annotations

import os
import subprocess
import threading
from dataclasses import dataclass
from pathlib import Path
from tkinter import END, LEFT, RIGHT, VERTICAL, W, Y, BooleanVar, StringVar, TclError, Tk
from tkinter import filedialog, messagebox, ttk

from camera_registry import enabled_cameras, load_cameras, target_modes_summary
from venv_guard import enforce_venv_python


ROOT_DIR = Path(__file__).resolve().parents[1]
ENV_PATH = ROOT_DIR / "camera.env.bat"
PYTHON_PATH = ROOT_DIR / ".venv" / "Scripts" / "python.exe"
WINDOW_TITLE = "MTImou Control Panel"
CREATE_NEW_CONSOLE = getattr(subprocess, "CREATE_NEW_CONSOLE", 0)


def parse_env_bat(path: Path) -> tuple[list[str], dict[str, str]]:
    lines: list[str] = []
    values: dict[str, str] = {}
    if path.exists():
        lines = path.read_text(encoding="ascii", errors="ignore").splitlines()
        for line in lines:
            stripped = line.strip()
            if stripped.lower().startswith("set ") and "=" in stripped:
                payload = stripped[4:]
                key, value = payload.split("=", 1)
                values[key.strip()] = value.strip()
    return lines, values


def write_env_bat(path: Path, original_lines: list[str], updates: dict[str, str]) -> None:
    remaining = dict(updates)
    new_lines: list[str] = []
    for line in original_lines:
        stripped = line.strip()
        if stripped.lower().startswith("set ") and "=" in stripped:
            payload = stripped[4:]
            key, _ = payload.split("=", 1)
            key = key.strip()
            if key in remaining:
                new_lines.append(f"set {key}={remaining.pop(key)}")
                continue
        new_lines.append(line)
    if remaining:
        if new_lines and new_lines[-1].strip():
            new_lines.append("")
        for key, value in remaining.items():
            new_lines.append(f"set {key}={value}")
    path.write_text("\r\n".join(new_lines) + "\r\n", encoding="ascii")


def launch_batch(batch_name: str, args: list[str] | None = None) -> None:
    cmd = ["cmd.exe", "/c", str(ROOT_DIR / batch_name)]
    if args:
        cmd.extend(args)
    subprocess.Popen(cmd, cwd=str(ROOT_DIR), creationflags=CREATE_NEW_CONSOLE)


@dataclass(slots=True)
class CameraRow:
    camera_id: str
    label: str


class ControlPanel:
    def __init__(self, root: Tk) -> None:
        self.root = root
        self.root.title(WINDOW_TITLE)
        self.root.geometry("980x720")
        self.root.minsize(900, 640)

        self.env_lines, self.env_values = parse_env_bat(ENV_PATH)
        self.mode_var = StringVar(value=self.env_values.get("IMOU_TARGET_MODE", "auto") or "auto")
        self.ddns_var = StringVar(value=self.env_values.get("IMOU_DDNS_HOST", ""))
        self.user_var = StringVar(value=self.env_values.get("IMOU_CAMERA_USERNAME", "admin") or "admin")
        self.pass1_var = StringVar(value=self.env_values.get("IMOU_CAMERA_PASSWORD", ""))
        self.pass2_var = StringVar(value=self.env_values.get("IMOU_CAMERA2_PASSWORD", ""))
        self.status_var = StringVar(value="Ready")
        self.open_log_after_check = BooleanVar(value=True)
        self.camera_rows = self._load_camera_rows()

        self._build_ui()
        self._refresh_camera_list()

    def _load_camera_rows(self) -> list[CameraRow]:
        self._apply_env_values_to_process()
        rows: list[CameraRow] = []
        for camera in load_cameras():
            rows.append(
                CameraRow(
                    camera_id=camera.camera_id,
                    label=f"{camera.camera_id} | {camera.name} | {' ; '.join(target_modes_summary(camera))}",
                )
            )
        return rows

    def _build_ui(self) -> None:
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except TclError:
            pass
        style.configure("Title.TLabel", font=("Segoe UI", 18, "bold"))
        style.configure("Section.TLabelframe.Label", font=("Segoe UI", 11, "bold"))
        style.configure("Status.TLabel", font=("Consolas", 10))

        main = ttk.Frame(self.root, padding=16)
        main.pack(fill="both", expand=True)

        ttk.Label(main, text="MTImou Control Panel", style="Title.TLabel").pack(anchor=W)
        ttk.Label(
            main,
            text="Launch cameras, choose target mode, update local settings, and validate the system from one place.",
        ).pack(anchor=W, pady=(4, 12))

        top = ttk.Frame(main)
        top.pack(fill="x", expand=False)

        left = ttk.Frame(top)
        left.pack(side=LEFT, fill="both", expand=True)
        right = ttk.Frame(top)
        right.pack(side=RIGHT, fill="y", expand=False, padx=(16, 0))

        self._build_camera_panel(left)
        self._build_settings_panel(left)
        self._build_actions_panel(right)
        self._build_output_panel(main)

    def _build_camera_panel(self, parent: ttk.Frame) -> None:
        frame = ttk.LabelFrame(parent, text="Cameras", style="Section.TLabelframe", padding=12)
        frame.pack(fill="both", expand=True)

        self.camera_list = tk_list = __import__("tkinter").Listbox(frame, height=8, exportselection=False)
        tk_list.pack(side=LEFT, fill="both", expand=True)
        scroll = ttk.Scrollbar(frame, orient=VERTICAL, command=tk_list.yview)
        scroll.pack(side=RIGHT, fill=Y)
        tk_list.configure(yscrollcommand=scroll.set)
        if self.camera_rows:
            tk_list.selection_set(0)

    def _build_settings_panel(self, parent: ttk.Frame) -> None:
        frame = ttk.LabelFrame(parent, text="Operator Settings", style="Section.TLabelframe", padding=12)
        frame.pack(fill="x", expand=False, pady=(16, 0))

        self._labeled_entry(frame, "Target mode", self.mode_var, row=0, values=["auto", "lan", "ddns", "public"], readonly=True)
        self._labeled_entry(frame, "Shared DDNS host", self.ddns_var, row=1)
        self._labeled_entry(frame, "Camera username", self.user_var, row=2)
        self._labeled_entry(frame, "Camera 1 password", self.pass1_var, row=3, show="*")
        self._labeled_entry(frame, "Camera 2 password", self.pass2_var, row=4, show="*")

        buttons = ttk.Frame(frame)
        buttons.grid(row=5, column=0, columnspan=2, sticky="w", pady=(10, 0))
        ttk.Button(buttons, text="Save Settings", command=self.save_settings).pack(side=LEFT)
        ttk.Button(buttons, text="Reload", command=self.reload_settings).pack(side=LEFT, padx=(8, 0))

        for i in range(2):
            frame.columnconfigure(i, weight=1 if i == 1 else 0)

    def _labeled_entry(
        self,
        parent: ttk.Frame,
        label: str,
        variable: StringVar,
        row: int,
        values: list[str] | None = None,
        readonly: bool = False,
        show: str | None = None,
    ) -> None:
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", padx=(0, 10), pady=4)
        if values is not None:
            widget = ttk.Combobox(parent, textvariable=variable, values=values, state="readonly" if readonly else "normal")
        else:
            widget = ttk.Entry(parent, textvariable=variable, show=show or "")
        widget.grid(row=row, column=1, sticky="ew", pady=4)

    def _build_actions_panel(self, parent: ttk.Frame) -> None:
        frame = ttk.LabelFrame(parent, text="Actions", style="Section.TLabelframe", padding=12)
        frame.pack(fill="y", expand=False)

        ttk.Button(frame, text="View Selected Camera", command=self.launch_selected_camera).pack(fill="x")
        ttk.Button(frame, text="View All Enabled Cameras", command=self.launch_all_cameras).pack(fill="x", pady=(8, 0))
        ttk.Button(frame, text="Run Health Check", command=self.run_health_check).pack(fill="x", pady=(8, 0))
        ttk.Button(frame, text="Open Logs Folder", command=self.open_logs_folder).pack(fill="x", pady=(8, 0))
        ttk.Button(frame, text="Open Project README", command=self.open_readme).pack(fill="x", pady=(8, 0))
        ttk.Checkbutton(frame, text="Open log after health check", variable=self.open_log_after_check).pack(anchor=W, pady=(12, 0))

    def _build_output_panel(self, parent: ttk.Frame) -> None:
        frame = ttk.LabelFrame(parent, text="Output", style="Section.TLabelframe", padding=12)
        frame.pack(fill="both", expand=True, pady=(16, 0))
        self.output = __import__("tkinter").Text(frame, height=16, wrap="word")
        self.output.pack(fill="both", expand=True)
        ttk.Label(parent, textvariable=self.status_var, style="Status.TLabel").pack(anchor=W, pady=(8, 0))

    def _refresh_camera_list(self) -> None:
        self.camera_rows = self._load_camera_rows()
        self.camera_list.delete(0, END)
        for row in self.camera_rows:
            self.camera_list.insert(END, row.label)
        if self.camera_rows:
            self.camera_list.selection_clear(0, END)
            self.camera_list.selection_set(0)

    def append_output(self, text: str) -> None:
        self.output.insert(END, text.rstrip() + "\n")
        self.output.see(END)

    def _apply_env_values_to_process(self) -> None:
        for key, value in self.env_values.items():
            if key.startswith("IMOU_"):
                os.environ[key] = value

    def save_settings(self) -> None:
        updates = {
            "IMOU_TARGET_MODE": self.mode_var.get().strip() or "auto",
            "IMOU_DDNS_HOST": self.ddns_var.get().strip(),
            "IMOU_CAMERA_USERNAME": self.user_var.get().strip() or "admin",
            "IMOU_CAMERA_PASSWORD": self.pass1_var.get().strip(),
            "IMOU_CAMERA2_PASSWORD": self.pass2_var.get().strip(),
        }
        if not ENV_PATH.exists():
            self.env_lines = [
                "@echo off",
                "REM Local operator settings for MTImou",
                "",
            ]
        write_env_bat(ENV_PATH, self.env_lines, updates)
        self.env_lines, self.env_values = parse_env_bat(ENV_PATH)
        self._apply_env_values_to_process()
        self.status_var.set(f"Saved settings to {ENV_PATH}")
        self.append_output(f"[INFO] Saved settings to {ENV_PATH}")
        self._refresh_camera_list()

    def reload_settings(self) -> None:
        self.env_lines, self.env_values = parse_env_bat(ENV_PATH)
        self._apply_env_values_to_process()
        self.mode_var.set(self.env_values.get("IMOU_TARGET_MODE", "auto") or "auto")
        self.ddns_var.set(self.env_values.get("IMOU_DDNS_HOST", ""))
        self.user_var.set(self.env_values.get("IMOU_CAMERA_USERNAME", "admin") or "admin")
        self.pass1_var.set(self.env_values.get("IMOU_CAMERA_PASSWORD", ""))
        self.pass2_var.set(self.env_values.get("IMOU_CAMERA2_PASSWORD", ""))
        self._refresh_camera_list()
        self.status_var.set("Reloaded settings")
        self.append_output("[INFO] Reloaded settings from camera.env.bat")

    def selected_camera_id(self) -> str | None:
        selected = self.camera_list.curselection()
        if not selected:
            return None
        return self.camera_rows[selected[0]].camera_id

    def launch_selected_camera(self) -> None:
        camera_id = self.selected_camera_id()
        if not camera_id:
            messagebox.showwarning(WINDOW_TITLE, "Please select a camera first.")
            return
        self.save_settings()
        launch_batch("run_camera_stable.bat", [camera_id])
        self.status_var.set(f"Launched camera viewer for {camera_id}")
        self.append_output(f"[INFO] Launched run_camera_stable.bat {camera_id}")

    def launch_all_cameras(self) -> None:
        self.save_settings()
        ids = [camera.camera_id for camera in enabled_cameras()]
        if not ids:
            messagebox.showwarning(WINDOW_TITLE, "No enabled cameras found.")
            return
        launch_batch("run_multi_camera_stable.bat", ids)
        self.status_var.set("Launched multi-camera viewer")
        self.append_output(f"[INFO] Launched run_multi_camera_stable.bat {' '.join(ids)}")

    def run_health_check(self) -> None:
        self.save_settings()
        self.status_var.set("Running health check...")
        self.append_output("[INFO] Running system health check...")

        def worker() -> None:
            env = os.environ.copy()
            process = subprocess.run(
                [str(PYTHON_PATH), str(ROOT_DIR / "src" / "system_health_check.py")],
                cwd=str(ROOT_DIR),
                capture_output=True,
                text=True,
                check=False,
                env=env,
            )
            output = (process.stdout or "") + (process.stderr or "")
            self.root.after(0, lambda: self._finish_health_check(process.returncode, output))

        threading.Thread(target=worker, daemon=True).start()

    def _finish_health_check(self, returncode: int, output: str) -> None:
        self.append_output(output.strip() or "[WARN] No output from health check")
        if returncode == 0:
            self.status_var.set("Health check passed")
        else:
            self.status_var.set(f"Health check failed (exit {returncode})")
        if self.open_log_after_check.get():
            self.open_logs_folder()

    def open_logs_folder(self) -> None:
        os.startfile(str(ROOT_DIR / "logs"))

    def open_readme(self) -> None:
        os.startfile(str(ROOT_DIR / "README.md"))


def main() -> int:
    enforce_venv_python()
    root = Tk()
    ControlPanel(root)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
