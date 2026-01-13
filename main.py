"""
i3 Settings GUI - A settings manager for i3wm
"""

import sys
from PyQt6.QtWidgets import QApplication

from modules.main_window import MainWindow

def main():
    import signal
    import threading

    # Flag to indicate if SIGINT was received
    sigint_received = threading.Event()

    def signal_handler(signum, frame):
        sigint_received.set()

    # Set up signal handler
    signal.signal(signal.SIGINT, signal_handler)

    app = QApplication(sys.argv)

    # Set application style - avoid invalid styles
    try:
        app.setStyle('Fusion')
    except:
        pass  # Use default style if Fusion is not available

    # Set up timer to check for Ctrl+C
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
