#!/usr/bin/env python3
"""
Build script for i3 Settings Manager
Creates an optimized standalone binary using PyInstaller

Usage:
    python3 build.py                    # Build only
    python3 build.py --install          # Build and install system-wide
    python3 build.py --remove           # Remove system installation
    python3 build.py --clean            # Remove then reinstall
"""

import os
import sys
import subprocess
import shutil
import argparse
from pathlib import Path

def run_command(cmd, desc=""):
    """Run a command and handle errors"""
    print(f"{'Running' if not desc else desc}: {' '.join(cmd) if isinstance(cmd, list) else cmd}")
    try:
        result = subprocess.run(cmd, shell=isinstance(cmd, str), check=True, capture_output=True, text=True)
        return result
    except subprocess.CalledProcessError as e:
        print(f"Error: {e}")
        print(f"STDOUT: {e.stdout}")
        print(f"STDERR: {e.stderr}")
        sys.exit(1)

def check_dependencies():
    """Check if required build dependencies are installed"""
    print("Checking build dependencies...")

    # Check if PyInstaller is installed
    try:
        import PyInstaller
        print("✓ PyInstaller is installed")
    except ImportError:
        print("✗ PyInstaller not found")
        exit(1)

    # Check for UPX (optional, for compression)
    upx_available = shutil.which("upx") is not None
    if upx_available:
        print("✓ UPX found (compression enabled)")
    else:
        print("⚠ UPX not found (compression disabled)")

    return upx_available

def clean_build_artifacts():
    """Clean previous build artifacts"""
    print("Cleaning previous build artifacts...")

    dirs_to_clean = ["build", "dist", "__pycache__"]
    for dir_name in dirs_to_clean:
        if os.path.exists(dir_name):
            shutil.rmtree(dir_name)
            print(f"✓ Removed {dir_name}/")

    # Clean __pycache__ in subdirectories
    for root, dirs, files in os.walk("."):
        if "__pycache__" in dirs:
            pycache_path = os.path.join(root, "__pycache__")
            shutil.rmtree(pycache_path)
            print(f"✓ Removed {pycache_path}/")

def create_spec_file():
    """Create a custom PyInstaller spec file for optimization"""
    spec_content = '''# -*- mode: python ; coding: utf-8 -*-

import os
from pathlib import Path

# Get the project root directory
project_root = os.path.abspath(SPEC)

a = Analysis(
    ['main.py'],
    pathex=[project_root],
    binaries=[],
    datas=[
        ('icons', '.'),
        ('config.default', '.'),
        ('appicon.png', '.'),
        ('i3wm-logo.png', '.'),
    ],
    hiddenimports=[
        'PyQt6.QtCore',
        'PyQt6.QtGui',
        'PyQt6.QtWidgets',
        'PyQt6.QtPrintSupport',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'unittest',
        'pdb',
        'pydoc',
        'doctest',
        'test',
        'sqlite3',
        'ssl',
        'bz2',
        'lzma',
        'xml',
        'xmlrpc',
        'email',
        'html',
        'http',
        'urllib',
        'ftplib',
        'poplib',
        'imaplib',
        'smtplib',
        'smtpd',
        'telnetlib',
        'socketserver',
        'http.server',
        'xmlrpc.server',
        'wsgiref',
        'webbrowser',
        'cgi',
        'cgitb',
        'xdrlib',
        'plistlib',
        'mailcap',
        'mailbox',
        'mhlib',
        'mimify',
        'multifile',
        'rfc822',
        'formatter',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='i3-settings-manager',
    debug=False,
    bootloader_ignore_signals=False,
    strip=True,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='appicon.png',
)
'''

    with open('i3-settings-manager.spec', 'w') as f:
        f.write(spec_content)

    print("✓ Created custom spec file for optimization")

def build_binary(upx_available):
    """Build the optimized binary"""
    print("Building optimized binary...")

    # Use the custom spec file for maximum optimization
    cmd = [
        'pyinstaller',
        '--clean',
        '--noconfirm',
        'i3-settings-manager.spec'
    ]

    run_command(cmd, "Building with PyInstaller")

    # Check if binary was created
    binary_path = Path("dist/i3-settings-manager")
    if binary_path.exists():
        size = binary_path.stat().st_size / (1024 * 1024)  # Size in MB
        print(f"✓ Binary created successfully ({size:.2f} MB)")
    else:
        print("✗ Binary not found after build")
        sys.exit(1)

