"""
KeybindDialog module for capturing keybind input
"""

from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QLineEdit, QDialogButtonBox, QHBoxLayout
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QKeySequence

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