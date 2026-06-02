from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from mtimou_v2.app_state import SelectionPreset


@dataclass(slots=True)
class PresetDocument:
    raw: dict


class PresetStore:
    def __init__(self, preset_path: Path) -> None:
        self.preset_path = preset_path

    def load_document(self) -> PresetDocument:
        if not self.preset_path.exists():
            return PresetDocument(raw={"presets": []})
        return PresetDocument(raw=json.loads(self.preset_path.read_text(encoding="utf-8")))

    def load_presets(self) -> tuple[PresetDocument, list[SelectionPreset]]:
        document = self.load_document()
        presets: list[SelectionPreset] = []
        for item in document.raw.get("presets", []):
            name = str(item.get("name", "")).strip()
            camera_ids = [str(camera_id).strip() for camera_id in item.get("camera_ids", []) if str(camera_id).strip()]
            if not name or not camera_ids:
                continue
            presets.append(
                SelectionPreset(
                    name=name,
                    camera_ids=camera_ids,
                    description=str(item.get("description", "")).strip(),
                    launch_mode=str(item.get("launch_mode", "normal")).strip() or "normal",
                )
            )
        presets.sort(key=lambda preset: preset.name.lower())
        return document, presets

    def save_presets(self, presets: list[SelectionPreset]) -> PresetDocument:
        payload = {
            "presets": [
                {
                    "name": preset.name,
                    "camera_ids": list(preset.camera_ids),
                    "description": preset.description,
                    "launch_mode": preset.launch_mode,
                }
                for preset in sorted(presets, key=lambda item: item.name.lower())
            ]
        }
        self.preset_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        return self.load_document()
