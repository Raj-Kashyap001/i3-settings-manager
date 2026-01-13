"""
i3 Settings GUI - A settings manager for i3wm
"""

import sys
import os
import re
import subprocess
import json
from pathlib import Path
from datetime import datetime
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTabWidget, QLabel, QPushButton, QSpinBox, QComboBox,
    QLineEdit, QCheckBox, QGroupBox, QScrollArea, QMessageBox,
    QFileDialog, QTableWidget, QTableWidgetItem, QHeaderView,
    QDialog, QDialogButtonBox, QTextEdit, QListWidget, QStatusBar
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QKeySequence, QColor, QPalette, QIcon, QPixmap
import subprocess
import time
import threading
try:
    import i3ipc
    HAS_I3IPC = True
except ImportError:
    HAS_I3IPC = False
    QMessageBox.warning(None, "Missing Dependency",
                      "python-i3ipc is not installed. Some features will use fallback methods.\n\n"
                      "Please install it for better performance: pip install i3ipc")

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


class KeybindDialog(QDialog):
    """Dialog for capturing keybind input"""
    
    def __init__(self, parent=None, current_bind=""):
        super().__init__(parent)
        self.setWindowTitle("Capture Keybind")
        self.setModal(True)
        self.captured_keys = []
        self.result_bind = current_bind
        
        layout = QVBoxLayout()
        
        self.label = QLabel("Press your key combination...\n(Press Escape to cancel)")
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.label)
        
        self.display = QLineEdit()
        self.display.setReadOnly(True)
        self.display.setText(current_bind)
        layout.addWidget(self.display)
        
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
        self.setLayout(layout)
        self.setMinimumWidth(400)
    
    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.reject()
            return
        
        modifiers = []
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            modifiers.append("Control")
        if event.modifiers() & Qt.KeyboardModifier.AltModifier:
            modifiers.append("Mod1")
        if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
            modifiers.append("Shift")
        if event.modifiers() & Qt.KeyboardModifier.MetaModifier:
            modifiers.append("Mod4")
        
        key = QKeySequence(event.key()).toString()
        
        # Special key mappings
        key_map = {
            "Return": "Return",
            "Space": "space",
            "Tab": "Tab",
            "Left": "Left",
            "Right": "Right",
            "Up": "Up",
            "Down": "Down",
            "-": "minus",
            "=": "equal",
            "[": "bracketleft",
            "]": "bracketright",
            ";": "semicolon",
            "'": "apostrophe",
            ",": "comma",
            ".": "period",
            "/": "slash",
            "\\": "backslash",
            "`": "grave",
        }
        
        key = key_map.get(key, key.lower())
        
        if modifiers or key not in ["Shift", "Control", "Alt", "Meta"]:
            bind_str = "+".join(modifiers + [key]) if modifiers else key
            self.result_bind = bind_str
            self.display.setText(bind_str)


class HistoryManager:
    """Manages configuration history"""
    
    def __init__(self, config_path):
        self.config_path = Path(config_path)
        self.history_dir = self.config_path.parent / ".i3config_history"
        self.history_dir.mkdir(exist_ok=True)
        self.max_history = 50
    
    def save_backup(self, label="Manual backup"):
        """Save current config to history"""
        if not self.config_path.exists():
            return None
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = self.history_dir / f"config_{timestamp}"
        
        with open(self.config_path) as f:
            content = f.read()
        
        with open(backup_file, 'w') as f:
            f.write(content)
        
        # Save metadata
        meta_file = backup_file.with_suffix('.json')
        with open(meta_file, 'w') as f:
            json.dump({
                'timestamp': timestamp,
                'label': label,
                'size': len(content)
            }, f)
        
        self._cleanup_old_backups()
        return backup_file
    
    def _cleanup_old_backups(self):
        """Keep only max_history backups"""
        backups = sorted(self.history_dir.glob("config_*"), 
                        key=lambda x: x.stat().st_mtime, reverse=True)
        
        for backup in backups[self.max_history:]:
            backup.unlink(missing_ok=True)
            backup.with_suffix('.json').unlink(missing_ok=True)
    
    def get_history(self):
        """Get list of all backups"""
        backups = []
        for config_file in sorted(self.history_dir.glob("config_*"), 
                                 key=lambda x: x.stat().st_mtime, reverse=True):
            if config_file.suffix == '.json':
                continue
            
            meta_file = config_file.with_suffix('.json')
            if meta_file.exists():
                with open(meta_file) as f:
                    meta = json.load(f)
            else:
                meta = {
                    'timestamp': config_file.stem.split('_', 1)[1],
                    'label': 'Unknown',
                    'size': config_file.stat().st_size
                }
            
            backups.append({
                'file': config_file,
                'meta': meta
            })
        
        return backups
    
    def restore_backup(self, backup_file):
        """Restore a backup"""
        with open(backup_file) as f:
            content = f.read()
        
        # Save current as backup before restoring
        self.save_backup("Before restore")
        
        with open(self.config_path, 'w') as f:
            f.write(content)


