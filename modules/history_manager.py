"""
HistoryManager module for managing configuration history
"""

import json
from pathlib import Path
from datetime import datetime

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