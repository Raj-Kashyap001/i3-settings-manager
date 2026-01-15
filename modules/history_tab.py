import sys
import os
from datetime import datetime
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, 
                             QTableWidgetItem, QHeaderView, QPushButton, QLabel, 
                             QDialog, QTextEdit, QInputDialog, QMessageBox, QApplication)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QIcon, QPalette, QColor

def apply_dark_theme(app):
    """Sets a professional dark Fusion palette to the application."""
    app.setStyle("Fusion")
    dark_palette = QPalette()
    dark_palette.setColor(QPalette.ColorRole.Window, QColor(45, 45, 45))
    dark_palette.setColor(QPalette.ColorRole.WindowText, Qt.GlobalColor.white)
    dark_palette.setColor(QPalette.ColorRole.Base, QColor(30, 30, 30))
    dark_palette.setColor(QPalette.ColorRole.AlternateBase, QColor(45, 45, 45))
    dark_palette.setColor(QPalette.ColorRole.ToolTipBase, Qt.GlobalColor.white)
    dark_palette.setColor(QPalette.ColorRole.ToolTipText, Qt.GlobalColor.white)
    dark_palette.setColor(QPalette.ColorRole.Text, Qt.GlobalColor.white)
    dark_palette.setColor(QPalette.ColorRole.Button, QColor(55, 55, 55))
    dark_palette.setColor(QPalette.ColorRole.ButtonText, Qt.GlobalColor.white)
    dark_palette.setColor(QPalette.ColorRole.Highlight, QColor(42, 130, 218))
    dark_palette.setColor(QPalette.ColorRole.HighlightedText, Qt.GlobalColor.white)
    app.setPalette(dark_palette)

class HistoryTab(QWidget):
    """Configuration history tab with system theme icons"""

    def __init__(self, history_manager, config_parser):
        super().__init__()
        self.history = history_manager
        self.config = config_parser
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        info = QLabel("Configuration backups are saved automatically")
        info.setStyleSheet("color: #aaaaaa; font-style: italic; margin-bottom: 5px;")
        layout.addWidget(info)
        
        # History table setup
        self.history_list = QTableWidget()
        self.history_list.setColumnCount(3)
        self.history_list.setHorizontalHeaderLabels(["Date/Time", "Label", "Actions"])
        self.history_list.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.history_list.setAlternatingRowColors(True)
        layout.addWidget(self.history_list)
        
        # Bottom Button Bar
        btn_layout = QHBoxLayout()
        
        # Create Backup
        self.backup_btn = QPushButton(" Create Backup")
        self.backup_btn.setIcon(QIcon.fromTheme("document-new", 
                                self.style().standardIcon(self.style().StandardPixmap.SP_FileDialogNewFolder)))
        self.backup_btn.clicked.connect(self.create_backup)
        
        # Refresh
        self.refresh_btn = QPushButton(" Refresh")
        self.refresh_btn.setIcon(QIcon.fromTheme("view-refresh", 
                                 self.style().standardIcon(self.style().StandardPixmap.SP_BrowserReload)))
        self.refresh_btn.clicked.connect(self.load_history)
        
        # Restore Default
        self.restore_default_btn = QPushButton(" Restore to Default")
        self.restore_default_btn.setIcon(QIcon.fromTheme("edit-clear-all", 
                                         self.style().standardIcon(self.style().StandardPixmap.SP_DialogResetButton)))
        self.restore_default_btn.clicked.connect(self.restore_to_default)
        
        btn_layout.addWidget(self.backup_btn)
        btn_layout.addWidget(self.refresh_btn)
        btn_layout.addWidget(self.restore_default_btn)
        btn_layout.addStretch()
        
        layout.addLayout(btn_layout)
        self.setLayout(layout)
        self.load_history()
    
    def load_history(self):
        """Load history list with action icons"""
        self.history_list.setRowCount(0)
        
        for backup in self.history.get_history():
            row = self.history_list.rowCount()
            self.history_list.insertRow(row)
            
            # Format Timestamp
            timestamp = backup['meta']['timestamp']
            try:
                dt = datetime.strptime(timestamp, "%Y%m%d_%H%M%S")
                date_str = dt.strftime("%Y-%m-%d %H:%M:%S")
            except:
                date_str = timestamp
            
            self.history_list.setItem(row, 0, QTableWidgetItem(date_str))
            self.history_list.setItem(row, 1, QTableWidgetItem(backup['meta']['label']))
            
            # Action buttons widget
            action_widget = QWidget()
            action_layout = QHBoxLayout()
            action_layout.setContentsMargins(2, 2, 2, 2)
            action_layout.setSpacing(6)

            # Restore Button
            restore_btn = QPushButton()
            restore_btn.setFixedSize(30, 30)
            restore_icon = QIcon.fromTheme("document-revert", 
                           self.style().standardIcon(self.style().StandardPixmap.SP_BrowserReload))
            restore_btn.setIcon(restore_icon)
            restore_btn.setToolTip("Restore this backup")
            restore_btn.clicked.connect(lambda checked, f=backup['file']: self.restore_backup(f))
            
            # View/Preview Button
            view_btn = QPushButton()
            view_btn.setFixedSize(30, 30)
            view_icon = QIcon.fromTheme("document-print-preview", 
                        self.style().standardIcon(self.style().StandardPixmap.SP_FileDialogContentsView))
            view_btn.setIcon(view_icon)
            view_btn.setToolTip("View content")
            view_btn.clicked.connect(lambda checked, f=backup['file']: self.view_backup(f))
            
            action_layout.addWidget(restore_btn)
            action_layout.addWidget(view_btn)
            action_widget.setLayout(action_layout)
            
            self.history_list.setCellWidget(row, 2, action_widget)

    def create_backup(self):
        label, ok = QInputDialog.getText(self, "Create Backup", "Enter backup label:")
        if ok and label:
            self.history.save_backup(label)
            self.load_history()
            QMessageBox.information(self, "Success", "Backup created!")

    def restore_backup(self, backup_file):
        reply = QMessageBox.question(
            self, "Confirm Restore",
            "Replace current configuration with this backup?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.history.restore_backup(backup_file)
            self.config.load()
            self.config.reload_i3()
            QMessageBox.information(self, "Success", "Configuration restored!")

    def restore_to_default(self):
        reply = QMessageBox.question(
            self, "Restore Default",
            "This will revert to the default config. Continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            try:
                # Assuming config.default exists in the root
                with open("config.default", "r") as f:
                    default_data = f.read()
                with open(self.config.config_path, "w") as f:
                    f.write(default_data)
                self.config.load()
                self.config.reload_i3()
                QMessageBox.information(self, "Success", "Defaults applied!")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed: {str(e)}")

    def view_backup(self, backup_file):
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Viewing: {os.path.basename(backup_file)}")
        dialog.resize(700, 500)
        
        layout = QVBoxLayout(dialog)
        text_edit = QTextEdit()
        text_edit.setReadOnly(True)
        text_edit.setStyleSheet("font-family: 'Monospace'; background-color: #1e1e1e;")
        
        try:
            with open(backup_file, 'r') as f:
                text_edit.setPlainText(f.read())
        except Exception as e:
            text_edit.setPlainText(f"Error loading file: {e}")
        
        layout.addWidget(text_edit)
        
        close_btn = QPushButton(" Close")
        close_btn.setIcon(self.style().standardIcon(self.style().StandardPixmap.SP_DialogCloseButton))
        close_btn.clicked.connect(dialog.accept)
        layout.addWidget(close_btn)
        
        dialog.exec()