def strip_binary():
    """Strip the binary to reduce size further"""
    binary_path = "dist/i3-settings-manager"

    if os.path.exists(binary_path):
        print("Stripping binary...")
        run_command(["strip", "--strip-all", binary_path], "Stripping binary")
        size = os.path.getsize(binary_path) / (1024 * 1024)
        print(f"✓ Binary stripped ({size:.2f} MB)")
def create_desktop_file():
    """Create a .desktop file for the application"""
    print("Creating .desktop file...")

    desktop_content = """[Desktop Entry]
Version=1.0
Type=Application
Name=i3 Settings Manager
Comment=GUI for managing i3 window manager configuration
Exec=env QT_QPA_PLATFORM=xcb i3-settings-manager
Icon=i3-settings-manager
Terminal=false
Categories=Settings;System;
Keywords=i3;wm;window;manager;settings;configuration;
"""

    with open("i3-settings-manager.desktop", "w") as f:
        f.write(desktop_content)

    print("✓ Created i3-settings-manager.desktop")

def install_system_wide():
    """Install the application system-wide"""
    print("Installing system-wide...")

    # Check if binary exists
    if not os.path.exists("dist/i3-settings-manager"):
        print("✗ Binary not found. Run build first.")
        sys.exit(1)

    try:
        # Install binary
        run_command(["sudo", "cp", "dist/i3-settings-manager", "/usr/local/bin/"], "Installing binary")

        # Install icons (only if appicon.png exists)
        if os.path.exists("appicon.png"):
            # Install in multiple standard sizes for better compatibility
            for size in ["16x16", "24x24", "32x32", "48x48", "64x64", "128x128"]:
                run_command(["sudo", "mkdir", "-p", f"/usr/share/icons/hicolor/{size}/apps"], f"Creating {size} icons directory")
                run_command(["sudo", "cp", "appicon.png", f"/usr/share/icons/hicolor/{size}/apps/i3-settings-manager.png"], f"Installing {size} desktop icon")
            print("✓ Desktop icons installed in multiple sizes")
        else:
            print("⚠ appicon.png not found, skipping desktop icon installation")

        # Install custom icons (SVG icons for application use)
        if os.path.exists("icons") and os.listdir("icons"):
            run_command(["sudo", "mkdir", "-p", "/usr/share/icons/i3-settings-manager"], "Creating custom icons directory")
            run_command(["sudo", "cp", "-r", "icons/", "/usr/share/icons/i3-settings-manager/"], "Installing custom icons")
            print("✓ Custom icons installed")
        else:
            print("⚠ Icons directory not found or empty, skipping custom icon installation")

        # Install desktop file (only if it exists)
        if os.path.exists("i3-settings-manager.desktop"):
            run_command(["sudo", "cp", "i3-settings-manager.desktop", "/usr/share/applications/"], "Installing desktop file")
            # Update desktop database
            run_command(["sudo", "update-desktop-database", "/usr/share/applications/"], "Updating desktop database")
            # Update icon cache
            run_command(["sudo", "gtk-update-icon-cache", "-f", "/usr/share/icons/hicolor"], "Updating icon cache")
            print("✓ Desktop integration installed")
        else:
            print("⚠ Desktop file not found, skipping desktop integration")

        print("✓ Installation completed successfully!")
        print("  - Binary: /usr/local/bin/i3-settings-manager")
        if os.path.exists("icons"):
            print("  - Icons: /usr/share/icons/i3-settings-manager/")
        if os.path.exists("i3-settings-manager.desktop"):
            print("  - Desktop: /usr/share/applications/i3-settings-manager.desktop")

    except subprocess.CalledProcessError:
        print("✗ Installation failed")
        sys.exit(1)

