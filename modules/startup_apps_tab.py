"""
StartupAppsTab module for managing startup applications
"""

import subprocess
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem, QHeaderView, QPushButton, QLabel, QComboBox, QCheckBox, QDialog, QDialogButtonBox, QLineEdit, QMessageBox
from PyQt6.QtGui import QIcon
import re

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
        self.startup_table.setColumnCount(3)
        self.startup_table.setHorizontalHeaderLabels(["Command", "Type", ""])
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
        
        # Action buttons
        action_widget = QWidget()
        action_layout = QHBoxLayout()
        action_layout.setContentsMargins(4, 2, 4, 2)

        edit_btn = QPushButton()
        edit_btn.setIcon(QIcon.fromTheme("document-edit",
                         self.style().standardIcon(self.style().StandardPixmap.SP_DialogResetButton)))
        edit_btn.setToolTip("Edit startup command")
        edit_btn.clicked.connect(lambda: self.edit_startup_command(row))
        action_layout.addWidget(edit_btn)
        
        action_widget.setLayout(action_layout)
        self.startup_table.setCellWidget(row, 2, action_widget)
    
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
                has_no_startup = True  # Default to True
                self.add_startup_row(command, cmd_type, has_no_startup)
    
    def edit_startup_command(self, row):
        """Edit startup command"""
        cmd_item = self.startup_table.item(row, 0)
        type_combo = self.startup_table.cellWidget(row, 1)
        
        if cmd_item and type_combo:
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
    
    def remove_startup_command(self):
        """Remove selected startup command"""
        selected = self.startup_table.selectedItems()
        if selected:
            row = selected[0].row()
            self.startup_table.removeRow(row)
    
    def remove_all_startup_commands(self):
        """Remove all startup commands"""
        self.startup_table.setRowCount(0)
        # send_notification("Startup Apps", "All startup commands removed")
    
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
                
                if cmd_item and type_combo:
                    command = cmd_item.text()
                    cmd_type = type_combo.currentText()
                    no_startup = True  # Default to True
                    
                    # Build the exec command
                    exec_cmd = f"{cmd_type}"
                    if no_startup:
                        exec_cmd += " --no-startup-id"
                    exec_cmd += f" {command}"
                    new_lines.append(exec_cmd + "\n")
            
            # Update config
            self.config.config_lines = new_lines
            self.config.save()
            
            # send_notification("Startup Apps", "Startup commands updated. i3 restart required for changes to take effect.")
        
        except Exception as e:
            send_notification("Error", f"Failed to apply startup commands: {str(e)}")


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