class I3ConfigParser:
    """Parse and modify i3 config file"""

    def __init__(self, config_path):
        self.config_path = Path(config_path)
        self.config_lines = []
        self.keybinds = {}
        self.default_config_path = Path("config.default")
        self.load()
    
    def load_default_config(self):
        """Load default configuration"""
        if self.default_config_path.exists():
            try:
                with open(self.default_config_path) as f:
                    return f.readlines()
            except Exception as e:
                print(f"Failed to load default config: {e}")
        return []
    
    def load(self):
        """Load config file"""
        if not self.config_path.exists():
            return
        
        with open(self.config_path) as f:
            self.config_lines = f.readlines()
        
        self._parse_keybinds()
    
    def _parse_keybinds(self):
        """Parse all keybindings from config"""
        self.keybinds = {}
        bind_pattern = re.compile(r'^\s*bindsym\s+(\S+)\s+(.+)$')
        bindcode_pattern = re.compile(r'^\s*bindcode\s+(\S+)\s+(.+)$')
        
        for i, line in enumerate(self.config_lines):
            match = bind_pattern.match(line)
            if match:
                keybind = match.group(1)
                command = match.group(2).strip()
                self.keybinds[keybind] = {
                    'command': command,
                    'line': i,
                    'type': 'bindsym'
                }
            
            match = bindcode_pattern.match(line)
            if match:
                keycode = match.group(1)
                command = match.group(2).strip()
                self.keybinds[f"code:{keycode}"] = {
                    'command': command,
                    'line': i,
                    'type': 'bindcode'
                }
    
    def get_value(self, key, default=None):
        """Get config value"""
        pattern = re.compile(rf'^\s*{re.escape(key)}\s+(.+)$', re.MULTILINE)
        content = ''.join(self.config_lines)
        match = pattern.search(content)
        return match.group(1).strip() if match else default
    
    def set_value(self, key, value):
        """Set config value"""
        pattern = re.compile(rf'^\s*{re.escape(key)}\s+.+$')
        new_line = f"{key} {value}\n"
        
        for i, line in enumerate(self.config_lines):
            if pattern.match(line):
                self.config_lines[i] = new_line
                return
        
        # If not found, add it
        self.config_lines.append(new_line)
    
    def update_keybind(self, old_bind, new_bind, command):
        """Update a keybinding"""
        if old_bind in self.keybinds:
            line_num = self.keybinds[old_bind]['line']
            bind_type = self.keybinds[old_bind]['type']
            
            if bind_type == 'bindsym':
                self.config_lines[line_num] = f"bindsym {new_bind} {command}\n"
            else:
                keycode = old_bind.split(':')[1]
                self.config_lines[line_num] = f"bindcode {keycode} {command}\n"
            
            # Update internal tracking
            del self.keybinds[old_bind]
            self.keybinds[new_bind] = {
                'command': command,
                'line': line_num,
                'type': bind_type
            }
    
    def check_conflicts(self, new_bind, exclude_bind=None):
        """Check if keybind conflicts with existing ones"""
        conflicts = []
        for bind, data in self.keybinds.items():
            if bind == exclude_bind:
                continue
            if bind == new_bind:
                conflicts.append((bind, data['command']))
        return conflicts
    
    def save(self):
        """Save config file"""
        with open(self.config_path, 'w') as f:
            f.writelines(self.config_lines)
    
    def reload_i3(self):
        """Reload i3 configuration with restart and delay"""
        try:
            if HAS_I3IPC:
                conn = i3ipc.Connection()
                # Use restart instead of reload with 500ms delay
                def restart_with_delay():
                    time.sleep(0.5)
                    conn.command('restart')
                
                threading.Thread(target=restart_with_delay, daemon=True).start()
                return True
            else:
                # Use restart with delay via subprocess
                def restart_delayed():
                    time.sleep(0.5)
                    subprocess.run(['i3-msg', 'restart'], check=True)
                
                threading.Thread(target=restart_delayed, daemon=True).start()
                return True
        except Exception as e:
            print(f"Failed to restart i3: {e}")
            return False
    
    def get_i3_version(self):
        """Get i3 version"""
        try:
            if HAS_I3IPC:
                conn = i3ipc.Connection()
                version = conn.get_version()
                return f"{version.major}.{version.minor}.{version.patch}"
            else:
                result = subprocess.run(['i3', '--version'], capture_output=True, text=True, check=True)
                version_line = result.stdout.split('\n')[0]
                return version_line.split()[-1]
        except Exception as e:
            print(f"Failed to get i3 version: {e}")
            return "Unknown"


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
        
        wallpaper_btn_layout = QHBoxLayout()
        
        set_wallpaper_btn = QPushButton("Set Wallpaper")
        set_wallpaper_btn.clicked.connect(self.set_wallpaper)
        wallpaper_btn_layout.addWidget(set_wallpaper_btn)
        
        random_wallpaper_btn = QPushButton("Random Wallpaper")
        random_wallpaper_btn.clicked.connect(self.set_random_wallpaper)
        wallpaper_btn_layout.addWidget(random_wallpaper_btn)
        
        wallpaper_layout.addLayout(wallpaper_btn_layout)
        
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
            # Set wallpaper using i3wallch
            subprocess.run(['i3wallch', wallpaper], check=True)
            QMessageBox.information(self, "Success", "Wallpaper set successfully!")
        except subprocess.CalledProcessError as e:
            QMessageBox.critical(self, "Error", f"Failed to set wallpaper: {e.stderr}")
        except FileNotFoundError:
            QMessageBox.critical(self, "Error", "i3wallch not found. Please install it first.")
    
    def set_random_wallpaper(self):
        try:
            # Set random wallpaper using i3wallch
            subprocess.run(['i3wallch', 'random'], check=True)
            QMessageBox.information(self, "Success", "Random wallpaper set successfully!")
        except subprocess.CalledProcessError as e:
            QMessageBox.critical(self, "Error", f"Failed to set random wallpaper: {e.stderr}")
        except FileNotFoundError:
            QMessageBox.critical(self, "Error", "i3wallch not found. Please install it first.")
    
    def apply_matugen_colors(self, colors):
        """Apply matugen colors to i3 config"""
        try:
            # Extract colors (matugen output structure may vary)
            if 'colors' in colors:
                color_data = colors['colors']
            else:
                color_data = colors
            
            # Find color variables section and update
            # This is a simplified version - adjust based on your config structure
            primary = color_data.get('primary', '#81a1c1')
            background = color_data.get('background', '#2e3440')
            
            # Update color variables in config
            for i, line in enumerate(self.config.config_lines):
                if line.strip().startswith('set $border'):
                    self.config.config_lines[i] = f'set $border   {primary}\n'
                elif line.strip().startswith('set $bg'):
                    self.config.config_lines[i] = f'set $bg       {background}\n'
        
        except Exception as e:
            QMessageBox.warning(self, "Warning", f"Partial color application: {str(e)}")
    
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


