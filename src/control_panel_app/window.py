from __future__ import annotations

from PySide6.QtCore import QProcess, QSettings, Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QFormLayout,
    QFrame,
    QGroupBox,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QLayout,
    QLineEdit,
    QMainWindow,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSplitter,
    QSizePolicy,
    QStatusBar,
    QSpinBox,
    QTabWidget,
    QTableWidget,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from control_panel_app.actions_mixin import ControlPanelActionsMixin
from control_panel_app.components import CollapsibleSection, MetricCard
from control_panel_app.constants import ENV_PATH, INVENTORY_COLUMNS, MODE_OPTIONS, ROOT_DIR, TABLE_COLUMNS, TIER_OPTIONS, WINDOW_TITLE
from control_panel_app.state_mixin import ControlPanelStateMixin
from mtimou_v2.viewmodels.control_panel_vm import ControlPanelViewModel


class ControlPanelWindow(ControlPanelStateMixin, ControlPanelActionsMixin, QMainWindow):
    DASHBOARD_BREAKPOINT = 1220

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(WINDOW_TITLE)
        self.resize(1360, 860)
        self.setMinimumSize(860, 620)
        self.ui_settings = QSettings("MTImou", "ControlPanel")

        self.vm = ControlPanelViewModel(root_dir=ROOT_DIR, env_path=ENV_PATH)
        self.health_process: QProcess | None = None
        self.source_process: QProcess | None = None

        self.mode_combo = QComboBox()
        self.mode_combo.addItems(MODE_OPTIONS)
        self.mode_combo.currentTextChanged.connect(lambda _value: self._update_metric_cards())
        self.ddns_edit = QLineEdit()
        self.ddns_edit.textChanged.connect(lambda _value: self._update_metric_cards())
        self.user_edit = QLineEdit()
        self.show_passwords_checkbox = QCheckBox("Show passwords")
        self.show_passwords_checkbox.toggled.connect(self.toggle_password_visibility)
        self.open_log_checkbox = QCheckBox("Open logs folder after health check")
        self.open_log_checkbox.setChecked(True)

        self.camera_table = QTableWidget(0, len(TABLE_COLUMNS))
        self.camera_table.setHorizontalHeaderLabels(TABLE_COLUMNS)
        self.camera_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.camera_table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.camera_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.camera_table.setAlternatingRowColors(True)
        self.camera_table.verticalHeader().setVisible(False)
        self.camera_table.itemSelectionChanged.connect(self._refresh_selection_summary)

        self.output = QPlainTextEdit()
        self.output.setReadOnly(True)
        self.output.setPlaceholderText("Activity and health-check output will appear here.")

        self.selection_summary = QLabel("No camera selected")
        self.selection_summary.setWordWrap(True)
        self.selection_summary.setObjectName("selectionSummary")
        self.camera_search_edit = QLineEdit()
        self.camera_search_edit.setPlaceholderText("Search camera, group, tier, host, or port")
        self.camera_search_edit.textChanged.connect(self._apply_camera_table_filters)
        self.group_filter_combo = QComboBox()
        self.group_filter_combo.addItem("All Groups")
        self.group_filter_combo.currentTextChanged.connect(self._apply_camera_table_filters)
        self.tier_filter_combo = QComboBox()
        self.tier_filter_combo.addItems(["All Tiers", *TIER_OPTIONS])
        self.tier_filter_combo.currentTextChanged.connect(self._apply_camera_table_filters)
        self.preset_combo = QComboBox()
        self.preset_combo.addItem("No preset selected")

        self.password_fields = []
        self.inventory_table = QTableWidget(0, len(INVENTORY_COLUMNS))
        self.inventory_table.setHorizontalHeaderLabels(INVENTORY_COLUMNS)
        self.inventory_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.inventory_table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.inventory_table.setAlternatingRowColors(True)
        self.inventory_table.verticalHeader().setVisible(False)
        self.password_rows_host = QWidget()
        self.password_rows_layout = QVBoxLayout(self.password_rows_host)
        self.password_rows_layout.setContentsMargins(0, 0, 0, 0)
        self.password_rows_layout.setSpacing(8)

        self.metric_enabled = MetricCard("Enabled Cameras", "green")
        self.metric_mode = MetricCard("Target Mode", "blue")
        self.metric_ddns = MetricCard("DDNS Host", "orange")
        self.metric_health = MetricCard("Health Snapshot", "green")
        self.metric_source = MetricCard("Source FPS Ceiling", "blue")
        self.metric_critical = MetricCard("Critical", "orange")
        self.metric_standard = MetricCard("Standard", "blue")
        self.metric_archive = MetricCard("Archive", "green")
        self.camera_health_status: dict[str, tuple[str, str]] = {}
        self.source_capability_status: dict[str, tuple[float, str]] = {}
        self.bulk_group_edit = QLineEdit()
        self.bulk_group_edit.setPlaceholderText("group")
        self.bulk_tier_combo = QComboBox()
        self.bulk_tier_combo.addItems(["No change", *TIER_OPTIONS])
        self.bulk_wall_combo = QComboBox()
        self.bulk_wall_combo.addItems(["No change", "1", "0"])
        self.bulk_focus_combo = QComboBox()
        self.bulk_focus_combo.addItems(["No change", "0", "1"])
        self.collapsible_sections: dict[str, CollapsibleSection] = {}

        self._build_ui()
        self._apply_styles()
        self.reload_settings()
        self._refresh_group_filter()
        self._restore_ui_state()
        self._update_dashboard_breakpoint()

    def _apply_styles(self) -> None:
        self.setStyleSheet(
            """
            QMainWindow {
                background: #f4f7fb;
            }
            QToolBar {
                spacing: 8px;
                padding: 6px;
                background: #ffffff;
                border-bottom: 1px solid #d9e2ef;
            }
            QGroupBox {
                font-weight: 600;
                border: 1px solid #d9e2ef;
                border-radius: 12px;
                margin-top: 12px;
                background: #ffffff;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 6px;
            }
            QFrame#metricCard {
                border-radius: 14px;
                border: 1px solid #d9e2ef;
                background: #ffffff;
            }
            QFrame#collapsibleSection {
                border: 1px solid #d9e2ef;
                border-radius: 12px;
                background: #ffffff;
                padding: 4px 8px 8px 8px;
            }
            QFrame[accent="green"] {
                border-left: 5px solid #1f9d64;
            }
            QFrame[accent="blue"] {
                border-left: 5px solid #2374e1;
            }
            QFrame[accent="orange"] {
                border-left: 5px solid #d97706;
            }
            QLabel#metricTitle {
                color: #5b6472;
                font-size: 12px;
                font-weight: 600;
            }
            QLabel#metricValue {
                color: #172233;
                font-size: 22px;
                font-weight: 700;
            }
            QLabel#metricHelper {
                color: #6b7280;
                font-size: 11px;
            }
            QLabel#selectionSummary {
                color: #334155;
                background: #f8fafc;
                border: 1px solid #d9e2ef;
                border-radius: 10px;
                padding: 10px 12px;
            }
            QToolButton {
                border: 0;
                font-weight: 700;
                color: #172233;
                background: transparent;
                text-align: left;
                padding: 6px 2px;
            }
            QTabWidget::pane {
                border: 1px solid #d9e2ef;
                background: #ffffff;
                border-radius: 12px;
                top: -1px;
            }
            QTabBar::tab {
                background: #e9eef6;
                color: #334155;
                padding: 10px 18px;
                margin-right: 4px;
                border-top-left-radius: 10px;
                border-top-right-radius: 10px;
            }
            QTabBar::tab:selected {
                background: #ffffff;
                font-weight: 700;
            }
            QPushButton {
                min-height: 40px;
                border-radius: 10px;
                border: 1px solid #d0d9e7;
                background: #ffffff;
                padding: 8px 12px;
            }
            QPushButton:hover {
                background: #f8fbff;
                border-color: #98b4df;
            }
            QPushButton#primary {
                background: #2374e1;
                color: white;
                border-color: #2374e1;
                font-weight: 700;
            }
            QPushButton#primary:hover {
                background: #1b63c4;
            }
            QLineEdit, QComboBox, QPlainTextEdit, QTableWidget {
                border: 1px solid #d0d9e7;
                border-radius: 10px;
                background: #ffffff;
                selection-background-color: #dbeafe;
            }
            QHeaderView::section {
                background: #eef3f9;
                border: 0;
                border-bottom: 1px solid #d0d9e7;
                padding: 8px;
                font-weight: 700;
            }
            """
        )

    def _build_ui(self) -> None:
        self._build_toolbar()

        central = QWidget()
        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(18, 18, 18, 18)
        root_layout.setSpacing(14)

        title = QLabel("MTImou Control Panel")
        title.setStyleSheet("font-size: 30px; font-weight: 800; color: #172233;")
        subtitle = QLabel(
            "Operate cameras from one place: choose the safest route, verify system health, and launch single or multi-camera views."
        )
        subtitle.setStyleSheet("color: #536173; font-size: 13px;")
        root_layout.addWidget(title)
        root_layout.addWidget(subtitle)

        metric_widget = QWidget()
        metric_layout = QHBoxLayout(metric_widget)
        metric_layout.setContentsMargins(0, 0, 0, 0)
        metric_layout.setSpacing(12)
        metric_layout.addWidget(self.metric_enabled)
        metric_layout.addWidget(self.metric_mode)
        metric_layout.addWidget(self.metric_ddns)
        metric_layout.addWidget(self.metric_health)
        metric_layout.addWidget(self.metric_source)
        metric_layout.addWidget(self.metric_critical)
        metric_layout.addWidget(self.metric_standard)
        metric_layout.addWidget(self.metric_archive)
        metric_widget.adjustSize()
        metric_widget.setMinimumWidth(metric_widget.sizeHint().width())
        metric_scroll = QScrollArea()
        metric_scroll.setWidgetResizable(True)
        metric_scroll.setFrameShape(QFrame.NoFrame)
        metric_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        metric_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        metric_scroll.setWidget(metric_widget)
        root_layout.addWidget(metric_scroll)

        self.tabs = QTabWidget()
        self.tabs.addTab(self._wrap_scroll(self._build_dashboard_tab()), "Dashboard")
        self.tabs.addTab(self._wrap_scroll(self._build_settings_tab()), "Settings")
        self.tabs.addTab(self._wrap_scroll(self._build_camera_management_tab()), "Camera Management")
        self.tabs.addTab(self._wrap_scroll(self._build_help_tab()), "Operator Guide")
        root_layout.addWidget(self.tabs, 1)

        self.setCentralWidget(central)

        status = QStatusBar()
        status.showMessage("Ready")
        self.setStatusBar(status)

    def _build_toolbar(self) -> None:
        toolbar = QToolBar("Main")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        save_action = QAction("Save Settings", self)
        save_action.triggered.connect(self.save_settings)
        toolbar.addAction(save_action)

        reload_action = QAction("Reload", self)
        reload_action.triggered.connect(self.reload_settings)
        toolbar.addAction(reload_action)

        toolbar.addSeparator()

        logs_action = QAction("Open Logs", self)
        logs_action.triggered.connect(self.open_logs_folder)
        toolbar.addAction(logs_action)

        source_action = QAction("Source Capability", self)
        source_action.triggered.connect(self.run_source_capability_check)
        toolbar.addAction(source_action)

        readme_action = QAction("Open README", self)
        readme_action.triggered.connect(self.open_readme)
        toolbar.addAction(readme_action)

    def _wrap_scroll(self, content: QWidget) -> QScrollArea:
        layout = content.layout()
        if layout is not None:
            layout.setSizeConstraint(QLayout.SetMinimumSize)
        content.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setWidget(content)
        return scroll

    def _build_dashboard_tab(self) -> QWidget:
        tab = QWidget()
        tab.setMinimumSize(980, 920)
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(14)

        camera_box = QGroupBox("Camera Grid")
        camera_layout = QVBoxLayout(camera_box)

        helper = QLabel(
            "Select one or more cameras. The table is optimized for N cameras, keeps network endpoints readable, and now carries source-ceiling hints from the latest capability check."
        )
        helper.setStyleSheet("color: #5b6472; font-size: 12px;")
        helper.setWordWrap(True)
        camera_layout.addWidget(helper)

        header = self.camera_table.horizontalHeader()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.camera_table.setColumnWidth(1, 170)
        self.camera_table.setColumnWidth(2, 260)
        self.camera_table.setColumnWidth(3, 180)
        self.camera_table.setColumnWidth(4, 90)
        camera_layout.addWidget(self.camera_table, 1)

        search_row = QHBoxLayout()
        search_row.addWidget(self.camera_search_edit, 1)
        camera_layout.addLayout(search_row)

        row_buttons = QHBoxLayout()
        btn_select_all = QPushButton("Select All")
        btn_select_all.clicked.connect(self._select_all_cameras)
        btn_clear = QPushButton("Clear Selection")
        btn_clear.clicked.connect(self.camera_table.clearSelection)
        btn_enabled = QPushButton("Select Enabled")
        btn_enabled.clicked.connect(self._select_enabled_cameras)
        btn_group = QPushButton("Select Group")
        btn_group.clicked.connect(self._select_group_cameras)
        row_buttons.addWidget(btn_select_all)
        row_buttons.addWidget(btn_enabled)
        row_buttons.addWidget(self.group_filter_combo)
        row_buttons.addWidget(self.tier_filter_combo)
        row_buttons.addWidget(btn_group)
        row_buttons.addWidget(btn_clear)
        camera_layout.addLayout(row_buttons)
        camera_layout.addWidget(self.selection_summary)

        action_box = QGroupBox("Launch & Validation")
        action_layout = QVBoxLayout(action_box)
        action_layout.setSpacing(10)

        button_specs = [
            ("View Selected Cameras", self.launch_selected_cameras, True),
            ("View Selected Cameras (High FPS)", self.launch_selected_cameras_high_fps, False),
            ("View All Enabled Cameras", self.launch_all_cameras, False),
            ("View Critical Cameras", self.launch_critical_cameras, False),
            ("View Critical Cameras (High FPS)", self.launch_critical_cameras_high_fps, False),
            ("View Filtered Group", self.launch_filtered_group_cameras, False),
            ("View Filtered Group (High FPS)", self.launch_filtered_group_cameras_high_fps, False),
            ("Run Health Check", self.run_health_check, False),
            ("Run Source Capability Check", self.run_source_capability_check, False),
            ("Open Logs Folder", self.open_logs_folder, False),
            ("Open Project README", self.open_readme, False),
        ]
        for text, callback, primary in button_specs:
            button = QPushButton(text)
            if primary:
                button.setObjectName("primary")
            button.clicked.connect(callback)
            action_layout.addWidget(button)

        action_layout.addWidget(self.open_log_checkbox)

        preset_box = QGroupBox("Saved Presets")
        preset_layout = QVBoxLayout(preset_box)
        preset_layout.addWidget(self.preset_combo)

        preset_button_specs = [
            ("Save Current Selection", self.save_current_selection_as_preset),
            ("Apply Preset", self.apply_selected_preset),
            ("Run Preset", self.run_selected_preset),
            ("Run Preset (High FPS)", self.run_selected_preset_high_fps),
            ("Delete Preset", self.delete_selected_preset),
        ]
        for text, callback in preset_button_specs:
            button = QPushButton(text)
            button.clicked.connect(callback)
            preset_layout.addWidget(button)

        action_layout.addWidget(preset_box)
        action_layout.addStretch(1)

        output_box = QGroupBox("Recent Activity")
        output_layout = QVBoxLayout(output_box)
        self.output.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        output_layout.addWidget(self.output)

        self.dashboard_side_splitter = QSplitter(Qt.Vertical)
        self.dashboard_side_splitter.addWidget(action_box)
        self.dashboard_side_splitter.addWidget(output_box)
        self.dashboard_side_splitter.setStretchFactor(0, 0)
        self.dashboard_side_splitter.setStretchFactor(1, 1)
        self.dashboard_side_splitter.setSizes([420, 320])

        self.dashboard_splitter = QSplitter(Qt.Horizontal)
        self.dashboard_splitter.addWidget(camera_box)
        self.dashboard_splitter.addWidget(self.dashboard_side_splitter)
        self.dashboard_splitter.setStretchFactor(0, 3)
        self.dashboard_splitter.setStretchFactor(1, 2)
        self.dashboard_splitter.setSizes([900, 460])

        layout.addWidget(self.dashboard_splitter, 1)
        return tab

    def _build_settings_tab(self) -> QWidget:
        tab = QWidget()
        tab.setMinimumSize(980, 760)
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(14)

        settings_body = QWidget()
        settings_layout = QFormLayout(settings_body)
        settings_layout.setContentsMargins(16, 18, 16, 16)
        settings_layout.setSpacing(12)
        settings_layout.addRow("Target mode", self.mode_combo)
        settings_layout.addRow("Shared DDNS host", self.ddns_edit)
        settings_layout.addRow("Camera username", self.user_edit)
        settings_layout.addRow("Camera passwords", self.password_rows_host)
        settings_layout.addRow("", self.show_passwords_checkbox)
        self.settings_section = CollapsibleSection("Operator Settings", settings_body)
        self.collapsible_sections["settings/operator"] = self.settings_section
        layout.addWidget(self.settings_section)

        notes_body = QWidget()
        notes_layout = QVBoxLayout(notes_body)
        notes = QLabel(
            "Auto mode is the normal choice. It prefers LAN when you are at home, then DDNS, then public IP.\n\n"
            "Use DDNS mode when you want to verify remote access specifically.\n\n"
            "Passwords are stored in camera.env.bat and mapped per camera using the environment names shown on the right.\n\n"
            "If you are chasing FPS, run Source Capability Check first. It tells us whether the camera stream itself is the limit."
        )
        notes.setWordWrap(True)
        notes.setStyleSheet("color: #4b5563;")
        notes_layout.addWidget(notes)
        self.settings_notes_section = CollapsibleSection("How To Use Settings", notes_body, collapsed=True)
        self.collapsible_sections["settings/notes"] = self.settings_notes_section
        layout.addWidget(self.settings_notes_section)
        layout.addStretch(1)
        return tab

    def _build_camera_management_tab(self) -> QWidget:
        tab = QWidget()
        tab.setMinimumSize(1180, 860)
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(14)

        inventory_body = QWidget()
        box_layout = QVBoxLayout(inventory_body)

        helper = QLabel(
            "Manage N cameras here. Edit network endpoints, assign each camera to a group, choose a tier, and define separate wall-view and focus-view stream policies."
        )
        helper.setWordWrap(True)
        helper.setStyleSheet("color: #5b6472; font-size: 12px;")
        box_layout.addWidget(helper)

        inventory_header = self.inventory_table.horizontalHeader()
        inventory_header.setStretchLastSection(False)
        inventory_header.setSectionResizeMode(2, QHeaderView.Stretch)
        self.inventory_table.setColumnWidth(0, 80)
        self.inventory_table.setColumnWidth(1, 90)
        self.inventory_table.setColumnWidth(3, 120)
        self.inventory_table.setColumnWidth(4, 90)
        self.inventory_table.setColumnWidth(5, 130)
        self.inventory_table.setColumnWidth(6, 80)
        self.inventory_table.setColumnWidth(7, 210)
        self.inventory_table.setColumnWidth(8, 90)
        self.inventory_table.setColumnWidth(9, 130)
        self.inventory_table.setColumnWidth(10, 90)
        self.inventory_table.setColumnWidth(11, 70)
        self.inventory_table.setColumnWidth(12, 70)
        self.inventory_table.setColumnWidth(13, 180)
        box_layout.addWidget(self.inventory_table, 1)

        actions = QHBoxLayout()
        action_specs = [
            ("Add Camera Wizard", self.open_add_camera_wizard, True),
            ("Add Draft Row", self.add_camera_inventory_row, False),
            ("Remove Selected", self.remove_selected_inventory_rows, False),
            ("Reload Inventory", self.reload_settings, False),
        ]
        for text, callback, primary in action_specs:
            button = QPushButton(text)
            if primary:
                button.setObjectName("primary")
            button.clicked.connect(callback)
            actions.addWidget(button)
        actions.addStretch(1)
        btn_save = QPushButton("Save Camera Inventory")
        btn_save.setObjectName("primary")
        btn_save.clicked.connect(self.save_camera_inventory)
        actions.addWidget(btn_save)
        box_layout.addLayout(actions)

        bulk_box = QGroupBox("Bulk Edit Selected Rows")
        bulk_layout = QHBoxLayout(bulk_box)
        bulk_layout.addWidget(QLabel("Group"))
        bulk_layout.addWidget(self.bulk_group_edit)
        bulk_layout.addWidget(QLabel("Tier"))
        bulk_layout.addWidget(self.bulk_tier_combo)
        bulk_layout.addWidget(QLabel("Wall"))
        bulk_layout.addWidget(self.bulk_wall_combo)
        bulk_layout.addWidget(QLabel("Focus"))
        bulk_layout.addWidget(self.bulk_focus_combo)
        btn_enable_selected = QPushButton("Enable Selected")
        btn_enable_selected.clicked.connect(lambda: self.bulk_set_enabled_state(True))
        btn_disable_selected = QPushButton("Disable Selected")
        btn_disable_selected.clicked.connect(lambda: self.bulk_set_enabled_state(False))
        btn_apply_bulk = QPushButton("Apply Bulk Edit")
        btn_apply_bulk.setObjectName("primary")
        btn_apply_bulk.clicked.connect(self.apply_bulk_edit_to_inventory)
        bulk_layout.addWidget(btn_enable_selected)
        bulk_layout.addWidget(btn_disable_selected)
        bulk_layout.addWidget(btn_apply_bulk)

        notes_body = QWidget()
        notes_layout = QVBoxLayout(notes_body)
        notes_text = QLabel(
            "Use one public port per camera. A typical pattern is 45554, 45555, 45556, and so on.\n\n"
            "Password Env should match the environment variable in camera.env.bat, for example IMOU_CAM_CAM3_PASSWORD.\n\n"
            "Recommended large-N strategy: keep Wall subtype at 1 for broad wall views, keep Focus subtype at 0 for detailed single-camera viewing, and organize cameras into groups such as front, side, rear, parking, gate, and indoor."
        )
        notes_text.setWordWrap(True)
        notes_layout.addWidget(notes_text)

        self.inventory_section = CollapsibleSection("Camera Inventory", inventory_body)
        self.bulk_section = CollapsibleSection("Bulk Edit Selected Rows", bulk_box, collapsed=True)
        self.inventory_notes_section = CollapsibleSection("Inventory Notes", notes_body, collapsed=True)
        self.collapsible_sections["inventory/main"] = self.inventory_section
        self.collapsible_sections["inventory/bulk"] = self.bulk_section
        self.collapsible_sections["inventory/notes"] = self.inventory_notes_section

        layout.addWidget(self.inventory_section, 1)
        layout.addWidget(self.bulk_section)
        layout.addWidget(self.inventory_notes_section)
        return tab

    def _build_help_tab(self) -> QWidget:
        tab = QWidget()
        tab.setMinimumSize(900, 720)
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(14)

        flow_box = QGroupBox("Recommended Operator Flow")
        flow_layout = QVBoxLayout(flow_box)
        flow_text = QLabel(
            "1. Save settings after any credential or DDNS change.\n"
            "2. Run health check before opening long-running views.\n"
            "3. Run Source Capability Check when FPS is lower than expected.\n"
            "4. Use View Selected Cameras for focused work.\n"
            "5. Use View All Enabled Cameras for the normal wall view.\n"
            "6. Keep target mode on auto for day-to-day operation."
        )
        flow_text.setWordWrap(True)
        flow_layout.addWidget(flow_text)

        mode_box = QGroupBox("Target Modes")
        mode_layout = QVBoxLayout(mode_box)
        mode_text = QLabel(
            "auto: best default, re-evaluates LAN, DDNS, and public targets.\n"
            "lan: use only local network addresses.\n"
            "ddns: use the dynamic DNS hostname for remote access.\n"
            "public: use the public IP and forwarded port directly.\n\n"
            "High-FPS split view opens one viewer process per camera. It is the best choice when you want the highest practical FPS per camera."
        )
        mode_text.setWordWrap(True)
        mode_layout.addWidget(mode_text)

        source_box = QGroupBox("Source Capability")
        source_layout = QVBoxLayout(source_box)
        source_text = QLabel(
            "Source Capability Check measures the stream that the camera really delivers over 10 seconds.\n\n"
            "If source FPS is already low, the bottleneck is camera-side or profile-side, not the desktop viewer."
        )
        source_text.setWordWrap(True)
        source_layout.addWidget(source_text)

        layout.addWidget(flow_box)
        layout.addWidget(mode_box)
        layout.addWidget(source_box)
        layout.addStretch(1)
        return tab

    def _update_dashboard_breakpoint(self) -> None:
        if not hasattr(self, "dashboard_splitter"):
            return
        target_orientation = Qt.Vertical if self.width() < self.DASHBOARD_BREAKPOINT else Qt.Horizontal
        if self.dashboard_splitter.orientation() == target_orientation:
            return
        self.dashboard_splitter.setOrientation(target_orientation)
        if target_orientation == Qt.Vertical:
            self.dashboard_splitter.setSizes([620, 340])
        else:
            self.dashboard_splitter.setSizes([900, 460])

    def _restore_ui_state(self) -> None:
        geometry = self.ui_settings.value("window/geometry")
        if geometry:
            self.restoreGeometry(geometry)
        saved_width = int(self.ui_settings.value("window/width", self.width()))
        saved_height = int(self.ui_settings.value("window/height", self.height()))
        self.resize(max(self.minimumWidth(), saved_width), max(self.minimumHeight(), saved_height))

        tab_index = int(self.ui_settings.value("tabs/current_index", 0))
        if hasattr(self, "tabs"):
            self.tabs.setCurrentIndex(max(0, min(tab_index, self.tabs.count() - 1)))

        for key, section in self.collapsible_sections.items():
            collapsed = str(self.ui_settings.value(f"section/{key}/collapsed", "false")).lower() == "true"
            section.set_collapsed(collapsed)

        main_sizes_raw = str(self.ui_settings.value("dashboard/main_splitter_sizes", "") or "").strip()
        if hasattr(self, "dashboard_splitter") and main_sizes_raw:
            sizes = [int(part) for part in main_sizes_raw.split(",") if part.strip().isdigit()]
            if sizes:
                self.dashboard_splitter.setSizes(sizes)

        side_sizes_raw = str(self.ui_settings.value("dashboard/side_splitter_sizes", "") or "").strip()
        if hasattr(self, "dashboard_side_splitter") and side_sizes_raw:
            sizes = [int(part) for part in side_sizes_raw.split(",") if part.strip().isdigit()]
            if sizes:
                self.dashboard_side_splitter.setSizes(sizes)

    def _save_ui_state(self) -> None:
        self.ui_settings.setValue("window/geometry", self.saveGeometry())
        self.ui_settings.setValue("window/width", self.width())
        self.ui_settings.setValue("window/height", self.height())
        if hasattr(self, "tabs"):
            self.ui_settings.setValue("tabs/current_index", self.tabs.currentIndex())
        for key, section in self.collapsible_sections.items():
            self.ui_settings.setValue(f"section/{key}/collapsed", section.is_collapsed())
        if hasattr(self, "dashboard_splitter"):
            self.ui_settings.setValue("dashboard/main_splitter_sizes", ",".join(str(size) for size in self.dashboard_splitter.sizes()))
        if hasattr(self, "dashboard_side_splitter"):
            self.ui_settings.setValue("dashboard/side_splitter_sizes", ",".join(str(size) for size in self.dashboard_side_splitter.sizes()))
        self.ui_settings.sync()

    def resizeEvent(self, event) -> None:  # type: ignore[override]
        super().resizeEvent(event)
        self._update_dashboard_breakpoint()

    def closeEvent(self, event) -> None:  # type: ignore[override]
        self._save_ui_state()
        super().closeEvent(event)
