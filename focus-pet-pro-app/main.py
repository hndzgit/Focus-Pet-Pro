import sys
import os
from PyQt6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLabel, QSpinBox, QPushButton, QCheckBox, QStyle,
                             QSystemTrayIcon, QMenu, QTabWidget, QFormLayout, QComboBox, QFrame)
from PyQt6.QtCore import QTimer, Qt, QUrl, QSettings, pyqtSignal
from PyQt6.QtGui import QIcon, QAction
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEnginePage
import PyQt6.QtSvg  # Force PyInstaller to bundle SVG plugin for Windows

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path).replace("\\", "/")

# Allow WebEngine to play video files from local filesystem without complaining
os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = "--autoplay-policy=no-user-gesture-required --disable-web-security"

class CustomWebPage(QWebEnginePage):
    snooze_requested = pyqtSignal()
    
    def acceptNavigationRequest(self, url, _type, isMainFrame):
        if url.scheme() == "gatekeeper" and url.host() == "snooze":
            self.snooze_requested.emit()
            return False
        return super().acceptNavigationRequest(url, _type, isMainFrame)

class LockScreenWindow(QWidget):
    break_finished = pyqtSignal()
    snooze_accepted = pyqtSignal()
    
    def __init__(self, break_total_seconds, strict_mode, language):
        super().__init__()
        self.break_seconds = break_total_seconds
        self.strict_mode = strict_mode
        self.language = language
        self.is_loaded = False
        self.initUI()
        
    def initUI(self):
        flags = Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool
        if self.strict_mode:
            # Bypass window manager on X11/Mac
            flags |= Qt.WindowType.BypassWindowManagerHint
        self.setWindowFlags(flags)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        
        self.webview = QWebEngineView(self)
        self.custom_page = CustomWebPage(self.webview)
        self.custom_page.snooze_requested.connect(self.on_snooze)
        self.webview.setPage(self.custom_page)
        
        self.webview.page().setBackgroundColor(Qt.GlobalColor.transparent)
        
        html_path = resource_path('lock_screen.html')
        
        self.webview.loadFinished.connect(self.on_load_finished)
        self.webview.setUrl(QUrl.fromLocalFile(html_path))
        
        self.layout.addWidget(self.webview)
        self.setLayout(self.layout)
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_countdown)
        self.timer.start(1000)
        
    def on_load_finished(self, ok):
        self.is_loaded = True
        self.webview.page().runJavaScript(f"setLanguage('{self.language}');")
        if self.strict_mode:
            self.grabKeyboard()
            self.grabMouse()
        
    def update_countdown(self):
        if self.break_seconds > 0:
            self.break_seconds -= 1
            if self.is_loaded:
                m = self.break_seconds // 60
                s = self.break_seconds % 60
                js_code = f"updateCountdown({m}, {s});"
                self.webview.page().runJavaScript(js_code)
        else:
            self.timer.stop()
            if self.is_loaded:
                self.webview.page().runJavaScript("fadeOut();")
            QTimer.singleShot(1000, self.finish_break)
            
    def on_snooze(self):
        self.timer.stop()
        if self.strict_mode:
            self.releaseKeyboard()
            self.releaseMouse()
        self.snooze_accepted.emit()
        self.close()

    def finish_break(self):
        if self.strict_mode:
            self.releaseKeyboard()
            self.releaseMouse()
        self.break_finished.emit()
        self.close()
            
    def closeEvent(self, event):
        # Prevent force closing if strict mode is enabled
        if self.break_seconds > 0 and self.strict_mode:
            event.ignore()
        else:
            event.accept()

class DashboardCard(QFrame):
    def __init__(self, number_color, num_size=32):
        super().__init__()
        self.setObjectName("dashboardCard")
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setContentsMargins(15, 20, 15, 20)
        layout.setSpacing(5)
        
        self.num_lbl = QLabel("0")
        self.num_lbl.setObjectName("cardNum")
        self.num_lbl.setStyleSheet(f"color: {number_color}; font-size: {num_size}px;")
        self.num_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.title_lbl = QLabel("")
        self.title_lbl.setObjectName("cardTitle")
        self.title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        layout.addWidget(self.num_lbl)
        layout.addWidget(self.title_lbl)
        self.setLayout(layout)

