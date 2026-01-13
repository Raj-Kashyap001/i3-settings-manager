#!/usr/bin/env python3
"""
i3 Settings GUI - A modern settings manager for i3wm
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
    QDialog, QDialogButtonBox, QTextEdit, QListWidget
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QKeySequence, QColor, QPalette


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
        self.load()
    
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
        """Reload i3 configuration"""
        try:
            subprocess.run(['i3-msg', 'reload'], check=True)
            return True
        except subprocess.CalledProcessError:
            return False


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
        
        # Matugen integration
        matugen_group = QGroupBox("Colors from Wallpaper (Matugen)")
        matugen_layout = QVBoxLayout()
        
        matugen_info = QLabel("Generate color scheme from your wallpaper")
        matugen_layout.addWidget(matugen_info)
        
        wallpaper_layout = QHBoxLayout()
        self.wallpaper_path = QLineEdit()
        self.wallpaper_path.setPlaceholderText("Select wallpaper...")
        wallpaper_layout.addWidget(self.wallpaper_path)
        
        browse_btn = QPushButton("Browse")
        browse_btn.clicked.connect(self.browse_wallpaper)
        wallpaper_layout.addWidget(browse_btn)
        matugen_layout.addLayout(wallpaper_layout)
        
        generate_btn = QPushButton("Generate & Apply Colors")
        generate_btn.clicked.connect(self.generate_colors)
        matugen_layout.addWidget(generate_btn)
        
        matugen_group.setLayout(matugen_layout)
        layout.addWidget(matugen_group)
        
        # Apply button
        apply_btn = QPushButton("Apply Appearance Settings")
        apply_btn.clicked.connect(self.apply_settings)
        layout.addWidget(apply_btn)
        
        layout.addStretch()
        self.setLayout(layout)
    
    def browse_wallpaper(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Wallpaper", str(Path.home()),
            "Images (*.png *.jpg *.jpeg *.webp)"
        )
        if file_path:
            self.wallpaper_path.setText(file_path)
    
    def generate_colors(self):
        wallpaper = self.wallpaper_path.text()
        if not wallpaper or not Path(wallpaper).exists():
            QMessageBox.warning(self, "Error", "Please select a valid wallpaper")
            return
        
        try:
            # Run matugen
            result = subprocess.run(
                ['matugen', 'image', wallpaper, '-j', 'hex'],
                capture_output=True, text=True, check=True
            )
            
            colors = json.loads(result.stdout)
            
            # Apply colors to i3 config
            self.apply_matugen_colors(colors)
            
            QMessageBox.information(self, "Success", "Colors generated and applied!")
        except subprocess.CalledProcessError as e:
            QMessageBox.critical(self, "Error", f"Matugen failed: {e.stderr}")
        except json.JSONDecodeError:
            QMessageBox.critical(self, "Error", "Failed to parse matugen output")
        except FileNotFoundError:
            QMessageBox.critical(self, "Error", "Matugen not found. Please install it first.")
    
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
        # Update gaps
        self.config.set_value("gaps inner", str(self.inner_gaps.value()))
        self.config.set_value("gaps outer", str(self.outer_gaps.value()))
        
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
        
        self.config.save()
        self.config.reload_i3()
        QMessageBox.information(self, "Success", "Appearance settings applied!")


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
        
        self.init_ui()
    
    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout()
        
        # Header
        header = QLabel("i3 Window Manager Settings")
        header.setStyleSheet("font-size: 18px; font-weight: bold; padding: 10px;")
        layout.addWidget(header)
        
        # Tab widget
        tabs = QTabWidget()
        
        # Add tabs
        tabs.addTab(AppearanceTab(self.config), "Appearance")
        tabs.addTab(KeybindsTab(self.config), "Keybindings")
        tabs.addTab(HistoryTab(self.history, self.config), "History")
        
        layout.addWidget(tabs)
        
        # Footer buttons
        footer_layout = QHBoxLayout()
        
        save_btn = QPushButton("Save & Reload i3")
        save_btn.clicked.connect(self.save_and_reload)
        footer_layout.addWidget(save_btn)
        
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
        
        self.config.save()
        if self.config.reload_i3():
            QMessageBox.information(self, "Success", "Configuration saved and i3 reloaded!")
        else:
            QMessageBox.warning(self, "Warning", "Configuration saved but i3 reload failed")
    
    def show_about(self):
        """Show about dialog"""
        QMessageBox.about(
            self, "About i3 Settings Manager",
            "i3 Settings Manager v1.0\n\n"
            "A modern GUI for managing i3wm configuration\n\n"
            "Features:\n"
            "• Visual appearance customization\n"
            "• Keybinding management with conflict detection\n"
            "• Configuration history and backups\n"
            "• Matugen color scheme integration\n\n"
            "Config location: ~/.config/i3/config"
        )


def main():
    app = QApplication(sys.argv)
    
    # Set application style
    app.setStyle('Fusion')
    
    # Dark theme
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(53, 53, 53))
    palette.setColor(QPalette.ColorRole.WindowText, Qt.GlobalColor.white)
    palette.setColor(QPalette.ColorRole.Base, QColor(25, 25, 25))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(53, 53, 53))
    palette.setColor(QPalette.ColorRole.ToolTipBase, Qt.GlobalColor.white)
    palette.setColor(QPalette.ColorRole.ToolTipText, Qt.GlobalColor.white)
    palette.setColor(QPalette.ColorRole.Text, Qt.GlobalColor.white)
    palette.setColor(QPalette.ColorRole.Button, QColor(53, 53, 53))
    palette.setColor(QPalette.ColorRole.ButtonText, Qt.GlobalColor.white)
    palette.setColor(QPalette.ColorRole.BrightText, Qt.GlobalColor.red)
    palette.setColor(QPalette.ColorRole.Link, QColor(42, 130, 218))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(42, 130, 218))
    palette.setColor(QPalette.ColorRole.HighlightedText, Qt.GlobalColor.black)
    app.setPalette(palette)
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
