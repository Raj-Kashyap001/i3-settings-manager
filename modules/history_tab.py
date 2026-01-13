"""
HistoryTab module for configuration history
"""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem, QHeaderView, QPushButton, QLabel, QDialog, QTextEdit, QInputDialog, QMessageBox
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon
from datetime import datetime

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
        self.history_list.setHorizontalHeaderLabels(["Date/Time", "Label", ""])
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
        
        restore_default_btn = QPushButton("Restore to Default")
        restore_default_btn.clicked.connect(self.restore_to_default)
        btn_layout.addWidget(restore_default_btn)
        
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

            restore_btn = QPushButton()
            restore_btn.setIcon(QIcon("icons/edit-symbolic.svg"))
            restore_btn.setToolTip("Restore backup")
            restore_btn.clicked.connect(lambda checked, f=backup['file']: self.restore_backup(f))
            action_layout.addWidget(restore_btn)

            view_btn = QPushButton()
            view_btn.setIcon(self.style().standardIcon(self.style().StandardPixmap.SP_FileDialogContentsView))
            view_btn.setToolTip("View backup")
            view_btn.clicked.connect(lambda checked, f=backup['file']: self.view_backup(f))
            action_layout.addWidget(view_btn)
            
            action_widget.setLayout(action_layout)
            self.history_list.setCellWidget(row, 2, action_widget)
    
    def create_backup(self):
        """Create manual backup"""
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
    
    def restore_to_default(self):
        """Restore to default configuration"""
        reply = QMessageBox.question(
            self, "Confirm Restore to Default",
            "This will restore the default configuration. Continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                with open("config.default", "r") as f:
                    default_config = f.read()
                
                with open(self.config.config_path, "w") as f:
                    f.write(default_config)
                
                self.config.load()
                QMessageBox.information(self, "Success", "Default configuration restored! Reloading i3...")
                self.config.reload_i3()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to restore default configuration: {str(e)}")
    
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

        close_btn = QPushButton()
        close_btn.setIcon(self.style().standardIcon(self.style().StandardPixmap.SP_DialogCloseButton))
        close_btn.setText("Close")
        close_btn.clicked.connect(dialog.accept)
        layout.addWidget(close_btn)
        
        dialog.setLayout(layout)
        dialog.exec()