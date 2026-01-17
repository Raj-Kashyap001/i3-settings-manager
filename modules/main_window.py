"""
MainWindow module for the main application window
"""

import subprocess
import sys
from PyQt6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, QLabel, QPushButton, QCheckBox, QMessageBox, QDialog, QTextEdit, QDialogButtonBox
from PyQt6.QtGui import QIcon, QPixmap
from PyQt6.QtCore import Qt
from pathlib import Path

class MainWindow(QMainWindow):
    """Main application window"""

    def __init__(self):
        super().__init__()
        self.config_path = Path.home() / ".config" / "i3" / "config"
        from modules.i3_config_parser import I3ConfigParser
        from modules.history_manager import HistoryManager
        self.config = I3ConfigParser(self.config_path)
        self.history = HistoryManager(self.config_path)

        # Set theme (default to dark for now)
        self.current_theme = "dark"
        self.setObjectName("dark")

        self.setWindowTitle("i3 Settings Manager")
        self.setMinimumSize(900, 700)

        # Set application icon
        self.set_window_icon()
        
        self.init_ui()
        
        # Set up signal handler for Ctrl+C
        import signal
        signal.signal(signal.SIGINT, lambda signum, frame: self.close())
    
    def set_window_icon(self):
        """Set application icon"""
        try:
            # Try bundled icon first (for frozen binary)
            icon_path = None
            if hasattr(sys, '_MEIPASS'):
                # Running as PyInstaller bundle
                bundled_path = Path(sys._MEIPASS) / "appicon.png"
                if bundled_path.exists():
                    icon_path = bundled_path
            else:
                # Running as script
                script_path = Path("appicon.png")
                if script_path.exists():
                    icon_path = script_path

            if icon_path:
                icon = QIcon(str(icon_path))
                self.setWindowIcon(icon)
        except Exception as e:
            print(f"Failed to set window icon: {e}")
    
    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout()
        
        # Header with logo - centered
        header_widget = QWidget()
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(0, 0, 0, 8)  # Bottom margin of 8px
        
        # Add logo
        logo_label = QLabel()
        try:
            # Try bundled logo first (for frozen binary)
            logo_path = None
            if hasattr(sys, '_MEIPASS'):
                # Running as PyInstaller bundle
                bundled_path = Path(sys._MEIPASS) / "i3wm-logo.png"
                if bundled_path.exists():
                    logo_path = bundled_path
            else:
                # Running as script
                script_path = Path("i3wm-logo.png")
                if script_path.exists():
                    logo_path = script_path

            if logo_path:
                pixmap = QPixmap(str(logo_path))
                # Scale logo to appropriate size
                logo_label.setPixmap(pixmap.scaled(48, 48, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
                logo_label.setStyleSheet("margin-right: 8px;")  # Reduced gap
        except Exception as e:
            print(f"Failed to load logo: {e}")
        
        header_layout.addWidget(logo_label)
        
        # Header text
        header = QLabel("i3 Window Manager Settings")
        header.setStyleSheet("font-size: 18px; font-weight: bold;")
        header_layout.addWidget(header)
        
        # Center the header content
        header_layout.addStretch()
        
        layout.addWidget(header_widget)
        
        # Tab widget
        self.tabs = QTabWidget()
        
        # Add tabs
        from modules.appearance_tab import AppearanceTab
        from modules.display_tab import DisplayTab
        from modules.startup_apps_tab import StartupAppsTab
        from modules.keybinds_tab import KeybindsTab
        from modules.history_tab import HistoryTab
        from modules.window_class_tab import WindowClassTab
        from modules.picom_tab import PicomTab

        self.tabs.addTab(AppearanceTab(self.config), "Appearance")
        self.tabs.addTab(PicomTab(self.config), "Compositor(picom)")
        self.tabs.addTab(DisplayTab(self.config), "Display")
        self.tabs.addTab(StartupAppsTab(self.config), "Startup Apps")
        self.tabs.addTab(KeybindsTab(self.config), "Keybindings")
        self.tabs.addTab(WindowClassTab(self.config), "Window Class")
        self.tabs.addTab(HistoryTab(self.history, self.config), "History")
        
        layout.addWidget(self.tabs)
        
        # Footer buttons
        footer_layout = QHBoxLayout()
        
        self.show_diff_checkbox = QCheckBox("Show changes before applying")
        footer_layout.addWidget(self.show_diff_checkbox)
        
        save_btn = QPushButton("Apply")
        save_btn.clicked.connect(self.save_and_reload)
        footer_layout.addWidget(save_btn)
        
        edit_config_btn = QPushButton("Edit Config")
        edit_config_btn.clicked.connect(self.edit_config)
        footer_layout.addWidget(edit_config_btn)
        

        footer_layout.addStretch()

        about_btn = QPushButton("About")
        about_btn.clicked.connect(self.show_about)
        footer_layout.addWidget(about_btn)
        
        layout.addLayout(footer_layout)
        
        central_widget.setLayout(layout)
    
    def save_and_reload(self):
        """Save config and reload i3"""
        # Create backup before saving
        self.history.save_backup("Auto-save before reload")
        
        # Get current config for diff
        original_config = ''.join(self.config.config_lines)
        
        # Apply all tab settings
        for i in range(self.tabs.count()):
            widget = self.tabs.widget(i)
            if hasattr(widget, 'apply_settings'):
                try:
                    widget.apply_settings()
                except Exception as e:
                    send_notification("Warning", f"Failed to apply settings from {widget.windowTitle()}: {str(e)}")
                    return
            elif hasattr(widget, 'apply_startup_commands'):
                try:
                    widget.apply_startup_commands()
                except Exception as e:
                    send_notification("Warning", f"Failed to apply startup commands: {str(e)}")
                    return
        
        # Get modified config
        modified_config = ''.join(self.config.config_lines)
        
        # Show diff if requested
        if self.show_diff_checkbox.isChecked() and original_config != modified_config:
            self.show_config_diff(original_config, modified_config)
        else:
            # Save and reload directly
            self.config.save()
            if self.config.reload_i3():
                send_notification("Success", "Configuration saved and i3 restart initiated!")
            else:
                send_notification("Warning", "Configuration saved but i3 restart failed")
    
    def show_config_diff(self, original, modified):
        """Show diff between original and modified config"""
        dialog = QDialog(self)
        dialog.setWindowTitle("Configuration Changes")
        dialog.resize(800, 600)
        
        layout = QVBoxLayout()
        
        # Create diff view
        diff_text = QTextEdit()
        diff_text.setReadOnly(True)
        diff_text.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        
        # Simple diff implementation
        original_lines = original.split('\n')
        modified_lines = modified.split('\n')
        
        diff_content = ""
        max_len = max(len(original_lines), len(modified_lines))
        
        for i in range(max_len):
            if i < len(original_lines) and i < len(modified_lines):
                if original_lines[i] != modified_lines[i]:
                    diff_content += f"- {original_lines[i]}\n+ {modified_lines[i]}\n"
                else:
                    diff_content += f"  {original_lines[i]}\n"
            elif i < len(original_lines):
                diff_content += f"- {original_lines[i]}\n"
            else:
                diff_content += f"+ {modified_lines[i]}\n"
        
        diff_text.setPlainText(diff_content)
        
        layout.addWidget(diff_text)
        
        # Buttons
        btn_layout = QHBoxLayout()
        
        apply_btn = QPushButton("Apply Changes")
        apply_btn.clicked.connect(lambda: self.apply_diff_changes(dialog))
        btn_layout.addWidget(apply_btn)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(dialog.reject)
        btn_layout.addWidget(cancel_btn)
        
        layout.addLayout(btn_layout)
        
        dialog.setLayout(layout)
        dialog.exec()
    
    def apply_diff_changes(self, dialog):
        """Apply the changes shown in diff"""
        self.config.save()
        if self.config.reload_i3():
            QMessageBox.information(self, "Success", "Configuration changes applied and i3 reloaded!")
        else:
            QMessageBox.warning(self, "Warning", "Configuration saved but i3 reload failed")
        dialog.accept()
    
    def show_about(self):
        """Show about dialog"""
        from PyQt6.QtWidgets import QLabel
        from PyQt6.QtGui import QFont, QDesktopServices
        from PyQt6.QtCore import QUrl

        dialog = QDialog(self)
        dialog.setWindowTitle("About i3 Settings Manager")
        dialog.resize(500, 400)

        layout = QVBoxLayout()

        # Title
        title = QLabel("i3 Settings Manager v1.2")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title)

        # Description
        desc = QLabel("A GUI for managing i3wm configuration")
        desc.setStyleSheet("font-size: 12px; margin-bottom: 10px;")
        layout.addWidget(desc)

        # Features
        features_title = QLabel("Features:")
        features_title.setStyleSheet("font-weight: bold; margin-top: 10px;")
        layout.addWidget(features_title)

        features = QLabel(
            "• Visual appearance customization\n"
            "• Keybinding management with conflict detection\n"
            "• Configuration history and backups\n"
            "• Wallpaper management\n"
            "• Monitor refresh rate control\n"
            "• Autostart application management"
        )
        features.setStyleSheet("font-size: 11px;")
        layout.addWidget(features)

        # Config location
        config_info = QLabel("Config location: ~/.config/i3/config")
        config_info.setStyleSheet("font-size: 11px; margin-top: 10px;")
        layout.addWidget(config_info)

        # GitHub link
        github_link = QLabel('<a href="https://github.com/Raj-Kashyap001" style="color: #0078d4;">GitHub: Raj-Kashyap001</a>')
        github_link.setOpenExternalLinks(True)
        github_link.setStyleSheet("font-size: 11px; margin-top: 15px;")
        layout.addWidget(github_link)

        # Copyright
        copyright = QLabel("© Raj Kashyap - 2026")
        copyright.setStyleSheet("font-size: 10px; color: #666; margin-top: 10px;")
        layout.addWidget(copyright)

        layout.addStretch()

        # Close button
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(dialog.accept)
        layout.addWidget(close_btn, alignment=Qt.AlignmentFlag.AlignCenter)

        dialog.setLayout(layout)
        dialog.exec()
    
    def edit_config(self):
        """Show and edit current config"""
        dialog = QDialog(self)
        dialog.setWindowTitle("Edit i3 Configuration")
        dialog.resize(800, 600)
        
        layout = QVBoxLayout()
        
        text_edit = QTextEdit()
        text_edit.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        
        # Load current config
        try:
            with open(self.config_path, 'r') as f:
                content = f.read()
            text_edit.setPlainText(content)
        except Exception as e:
            text_edit.setPlainText(f"Failed to load config: {str(e)}")
        
        layout.addWidget(text_edit)
        
        # Buttons
        btn_layout = QHBoxLayout()
        
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(lambda: self.save_config_edits(text_edit.toPlainText(), dialog))
        btn_layout.addWidget(save_btn)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(dialog.reject)
        btn_layout.addWidget(cancel_btn)
        
        layout.addLayout(btn_layout)
        
        dialog.setLayout(layout)
        dialog.exec()
    
    def save_config_edits(self, content, dialog):
        """Save edited config"""
        try:
            # Create backup
            self.history.save_backup("Manual config edit")
            
            # Save new content
            with open(self.config_path, 'w') as f:
                f.write(content)
            
            # Reload config
            self.config.load()
            
            # Reload i3
            if self.config.reload_i3():
                QMessageBox.information(self, "Success", "Configuration saved and reloaded!")
                dialog.accept()
            else:
                QMessageBox.warning(self, "Warning", "Configuration saved but i3 reload failed")
                dialog.accept()
        
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save config: {str(e)}")

    def switch_theme(self):
        """Switch between light and dark themes"""
        if self.current_theme == "light":
            self.current_theme = "dark"
            self.setObjectName("dark")
            self.sender().setText("🌙 Dark")
        else:
            self.current_theme = "light"
            self.setObjectName("light")
            self.sender().setText("☀️ Light")

        # Force stylesheet reapplication
        self.style().unpolish(self)
        self.style().polish(self)
        self.update()


def send_notification(title, message):
    """Send notification using dunst or notify-send"""
    try:
        # Try dunst first
        subprocess.run(['dunstify', title, message], check=True)
    except:
        try:
            # Fallback to notify-send
            subprocess.run(['notify-send', title, message], check=True)
        except Exception as e:
            print(f"Failed to send notification: {e}")