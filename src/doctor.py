from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path

from mtimou_v2.registry import default_password_env_names, load_cameras, load_raw_config
from mtimou_v2.settings_store import BatchEnvSettingsStore
from venv_guard import enforce_venv_python, expected_python_path


@dataclass(slots=True)
class CheckResult:
    name: str
    status: str
    detail: str


class Doctor:
    def __init__(self, root_dir: Path) -> None:
        self.root_dir = root_dir
        self.results: list[CheckResult] = []

    def run(self) -> int:
        self._check_python()
        self._check_core_files()
        self._check_dependencies()
        self._check_camera_registry()
        self._check_camera_env()
        self._check_password_coverage()
        self._check_ui_import()
        self._check_logs_directory()
        return self._print_summary()

    def _add(self, name: str, status: str, detail: str) -> None:
        self.results.append(CheckResult(name=name, status=status, detail=detail))

    def _check_python(self) -> None:
        expected = expected_python_path()
        if Path(sys.executable).resolve() != expected.resolve():
            self._add("python", "FAIL", f"Expected {expected}, got {sys.executable}")
            return
        self._add("python", "OK", sys.executable)

    def _check_core_files(self) -> None:
        required = [
            "README.md",
            "requirements.txt",
            "run_control_panel.bat",
            "run_camera_stable.bat",
            "run_multi_camera_stable.bat",
            "run_system_health_check.bat",
            "cameras.json",
            "camera.env.bat.example",
        ]
        missing = [path for path in required if not (self.root_dir / path).exists()]
        if missing:
            self._add("core-files", "FAIL", f"Missing: {', '.join(missing)}")
            return
        self._add("core-files", "OK", "All onboarding files are present")

    def _check_dependencies(self) -> None:
        modules = [
            ("PySide6", "PySide6"),
            ("opencv-python", "cv2"),
            ("numpy", "numpy"),
            ("cryptography", "cryptography"),
            ("xmltodict", "xmltodict"),
        ]
        missing: list[str] = []
        for label, module_name in modules:
            try:
                __import__(module_name)
            except Exception as exc:  # pragma: no cover - defensive diagnostics
                missing.append(f"{label} ({exc})")
        if missing:
            self._add("dependencies", "FAIL", f"Import failed: {'; '.join(missing)}")
            return
        self._add("dependencies", "OK", "Pinned runtime dependencies import successfully")

    def _check_camera_registry(self) -> None:
        config_path = self.root_dir / "cameras.json"
        try:
            raw = json.loads(config_path.read_text(encoding="utf-8"))
            cameras = load_cameras()
        except Exception as exc:
            self._add("camera-registry", "FAIL", f"Invalid cameras.json: {exc}")
            return
        if not isinstance(raw, dict) or not isinstance(raw.get("cameras"), list):
            self._add("camera-registry", "FAIL", "cameras.json must contain a top-level cameras array")
            return
        if not cameras:
            self._add("camera-registry", "WARN", "No cameras configured yet")
            return
        self._add("camera-registry", "OK", f"Loaded {len(cameras)} camera(s)")

    def _check_camera_env(self) -> None:
        env_path = self.root_dir / "camera.env.bat"
        example_path = self.root_dir / "camera.env.bat.example"
        if not env_path.exists():
            self._add(
                "camera-env",
                "WARN",
                f"{env_path.name} is missing. Run setup_windows.bat or copy {example_path.name}.",
            )
            return

        try:
            document = BatchEnvSettingsStore(env_path).load_document()
        except Exception as exc:
            self._add("camera-env", "FAIL", f"Could not parse {env_path.name}: {exc}")
            return

        size = env_path.stat().st_size
        if size > 256 * 1024:
            self._add("camera-env", "FAIL", f"{env_path.name} is unexpectedly large ({size} bytes)")
            return

        target_mode = document.values.get("IMOU_TARGET_MODE", "auto") or "auto"
        username = document.values.get("IMOU_CAMERA_USERNAME", "")
        if any("YOUR_" in value for value in document.values.values()):
            self._add("camera-env", "WARN", f"{env_path.name} still contains placeholder values")
            return
        detail = f"size={size} bytes, target_mode={target_mode}, username={'set' if username else 'missing'}"
        self._add("camera-env", "OK", detail)

    def _check_password_coverage(self) -> None:
        env_path = self.root_dir / "camera.env.bat"
        if not env_path.exists():
            self._add("passwords", "WARN", "camera.env.bat missing, password coverage not checked")
            return

        values = BatchEnvSettingsStore(env_path).load_document().values
        raw = load_raw_config()
        missing: list[str] = []
        for item in raw.get("cameras", []):
            camera_id = str(item.get("id", "")).strip()
            if not camera_id:
                continue
            configured = False
            env_names = [str(name).strip() for name in item.get("password_envs", []) if str(name).strip()]
            env_names.extend(default_password_env_names(camera_id))
            for env_name in env_names:
                if values.get(env_name, "").strip():
                    configured = True
                    break
            if not configured:
                missing.append(camera_id)
        if missing:
            self._add("passwords", "WARN", f"Missing password env for: {', '.join(missing)}")
            return
        self._add("passwords", "OK", "Every configured camera has at least one password source")

    def _check_ui_import(self) -> None:
        try:
            from control_panel_app.window import ControlPanelWindow  # noqa: F401
            from mtimou_v2.viewmodels.control_panel_vm import ControlPanelViewModel  # noqa: F401
        except Exception as exc:
            self._add("ui-import", "FAIL", f"Control panel import failed: {exc}")
            return
        self._add("ui-import", "OK", "Control panel modules import successfully")

    def _check_logs_directory(self) -> None:
        logs_dir = self.root_dir / "logs"
        try:
            logs_dir.mkdir(exist_ok=True)
            probe = logs_dir / ".doctor_write_test"
            probe.write_text("ok", encoding="ascii")
            probe.unlink()
        except Exception as exc:
            self._add("logs-dir", "FAIL", f"Cannot write logs directory: {exc}")
            return
        self._add("logs-dir", "OK", str(logs_dir))

    def _print_summary(self) -> int:
        width = max(len(item.name) for item in self.results) if self.results else 10
        failures = 0
        warnings = 0
        for item in self.results:
            print(f"[{item.status:<4}] {item.name:<{width}}  {item.detail}")
            if item.status == "FAIL":
                failures += 1
            elif item.status == "WARN":
                warnings += 1
        print()
        print(f"[SUMMARY] ok={sum(1 for item in self.results if item.status == 'OK')} warn={warnings} fail={failures}")
        return 1 if failures else 0


def main() -> int:
    enforce_venv_python()
    root_dir = Path(__file__).resolve().parents[1]
    doctor = Doctor(root_dir)
    return doctor.run()


if __name__ == "__main__":
    raise SystemExit(main())
