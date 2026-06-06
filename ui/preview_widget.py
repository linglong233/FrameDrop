import cv2
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import QLabel, QSizePolicy


class PreviewWidget(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignCenter)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMinimumSize(480, 360)
        self.setText("拖拽或点击导入视频")
        self.setStyleSheet(
            "QLabel { background-color: #1a1a2e; color: #888; "
            "font-size: 16px; border: 2px dashed #444; border-radius: 8px; }"
        )
        self._pixmaps: list[QPixmap] = []
        self._current_idx = 0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._show_next_frame)

    def set_frames(self, frame_paths: list[str], fps: int = 8):
        self.stop()
        self._pixmaps = []
        for path in frame_paths:
            img = cv2.imread(path)
            if img is not None:
                img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                h, w, ch = img.shape
                qimg = QImage(img.data, w, h, ch * w, QImage.Format_RGB888)
                self._pixmaps.append(QPixmap.fromImage(qimg.copy()))
        self._current_idx = 0
        if self._pixmaps:
            self._display_frame(0)
            self._timer.start(int(1000 / fps))

    def update_fps(self, fps: int):
        if self._pixmaps:
            self._timer.setInterval(int(1000 / fps))

    def _show_next_frame(self):
        if not self._pixmaps:
            return
        self._current_idx = (self._current_idx + 1) % len(self._pixmaps)
        self._display_frame(self._current_idx)

    def _display_frame(self, idx):
        pixmap = self._pixmaps[idx].scaled(
            self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation,
        )
        self.setPixmap(pixmap)

    def stop(self):
        self._timer.stop()
        self._pixmaps = []
        self._current_idx = 0
        self.clear()
        self.setText("拖拽或点击导入视频")

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._pixmaps:
            self._display_frame(self._current_idx)
