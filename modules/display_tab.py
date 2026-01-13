"""
DisplayTab module for display configuration
"""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel, QComboBox, QPushButton, QMessageBox
from PyQt6.QtCore import Qt
import subprocess

class DisplayTab(QWidget):
    """Display configuration tab with responsive, centered layout"""

    def __init__(self, config_parser=None):
        super().__init__()
        self.config = config_parser
        self.current_rates = {}
        self.init_ui()

    def init_ui(self):
        # Outer layout to center content
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Container for all content, max width limits stretching
        self.container = QWidget()
        self.container_layout = QVBoxLayout(self.container)
        self.container_layout.setSpacing(20)
        self.container_layout.setContentsMargins(16, 16, 16, 16)

        outer_layout.addWidget(self.container)

        # Load monitors into container
        self.load_monitor_info()

    # -------------------- Monitor Info --------------------
    def get_monitor_info(self):
        """Get monitor info using xrandr"""
        monitors = []
        try:
            result = subprocess.run(['xrandr'], capture_output=True, text=True, check=True)

            current_output = None
            current_info = {}
            in_resolution_section = False

            for line in result.stdout.splitlines():
                original_line = line
                line = line.strip()

                # Start of monitor output
                if ' connected' in line or ' disconnected' in line:
                    if current_output and current_info:
                        monitors.append(current_info)

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

                # Parse resolutions for connected monitor
                elif current_output and current_info['connected'] and in_resolution_section and line and (line[0].isdigit() or ('x' in line and any(c.isdigit() for c in line))):
                    parts = line.split()
                    if len(parts) >= 2:
                        res = parts[0]
                        current_info['resolutions'].append(res)

                        # Find current rate
                        for part in parts[1:]:
                            if '*' in part:
                                current_info['current_resolution'] = res
                                current_info['current_rate'] = part.replace('*', '').replace('+', '').strip()
                                break

                        # Collect all rates
                        rates = []
                        for part in parts[1:]:
                            clean = part.replace('*', '').replace('+', '').strip()
                            if clean.replace('.', '').isdigit() and clean not in rates:
                                rates.append(clean)
                        current_info['refresh_rates'].extend(rates)

                # End of resolution section
                elif current_output and original_line.startswith(' ') and not original_line.strip().startswith(('Screen', 'VGA', 'HDMI', 'DP')):
                    in_resolution_section = False

            # Add last monitor
            if current_output and current_info:
                monitors.append(current_info)

        except Exception as e:
            print(f"Failed to get monitor info: {e}")
        return monitors

    # -------------------- Load Monitors --------------------
    def load_monitor_info(self):
        """Display monitor info in container"""
        # Clear previous widgets
        for i in reversed(range(self.container_layout.count())):
            widget = self.container_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)

        monitors = self.get_monitor_info()
        for monitor in monitors:
            if not monitor['connected']:
                continue

            monitor_group = QGroupBox(f"Monitor: {monitor['name']}")
            monitor_layout = QVBoxLayout()
            monitor_layout.setSpacing(12)
            monitor_layout.setContentsMargins(12, 12, 12, 12)

            # Info label
            info_text = f"Resolution: {monitor['current_resolution'] or 'Unknown'} @ {monitor['current_rate'] or 'Unknown'}Hz"
            if monitor.get('primary'):
                info_text += " (Primary)"
            info_label = QLabel(info_text)
            monitor_layout.addWidget(info_label)

            # Refresh rate selection
            if monitor['refresh_rates']:
                rate_layout = QHBoxLayout()
                rate_layout.setSpacing(8)
                rate_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)

                rate_layout.addWidget(QLabel("Refresh Rate:"))
                rate_combo = QComboBox()

                # Unique rates
                seen = set()
                unique_rates = [r for r in monitor['refresh_rates'] if not (r in seen or seen.add(r))]
                rate_combo.addItems(unique_rates)

                # Current rate
                current_rate = monitor['current_rate']
                self.current_rates[monitor['name']] = current_rate
                if current_rate:
                    idx = rate_combo.findText(current_rate)
                    if idx >= 0:
                        rate_combo.setCurrentIndex(idx)

                rate_layout.addWidget(rate_combo)

                # Apply button
                apply_btn = QPushButton("Apply")
                apply_btn.setEnabled(False)

                # Enable apply only when changed
                def on_rate_changed(index, combo=rate_combo, btn=apply_btn):
                    btn.setEnabled(combo.currentText() != current_rate)

                rate_combo.currentIndexChanged.connect(on_rate_changed)
                apply_btn.clicked.connect(lambda _, m=monitor['name'], rc=rate_combo: self.apply_monitor_refresh_rate(m, rc))
                monitor_layout.addLayout(rate_layout)
                monitor_layout.addWidget(apply_btn)

            monitor_group.setLayout(monitor_layout)
            self.container_layout.addWidget(monitor_group)

    # -------------------- Apply Refresh --------------------
    def apply_monitor_refresh_rate(self, monitor_name, rate_combo):
        """Apply refresh rate"""
        rate = rate_combo.currentText()
        try:
            monitors = self.get_monitor_info()
            monitor_info = next((m for m in monitors if m['name'] == monitor_name and m['connected']), None)
            if not monitor_info or not monitor_info['current_resolution']:
                send_notification("Error", f"Could not get current resolution for {monitor_name}")
                return

            subprocess.run(
                ['xrandr', '--output', monitor_name, '--mode', monitor_info['current_resolution'], '--rate', rate],
                capture_output=True, text=True, check=True
            )
            send_notification("Success", f"{monitor_name}: {monitor_info['current_resolution']} @ {rate}Hz applied")

            # Refresh UI
            self.load_monitor_info()
        except subprocess.CalledProcessError as e:
            send_notification("Error", f"Failed to set refresh rate: {e.stderr}")
        except Exception as e:
            send_notification("Error", str(e))


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