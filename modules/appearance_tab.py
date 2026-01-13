"""
AppearanceTab module for appearance settings
"""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel, QSpinBox, QCheckBox, QPushButton, QLineEdit, QFileDialog, QMessageBox
from pathlib import Path
import subprocess

class AppearanceTab(QWidget):
    """Appearance settings tab"""
    
    def __init__(self, config_parser):
        super().__init__()
        self.config = config_parser
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # Gaps settings
        gaps_group = QGroupBox("Gaps")
        gaps_layout = QVBoxLayout()
        
        inner_layout = QHBoxLayout()
        inner_layout.addWidget(QLabel("Inner Gaps:"))
        self.inner_gaps = QSpinBox()
        self.inner_gaps.setRange(0, 50)
        self.inner_gaps.setValue(int(self.config.get_value("gaps inner", "6").split()[0]))
        inner_layout.addWidget(self.inner_gaps)
        gaps_layout.addLayout(inner_layout)
        
        outer_layout = QHBoxLayout()
        outer_layout.addWidget(QLabel("Outer Gaps:"))
        self.outer_gaps = QSpinBox()
        self.outer_gaps.setRange(0, 50)
        self.outer_gaps.setValue(int(self.config.get_value("gaps outer", "3").split()[0]))
        outer_layout.addWidget(self.outer_gaps)
        gaps_layout.addLayout(outer_layout)
        
        self.smart_gaps = QCheckBox("Smart Gaps")
        self.smart_gaps.setChecked("smart_gaps on" in ''.join(self.config.config_lines))
        gaps_layout.addWidget(self.smart_gaps)
        
        self.smart_borders = QCheckBox("Smart Borders")
        self.smart_borders.setChecked("smart_borders on" in ''.join(self.config.config_lines))
        gaps_layout.addWidget(self.smart_borders)
        
        gaps_group.setLayout(gaps_layout)
        layout.addWidget(gaps_group)
        
        # Border settings
        border_group = QGroupBox("Borders")
        border_layout = QVBoxLayout()
        
        border_size_layout = QHBoxLayout()
        border_size_layout.addWidget(QLabel("Border Width:"))
        self.border_width = QSpinBox()
        self.border_width.setRange(0, 10)
        
        # Extract border width from config
        border_value = self.config.get_value('for_window [class="^.*"] border pixel', '2')
        try:
            self.border_width.setValue(int(border_value))
        except ValueError:
            self.border_width.setValue(2)
        
        border_size_layout.addWidget(self.border_width)
        border_layout.addLayout(border_size_layout)
        
        border_group.setLayout(border_layout)
        layout.addWidget(border_group)
        
        # Wallpaper settings
        wallpaper_group = QGroupBox("Wallpaper Settings")
        wallpaper_layout = QVBoxLayout()
        
        wallpaper_info = QLabel("Set wallpaper and apply colors")
        wallpaper_layout.addWidget(wallpaper_info)
        
        wallpaper_path_layout = QHBoxLayout()
        self.wallpaper_path = QLineEdit()
        self.wallpaper_path.setPlaceholderText("Select wallpaper...")
        wallpaper_path_layout.addWidget(self.wallpaper_path)
        
        browse_btn = QPushButton("Browse")
        browse_btn.clicked.connect(self.browse_wallpaper)
        wallpaper_path_layout.addWidget(browse_btn)
        wallpaper_layout.addLayout(wallpaper_path_layout)
        
        set_wallpaper_btn = QPushButton("Set Wallpaper")
        set_wallpaper_btn.clicked.connect(self.set_wallpaper)
        wallpaper_layout.addWidget(set_wallpaper_btn)
        
        wallpaper_group.setLayout(wallpaper_layout)
        layout.addWidget(wallpaper_group)
        
        layout.addStretch()
        self.setLayout(layout)
    
    def browse_wallpaper(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Wallpaper", str(Path.home()),
            "Images (*.png *.jpg *.jpeg *.webp)"
        )
        if file_path:
            self.wallpaper_path.setText(file_path)
    
    def set_wallpaper(self):
        wallpaper = self.wallpaper_path.text()
        if not wallpaper or not Path(wallpaper).exists():
            QMessageBox.warning(self, "Error", "Please select a valid wallpaper")
            return

        try:
            # Set wallpaper using feh
            subprocess.run(['feh', '--bg-fill', wallpaper], check=True)

            # Generate colors using matugen
            subprocess.run(['matugen', 'image', wallpaper], check=True)

            # Reload Xresources
            xresources_path = Path.home() / ".Xresources"
            if xresources_path.exists():
                subprocess.run(['xrdb', '-merge', str(xresources_path)], check=True)

            # Small delay to ensure xrdb finishes
            import time
            time.sleep(1)

            # Reload i3
            subprocess.run(['i3-msg', 'restart'], check=True)

            QMessageBox.information(self, "Success", "Wallpaper set successfully!")
        except subprocess.CalledProcessError as e:
            QMessageBox.critical(self, "Error", f"Failed to set wallpaper: {e}")
        except FileNotFoundError as e:
            QMessageBox.critical(self, "Error", f"Required tool not found: {e.filename}. Please install feh, matugen, and xrdb.")
    
    
    def apply_settings(self):
        try:
            # Update gaps with proper formatting
            self.config.set_value("gaps inner", f"{self.inner_gaps.value()} px")
            self.config.set_value("gaps outer", f"{self.outer_gaps.value()} px")
            
            # Update smart gaps/borders
            smart_gaps_str = "on" if self.smart_gaps.isChecked() else "off"
            smart_borders_str = "on" if self.smart_borders.isChecked() else "off"
            self.config.set_value("smart_gaps", smart_gaps_str)
            self.config.set_value("smart_borders", smart_borders_str)
            
            # Update border width
            border_str = f'for_window [class="^.*"] border pixel {self.border_width.value()}'
            for i, line in enumerate(self.config.config_lines):
                if 'for_window [class="^.*"] border pixel' in line:
                    self.config.config_lines[i] = border_str + '\n'
                    break
            else:
                # If not found, add it
                self.config.config_lines.append(border_str + '\n')
            
            self.config.save()
            
            # Reload i3 with error handling
            if not self.config.reload_i3():
                send_notification("Warning", "Configuration saved but i3 restart failed. Changes may not be visible until you manually restart i3.")
            else:
                send_notification("Success", "Settings applied successfully!")
        
        except Exception as e:
            send_notification("Error", f"Failed to apply settings: {str(e)}")


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