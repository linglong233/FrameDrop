import sys
import shutil
import os

from PySide6.QtGui import QPixmap, QIcon
from PySide6.QtWidgets import QApplication, QMessageBox

from ui.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("FrameDrop")
    app.setStyleSheet("""
        QMessageBox { background-color: #2b2b3d; }
        QMessageBox QLabel { color: #ddd; }
        QPushButton { background-color: #3d5af1; color: white;
            border: none; border-radius: 6px; padding: 6px 16px; min-width: 80px; }
        QPushButton:hover { background-color: #2a4ad1; }
    """)

    icon_path = os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), "logo.png")
    if os.path.exists(icon_path):
        icon = QIcon(icon_path)
        app.setWindowIcon(icon)

    if sys.platform == "win32":
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("FrameDrop")

    if not shutil.which("ffmpeg"):
        QMessageBox.critical(
            None, "缺少依赖",
            "未检测到 FFmpeg。\n"
            "请安装 FFmpeg 并添加到系统 PATH。\n"
            "下载地址: https://ffmpeg.org/download.html",
        )
        sys.exit(1)

    window = MainWindow()
    window.show()

    exit_code = app.exec()
    window.cleanup()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