class CatGatekeeperApp(QWidget):
    def __init__(self):
        super().__init__()
        self.settings = QSettings("Zokuzoku", "CatGatekeeper")
        self.work_seconds_left = 0
        self.is_running = False
        self.lock_window = None
        
        self.current_lang = self.settings.value("language", "vi", type=str)
        self.setup_i18n()
        
        self.total_work_minutes = self.settings.value("stats_work_m", 0, type=int)
        self.total_breaks = self.settings.value("stats_breaks", 0, type=int)
        self.total_snoozes = self.settings.value("stats_snoozes", 0, type=int)
        self.snoozes_today = self.settings.value("snoozes_today", 0, type=int)
        
        self.work_timer = QTimer(self)
        self.work_timer.timeout.connect(self.tick_work_timer)
        
        self.initUI()
        self.apply_dark_theme()
        
    def setup_i18n(self):
        self.i18n = {
            "vi": {
                "tab_settings": "Cài đặt",
                "tab_dashboard": "Thống kê",
                "lang_label": "Ngôn ngữ (Language):",
                "work_time": "Thời gian tập trung:",
                "break_time": "Thời gian giải lao:",
                "enable_gatekeeper": "Kích hoạt tự động đếm giờ",
                "strict_mode": "Khóa phím chuột",
                "autostart": "Tự động chạy khi mở máy",
                "save_btn": "Lưu Thiết Lập",
                "saved_msg": "Đã lưu thành công!",
                "idle": "Sẵn sàng",
                "stats_title_work": "Phút Tập trung",
                "stats_title_breaks": "Lần Giải lao",
                "stats_title_snoozes": "Lần Hoãn",
                "snooze_limit": "Bạn đã hết lượt hoãn hôm nay!",
                "status_tracking": "Đến giờ giải lao sau: {0}:{1:02d}",
                "tracking_disabled": "Đã tắt theo dõi",
                "show_dashboard": "Mở ứng dụng",
                "quit_app": "Thoát hoàn toàn"
            },
            "en": {
                "tab_settings": "Settings",
                "tab_dashboard": "Dashboard",
                "lang_label": "Language (Ngôn ngữ):",
                "work_time": "Focus Duration:",
                "break_time": "Break Duration:",
                "enable_gatekeeper": "Enable Auto-Timer",
                "strict_mode": "Lock Mouse & Keyboard during breaks",
                "autostart": "Launch at Startup",
                "save_btn": "Save Settings",
                "saved_msg": "Saved Successfully!",
                "idle": "Ready",
                "stats_title_work": "Focus Minutes",
                "stats_title_breaks": "Breaks Taken",
                "stats_title_snoozes": "Snoozes Used",
                "snooze_limit": "Snooze limit reached today! Cannot skip.",
                "status_tracking": "Time until break: {0}:{1:02d}",
                "tracking_disabled": "Tracking disabled",
                "show_dashboard": "Show App",
                "quit_app": "Quit App"
            }
        }

    def initUI(self):
        self.setWindowTitle("Focus Pet Pro")
        self.setFixedSize(450, 550)
        
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(18, 14, 18, 18)
        main_layout.setSpacing(15)
        
        self.tabs = QTabWidget()
        self.tab_settings = QWidget()
        self.tab_dashboard = QWidget()
        self.tabs.addTab(self.tab_settings, "")
        self.tabs.addTab(self.tab_dashboard, "")
        
        self.setup_settings_tab()
        self.setup_dashboard_tab()
        
        main_layout.addWidget(self.tabs)
        
        self.save_btn = QPushButton()
        self.save_btn.setObjectName("saveBtn")
        self.save_btn.clicked.connect(self.on_save_clicked)
        main_layout.addWidget(self.save_btn)
        
        self.saved_msg = QLabel()
        self.saved_msg.setObjectName("savedMsg")
        self.saved_msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.saved_msg.hide()
        main_layout.addWidget(self.saved_msg)
        
        self.status_label = QLabel()
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(self.status_label)
        
        footer_layout = QHBoxLayout()
        footer_label = QLabel("by Hoai Nam")
        footer_label.setObjectName("footer")
        
        self.info_btn = QPushButton("ℹ")
        self.info_btn.setObjectName("infoBtn")
        self.info_btn.setFixedSize(24, 24)
        self.info_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.info_btn.clicked.connect(self.show_about)
        
        footer_layout.addWidget(footer_label)
        footer_layout.addStretch()
        footer_layout.addWidget(self.info_btn)
        main_layout.addLayout(footer_layout)
        
        self.setLayout(main_layout)
        
        # System Tray Menu
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon))
        self.tray_menu = QMenu()
        self.show_action = QAction(self)
        self.show_action.triggered.connect(self.show)
        self.quit_action = QAction(self)
        self.quit_action.triggered.connect(QApplication.instance().quit)
        self.tray_menu.addAction(self.show_action)
        self.tray_menu.addAction(self.quit_action)
        self.tray_icon.setContextMenu(self.tray_menu)
        self.tray_icon.show()
        
        # Apply translations
        self.retranslateUi()
        
        if self.show_cat_cb.isChecked():
            self.start_tracking()

    def show_about(self):
        from PyQt6.QtWidgets import QMessageBox
        msg = QMessageBox(self)
        msg.setWindowTitle("Về Tác Giả" if self.current_lang == "vi" else "About Author")
        msg.setText("<b>Trần Hoài Nam</b><br>K21 Sinh Viên Đại Học FPT<br>Chuyên Ngành AI")
        msg.setIcon(QMessageBox.Icon.Information)
        msg.exec()
    def setup_settings_tab(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(5, 15, 5, 5)
        layout.setSpacing(15)
        
        self.form_layout = QFormLayout()
        self.form_layout.setVerticalSpacing(15)
        
        self.lang_cb = QComboBox()
        self.lang_cb.addItem("Tiếng Việt", "vi")
        self.lang_cb.addItem("English", "en")
        idx = self.lang_cb.findData(self.current_lang)
        if idx >= 0:
            self.lang_cb.setCurrentIndex(idx)
        self.lang_cb.currentIndexChanged.connect(self.on_language_changed)
        self.lang_label_widget = QLabel()
        self.form_layout.addRow(self.lang_label_widget, self.lang_cb)
        
        self.work_spinbox = QSpinBox()
        self.work_spinbox.setRange(0, 480)
        self.work_spinbox.setSuffix(" m")
        self.work_sec_spinbox = QSpinBox()
        self.work_sec_spinbox.setRange(0, 59)
        self.work_sec_spinbox.setSuffix(" s")
        wl = QHBoxLayout()
        wl.addWidget(self.work_spinbox)
        wl.addWidget(self.work_sec_spinbox)
        self.work_label_widget = QLabel()
        self.form_layout.addRow(self.work_label_widget, wl)
        
        self.break_spinbox = QSpinBox()
        self.break_spinbox.setRange(0, 60)
        self.break_spinbox.setSuffix(" m")
        self.break_sec_spinbox = QSpinBox()
        self.break_sec_spinbox.setRange(0, 59)
        self.break_sec_spinbox.setSuffix(" s")
        bl = QHBoxLayout()
        bl.addWidget(self.break_spinbox)
        bl.addWidget(self.break_sec_spinbox)
        self.break_label_widget = QLabel()
        self.form_layout.addRow(self.break_label_widget, bl)
        
        layout.addLayout(self.form_layout)
        
        sep = QWidget()
        sep.setFixedHeight(1)
        sep.setStyleSheet("background-color: rgba(255, 255, 255, 0.1); margin: 5px 0;")
        layout.addWidget(sep)
        
        self.show_cat_cb = QCheckBox()
        self.show_cat_label = QLabel()
        hl1 = QHBoxLayout()
        hl1.addWidget(self.show_cat_label)
        hl1.addStretch()
        hl1.addWidget(self.show_cat_cb)
        layout.addLayout(hl1)
        
        self.strict_mode_cb = QCheckBox()
        self.strict_mode_label = QLabel()
        hl2 = QHBoxLayout()
        hl2.addWidget(self.strict_mode_label)
        hl2.addStretch()
        hl2.addWidget(self.strict_mode_cb)
        layout.addLayout(hl2)
        
        self.autostart_cb = QCheckBox()
        self.autostart_label = QLabel()
        hl3 = QHBoxLayout()
        hl3.addWidget(self.autostart_label)
        hl3.addStretch()
        hl3.addWidget(self.autostart_cb)
        layout.addLayout(hl3)
        
        layout.addStretch()
        
        self.tab_settings.setLayout(layout)
        
        # Load values
        self.work_spinbox.setValue(self.settings.value("work_m", 240, type=int))
        self.work_sec_spinbox.setValue(self.settings.value("work_s", 0, type=int))
        self.break_spinbox.setValue(self.settings.value("break_m", 5, type=int))
        self.break_sec_spinbox.setValue(self.settings.value("break_s", 0, type=int))
        self.show_cat_cb.setChecked(self.settings.value("show_cat", True, type=bool))
        self.strict_mode_cb.setChecked(self.settings.value("strict_mode", False, type=bool))
        self.autostart_cb.setChecked(self.settings.value("autostart", False, type=bool))
        
    def setup_dashboard_tab(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 15, 10, 10)
        layout.setSpacing(12)
        
        self.work_card = DashboardCard("#3b82f6", num_size=42)
        self.break_card = DashboardCard("#10b981")
        self.snooze_card = DashboardCard("#f59e0b")
        
        bottom_layout = QHBoxLayout()
        bottom_layout.setSpacing(12)
        bottom_layout.addWidget(self.break_card)
        bottom_layout.addWidget(self.snooze_card)
        
        layout.addWidget(self.work_card)
        layout.addLayout(bottom_layout)
        layout.addStretch()
        
        self.tab_dashboard.setLayout(layout)

    def on_language_changed(self):
        self.current_lang = self.lang_cb.currentData()
        self.settings.setValue("language", self.current_lang)
        self.retranslateUi()

    def retranslateUi(self):
        texts = self.i18n.get(self.current_lang, self.i18n["vi"])
        
        self.tabs.setTabText(0, texts["tab_settings"])
        self.tabs.setTabText(1, texts["tab_dashboard"])
        
        self.lang_label_widget.setText(texts["lang_label"])
        self.work_label_widget.setText(texts["work_time"])
        self.break_label_widget.setText(texts["break_time"])
        
        self.show_cat_label.setText(texts["enable_gatekeeper"])
        self.strict_mode_label.setText(texts["strict_mode"])
        self.autostart_label.setText(texts["autostart"])
        
        self.save_btn.setText(texts["save_btn"])
        self.saved_msg.setText(texts["saved_msg"])
        
        if not self.is_running:
            self.status_label.setText(texts["idle"])
            
        self.work_card.title_lbl.setText(texts["stats_title_work"])
        self.break_card.title_lbl.setText(texts["stats_title_breaks"])
        self.snooze_card.title_lbl.setText(texts["stats_title_snoozes"])
        
        self.show_action.setText(texts["show_dashboard"])
        self.quit_action.setText(texts["quit_app"])
        
        self.refresh_dashboard()

    def refresh_dashboard(self):
        self.work_card.num_lbl.setText(str(self.total_work_minutes))
        self.break_card.num_lbl.setText(str(self.total_breaks))
        self.snooze_card.num_lbl.setText(str(self.total_snoozes))

    def on_save_clicked(self):
        self.settings.setValue("work_m", self.work_spinbox.value())
        self.settings.setValue("work_s", self.work_sec_spinbox.value())
        self.settings.setValue("break_m", self.break_spinbox.value())
        self.settings.setValue("break_s", self.break_sec_spinbox.value())
        self.settings.setValue("show_cat", self.show_cat_cb.isChecked())
        self.settings.setValue("strict_mode", self.strict_mode_cb.isChecked())
        
        autostart = self.autostart_cb.isChecked()
        self.settings.setValue("autostart", autostart)
        self.setup_autostart(autostart)
        
        self.saved_msg.show()
        QTimer.singleShot(2000, self.saved_msg.hide)
        
        if self.show_cat_cb.isChecked():
            self.start_tracking()
        else:
            self.stop_tracking()

    def setup_autostart(self, enable):
        import platform
        executable = sys.executable
        is_bundled = getattr(sys, 'frozen', False)
        
        if platform.system() == "Darwin":
            plist_path = os.path.expanduser("~/Library/LaunchAgents/com.hoainam.catgatekeeper.plist")
            if enable:
                if is_bundled:
                    args_xml = f'<string>{executable}</string>'
                else:
                    args_xml = f'<string>{executable}</string>\n        <string>{os.path.abspath(__file__)}</string>'
                    
                plist_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.hoainam.catgatekeeper</string>
    <key>ProgramArguments</key>
    <array>
        {args_xml}
    </array>
    <key>RunAtLoad</key>
    <true/>
</dict>
</plist>'''
                try:
                    with open(plist_path, 'w') as f:
                        f.write(plist_content)
                except Exception:
                    pass
            else:
                if os.path.exists(plist_path):
                    os.remove(plist_path)
        elif platform.system() == "Windows":
            import winreg
            key = winreg.HKEY_CURRENT_USER
            key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
            try:
                registry_key = winreg.OpenKey(key, key_path, 0, winreg.KEY_ALL_ACCESS)
                if enable:
                    if is_bundled:
                        cmd = f'"{executable}"'
                    else:
                        cmd = f'"{executable}" "{os.path.abspath(__file__)}"'
                    winreg.SetValueEx(registry_key, "CatGatekeeper", 0, winreg.REG_SZ, cmd)
                else:
                    winreg.DeleteValue(registry_key, "CatGatekeeper")
                winreg.CloseKey(registry_key)
            except Exception:
                pass

    def start_tracking(self):
        self.work_seconds_left = (self.work_spinbox.value() * 60) + self.work_sec_spinbox.value()
        if self.work_seconds_left == 0:
            self.work_seconds_left = 1
        self.is_running = True
        self.update_status_label()
        self.work_timer.start(1000)
        
    def stop_tracking(self):
        self.is_running = False
        self.work_timer.stop()
        texts = self.i18n.get(self.current_lang, self.i18n["vi"])
        self.status_label.setText(texts["tracking_disabled"])
        
    def tick_work_timer(self):
        if self.work_seconds_left > 0:
            self.work_seconds_left -= 1
            if self.work_seconds_left % 60 == 0:
                self.total_work_minutes += 1
                self.settings.setValue("stats_work_m", self.total_work_minutes)
                self.refresh_dashboard()
            self.update_status_label()
        else:
            self.work_timer.stop()
            self.show_cat_lock()
            
    def update_status_label(self):
        m = self.work_seconds_left // 60
        s = self.work_seconds_left % 60
        texts = self.i18n.get(self.current_lang, self.i18n["vi"])
        self.status_label.setText(texts["status_tracking"].format(m, s))
        
    def show_cat_lock(self):
        if not self.show_cat_cb.isChecked():
            return
            
        break_total_seconds = (self.break_spinbox.value() * 60) + self.break_sec_spinbox.value()
        if break_total_seconds == 0:
            break_total_seconds = 1
            
        strict = self.strict_mode_cb.isChecked()
        self.lock_window = LockScreenWindow(break_total_seconds, strict, self.current_lang)
        self.lock_window.break_finished.connect(self.on_break_finished)
        self.lock_window.snooze_accepted.connect(self.on_snooze_accepted)
        self.lock_window.showFullScreen()

    def on_break_finished(self):
        self.total_breaks += 1
        self.settings.setValue("stats_breaks", self.total_breaks)
        self.refresh_dashboard()
        self.start_tracking()
        
    def on_snooze_accepted(self):
        if self.snoozes_today >= 2:
            texts = self.i18n.get(self.current_lang, self.i18n["vi"])
            self.status_label.setText(texts["snooze_limit"])
            self.show_cat_lock()
            return
            
        self.snoozes_today += 1
        self.total_snoozes += 1
        self.settings.setValue("snoozes_today", self.snoozes_today)
        self.settings.setValue("stats_snoozes", self.total_snoozes)
        self.refresh_dashboard()
        
        # Add 5 minutes
        self.work_seconds_left = 5 * 60
        self.is_running = True
        self.update_status_label()
        self.work_timer.start(1000)

    def closeEvent(self, event):
        event.ignore()
        self.hide()
        
        # Notify about running in background
        title = "Focus Pet Pro"
        msg = "Chương trình đang chạy ngầm ở đây." if self.current_lang == "vi" else "Running in the background."
        
        self.tray_icon.showMessage(title, msg, QSystemTrayIcon.MessageIcon.Information, 2000)

    def apply_dark_theme(self):
        toggle_off = resource_path("assets/toggle_off.svg")
        toggle_on = resource_path("assets/toggle_on.svg")
        
        self.setStyleSheet(f"""
            QWidget {{
                background-color: #0f172a;
                color: #f8fafc;
                font-family: ".AppleSystemUIFont", "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            }}
            QTabWidget::pane {{
                border: none;
                background: transparent;
            }}
            QTabWidget::tab-bar {{
                alignment: center;
            }}
            QTabBar::tab {{
                background: transparent;
                color: #64748b;
                padding: 10px 24px;
                border-bottom: 2px solid transparent;
                font-size: 15px;
                font-weight: bold;
                margin: 0 5px;
            }
            QTabBar::tab:selected {
                color: #3b82f6;
                border-bottom: 3px solid #3b82f6;
            }
            QTabBar::tab:hover {
                color: #cbd5e1;
            }
            QLabel {
                font-size: 15px;
                color: #e2e8f0;
                font-weight: 600;
            }
            QLabel#footer {
                font-size: 11px;
                color: #475569;
                font-style: italic;
                margin-top: 5px;
                qproperty-alignment: AlignRight;
            }
            QSpinBox {
                background-color: #1e293b;
                color: #f8fafc;
                border: 1px solid #334155;
                border-radius: 8px;
                padding: 6px 10px;
                font-size: 15px;
                font-weight: bold;
            }
            QSpinBox::up-button, QSpinBox::down-button {
                width: 0px; 
            }
            QComboBox {
                background-color: #1e293b;
                color: #f8fafc;
                border: 1px solid #334155;
                border-radius: 8px;
                padding: 6px 10px;
                font-size: 15px;
                font-weight: bold;
            }
            QComboBox QAbstractItemView {
                background-color: #1e293b;
                selection-background-color: #3b82f6;
                border-radius: 8px;
            }
            QCheckBox {
                spacing: 0px;
            }}
            QCheckBox::indicator {{
                width: 44px;
                height: 26px;
                image: url('{toggle_off}');
                border: none;
                background: transparent;
            }}
            QCheckBox::indicator:checked {{
                image: url('{toggle_on}');
            }}
            QPushButton#saveBtn {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #3b82f6, stop:1 #8b5cf6);
                color: white;
                border: none;
                border-radius: 12px;
                padding: 16px;
                font-size: 16px;
                font-weight: bold;
                margin-top: 15px;
            }
            QPushButton#saveBtn:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #2563eb, stop:1 #7c3aed);
            }
            QLabel#savedMsg {{
                font-size: 14px;
                color: #10b981;
                font-weight: bold;
                margin-top: 5px;
            }}
            QPushButton#infoBtn {{
                background-color: #334155;
                color: #e2e8f0;
                border-radius: 12px;
                font-size: 14px;
                font-weight: bold;
                border: none;
            }}
            QPushButton#infoBtn:hover {{
                background-color: #3b82f6;
                color: white;
            }}
            
            /* CleanMyMac Style Dashboard Cards */
            QFrame#dashboardCard {
                background-color: #1e293b;
                border: 1px solid #334155;
                border-radius: 16px;
            }
            QFrame#dashboardCard:hover {
                background-color: #24354b;
                border: 1px solid #3b82f6;
            }
            QLabel#cardNum {
                font-weight: 800;
                background: transparent;
            }
            QLabel#cardTitle {
                font-size: 13px;
                color: #94a3b8;
                font-weight: 600;
                background: transparent;
            }}
        """)

def main():
    # Fix High DPI scaling and visual glitches on Windows
    os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "1"
    os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
    
    app = QApplication(sys.argv)
    if os.name == 'nt':
        app.setStyle("Fusion")
    
    app.setQuitOnLastWindowClosed(False)
    window = CatGatekeeperApp()
    window.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()