def remove_system_installation():
    """Remove the system-wide installation"""
    print("Removing system installation...")

    try:
        # Remove binary
        if os.path.exists("/usr/local/bin/i3-settings-manager"):
            run_command(["sudo", "rm", "/usr/local/bin/i3-settings-manager"], "Removing binary")

        # Remove desktop icons (all sizes)
        for size in ["16x16", "24x24", "32x32", "48x48", "64x64", "128x128"]:
            icon_path = f"/usr/share/icons/hicolor/{size}/apps/i3-settings-manager.png"
            if os.path.exists(icon_path):
                run_command(["sudo", "rm", icon_path], f"Removing {size} desktop icon")

        # Remove custom icons
        if os.path.exists("/usr/share/icons/i3-settings-manager"):
            run_command(["sudo", "rm", "-rf", "/usr/share/icons/i3-settings-manager"], "Removing custom icons")

        # Remove desktop file
        if os.path.exists("/usr/share/applications/i3-settings-manager.desktop"):
            run_command(["sudo", "rm", "/usr/share/applications/i3-settings-manager.desktop"], "Removing desktop file")

        # Update desktop database
        run_command(["sudo", "update-desktop-database", "/usr/share/applications/"], "Updating desktop database")

        print("✓ Removal completed successfully!")

    except subprocess.CalledProcessError:
        print("✗ Removal failed")
        sys.exit(1)

def create_archive():
    """Create a compressed archive of the build"""
    print("Creating distribution archive...")

    # Create desktop file first
    create_desktop_file()

    archive_name = "i3wm Settings"
    archive_path = f"{archive_name}.tar.gz"

    # Create archive - copy binary to current dir temporarily for easier archiving
    import shutil
    shutil.copy("dist/i3-settings-manager", ".")

    try:
        run_command([
            "tar", "-czf", archive_path,
            "i3-settings-manager",
            "icons",
            "config.default",
            "README.md",
            "LICENSE.md",
            "i3-settings-manager.desktop"
        ], "Creating archive")
    finally:
        # Clean up the copied binary
        if os.path.exists("i3-settings-manager"):
            os.remove("i3-settings-manager")

    size = os.path.getsize(archive_path) / (1024 * 1024)
    print(f"✓ Archive created ({size:.2f} MB)")
def main():
    """Main build process"""
    parser = argparse.ArgumentParser(
        description="Build script for i3 Settings Manager",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 build.py                    # Build only
  python3 build.py --install          # Build and install system-wide
  python3 build.py --remove           # Remove system installation
  python3 build.py --clean            # Remove then reinstall
        """
    )

    parser.add_argument('--install', action='store_true',
                       help='Build and install system-wide')
    parser.add_argument('--remove', action='store_true',
                       help='Remove system installation')
    parser.add_argument('--clean', action='store_true',
                       help='Remove then reinstall system-wide')

    args = parser.parse_args()

    print("  i3 Settings Manager Build Script")
    print("=" * 40)

    # Handle removal/clean operations
    if args.remove or args.clean:
        remove_system_installation()
        if args.remove:
            return  # Exit after removal

    # Handle installation operations
    if args.install or args.clean:
        # Check if we're on Linux
        if not sys.platform.startswith('linux'):
            print("✗ This build script is designed for Linux systems")
            sys.exit(1)

        # Check dependencies
        upx_available = check_dependencies()

        # Clean previous builds
        clean_build_artifacts()

        # Create optimized spec file
        create_spec_file()

        # Build the binary
        build_binary(upx_available)

        # Strip the binary
        strip_binary()

        # Create desktop file
        create_desktop_file()

        # Install system-wide
        install_system_wide()

        return  # Exit after installation

    # Default: just build
    if not sys.platform.startswith('linux'):
        print("✗ This build script is designed for Linux systems")
        sys.exit(1)

    # Check dependencies
    upx_available = check_dependencies()

    # Clean previous builds
    clean_build_artifacts()

    # Create optimized spec file
    create_spec_file()

    # Build the binary
    build_binary(upx_available)

    # Strip the binary
    strip_binary()

    # Create distribution archive
    create_archive()

    print("\n✅ Build completed successfully!")
    print("\n Distribution files:")
    print("  - dist/i3-settings-manager (standalone binary)")
    print("  - i3wm Settings.tar.gz (complete package)")

    print("\n Installation instructions:")
    print("  1. Extract the tar.gz archive")
    print("  2. Make the binary executable: chmod +x i3-settings-manager")
    print("  3. Copy binary to /usr/local/bin/: sudo cp i3-settings-manager /usr/local/bin/")
    print("  4. Copy icon to /usr/share/icons/: sudo cp -r icons /usr/share/icons/i3-settings-manager")
    print("  5. Install desktop file: sudo cp i3-settings-manager.desktop /usr/share/applications/")
    print("  6. Run from menu or: i3-settings-manager")

    print("\n System requirements for the binary:")
    print("  - i3 window manager")
    print("  - feh, matugen, xrdb, dunst/notify-send")
    print("  - X11 display server")

if __name__ == "__main__":
    main()