# i3 Settings Manager

A modern GUI application for managing i3 window manager configuration with an intuitive interface.

## Features

- **Visual Appearance Customization** - Configure gaps, borders, and window styling
- **Keybinding Management** - Add, edit, and delete keybindings with conflict detection
- **Configuration History** - Automatic backups and restore functionality
- **Wallpaper Management** - Set wallpapers and random wallpaper support
- **Monitor Control** - Configure display refresh rates
- **Startup Applications** - Manage exec commands and startup applications
- **Live Preview** - See changes before applying them

## Screenshots

_Add screenshots here_

## Requirements

- Python 3.8+
- PyQt6
- i3 window manager
- Linux duh (tested on systems with i3wm)

## Installation

### Automated Builds (Recommended)

Pre-built binaries are automatically created for each commit to the main branch:

1. Go to [Releases](https://github.com/Raj-Kashyap001/i3-settings-manager/releases)
2. Download the latest `i3-settings-manager-linux-x64.tar.gz`
3. Extract and run: `tar -xzf i3-settings-manager-linux-x64.tar.gz && ./i3-settings-manager`

### From Source

1. Clone the repository:

```bash
git clone https://github.com/Raj-Kashyap001/i3-settings-manager.git
cd i3-settings-manager
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Run the application:

```bash
python3 main.py
```

### Dependencies

The application requires these external tools to be installed:

- [`i3-msg`](https://github.com/i3/i3) (i3 window manager)
- [`feh`](https://github.com/derf/feh) (for wallpaper setting)
- [`matugen`](https://github.com/InioX/matugen) (for color scheme generation - optional)
- `xrdb` (X resource database utility - part of Xorg)
- [`dunst`](https://github.com/dunst-project/dunst) (`dunstify`) or `notify-send` (for notifications)

## Usage

1. Launch the application: `python3 main.py`
2. Configure your i3 settings through the various tabs
3. Click "Apply" to save changes and reload i3
4. Use "Show changes before applying" to preview modifications

## Configuration

The application manages your i3 config at `~/.config/i3/config`. It automatically creates backups before making changes.

## Key Features

- **Conflict Detection**: Prevents duplicate keybindings
- **Backup System**: Automatic configuration backups
- **Live Reload**: Instantly apply changes to i3
- **System Integration**: Uses system icons and themes

## Development

### Project Structure

```
├── main.py                 # Application entry point
├── modules/
│   ├── main_window.py      # Main application window
│   ├── appearance_tab.py   # Appearance settings
│   ├── keybinds_tab.py     # Keybinding management
│   ├── startup_apps_tab.py # Startup applications
│   ├── history_tab.py      # Configuration history
│   └── ...
├── icons/                  # Custom icons
├── config.default          # Default i3 config template
└── appicon.png            # Application icon
```

### Building from Source

The application is written in Python with PyQt6. No compilation is required - just ensure all dependencies are installed.

### Building Optimized Binary

For distribution or performance, you can build a standalone optimized binary:

```bash
# Install build dependencies (Arch Linux)
sudo pacman -S python-pyinstaller upx  # UPX is optional for compression

# Run the build script
./build.py
```

This creates:

- `dist/i3-settings-manager` - Standalone executable binary
- `i3wm Settings.tar.gz` - Complete distribution package with:
  - Binary executable
  - Custom icons
  - Desktop integration file (.desktop)
  - Default configuration
  - Documentation

The binary includes all Python dependencies and is optimized for size and performance.

### Installing the Binary

```bash
# Extract the archive
tar -xzf "i3wm Settings.tar.gz"

# Install system-wide (optional)
sudo cp i3-settings-manager /usr/local/bin/
sudo cp -r icons /usr/share/icons/i3-settings-manager
sudo cp i3-settings-manager.desktop /usr/share/applications/

# Or run directly
./i3-settings-manager
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE.md) file for details.

## Author

**Raj Kashyap**

- GitHub: [@Raj-Kashyap001](https://github.com/Raj-Kashyap001)

## Acknowledgments

- Built with PyQt6
- Designed for i3 window manager
- Inspired by the need for better i3 configuration management
