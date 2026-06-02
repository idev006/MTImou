from __future__ import annotations

from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[2]
ENV_PATH = ROOT_DIR / "camera.env.bat"
WINDOW_TITLE = "MTImou Control Panel"
MODE_OPTIONS = ["auto", "lan", "ddns", "public"]
TABLE_COLUMNS = ["Camera", "LAN", "DDNS", "Public", "Status"]
TIER_OPTIONS = ["critical", "standard", "archive"]
INVENTORY_COLUMNS = [
    "Enabled",
    "ID",
    "Name",
    "Group",
    "Tier",
    "LAN Host",
    "LAN Port",
    "DDNS Host",
    "DDNS Port",
    "Public Host",
    "Public Port",
    "Wall",
    "Focus",
    "Password Env",
]
