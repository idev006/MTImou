from __future__ import annotations

import os
import subprocess
from pathlib import Path


CREATE_NEW_CONSOLE = getattr(subprocess, "CREATE_NEW_CONSOLE", 0)


class OperatorServices:
    def __init__(self, root_dir: Path) -> None:
        self.root_dir = root_dir

    def launch_batch(self, batch_name: str, args: list[str] | None = None) -> None:
        cmd = ["cmd.exe", "/c", str(self.root_dir / batch_name)]
        if args:
            cmd.extend(args)
        process_env = dict(os.environ)
        process_env["PYTHONUTF8"] = "1"
        process_env["PYTHONIOENCODING"] = "utf-8"
        subprocess.Popen(cmd, cwd=str(self.root_dir), env=process_env, creationflags=CREATE_NEW_CONSOLE)

    def open_logs_folder(self) -> None:
        os.startfile(str(self.root_dir / "logs"))

    def open_readme(self) -> None:
        os.startfile(str(self.root_dir / "README.md"))
