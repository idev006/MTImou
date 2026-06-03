from __future__ import annotations

import re
from dataclasses import dataclass

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from control_panel_app.constants import TIER_OPTIONS


@dataclass(slots=True)
class CameraRow:
    camera_id: str
    name: str
    group_name: str
    tier: str
    lan: str
    ddns: str
    public: str
    enabled: bool


@dataclass(slots=True)
class PasswordField:
    camera_id: str
    env_name: str
    edit: QLineEdit


class MetricCard(QFrame):
    def __init__(self, title: str, accent: str) -> None:
        super().__init__()
        self.setObjectName("metricCard")
        self.setProperty("accent", accent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(6)

        self.title_label = QLabel(title)
        self.title_label.setObjectName("metricTitle")
        self.value_label = QLabel("-")
        self.value_label.setObjectName("metricValue")
        self.helper_label = QLabel("")
        self.helper_label.setObjectName("metricHelper")
        self.helper_label.setWordWrap(True)

        layout.addWidget(self.title_label)
        layout.addWidget(self.value_label)
        layout.addWidget(self.helper_label)

    def set_value(self, value: str, helper: str = "") -> None:
        self.value_label.setText(value)
        self.helper_label.setText(helper)


class CollapsibleSection(QFrame):
    def __init__(self, title: str, body: QWidget, *, collapsed: bool = False) -> None:
        super().__init__()
        self.setObjectName("collapsibleSection")

        self.toggle_button = QToolButton()
        self.toggle_button.setText(title)
        self.toggle_button.setCheckable(True)
        self.toggle_button.setChecked(not collapsed)
        self.toggle_button.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.toggle_button.setArrowType(Qt.DownArrow if not collapsed else Qt.RightArrow)
        self.toggle_button.clicked.connect(self._apply_state)

        self.body = body
        self.body.setVisible(not collapsed)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        layout.addWidget(self.toggle_button)
        layout.addWidget(self.body)

    def _apply_state(self) -> None:
        expanded = self.toggle_button.isChecked()
        self.toggle_button.setArrowType(Qt.DownArrow if expanded else Qt.RightArrow)
        self.body.setVisible(expanded)

    def is_collapsed(self) -> bool:
        return not self.toggle_button.isChecked()

    def set_collapsed(self, collapsed: bool) -> None:
        self.toggle_button.setChecked(not collapsed)
        self._apply_state()


class CameraWizardDialog(QDialog):
    def __init__(self, *, next_camera_id: str, ddns_host: str, public_host: str, public_port: int, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Add Camera Wizard")
        self.setModal(True)
        self.resize(520, 420)

        self.id_edit = QLineEdit(next_camera_id)
        self.name_edit = QLineEdit(f"Camera {re.sub(r'[^0-9]+', '', next_camera_id) or next_camera_id}")
        self.group_edit = QLineEdit("default")
        self.tier_combo = QComboBox()
        self.tier_combo.addItems(TIER_OPTIONS)
        self.lan_host_edit = QLineEdit("192.168.1.10")
        self.lan_port_spin = QSpinBox()
        self.lan_port_spin.setRange(1, 65535)
        self.lan_port_spin.setValue(554)
        self.ddns_host_edit = QLineEdit(ddns_host)
        self.ddns_port_spin = QSpinBox()
        self.ddns_port_spin.setRange(1, 65535)
        self.ddns_port_spin.setValue(public_port)
        self.public_host_edit = QLineEdit(public_host)
        self.public_port_spin = QSpinBox()
        self.public_port_spin.setRange(1, 65535)
        self.public_port_spin.setValue(public_port)
        self.password_env_edit = QLineEdit(f"IMOU_CAM_{re.sub(r'[^A-Za-z0-9]+', '_', next_camera_id).upper()}_PASSWORD")
        self.wall_subtype_combo = QComboBox()
        self.wall_subtype_combo.addItems(["0", "1"])
        self.focus_subtype_combo = QComboBox()
        self.focus_subtype_combo.addItems(["0", "1"])
        self.enabled_check = QCheckBox("Enable this camera immediately")
        self.enabled_check.setChecked(True)

        form = QFormLayout()
        form.addRow("Camera ID", self.id_edit)
        form.addRow("Display Name", self.name_edit)
        form.addRow("Group", self.group_edit)
        form.addRow("Tier", self.tier_combo)
        form.addRow("LAN Host", self.lan_host_edit)
        form.addRow("LAN Port", self.lan_port_spin)
        form.addRow("DDNS Host", self.ddns_host_edit)
        form.addRow("DDNS Port", self.ddns_port_spin)
        form.addRow("Public Host", self.public_host_edit)
        form.addRow("Public Port", self.public_port_spin)
        form.addRow("Wall Subtype", self.wall_subtype_combo)
        form.addRow("Focus Subtype", self.focus_subtype_combo)
        form.addRow("Password Env", self.password_env_edit)
        form.addRow("", self.enabled_check)

        helper = QLabel(
            "Recommended pattern: keep LAN port at 554, use one unique forwarded public port per camera, map one password env per camera, and keep Wall Subtype at 0 when image detail matters most."
        )
        helper.setWordWrap(True)
        helper.setStyleSheet("color: #5b6472;")

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(helper)
        layout.addStretch(1)
        layout.addWidget(buttons)

    def values(self) -> dict[str, object]:
        return {
            "camera_id": self.id_edit.text().strip(),
            "name": self.name_edit.text().strip(),
            "group_name": self.group_edit.text().strip(),
            "tier": self.tier_combo.currentText().strip(),
            "lan_host": self.lan_host_edit.text().strip(),
            "lan_port": int(self.lan_port_spin.value()),
            "ddns_host": self.ddns_host_edit.text().strip(),
            "ddns_port": int(self.ddns_port_spin.value()),
            "public_host": self.public_host_edit.text().strip(),
            "public_port": int(self.public_port_spin.value()),
            "remote_wall_subtype": self.wall_subtype_combo.currentText().strip(),
            "remote_focus_subtype": self.focus_subtype_combo.currentText().strip(),
            "password_env_name": self.password_env_edit.text().strip(),
            "enabled": self.enabled_check.isChecked(),
        }


class PresetDialog(QDialog):
    def __init__(self, *, suggested_name: str = "", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Save Selection Preset")
        self.setModal(True)
        self.resize(480, 240)

        self.name_edit = QLineEdit(suggested_name)
        self.description_edit = QLineEdit()
        self.launch_mode_combo = QComboBox()
        self.launch_mode_combo.addItems(["normal", "high-fps"])

        form = QFormLayout()
        form.addRow("Preset Name", self.name_edit)
        form.addRow("Description", self.description_edit)
        form.addRow("Default Launch Mode", self.launch_mode_combo)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addStretch(1)
        layout.addWidget(buttons)

    def values(self) -> dict[str, str]:
        return {
            "name": self.name_edit.text().strip(),
            "description": self.description_edit.text().strip(),
            "launch_mode": self.launch_mode_combo.currentText().strip(),
        }


class FirstRunGuideDialog(QDialog):
    def __init__(self, *, issues: list[str], tips: list[str], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("First-Run Setup Guide")
        self.setModal(True)
        self.resize(620, 420)
        self.target_tab: str | None = None

        intro = QLabel(
            "MTImou is almost ready. Let's finish the minimum setup so the control panel can launch cameras reliably."
        )
        intro.setWordWrap(True)

        body = QLabel(self._build_body_text(issues, tips))
        body.setWordWrap(True)
        body.setTextInteractionFlags(Qt.TextSelectableByMouse)

        button_row = QHBoxLayout()
        open_settings = QPushButton("Open Settings")
        open_settings.clicked.connect(lambda: self._accept_with_target("settings"))
        open_inventory = QPushButton("Open Camera Management")
        open_inventory.clicked.connect(lambda: self._accept_with_target("inventory"))
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.accept)
        button_row.addWidget(open_settings)
        button_row.addWidget(open_inventory)
        button_row.addStretch(1)
        button_row.addWidget(close_button)

        layout = QVBoxLayout(self)
        layout.addWidget(intro)
        layout.addWidget(body)
        layout.addStretch(1)
        layout.addLayout(button_row)

    def _accept_with_target(self, target: str) -> None:
        self.target_tab = target
        self.accept()

    @staticmethod
    def _build_body_text(issues: list[str], tips: list[str]) -> str:
        lines: list[str] = []
        if issues:
            lines.append("Finish these first:")
            lines.extend(f"- {issue}" for issue in issues)
        if tips:
            if lines:
                lines.append("")
            lines.append("Helpful next steps:")
            lines.extend(f"- {tip}" for tip in tips)
        if not lines:
            lines.append("No first-run setup items are pending.")
        return "\n".join(lines)
