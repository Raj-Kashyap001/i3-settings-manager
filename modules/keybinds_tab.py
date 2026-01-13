"""
KeybindsTab module for keybindings management
"""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem, QHeaderView, QPushButton, QLineEdit, QDialog, QDialogButtonBox, QLabel, QComboBox, QCheckBox, QMessageBox
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon

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
        self.table.setHorizontalHeaderLabels(["Keybind", "Command", ""])
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

        edit_btn = QPushButton()
        edit_btn.setIcon(QIcon("icons/edit-symbolic.svg"))
        edit_btn.setToolTip("Edit keybind")
        edit_btn.clicked.connect(lambda: self.edit_keybind(bind))
        action_layout.addWidget(edit_btn)

        delete_btn = QPushButton()
        delete_btn.setIcon(QIcon("icons/edit-delete-symbolic.svg"))
        delete_btn.setToolTip("Delete keybind")
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
        from modules.keybind_dialog import KeybindDialog
        dialog = KeybindDialog(self, line_edit.text())
        if dialog.exec() == QDialog.DialogCode.Accepted:
            line_edit.setText(dialog.result_bind)