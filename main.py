"""
i3 Settings GUI - A settings manager for i3wm
"""

import sys
from PyQt6.QtWidgets import QApplication

from modules.main_window import MainWindow

def main():
    import signal
    import threading

    sigint_received = threading.Event()

    def signal_handler(signum, frame):
        sigint_received.set()

    # Set up signal handler
    signal.signal(signal.SIGINT, signal_handler)

    app = QApplication(sys.argv)

    # Try to use system native style
    try:
        # For Qt 6.3+, this will use the system theme
        from PyQt6.QtCore import Qt
        app.setStyle('Fusion')  # Fallback to Fusion if system style not available
    except:
        pass

    from PyQt6.QtCore import QTimer

    def check_signals():
        if sigint_received.is_set():
            app.quit()

    timer = QTimer()
    timer.timeout.connect(check_signals)
    timer.start(100)  # Check every 100ms

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == '__main__':
    main()
