import sys
import shutil

from PySide6.QtWidgets import QApplication, QMessageBox

from ui.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("FrameDrop")

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
