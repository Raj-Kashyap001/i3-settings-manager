"""
I3ConfigParser module for parsing and modifying i3 config files
"""

import re
import subprocess
import time
import threading
from pathlib import Path

try:
    import i3ipc
    HAS_I3IPC = True
except ImportError:
    HAS_I3IPC = False

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