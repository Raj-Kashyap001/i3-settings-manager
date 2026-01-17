"""
PicomTab module for picom compositor settings with dynamic UI
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, 
                              QLabel, QSpinBox, QCheckBox, QPushButton, 
                              QMessageBox, QComboBox, QScrollArea, QListWidget,
                              QDialog, QDialogButtonBox)
from PyQt6.QtCore import Qt, QTimer
from pathlib import Path
import subprocess
import re


class AppSelectorDialog(QDialog):
    """Dialog for selecting applications to exclude from shadows"""
    
    def __init__(self, parent=None, current_exclusions=None):
        super().__init__(parent)
        self.setWindowTitle("Select Apps to Exclude from Shadows")
        self.resize(500, 400)
        self.selected_class = None
        self.current_exclusions = current_exclusions or []
        
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # Instructions
        info = QLabel("Click 'Pick Window' then click on any window to get its class name")
        info.setWordWrap(True)
        layout.addWidget(info)
        
        # Pick window button
        pick_btn = QPushButton("Pick Window (Click on target window)")
        pick_btn.clicked.connect(self.pick_window)
        layout.addWidget(pick_btn)
        
        # Current selection
        self.current_label = QLabel("Selected: None")
        self.current_label.setStyleSheet("font-weight: bold; padding: 10px;")
        layout.addWidget(self.current_label)
        
        # List of excluded apps
        excluded_label = QLabel("Currently Excluded Apps:")
        excluded_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        layout.addWidget(excluded_label)
        
        self.excluded_list = QListWidget()
        self.excluded_list.addItems(self.current_exclusions)
        layout.addWidget(self.excluded_list)
        
        # Remove button
        remove_btn = QPushButton("Remove Selected")
        remove_btn.clicked.connect(self.remove_selected)
        layout.addWidget(remove_btn)
        
        # Dialog buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | 
            QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
        self.setLayout(layout)
    
    def pick_window(self):
        """Use xwininfo to pick a window and get its class"""
        try:
            # Run xwininfo and let user click on a window
            result = subprocess.run(
                ['xprop', 'WM_CLASS'],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                # Parse WM_CLASS output
                # Format: WM_CLASS(STRING) = "instance", "class"
                match = re.search(r'WM_CLASS\(STRING\)\s*=\s*"([^"]+)",\s*"([^"]+)"', result.stdout)
                if match:
                    window_class = match.group(2)
                    self.selected_class = window_class
                    self.current_label.setText(f"Selected: {window_class}")
                    
                    # Add to exclusions if not already present
                    if window_class not in self.current_exclusions:
                        self.current_exclusions.append(window_class)
                        self.excluded_list.addItem(window_class)
                else:
                    QMessageBox.warning(self, "Error", "Could not parse window class")
            else:
                QMessageBox.warning(self, "Error", "Failed to get window information")
                
        except subprocess.TimeoutExpired:
            QMessageBox.warning(self, "Timeout", "Window selection timed out")
        except FileNotFoundError:
            QMessageBox.critical(self, "Error", "xprop not found. Please install x11-utils package.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to pick window: {e}")
    
    def remove_selected(self):
        """Remove selected app from exclusion list"""
        current_item = self.excluded_list.currentItem()
        if current_item:
            app_name = current_item.text()
            self.current_exclusions.remove(app_name)
            self.excluded_list.takeItem(self.excluded_list.row(current_item))
    
    def get_exclusions(self):
        """Return the list of excluded apps"""
        return self.current_exclusions


class PicomTab(QWidget):
    """Picom compositor settings tab with dynamic UI"""
    
    def __init__(self, config_parser):
        super().__init__()
        self.config = config_parser
        self.picom_config_path = Path.home() / ".config" / "picom" / "picom.conf"
        self.picom_installed = self.check_picom_installed()
        self.original_config = self.load_original_config()
        
        # UI element references for dynamic show/hide
        self.shadow_details_widget = None
        self.blur_details_widget = None
        self.fading_details_widget = None
        self.animation_details_widget = None
        
        self.init_ui()
    
    def check_picom_installed(self):
        """Check if picom is installed"""
        try:
            subprocess.run(['which', 'picom'], check=True, capture_output=True, text=True)
            return True
        except subprocess.CalledProcessError:
            return False
    
    def load_original_config(self):
        """Load original config to restore if changes are discarded"""
        if not self.picom_config_path.exists():
            return ""
        try:
            with open(self.picom_config_path, 'r') as f:
                return f.read()
        except Exception:
            return ""
    
    def init_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Create scroll area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        # Create scroll content widget
        scroll_content = QWidget()
        scroll_content.setObjectName("picomScrollContent")
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setSpacing(15)
        scroll_layout.setContentsMargins(10, 10, 10, 10)
        
        if not self.picom_installed:
            # Show installation message
            self.add_installation_widget(scroll_layout)
        else:
            # Add all settings groups
            self.add_corner_settings(scroll_layout)
            self.add_shadow_settings(scroll_layout)
            self.add_blur_settings(scroll_layout)
            self.add_fading_settings(scroll_layout)
            self.add_animation_settings(scroll_layout)
            self.add_opacity_settings(scroll_layout)
            self.add_general_settings(scroll_layout)
            self.add_action_buttons(scroll_layout)
        
        scroll_layout.addStretch()
        
        # Set scroll area content
        scroll_area.setWidget(scroll_content)
        layout.addWidget(scroll_area)
        
        self.setLayout(layout)
    
        
    
    def add_corner_settings(self, parent_layout):
        """Add corner radius settings"""
        corner_group = QGroupBox("Window Corner Radius")
        corner_layout = QVBoxLayout()
        corner_layout.setSpacing(10)
        
        radius_layout = QHBoxLayout()
        radius_layout.addWidget(QLabel("Corner Radius:"))
        self.corner_radius = QSpinBox()
        self.corner_radius.setRange(0, 30)
        self.corner_radius.setValue(self.get_current_corner_radius())
        radius_layout.addWidget(self.corner_radius)
        radius_layout.addStretch()
        
        corner_layout.addLayout(radius_layout)
        corner_group.setLayout(corner_layout)
        parent_layout.addWidget(corner_group)
    
    def add_shadow_settings(self, parent_layout):
        """Add shadow settings with collapsible details"""
        shadow_group = QGroupBox("Shadows")
        shadow_layout = QVBoxLayout()
        shadow_layout.setSpacing(10)
        
        # Main checkbox
        self.shadow_enabled = QCheckBox("Enable Shadows")
        self.shadow_enabled.setChecked(self.get_current_shadow_enabled())
        self.shadow_enabled.stateChanged.connect(self.toggle_shadow_details)
        shadow_layout.addWidget(self.shadow_enabled)
        
        # Details widget (collapsible)
        self.shadow_details_widget = QWidget()
        details_layout = QVBoxLayout(self.shadow_details_widget)
        details_layout.setContentsMargins(20, 0, 0, 0)
        
        # Shadow radius
        shadow_radius_layout = QHBoxLayout()
        shadow_radius_layout.addWidget(QLabel("Shadow Radius:"))
        self.shadow_radius = QSpinBox()
        self.shadow_radius.setRange(0, 50)
        self.shadow_radius.setValue(self.get_current_shadow_radius())
        shadow_radius_layout.addWidget(self.shadow_radius)
        shadow_radius_layout.addStretch()
        details_layout.addLayout(shadow_radius_layout)
        
        # Shadow offsets
        shadow_offset_layout = QHBoxLayout()
        shadow_offset_layout.addWidget(QLabel("Offset X:"))
        self.shadow_offset_x = QSpinBox()
        self.shadow_offset_x.setRange(-50, 50)
        self.shadow_offset_x.setValue(self.get_current_shadow_offset_x())
        shadow_offset_layout.addWidget(self.shadow_offset_x)
        
        shadow_offset_layout.addWidget(QLabel("Offset Y:"))
        self.shadow_offset_y = QSpinBox()
        self.shadow_offset_y.setRange(-50, 50)
        self.shadow_offset_y.setValue(self.get_current_shadow_offset_y())
        shadow_offset_layout.addWidget(self.shadow_offset_y)
        shadow_offset_layout.addStretch()
        details_layout.addLayout(shadow_offset_layout)
        
        # Shadow opacity
        shadow_opacity_layout = QHBoxLayout()
        shadow_opacity_layout.addWidget(QLabel("Shadow Opacity:"))
        self.shadow_opacity = QSpinBox()
        self.shadow_opacity.setRange(0, 100)
        self.shadow_opacity.setValue(int(self.get_current_shadow_opacity() * 100))
        self.shadow_opacity.setSuffix(" %")
        shadow_opacity_layout.addWidget(self.shadow_opacity)
        shadow_opacity_layout.addStretch()
        details_layout.addLayout(shadow_opacity_layout)
        
        # Exclude apps button
        exclude_btn = QPushButton("Exclude Apps from Shadows...")
        exclude_btn.clicked.connect(self.show_app_selector)
        details_layout.addWidget(exclude_btn)
        
        # Excluded apps label
        self.excluded_apps_label = QLabel(f"Excluded apps: {', '.join(self.get_shadow_exclusions()) or 'None'}")
        self.excluded_apps_label.setWordWrap(True)
        details_layout.addWidget(self.excluded_apps_label)
        
        shadow_layout.addWidget(self.shadow_details_widget)
        
        # Set initial visibility
        self.shadow_details_widget.setVisible(self.shadow_enabled.isChecked())
        
        shadow_group.setLayout(shadow_layout)
        parent_layout.addWidget(shadow_group)
    
    def add_blur_settings(self, parent_layout):
        """Add blur settings with collapsible details"""
        blur_group = QGroupBox("Blur")
        blur_layout = QVBoxLayout()
        blur_layout.setSpacing(10)
        
        # Main checkbox
        self.blur_background = QCheckBox("Enable Blur")
        self.blur_background.setChecked(self.get_current_blur_background())
        self.blur_background.stateChanged.connect(self.toggle_blur_details)
        blur_layout.addWidget(self.blur_background)
        
        # Details widget (collapsible)
        self.blur_details_widget = QWidget()
        details_layout = QVBoxLayout(self.blur_details_widget)
        details_layout.setContentsMargins(20, 0, 0, 0)
        
        # Blur frame
        self.blur_background_frame = QCheckBox("Blur Background Frame")
        self.blur_background_frame.setChecked(self.get_current_blur_background_frame())
        details_layout.addWidget(self.blur_background_frame)
        
        # Blur method
        blur_method_layout = QHBoxLayout()
        blur_method_layout.addWidget(QLabel("Blur Method:"))
        self.blur_method = QComboBox()
        self.blur_method.addItems(["none", "gaussian", "box", "dual_kawase", "kernel"])
        current_method = self.get_current_blur_method()
        if current_method in ["none", "gaussian", "box", "dual_kawase", "kernel"]:
            self.blur_method.setCurrentText(current_method)
        blur_method_layout.addWidget(self.blur_method)
        blur_method_layout.addStretch()
        details_layout.addLayout(blur_method_layout)
        
        # Blur strength
        blur_strength_layout = QHBoxLayout()
        blur_strength_layout.addWidget(QLabel("Blur Strength:"))
        self.blur_strength = QSpinBox()
        self.blur_strength.setRange(1, 20)
        self.blur_strength.setValue(self.get_current_blur_strength())
        blur_strength_layout.addWidget(self.blur_strength)
        blur_strength_layout.addStretch()
        details_layout.addLayout(blur_strength_layout)
        
        # Blur size
        blur_size_layout = QHBoxLayout()
        blur_size_layout.addWidget(QLabel("Blur Size:"))
        self.blur_size = QSpinBox()
        self.blur_size.setRange(1, 50)
        self.blur_size.setValue(self.get_current_blur_size())
        blur_size_layout.addWidget(self.blur_size)
        blur_size_layout.addStretch()
        details_layout.addLayout(blur_size_layout)
        
        blur_layout.addWidget(self.blur_details_widget)
        
        # Set initial visibility
        self.blur_details_widget.setVisible(self.blur_background.isChecked())
        
        blur_group.setLayout(blur_layout)
        parent_layout.addWidget(blur_group)
    
    def add_fading_settings(self, parent_layout):
        """Add fading settings with collapsible details"""
        fading_group = QGroupBox("Fading")
        fading_layout = QVBoxLayout()
        fading_layout.setSpacing(10)
        
        # Main checkbox
        self.fading_enabled = QCheckBox("Enable Fading")
        self.fading_enabled.setChecked(self.get_current_fading_enabled())
        self.fading_enabled.stateChanged.connect(self.toggle_fading_details)
        fading_layout.addWidget(self.fading_enabled)
        
        # Details widget (collapsible)
        self.fading_details_widget = QWidget()
        details_layout = QVBoxLayout(self.fading_details_widget)
        details_layout.setContentsMargins(20, 0, 0, 0)
        
        # Fade steps
        fade_step_layout = QHBoxLayout()
        fade_step_layout.addWidget(QLabel("Fade In Step:"))
        self.fade_in_step = QSpinBox()
        self.fade_in_step.setRange(1, 100)
        self.fade_in_step.setValue(int(self.get_current_fade_in_step() * 100))
        self.fade_in_step.setSuffix(" %")
        fade_step_layout.addWidget(self.fade_in_step)
        
        fade_step_layout.addWidget(QLabel("Fade Out Step:"))
        self.fade_out_step = QSpinBox()
        self.fade_out_step.setRange(1, 100)
        self.fade_out_step.setValue(int(self.get_current_fade_out_step() * 100))
        self.fade_out_step.setSuffix(" %")
        fade_step_layout.addWidget(self.fade_out_step)
        fade_step_layout.addStretch()
        details_layout.addLayout(fade_step_layout)
        
        # Fade delta
        fade_delta_layout = QHBoxLayout()
        fade_delta_layout.addWidget(QLabel("Fade Delta (ms):"))
        self.fade_delta = QSpinBox()
        self.fade_delta.setRange(1, 100)
        self.fade_delta.setValue(self.get_current_fade_delta())
        fade_delta_layout.addWidget(self.fade_delta)
        fade_delta_layout.addStretch()
        details_layout.addLayout(fade_delta_layout)
        
        fading_layout.addWidget(self.fading_details_widget)
        
        # Set initial visibility
        self.fading_details_widget.setVisible(self.fading_enabled.isChecked())
        
        fading_group.setLayout(fading_layout)
        parent_layout.addWidget(fading_group)
    
    def add_animation_settings(self, parent_layout):
        """Add animation settings with collapsible details"""
        animation_group = QGroupBox("Animations")
        animation_layout = QVBoxLayout()
        animation_layout.setSpacing(10)
        
        # Main checkbox
        self.animations_enabled = QCheckBox("Enable Animations")
        self.animations_enabled.setChecked(self.get_current_animations_enabled())
        self.animations_enabled.stateChanged.connect(self.toggle_animation_details)
        animation_layout.addWidget(self.animations_enabled)
        
        # Details widget (collapsible)
        self.animation_details_widget = QWidget()
        details_layout = QVBoxLayout(self.animation_details_widget)
        details_layout.setContentsMargins(20, 0, 0, 0)
        
        # Animation style
        animation_style_layout = QHBoxLayout()
        animation_style_layout.addWidget(QLabel("Animation Style:"))
        self.animation_style = QComboBox()
        self.animation_style.addItems(["none", "slide", "fade", "scale"])
        current_style = self.get_current_animation_style()
        if current_style in ["none", "slide", "fade", "scale"]:
            self.animation_style.setCurrentText(current_style)
        animation_style_layout.addWidget(self.animation_style)
        animation_style_layout.addStretch()
        details_layout.addLayout(animation_style_layout)
        
        # Animation duration
        animation_duration_layout = QHBoxLayout()
        animation_duration_layout.addWidget(QLabel("Animation Duration (ms):"))
        self.animation_duration = QSpinBox()
        self.animation_duration.setRange(10, 2000)
        self.animation_duration.setValue(self.get_current_animation_duration())
        animation_duration_layout.addWidget(self.animation_duration)
        animation_duration_layout.addStretch()
        details_layout.addLayout(animation_duration_layout)
        
        animation_layout.addWidget(self.animation_details_widget)
        
        # Set initial visibility
        self.animation_details_widget.setVisible(self.animations_enabled.isChecked())
        
        animation_group.setLayout(animation_layout)
        parent_layout.addWidget(animation_group)
    
    def add_opacity_settings(self, parent_layout):
        """Add opacity settings"""
        opacity_group = QGroupBox("Transparency")
        opacity_layout = QVBoxLayout()
        opacity_layout.setSpacing(10)
        
        # Frame opacity
        frame_opacity_layout = QHBoxLayout()
        frame_opacity_layout.addWidget(QLabel("Frame Opacity:"))
        self.frame_opacity = QSpinBox()
        self.frame_opacity.setRange(10, 100)
        self.frame_opacity.setValue(int(self.get_current_frame_opacity() * 100))
        self.frame_opacity.setSuffix(" %")
        frame_opacity_layout.addWidget(self.frame_opacity)
        frame_opacity_layout.addStretch()
        opacity_layout.addLayout(frame_opacity_layout)
        
        # Inactive opacity
        inactive_opacity_layout = QHBoxLayout()
        inactive_opacity_layout.addWidget(QLabel("Inactive Opacity:"))
        self.inactive_opacity = QSpinBox()
        self.inactive_opacity.setRange(10, 100)
        self.inactive_opacity.setValue(int(self.get_current_inactive_opacity() * 100))
        self.inactive_opacity.setSuffix(" %")
        inactive_opacity_layout.addWidget(self.inactive_opacity)
        inactive_opacity_layout.addStretch()
        opacity_layout.addLayout(inactive_opacity_layout)
        
        opacity_group.setLayout(opacity_layout)
        parent_layout.addWidget(opacity_group)
    
    def add_general_settings(self, parent_layout):
        """Add general settings"""
        general_group = QGroupBox("General Settings")
        general_layout = QVBoxLayout()
        general_layout.setSpacing(10)
        
        # Backend
        backend_layout = QHBoxLayout()
        backend_layout.addWidget(QLabel("Backend:"))
        self.backend = QComboBox()
        self.backend.addItems(["xrender", "glx", "xr_glx_hybrid"])
        current_backend = self.get_current_backend()
        if current_backend in ["xrender", "glx", "xr_glx_hybrid"]:
            self.backend.setCurrentText(current_backend)
        backend_layout.addWidget(self.backend)
        backend_layout.addStretch()
        general_layout.addLayout(backend_layout)
        
        # VSync
        self.vsync_enabled = QCheckBox("Enable VSync")
        self.vsync_enabled.setChecked(self.get_current_vsync_enabled())
        general_layout.addWidget(self.vsync_enabled)
        
        # Detect rounded corners
        self.detect_rounded_corners = QCheckBox("Detect Rounded Corners")
        self.detect_rounded_corners.setChecked(self.get_current_detect_rounded_corners())
        general_layout.addWidget(self.detect_rounded_corners)
        
        general_group.setLayout(general_layout)
        parent_layout.addWidget(general_group)
    
    def add_action_buttons(self, parent_layout):
        """Add action buttons"""
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        
        apply_btn = QPushButton("Apply Picom Settings")
        apply_btn.clicked.connect(self.apply_settings)
        button_layout.addWidget(apply_btn)
        
        discard_btn = QPushButton("Discard Changes")
        discard_btn.setStyleSheet("padding: 8px 16px;")
        discard_btn.clicked.connect(self.discard_changes)
        button_layout.addWidget(discard_btn)
        
        button_layout.addStretch()
        
        parent_layout.addLayout(button_layout)
    
    # Toggle methods for collapsible sections
    def toggle_shadow_details(self, state):
        """Toggle shadow details visibility"""
        self.shadow_details_widget.setVisible(state == Qt.CheckState.Checked.value)
    
    def toggle_blur_details(self, state):
        """Toggle blur details visibility"""
        self.blur_details_widget.setVisible(state == Qt.CheckState.Checked.value)
    
    def toggle_fading_details(self, state):
        """Toggle fading details visibility"""
        self.fading_details_widget.setVisible(state == Qt.CheckState.Checked.value)
    
    def toggle_animation_details(self, state):
        """Toggle animation details visibility"""
        self.animation_details_widget.setVisible(state == Qt.CheckState.Checked.value)
    
    def show_app_selector(self):
        """Show app selector dialog for shadow exclusions"""
        current_exclusions = self.get_shadow_exclusions()
        dialog = AppSelectorDialog(self, current_exclusions)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            exclusions = dialog.get_exclusions()
            self.excluded_apps_label.setText(f"Excluded apps: {', '.join(exclusions) or 'None'}")
    
    def get_shadow_exclusions(self):
        """Get list of apps excluded from shadows"""
        if not self.picom_config_path.exists():
            return []
        
        try:
            with open(self.picom_config_path, 'r') as f:
                content = f.read()
            
            # Look for shadow-exclude array
            match = re.search(r'shadow-exclude\s*=\s*\[(.*?)\];', content, re.DOTALL)
            if match:
                exclusions_str = match.group(1)
                # Extract class names
                class_matches = re.findall(r'class_g\s*=\s*"([^"]+)"', exclusions_str)
                return class_matches
            return []
        except Exception:
            return []
    
    def save_shadow_exclusions(self, content, exclusions):
        """Save shadow exclusions to config"""
        # Build exclusion array
        if exclusions:
            exclusion_rules = []
            for app_class in exclusions:
                exclusion_rules.append(f'  "class_g = \'{app_class}\'"')
            
            exclusion_str = 'shadow-exclude = [\n' + ',\n'.join(exclusion_rules) + '\n];'
            
            # Remove existing shadow-exclude
            content = re.sub(r'shadow-exclude\s*=\s*\[.*?\];', '', content, flags=re.DOTALL)
            
            # Add new shadow-exclude
            content += '\n' + exclusion_str + '\n'
        else:
            # Remove shadow-exclude if no exclusions
            content = re.sub(r'shadow-exclude\s*=\s*\[.*?\];', '', content, flags=re.DOTALL)
        
        return content

    # All the get_current_* methods from original code
    def get_current_corner_radius(self):
        if not self.picom_config_path.exists():
            return 0
        try:
            with open(self.picom_config_path, 'r') as f:
                content = f.read()
            match = re.search(r'corner-radius\s*=\s*(\d+)\s*;?', content)
            if match:
                return int(match.group(1))
            return 0
        except Exception:
            return 0
    
    def get_current_shadow_enabled(self):
        if not self.picom_config_path.exists():
            return False
        try:
            with open(self.picom_config_path, 'r') as f:
                content = f.read()
            match = re.search(r'shadow\s*=\s*(true|false);', content)
            if match:
                return match.group(1) == 'true'
            return False
        except Exception:
            return False
    
    def get_current_shadow_radius(self):
        if not self.picom_config_path.exists():
            return 12
        try:
            with open(self.picom_config_path, 'r') as f:
                content = f.read()
            match = re.search(r'shadow-radius\s*=\s*(\d+);', content)
            if match:
                return int(match.group(1))
            return 12
        except Exception:
            return 12
    
    def get_current_shadow_offset_x(self):
        if not self.picom_config_path.exists():
            return -15
        try:
            with open(self.picom_config_path, 'r') as f:
                content = f.read()
            match = re.search(r'shadow-offset-x\s*=\s*(-?\d+);', content)
            if match:
                return int(match.group(1))
            return -15
        except Exception:
            return -15
    
    def get_current_shadow_offset_y(self):
        if not self.picom_config_path.exists():
            return -15
        try:
            with open(self.picom_config_path, 'r') as f:
                content = f.read()
            match = re.search(r'shadow-offset-y\s*=\s*(-?\d+);', content)
            if match:
                return int(match.group(1))
            return -15
        except Exception:
            return -15
    
    def get_current_shadow_opacity(self):
        if not self.picom_config_path.exists():
            return 0.75
        try:
            with open(self.picom_config_path, 'r') as f:
                content = f.read()
            match = re.search(r'shadow-opacity\s*=\s*([\d.]+);', content)
            if match:
                return float(match.group(1))
            return 0.75
        except Exception:
            return 0.75
    
    def get_current_blur_background(self):
        if not self.picom_config_path.exists():
            return False
        try:
            with open(self.picom_config_path, 'r') as f:
                content = f.read()
            match = re.search(r'blur-background\s*=\s*(true|false);', content)
            if match:
                return match.group(1) == 'true'
            return False
        except Exception:
            return False
    
    def get_current_blur_background_frame(self):
        if not self.picom_config_path.exists():
            return False
        try:
            with open(self.picom_config_path, 'r') as f:
                content = f.read()
            match = re.search(r'blur-background-frame\s*=\s*(true|false);', content)
            if match:
                return match.group(1) == 'true'
            return False
        except Exception:
            return False
    
    def get_current_blur_method(self):
        if not self.picom_config_path.exists():
            return "none"
        try:
            with open(self.picom_config_path, 'r') as f:
                content = f.read()
            match = re.search(r'blur-method\s*=\s*"?([a-zA-Z_]+)"?;', content)
            if match:
                return match.group(1)
            return "none"
        except Exception:
            return "none"
    
    def get_current_blur_strength(self):
        if not self.picom_config_path.exists():
            return 5
        try:
            with open(self.picom_config_path, 'r') as f:
                content = f.read()
            match = re.search(r'blur-strength\s*=\s*(\d+);', content)
            if match:
                return int(match.group(1))
            return 5
        except Exception:
            return 5
    
    def get_current_blur_size(self):
        if not self.picom_config_path.exists():
            return 12
        try:
            with open(self.picom_config_path, 'r') as f:
                content = f.read()
            match = re.search(r'blur-size\s*=\s*(\d+);', content)
            if match:
                return int(match.group(1))
            return 12
        except Exception:
            return 12
    
    def get_current_fading_enabled(self):
        if not self.picom_config_path.exists():
            return False
        try:
            with open(self.picom_config_path, 'r') as f:
                content = f.read()
            match = re.search(r'fading\s*=\s*(true|false);', content)
            if match:
                return match.group(1) == 'true'
            return False
        except Exception:
            return False
    
    def get_current_fade_in_step(self):
        if not self.picom_config_path.exists():
            return 0.028
        try:
            with open(self.picom_config_path, 'r') as f:
                content = f.read()
            match = re.search(r'fade-in-step\s*=\s*([\d.]+);', content)
            if match:
                return float(match.group(1))
            return 0.028
        except Exception:
            return 0.028
    
    def get_current_fade_out_step(self):
        if not self.picom_config_path.exists():
            return 0.03
        try:
            with open(self.picom_config_path, 'r') as f:
                content = f.read()
            match = re.search(r'fade-out-step\s*=\s*([\d.]+);', content)
            if match:
                return float(match.group(1))
            return 0.03
        except Exception:
            return 0.03
    
    def get_current_fade_delta(self):
        if not self.picom_config_path.exists():
            return 10
        try:
            with open(self.picom_config_path, 'r') as f:
                content = f.read()
            match = re.search(r'fade-delta\s*=\s*(\d+);', content)
            if match:
                return int(match.group(1))
            return 10
        except Exception:
            return 10
    
    def get_current_animations_enabled(self):
        if not self.picom_config_path.exists():
            return False
        try:
            with open(self.picom_config_path, 'r') as f:
                content = f.read()
            match = re.search(r'animations\s*=', content)
            return bool(match)
        except Exception:
            return False
    
    def get_current_animation_style(self):
        if not self.picom_config_path.exists():
            return "none"
        try:
            with open(self.picom_config_path, 'r') as f:
                content = f.read()
            match = re.search(r'preset\s*=\s*"?([a-zA-Z_]+)"?', content)
            if match:
                return match.group(1)
            return "none"
        except Exception:
            return "none"
    
    def get_current_animation_duration(self):
        if not self.picom_config_path.exists():
            return 300
        try:
            with open(self.picom_config_path, 'r') as f:
                content = f.read()
            match = re.search(r'duration\s*=\s*([\d.]+)', content)
            if match:
                return int(float(match.group(1)) * 1000)
            return 300
        except Exception:
            return 300
    
    def get_current_frame_opacity(self):
        if not self.picom_config_path.exists():
            return 1.0
        try:
            with open(self.picom_config_path, 'r') as f:
                content = f.read()
            match = re.search(r'frame-opacity\s*=\s*([\d.]+);', content)
            if match:
                return float(match.group(1))
            return 1.0
        except Exception:
            return 1.0
    
    def get_current_inactive_opacity(self):
        if not self.picom_config_path.exists():
            return 1.0
        try:
            with open(self.picom_config_path, 'r') as f:
                content = f.read()
            match = re.search(r'inactive-opacity\s*=\s*([\d.]+);', content)
            if match:
                return float(match.group(1))
            return 1.0
        except Exception:
            return 1.0
    
    def get_current_backend(self):
        if not self.picom_config_path.exists():
            return "xrender"
        try:
            with open(self.picom_config_path, 'r') as f:
                content = f.read()
            match = re.search(r'backend\s*=\s*"?([a-zA-Z_]+)"?;', content)
            if match:
                return match.group(1)
            return "xrender"
        except Exception:
            return "xrender"
    
    def get_current_vsync_enabled(self):
        if not self.picom_config_path.exists():
            return False
        try:
            with open(self.picom_config_path, 'r') as f:
                content = f.read()
            match = re.search(r'vsync\s*=\s*(true|false);', content)
            if match:
                return match.group(1) == 'true'
            return False
        except Exception:
            return False
    
    def get_current_detect_rounded_corners(self):
        if not self.picom_config_path.exists():
            return False
        try:
            with open(self.picom_config_path, 'r') as f:
                content = f.read()
            match = re.search(r'detect-rounded-corners\s*=\s*(true|false);', content)
            if match:
                return match.group(1) == 'true'
            return False
        except Exception:
            return False
    
   
    def apply_settings(self):
        """Apply picom settings"""
        if not self.picom_installed:
            QMessageBox.warning(self, "Warning", "Picom is not installed. Please install it first.")
            return
        
        try:
            self.picom_config_path.parent.mkdir(parents=True, exist_ok=True)
            
            if self.picom_config_path.exists():
                with open(self.picom_config_path, 'r') as f:
                    content = f.read()
            else:
                content = ""
            
            # Update all settings
            content = self.update_config_value(content, 'corner-radius', self.corner_radius.value())
            content = self.update_config_value(content, 'shadow', str(self.shadow_enabled.isChecked()).lower(), is_bool=True)
            
            if self.shadow_enabled.isChecked():
                content = self.update_config_value(content, 'shadow-radius', self.shadow_radius.value())
                content = self.update_config_value(content, 'shadow-offset-x', self.shadow_offset_x.value())
                content = self.update_config_value(content, 'shadow-offset-y', self.shadow_offset_y.value())
                content = self.update_config_value(content, 'shadow-opacity', self.shadow_opacity.value() / 100, is_float=True)
                
                # Save shadow exclusions
                exclusions = self.get_shadow_exclusions()
                content = self.save_shadow_exclusions(content, exclusions)
            
            content = self.update_config_value(content, 'blur-background', str(self.blur_background.isChecked()).lower(), is_bool=True)
            
            if self.blur_background.isChecked():
                content = self.update_config_value(content, 'blur-background-frame', str(self.blur_background_frame.isChecked()).lower(), is_bool=True)
                content = self.update_config_value(content, 'blur-method', self.blur_method.currentText(), is_string=True)
                content = self.update_config_value(content, 'blur-strength', self.blur_strength.value())
                content = self.update_config_value(content, 'blur-size', self.blur_size.value())
            
            content = self.update_config_value(content, 'fading', str(self.fading_enabled.isChecked()).lower(), is_bool=True)
            
            if self.fading_enabled.isChecked():
                content = self.update_config_value(content, 'fade-in-step', self.fade_in_step.value() / 100, is_float=True)
                content = self.update_config_value(content, 'fade-out-step', self.fade_out_step.value() / 100, is_float=True)
                content = self.update_config_value(content, 'fade-delta', self.fade_delta.value())
            
            if self.animations_enabled.isChecked():
                if not re.search(r'animations\s*=', content):
                    content += '\nanimations = (\n'
                    content += '  {\n'
                    content += '    preset = "fade";\n'
                    content += '    duration = 0.3;\n'
                    content += '    triggers = ["open", "close"];\n'
                    content += '  },\n'
                    content += '  {\n'
                    content += '    preset = "slide";\n'
                    content += '    duration = 0.3;\n'
                    content += '    triggers = ["focus", "blur"];\n'
                    content += '  }\n'
                    content += ');\n'
            else:
                content = re.sub(r'\s*animations\s*=\s*\([\s\S]*?\);', '', content)
            
            content = self.update_config_value(content, 'frame-opacity', self.frame_opacity.value() / 100, is_float=True)
            
            if not re.search(r'rules\s*=', content):
                content = self.update_config_value(content, 'inactive-opacity', self.inactive_opacity.value() / 100, is_float=True)
            else:
                content = re.sub(r'\s*inactive-opacity\s*=\s*[\d.]+;', '', content)
            
            content = self.update_config_value(content, 'backend', self.backend.currentText(), is_string=True)
            content = self.update_config_value(content, 'vsync', str(self.vsync_enabled.isChecked()).lower(), is_bool=True)
            content = self.update_config_value(content, 'detect-rounded-corners', str(self.detect_rounded_corners.isChecked()).lower(), is_bool=True)
            
            with open(self.picom_config_path, 'w') as f:
                f.write(content)
            
            self.restart_picom()
            QMessageBox.information(self, "Success", "Picom settings applied successfully!")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to apply picom settings: {e}")
    
    def update_config_value(self, content, key, value, is_bool=False, is_float=False, is_string=False):
        """Update a config value in the content"""
        if is_string:
            value_str = f'"{value}"'
        elif is_float:
            value_str = f'{value:.2f}'
        else:
            value_str = str(value)
        
        pattern = rf'{key}\s*=\s*[^;]+;'
        replacement = f'{key} = {value_str};'
        
        if re.search(pattern, content):
            content = re.sub(pattern, replacement, content)
        else:
            content += f'\n{replacement}'
        
        return content
    
    def discard_changes(self):
        """Discard changes and restore original settings"""
        try:
            with open(self.picom_config_path, 'w') as f:
                f.write(self.original_config)
            
            self.restart_picom()
            
            # Reinitialize UI
            for i in reversed(range(self.layout().count())): 
                self.layout().itemAt(i).widget().setParent(None)
            self.init_ui()
            
            QMessageBox.information(self, "Success", "Changes discarded and picom settings restored!")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to discard changes: {e}")
    
    def restart_picom(self):
        """Restart picom compositor"""
        try:
            subprocess.run(['pkill', 'picom'], check=False)
            import time
            time.sleep(0.5)
            subprocess.Popen(['picom', '-b'])
        except Exception as e:
            QMessageBox.warning(self, "Warning", f"Failed to restart picom: {e}")