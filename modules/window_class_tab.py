"""
WindowClassTab module for window class settings
"""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel, QLineEdit, QCheckBox, QPushButton, QComboBox, QMessageBox
import subprocess
import re

class WindowClassTab(QWidget):
    """Window class settings tab"""

    def __init__(self, config_parser):
        super().__init__()
        self.config = config_parser
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        # Window info group
        info_group = QGroupBox("Get Window Information")
        info_layout = QVBoxLayout()

        self.window_class_edit = QLineEdit()
        self.window_class_edit.setPlaceholderText("Window class (e.g., ^Firefox$)")
        info_layout.addWidget(QLabel("Window Class:"))
        info_layout.addWidget(self.window_class_edit)

        get_info_btn = QPushButton("Get Focused Window Info")
        get_info_btn.clicked.connect(self.get_window_info)
        info_layout.addWidget(get_info_btn)

        info_group.setLayout(info_layout)
        layout.addWidget(info_group)

        # Rules group
        rules_group = QGroupBox("Window Rules")
        rules_layout = QVBoxLayout()

        self.floating_checkbox = QCheckBox("Enable Floating")
        rules_layout.addWidget(self.floating_checkbox)

        position_layout = QHBoxLayout()
        position_layout.addWidget(QLabel("Floating Position:"))
        self.position_combo = QComboBox()
        self.position_combo.addItems(["center", "mouse", "custom"])
        position_layout.addWidget(self.position_combo)
        rules_layout.addLayout(position_layout)

        # Custom position fields
        custom_layout = QHBoxLayout()
        custom_layout.addWidget(QLabel("X:"))
        self.x_edit = QLineEdit()
        self.x_edit.setPlaceholderText("X coordinate")
        custom_layout.addWidget(self.x_edit)
        custom_layout.addWidget(QLabel("Y:"))
        self.y_edit = QLineEdit()
        self.y_edit.setPlaceholderText("Y coordinate")
        custom_layout.addWidget(self.y_edit)
        rules_layout.addLayout(custom_layout)

        apply_rule_btn = QPushButton("Add Rule")
        apply_rule_btn.clicked.connect(self.add_rule)
        rules_layout.addWidget(apply_rule_btn)

        rules_group.setLayout(rules_layout)
        layout.addWidget(rules_group)

        layout.addStretch()
        self.setLayout(layout)

    def get_window_info(self):
        try:
            # Run xwininfo to let user select a window and get id
            result = subprocess.run(['xwininfo'], capture_output=True, text=True, check=True)
            output = result.stdout

            # Parse window id
            id_match = re.search(r'Window id:\s*(0x[0-9a-fA-F]+)', output)
            if not id_match:
                QMessageBox.critical(self, "Error", "Could not get window id")
                return
            window_id = id_match.group(1)

            # Get WM_CLASS using xprop
            result = subprocess.run(['xprop', '-id', window_id, 'WM_CLASS'], capture_output=True, text=True, check=True)
            class_output = result.stdout
            # WM_CLASS(STRING) = "class", "instance"
            class_match = re.search(r'WM_CLASS\(STRING\) = "([^"]*)"', class_output)
            if class_match:
                window_class = class_match.group(1)
                self.window_class_edit.setText(f"^{window_class}$")

            # Parse position from xwininfo output
            x_match = re.search(r'Absolute upper-left X:\s*(\d+)', output)
            y_match = re.search(r'Absolute upper-left Y:\s*(\d+)', output)
            if x_match and y_match:
                self.x_edit.setText(x_match.group(1))
                self.y_edit.setText(y_match.group(1))
                self.position_combo.setCurrentText("custom")

            QMessageBox.information(self, "Success", "Window information retrieved successfully!")

        except subprocess.CalledProcessError as e:
            QMessageBox.critical(self, "Error", f"Failed to get window info: {e}")
        except FileNotFoundError:
            QMessageBox.critical(self, "Error", "xwininfo or xprop not found. Please install them.")

    def add_rule(self):
        window_class = self.window_class_edit.text().strip()
        if not window_class:
            QMessageBox.warning(self, "Warning", "Please enter a window class")
            return

        # Check if rules for this class already exist
        existing_rules = [line for line in self.config.config_lines if f'for_window [class="{window_class}"]' in line]
        if existing_rules:
            reply = QMessageBox.question(self, "Rule Exists",
                                         f"Rules for class '{window_class}' already exist:\n" + '\n'.join(existing_rules) +
                                         "\n\nAdd new rules anyway?",
                                         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.No:
                return

        rules = []

        if self.floating_checkbox.isChecked():
            rules.append(f'for_window [class="{window_class}"] floating enable')

        position = self.position_combo.currentText()
        if position == "center":
            rules.append(f'for_window [class="{window_class}"] move position center')
        elif position == "mouse":
            rules.append(f'for_window [class="{window_class}"] move position mouse')
        elif position == "custom":
            x = self.x_edit.text().strip()
            y = self.y_edit.text().strip()
            if x and y:
                rules.append(f'for_window [class="{window_class}"] move position {x} px {y} px')

        if rules:
            # Add rules to config
            for rule in rules:
                self.config.config_lines.append(rule + '\n')
            QMessageBox.information(self, "Success", "Rule added successfully!")
        else:
            QMessageBox.warning(self, "Warning", "No rules to add")

    def apply_settings(self):
        # Since rules are added immediately, no need to do anything here
        # But to follow the pattern, perhaps save is handled elsewhere
        pass