class KeybindsTab(QWidget):
    """Keybindings management tab"""
    
    def __init__(self, config_parser):
        super().__init__()
        self.config = config_parser
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # Search bar
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("Search:"))
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Filter keybindings...")
        self.search_box.textChanged.connect(self.filter_keybinds)
        search_layout.addWidget(self.search_box)
        layout.addLayout(search_layout)
        
        # Keybinds table
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Keybind", "Command", "Actions"])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.table)
        
        # Buttons
        btn_layout = QHBoxLayout()
        
        add_btn = QPushButton("Add Keybind")
        add_btn.clicked.connect(self.add_keybind)
        btn_layout.addWidget(add_btn)
        
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.load_keybinds)
        btn_layout.addWidget(refresh_btn)
        
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        
        self.setLayout(layout)
        self.load_keybinds()
    
    def load_keybinds(self):
        """Load keybindings into table"""
        self.config._parse_keybinds()
        self.table.setRowCount(0)
        
        for bind, data in sorted(self.config.keybinds.items()):
            self.add_keybind_row(bind, data['command'])
    
    def add_keybind_row(self, bind, command):
        """Add a keybind row to table"""
        row = self.table.rowCount()
        self.table.insertRow(row)
        
        self.table.setItem(row, 0, QTableWidgetItem(bind))
        self.table.setItem(row, 1, QTableWidgetItem(command))
        
        # Action buttons
        action_widget = QWidget()
        action_layout = QHBoxLayout()
        action_layout.setContentsMargins(4, 2, 4, 2)
        
        edit_btn = QPushButton("Edit")
        edit_btn.clicked.connect(lambda: self.edit_keybind(bind))
        action_layout.addWidget(edit_btn)
        
        delete_btn = QPushButton("Delete")
        delete_btn.clicked.connect(lambda: self.delete_keybind(bind))
        action_layout.addWidget(delete_btn)
        
        action_widget.setLayout(action_layout)
        self.table.setCellWidget(row, 2, action_widget)
    
    def filter_keybinds(self, text):
        """Filter keybinds based on search text"""
        for row in range(self.table.rowCount()):
            bind_item = self.table.item(row, 0)
            cmd_item = self.table.item(row, 1)
            
            if text.lower() in bind_item.text().lower() or text.lower() in cmd_item.text().lower():
                self.table.setRowHidden(row, False)
            else:
                self.table.setRowHidden(row, True)
    
    def add_keybind(self):
        """Add new keybind"""
        dialog = QDialog(self)
        dialog.setWindowTitle("Add Keybind")
        layout = QVBoxLayout()
        
        bind_layout = QHBoxLayout()
        bind_layout.addWidget(QLabel("Keybind:"))
        bind_input = QLineEdit()
        bind_layout.addWidget(bind_input)
        capture_btn = QPushButton("Capture")
        capture_btn.clicked.connect(lambda: self.capture_key(bind_input))
        bind_layout.addWidget(capture_btn)
        layout.addLayout(bind_layout)
        
        cmd_layout = QHBoxLayout()
        cmd_layout.addWidget(QLabel("Command:"))
        cmd_input = QLineEdit()
        cmd_layout.addWidget(cmd_input)
        layout.addLayout(cmd_layout)
        
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        
        dialog.setLayout(layout)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            bind = bind_input.text().strip()
            command = cmd_input.text().strip()
            
            if not bind or not command:
                QMessageBox.warning(self, "Error", "Both keybind and command are required")
                return
            
            # Check conflicts
            conflicts = self.config.check_conflicts(bind)
            if conflicts:
                QMessageBox.warning(
                    self, "Conflict Detected",
                    f"Keybind '{bind}' conflicts with:\n{conflicts[0][1]}"
                )
                return
            
            # Add to config
            self.config.config_lines.append(f"bindsym {bind} {command}\n")
            self.config.keybinds[bind] = {'command': command, 'line': len(self.config.config_lines) - 1, 'type': 'bindsym'}
            self.config.save()
            self.load_keybinds()
    
    def edit_keybind(self, bind):
        """Edit existing keybind"""
        data = self.config.keybinds[bind]
        
        dialog = QDialog(self)
        dialog.setWindowTitle("Edit Keybind")
        layout = QVBoxLayout()
        
        bind_layout = QHBoxLayout()
        bind_layout.addWidget(QLabel("Keybind:"))
        bind_input = QLineEdit(bind)
        bind_layout.addWidget(bind_input)
        capture_btn = QPushButton("Capture")
        capture_btn.clicked.connect(lambda: self.capture_key(bind_input))
        bind_layout.addWidget(capture_btn)
        layout.addLayout(bind_layout)
        
        cmd_layout = QHBoxLayout()
        cmd_layout.addWidget(QLabel("Command:"))
        cmd_input = QLineEdit(data['command'])
        cmd_layout.addWidget(cmd_input)
        layout.addLayout(cmd_layout)
        
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        
        dialog.setLayout(layout)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_bind = bind_input.text().strip()
            new_command = cmd_input.text().strip()
            
            if not new_bind or not new_command:
                QMessageBox.warning(self, "Error", "Both keybind and command are required")
                return
            
            # Check conflicts (exclude current bind)
            if new_bind != bind:
                conflicts = self.config.check_conflicts(new_bind, bind)
                if conflicts:
                    QMessageBox.warning(
                        self, "Conflict Detected",
                        f"Keybind '{new_bind}' conflicts with:\n{conflicts[0][1]}"
                    )
                    return
            
            self.config.update_keybind(bind, new_bind, new_command)
            self.config.save()
            self.load_keybinds()
    
    def delete_keybind(self, bind):
        """Delete keybind"""
        reply = QMessageBox.question(
            self, "Confirm Delete",
            f"Delete keybind '{bind}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            line_num = self.config.keybinds[bind]['line']
            self.config.config_lines[line_num] = f"# Deleted: {self.config.config_lines[line_num]}"
            del self.config.keybinds[bind]
            self.config.save()
            self.load_keybinds()
    
    def capture_key(self, line_edit):
        """Capture keyboard input"""
        dialog = KeybindDialog(self, line_edit.text())
        if dialog.exec() == QDialog.DialogCode.Accepted:
            line_edit.setText(dialog.result_bind)


class DisplayTab(QWidget):
    """Display configuration tab"""

    def __init__(self, config_parser):
        super().__init__()
        self.config = config_parser
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # Refresh rate selection
        refresh_group = QGroupBox("Monitor Refresh Rate")
        refresh_layout = QVBoxLayout()
        
        refresh_info = QLabel("Select your monitor's refresh rate")
        refresh_layout.addWidget(refresh_info)
        
        self.refresh_combo = QComboBox()
        self.refresh_combo.addItems(["60Hz", "75Hz", "120Hz", "144Hz", "165Hz", "240Hz"])
        
        # Try to get current refresh rate
        current_rate = self.get_current_refresh_rate()
        if current_rate:
            index = self.refresh_combo.findText(current_rate)
            if index >= 0:
                self.refresh_combo.setCurrentIndex(index)
        
        refresh_layout.addWidget(self.refresh_combo)
        
        apply_refresh_btn = QPushButton("Apply Refresh Rate")
        apply_refresh_btn.clicked.connect(self.apply_refresh_rate)
        refresh_layout.addWidget(apply_refresh_btn)
        
        refresh_group.setLayout(refresh_layout)
        layout.addWidget(refresh_group)
        
        layout.addStretch()
        self.setLayout(layout)
    
    def get_current_refresh_rate(self):
        """Get current refresh rate using xrandr"""
        try:
            result = subprocess.run(['xrandr'], capture_output=True, text=True, check=True)
            # Parse xrandr output to find current refresh rate
            for line in result.stdout.split('\n'):
                if ' connected' in line and '*' in line:
                    parts = line.split()
                    for part in parts:
                        if part.endswith('Hz') and '*' in part:
                            return part.replace('*', '').strip()
            return None
        except Exception as e:
            print(f"Failed to get refresh rate: {e}")
            return None
    
    def get_monitor_info(self):
        """Get detailed monitor information using xrandr"""
        monitors = []
        try:
            # print("DEBUG: Running xrandr command...")
            result = subprocess.run(['xrandr'], capture_output=True, text=True, check=True)
            # print(f"DEBUG: xrandr stdout: {result.stdout}")
            # print(f"DEBUG: xrandr stderr: {result.stderr}")
            
            current_output = None
            current_info = {}
            in_resolution_section = False
            
            for line in result.stdout.split('\n'):
                original_line = line
                line = line.strip()
                # print(f"DEBUG: Processing line: '{original_line}' -> '{line}'")
                
                # Check if this is an output line
                if ' connected' in line or ' disconnected' in line:
                    # print(f"DEBUG: Found monitor output: {line}")
                    # Save previous monitor if exists
                    if current_output and current_info:
                        # print(f"DEBUG: Saving previous monitor: {current_info}")
                        monitors.append(current_info)
                    
                    # Start new monitor
                    parts = line.split()
                    current_output = parts[0]
                    current_info = {
                        'name': current_output,
                        'connected': ' connected' in line,
                        'resolutions': [],
                        'current_resolution': None,
                        'refresh_rates': [],
                        'current_rate': None,
                        'primary': ' primary' in line,
                        'position': None
                    }
                    in_resolution_section = True
                    # print(f"DEBUG: Started new monitor: {current_output}, connected: {current_info['connected']}, primary: {current_info['primary']}")
                
                # Parse resolutions and rates (only for connected monitors)
                elif current_output and current_info['connected'] and in_resolution_section and line and (line[0].isdigit() or ('x' in line and any(c.isdigit() for c in line))):
                    # print(f"DEBUG: Found resolution line: {line}")
                    # This is a resolution line like "1920x1080     60.00*+  74.97    50.00    59.94"
                    parts = line.split()
                    if len(parts) >= 2:
                        res = parts[0]
                        current_info['resolutions'].append(res)
                        # print(f"DEBUG: Added resolution: {res}")
                        
                        # Check if this is current resolution (has *)
                        current_rate = None
                        for i, part in enumerate(parts[1:]):
                            if '*' in part:
                                current_info['current_resolution'] = res
                                # Extract current rate (remove * and +)
                                current_rate = part.replace('*', '').replace('+', '').strip()
                                current_info['current_rate'] = current_rate
                                # print(f"DEBUG: Set current resolution: {res} @ {current_rate}Hz")
                                break
                        
                        # Collect all available rates for this resolution
                        rates = []
                        for part in parts[1:]:
                            clean_part = part.replace('*', '').replace('+', '').strip()
                            if clean_part.replace('.', '').isdigit():
                                if clean_part not in rates:
                                    rates.append(clean_part)
                        current_info['refresh_rates'].extend(rates)
                        # print(f"DEBUG: Available rates: {rates}")
                
                # End of resolution section - look for lines that start with spaces but aren't resolution lines
                elif current_output and original_line.startswith(' ') and not original_line.strip().startswith(('Screen', 'VGA', 'HDMI', 'DP')):
                    # print(f"DEBUG: End of resolution section (blank line)")
                    in_resolution_section = False
                
            # Add the last monitor
            if current_output and current_info:
                # print(f"DEBUG: Adding final monitor: {current_info}")
                monitors.append(current_info)
            else:
                print("DEBUG: No final monitor to add")
                
        except Exception as e:
            print(f"DEBUG ERROR: Failed to get monitor info: {e}")
            import traceback
            traceback.print_exc()
        
        # print(f"DEBUG: Final monitors list: {monitors}")
        return monitors
    
    def load_monitor_info(self):
        """Load and display monitor information"""
        monitors = self.get_monitor_info()
        
        # Store current rates for comparison
        self.current_rates = {}
        
        # Clear existing layout
        for i in reversed(range(self.layout().count())):
            widget = self.layout().itemAt(i).widget()
            if widget:
                widget.deleteLater()
        
        # Add monitor info for each connected monitor
        for monitor in monitors:
            if monitor['connected']:
                monitor_group = QGroupBox(f"Monitor: {monitor['name']}")
                monitor_layout = QVBoxLayout()
                
                # Basic info
                info_text = f"Resolution: {monitor['current_resolution'] or 'Unknown'} @ {monitor['current_rate'] or 'Unknown'}Hz"
                if monitor.get('primary'):
                    info_text += " (Primary)"
                
                info_label = QLabel(info_text)
                monitor_layout.addWidget(info_label)
                
                # Refresh rate selection
                if monitor['refresh_rates']:
                    rate_layout = QHBoxLayout()
                    rate_layout.addWidget(QLabel("Refresh Rate:"))
                    
                    rate_combo = QComboBox()
                    # Remove duplicates while preserving order
                    seen_rates = set()
                    unique_rates = []
                    for rate in monitor['refresh_rates']:
                        if rate not in seen_rates:
                            seen_rates.add(rate)
                            unique_rates.append(rate)
                    rate_combo.addItems(unique_rates)
                    
                    # Store current rate for this monitor
                    current_rate = monitor['current_rate']
                    self.current_rates[monitor['name']] = current_rate
                    
                    if current_rate:
                        index = rate_combo.findText(current_rate)
                        if index >= 0:
                            rate_combo.setCurrentIndex(index)
                    
                    rate_layout.addWidget(rate_combo)
                    monitor_layout.addLayout(rate_layout)
                    
                    # Create apply button and connect with change detection
                    apply_btn = QPushButton("Apply")
                    apply_btn.setEnabled(False)  # Start disabled
                    
                    def on_rate_changed(index):
                        selected_rate = rate_combo.itemText(index)
                        apply_btn.setEnabled(selected_rate != current_rate)
                    
                    rate_combo.currentIndexChanged.connect(on_rate_changed)
                    apply_btn.clicked.connect(lambda _, m=monitor['name'], rc=rate_combo: self.apply_monitor_refresh_rate(m, rc))
                    monitor_layout.addWidget(apply_btn)
                
                monitor_group.setLayout(monitor_layout)
                self.layout().addWidget(monitor_group)
        
        # Remove stretch to keep content at top
        while self.layout().count() > 0:
            item = self.layout().itemAt(self.layout().count() - 1)
            if isinstance(item, QSpacerItem):
                self.layout().takeAt(self.layout().count() - 1)
            else:
                break
    
    def apply_monitor_refresh_rate(self, monitor_name, rate_combo):
        """Apply refresh rate to specific monitor"""
        rate = rate_combo.currentText()
        try:
            # Get current resolution to preserve it
            monitors = self.get_monitor_info()
            monitor_info = next((m for m in monitors if m['name'] == monitor_name and m['connected']), None)
            
            if not monitor_info or not monitor_info['current_resolution']:
                send_notification("Error", f"Could not get current resolution for {monitor_name}")
                return
            
            # Apply new refresh rate while keeping current resolution
            result = subprocess.run(
                ['xrandr', '--output', monitor_name, '--mode', monitor_info['current_resolution'], '--rate', rate],
                capture_output=True, text=True, check=True
            )
            
            send_notification("Success", f"Set {monitor_name} to {monitor_info['current_resolution']} @ {rate}Hz")
            
            # Refresh monitor info
            self.load_monitor_info()
            
        except subprocess.CalledProcessError as e:
            send_notification("Error", f"Failed to set refresh rate: {e.stderr}")
        except Exception as e:
            send_notification("Error", f"Error setting refresh rate: {str(e)}")
    
    def init_ui(self):
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Load monitor information
        self.load_monitor_info()


class StartupAppsTab(QWidget):
    """Startup applications tab - manages exec commands in i3 config"""

    def __init__(self, config_parser):
        super().__init__()
        self.config = config_parser
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # Startup apps list
        self.startup_table = QTableWidget()
        self.startup_table.setColumnCount(4)
        self.startup_table.setHorizontalHeaderLabels(["Command", "Type", "No-Startup-ID", "Actions"])
        self.startup_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        
        layout.addWidget(self.startup_table)
        
        # Buttons
        btn_layout = QHBoxLayout()
        
        add_btn = QPushButton("Add Startup Command")
        add_btn.clicked.connect(self.add_startup_command)
        btn_layout.addWidget(add_btn)
        
        remove_btn = QPushButton("Remove Selected")
        remove_btn.clicked.connect(self.remove_startup_command)
        btn_layout.addWidget(remove_btn)
        
        remove_all_btn = QPushButton("Remove All")
        remove_all_btn.clicked.connect(self.remove_all_startup_commands)
        btn_layout.addWidget(remove_all_btn)
        
        layout.addLayout(btn_layout)
        
        # Info
        info_label = QLabel("Manage startup applications (exec commands) from your i3 config")
        info_label.setStyleSheet("color: #888; font-style: italic;")
        layout.addWidget(info_label)
        
        # Load startup commands from config
        self.load_startup_commands()
        
        layout.addStretch()
        self.setLayout(layout)
    
    def load_startup_commands(self):
        """Load startup commands from i3 config"""
        self.startup_table.setRowCount(0)
        
        try:
            # Parse config for exec commands
            exec_pattern = re.compile(r'^\s*(exec(_always|_once)?)\s+--no-startup-id\s+(.+)$', re.MULTILINE)
            config_content = ''.join(self.config.config_lines)
            
            for match in exec_pattern.finditer(config_content):
                cmd_type = match.group(1)
                command = match.group(3).strip()
                
                # Determine if it has no-startup-id
                has_no_startup = '--no-startup-id' in match.group(0)
                
                self.add_startup_row(command, cmd_type, has_no_startup)
                
        except Exception as e:
            print(f"Failed to load startup commands: {e}")
    
    def add_startup_row(self, command, cmd_type="exec", has_no_startup=True):
        """Add startup command to table"""
        row = self.startup_table.rowCount()
        self.startup_table.insertRow(row)
        
        self.startup_table.setItem(row, 0, QTableWidgetItem(command))
        
        # Type combo
        type_combo = QComboBox()
        type_combo.addItems(["exec", "exec_always", "exec_once"])
        type_combo.setCurrentText(cmd_type)
        self.startup_table.setCellWidget(row, 1, type_combo)
        
        # No-startup-id checkbox
        no_startup_checkbox = QCheckBox()
        no_startup_checkbox.setChecked(has_no_startup)
        self.startup_table.setCellWidget(row, 2, no_startup_checkbox)
        
        # Action buttons
        action_widget = QWidget()
        action_layout = QHBoxLayout()
        action_layout.setContentsMargins(4, 2, 4, 2)
        
        edit_btn = QPushButton("Edit")
        edit_btn.clicked.connect(lambda: self.edit_startup_command(row))
        action_layout.addWidget(edit_btn)
        
        action_widget.setLayout(action_layout)
        self.startup_table.setCellWidget(row, 3, action_widget)
    
    def add_startup_command(self):
        """Add new startup command"""
        dialog = QDialog(self)
        dialog.setWindowTitle("Add Startup Command")
        layout = QVBoxLayout()
        
        # Command
        cmd_layout = QHBoxLayout()
        cmd_layout.addWidget(QLabel("Command:"))
        self.cmd_input = QLineEdit()
        cmd_layout.addWidget(self.cmd_input)
        layout.addLayout(cmd_layout)
        
        # Type
        type_layout = QHBoxLayout()
        type_layout.addWidget(QLabel("Type:"))
        self.type_combo = QComboBox()
        self.type_combo.addItems(["exec", "exec_always", "exec_once"])
        type_layout.addWidget(self.type_combo)
        layout.addLayout(type_layout)
        
        # No-startup-id
        self.no_startup_checkbox = QCheckBox("Add --no-startup-id flag")
        self.no_startup_checkbox.setChecked(True)
        layout.addWidget(self.no_startup_checkbox)
        
        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        
        dialog.setLayout(layout)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            command = self.cmd_input.text().strip()
            if command:
                cmd_type = self.type_combo.currentText()
                has_no_startup = self.no_startup_checkbox.isChecked()
                self.add_startup_row(command, cmd_type, has_no_startup)
    
    def edit_startup_command(self, row):
        """Edit startup command"""
        cmd_item = self.startup_table.item(row, 0)
        type_combo = self.startup_table.cellWidget(row, 1)
        no_startup_checkbox = self.startup_table.cellWidget(row, 2)
        
        if cmd_item and type_combo and no_startup_checkbox:
            dialog = QDialog(self)
            dialog.setWindowTitle("Edit Startup Command")
            layout = QVBoxLayout()
            
            # Command
            cmd_layout = QHBoxLayout()
            cmd_layout.addWidget(QLabel("Command:"))
            cmd_input = QLineEdit(cmd_item.text())
            cmd_layout.addWidget(cmd_input)
            layout.addLayout(cmd_layout)
            
            # Type
            type_layout = QHBoxLayout()
            type_layout.addWidget(QLabel("Type:"))
            type_combo_edit = QComboBox()
            type_combo_edit.addItems(["exec", "exec_always", "exec_once"])
            type_combo_edit.setCurrentText(type_combo.currentText())
            type_layout.addWidget(type_combo_edit)
            layout.addLayout(type_layout)
            
            # No-startup-id
            no_startup_checkbox_edit = QCheckBox("Add --no-startup-id flag")
            no_startup_checkbox_edit.setChecked(no_startup_checkbox.isChecked())
            layout.addWidget(no_startup_checkbox_edit)
            
            # Buttons
            buttons = QDialogButtonBox(
                QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
            )
            buttons.accepted.connect(dialog.accept)
            buttons.rejected.connect(dialog.reject)
            layout.addWidget(buttons)
            
            dialog.setLayout(layout)
            
            if dialog.exec() == QDialog.DialogCode.Accepted:
                cmd_item.setText(cmd_input.text().strip())
                type_combo.setCurrentText(type_combo_edit.currentText())
                no_startup_checkbox.setChecked(no_startup_checkbox_edit.isChecked())
    
    def remove_startup_command(self):
        """Remove selected startup command"""
        selected = self.startup_table.selectedItems()
        if selected:
            row = selected[0].row()
            self.startup_table.removeRow(row)
    
    def remove_all_startup_commands(self):
        """Remove all startup commands"""
        self.startup_table.setRowCount(0)
        send_notification("Startup Apps", "All startup commands removed")
    
    def apply_startup_commands(self):
        """Apply startup commands to i3 config"""
        try:
            # Remove all existing exec commands
            new_lines = []
            for line in self.config.config_lines:
                if not line.strip().startswith('exec') and not line.strip().startswith('exec_always') and not line.strip().startswith('exec_once'):
                    new_lines.append(line)
            
            # Add new startup commands
            for row in range(self.startup_table.rowCount()):
                cmd_item = self.startup_table.item(row, 0)
                type_combo = self.startup_table.cellWidget(row, 1)
                no_startup_checkbox = self.startup_table.cellWidget(row, 2)
                
                if cmd_item and type_combo and no_startup_checkbox:
                    command = cmd_item.text()
                    cmd_type = type_combo.currentText()
                    no_startup = no_startup_checkbox.isChecked()
                    
                    # Build the exec command
                    exec_cmd = f"{cmd_type}"
                    if no_startup:
                        exec_cmd += " --no-startup-id"
                    exec_cmd += f" {command}"
                    new_lines.append(exec_cmd + "\n")
            
            # Update config
            self.config.config_lines = new_lines
            self.config.save()
            
            send_notification("Startup Apps", "Startup commands updated. i3 restart required for changes to take effect.")
            
        except Exception as e:
            send_notification("Error", f"Failed to apply startup commands: {str(e)}")


class HistoryTab(QWidget):
    """Configuration history tab"""

    def __init__(self, history_manager, config_parser):
        super().__init__()
        self.history = history_manager
        self.config = config_parser
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        info = QLabel("Configuration backups are saved automatically")
        layout.addWidget(info)
        
        # History list
        self.history_list = QTableWidget()
        self.history_list.setColumnCount(3)
        self.history_list.setHorizontalHeaderLabels(["Date/Time", "Label", "Actions"])
        self.history_list.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.history_list)
        
        # Buttons
        btn_layout = QHBoxLayout()
        
        backup_btn = QPushButton("Create Backup")
        backup_btn.clicked.connect(self.create_backup)
        btn_layout.addWidget(backup_btn)
        
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.load_history)
        btn_layout.addWidget(refresh_btn)
        
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        
        self.setLayout(layout)
        self.load_history()
    
    def load_history(self):
        """Load history list"""
        self.history_list.setRowCount(0)
        
        for backup in self.history.get_history():
            row = self.history_list.rowCount()
            self.history_list.insertRow(row)
            
            timestamp = backup['meta']['timestamp']
            dt = datetime.strptime(timestamp, "%Y%m%d_%H%M%S")
            
            self.history_list.setItem(row, 0, QTableWidgetItem(dt.strftime("%Y-%m-%d %H:%M:%S")))
            self.history_list.setItem(row, 1, QTableWidgetItem(backup['meta']['label']))
            
            # Action buttons
            action_widget = QWidget()
            action_layout = QHBoxLayout()
            action_layout.setContentsMargins(4, 2, 4, 2)
            
            restore_btn = QPushButton("Restore")
            restore_btn.clicked.connect(lambda checked, f=backup['file']: self.restore_backup(f))
            action_layout.addWidget(restore_btn)
            
            view_btn = QPushButton("View")
            view_btn.clicked.connect(lambda checked, f=backup['file']: self.view_backup(f))
            action_layout.addWidget(view_btn)
            
            action_widget.setLayout(action_layout)
            self.history_list.setCellWidget(row, 2, action_widget)
    
    def create_backup(self):
        """Create manual backup"""
        from PyQt6.QtWidgets import QInputDialog
        label, ok = QInputDialog.getText(self, "Create Backup", "Enter backup label:")
        if ok and label:
            self.history.save_backup(label)
            self.load_history()
            QMessageBox.information(self, "Success", "Backup created!")
    
    def restore_backup(self, backup_file):
        """Restore a backup"""
        reply = QMessageBox.question(
            self, "Confirm Restore",
            "This will replace your current configuration. Continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.history.restore_backup(backup_file)
            self.config.load()
            QMessageBox.information(self, "Success", "Configuration restored! Reloading i3...")
            self.config.reload_i3()
    
    def view_backup(self, backup_file):
        """View backup content"""
        dialog = QDialog(self)
        dialog.setWindowTitle("View Backup")
        dialog.resize(800, 600)
        
        layout = QVBoxLayout()
        
        text_edit = QTextEdit()
        text_edit.setReadOnly(True)
        
        with open(backup_file) as f:
            text_edit.setPlainText(f.read())
        
        layout.addWidget(text_edit)
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(dialog.accept)
        layout.addWidget(close_btn)
        
        dialog.setLayout(layout)
        dialog.exec()


class MainWindow(QMainWindow):
    """Main application window"""

    def __init__(self):
        super().__init__()
        self.config_path = Path.home() / ".config" / "i3" / "config"
        self.config = I3ConfigParser(self.config_path)
        self.history = HistoryManager(self.config_path)
        
        self.setWindowTitle("i3 Settings Manager")
        self.setMinimumSize(900, 700)
        
        # Set application icon
        self.set_window_icon()
        
        self.init_ui()
    
    def set_window_icon(self):
        """Set application icon"""
        try:
            icon_path = Path("appicon.png")
            if icon_path.exists():
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
            logo_path = Path("i3wm-logo.png")
            if logo_path.exists():
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
        self.tabs.addTab(AppearanceTab(self.config), "Appearance")
        self.tabs.addTab(DisplayTab(self.config), "Display")
        self.tabs.addTab(StartupAppsTab(self.config), "Startup Apps")
        self.tabs.addTab(KeybindsTab(self.config), "Keybindings")
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
        QMessageBox.about(
            self, "About i3 Settings Manager",
            "i3 Settings Manager v1.0\n\n"
            "A GUI for managing i3wm configuration\n\n"
            "Features:\n"
            "• Visual appearance customization\n"
            "• Keybinding management with conflict detection\n"
            "• Configuration history and backups\n"
            "• Wallpaper management\n"
            "• Monitor refresh rate control\n"
            "• Autostart application management\n\n"
            "Config location: ~/.config/i3/config"
        )
    
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


def main():
    app = QApplication(sys.argv)
    
    # Set application style
    app.setStyle('Fusion')

    # try:
    #     with open("dark.qss", "r") as f:
    #         style_sheet = f.read()
    # except FileNotFoundError:
    #     print("Stylesheet file not found. Running without style.")
    #     style_sheet = ""

    # # 2. Apply the stylesheet to the entire application
    # app.setStyleSheet(style_sheet)
    

    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
