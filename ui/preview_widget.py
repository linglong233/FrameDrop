import cv2
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)


def _format_time(seconds: float) -> str:
    s = max(0, int(seconds))
    m, s = divmod(s, 60)
    if m > 0:
        return f"{m}:{s:02d}"
    return f"{s}"


class PreviewWidget(QWidget):
    frame_changed = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMinimumSize(480, 360)

        self._pixmaps: list[QPixmap] = []
        self._current_idx = 0
        self._fps: int = 4
        self._playing = False
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._advance)

        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Frame display
        self._image_label = QLabel()
        self._image_label.setAlignment(Qt.AlignCenter)
        self._image_label.setStyleSheet(
            "QLabel { background-color: #1a1a2e; color: #888; "
            "font-size: 16px; border: 2px dashed #444; border-radius: 8px; }"
        )
        self._image_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._image_label.setText("拖拽或点击导入视频")
        layout.addWidget(self._image_label, stretch=1)

        # Control bar
        bar = QWidget()
        bar.setStyleSheet("background-color: #22223a;")
        bar_layout = QHBoxLayout(bar)
        bar_layout.setContentsMargins(8, 4, 8, 4)

        self._btn_play = QPushButton("⏸")
        self._btn_play.setFixedWidth(32)
        self._btn_play.setFixedHeight(28)
        self._btn_play.setStyleSheet(
            "QPushButton { background-color: #3d5af1; color: white; "
            "border: none; border-radius: 4px; font-size: 14px; }"
            "QPushButton:hover { background-color: #2a4ad1; }"
        )
        self._btn_play.clicked.connect(self._toggle_play)
        bar_layout.addWidget(self._btn_play)

        self._slider = QSlider(Qt.Horizontal)
        self._slider.setRange(0, 0)
        self._slider.setStyleSheet(
            "QSlider::groove:horizontal { height: 6px; background: #444; "
            "border-radius: 3px; }"
            "QSlider::handle:horizontal { width: 14px; height: 14px; "
            "margin: -4px 0; background: #3d5af1; border-radius: 7px; }"
        )
        self._slider.sliderPressed.connect(self._on_slider_pressed)
        self._slider.sliderReleased.connect(self._on_slider_released)
        self._slider.valueChanged.connect(self._on_slider_moved)
        self._dragging = False
        bar_layout.addWidget(self._slider, stretch=1)

        self._lbl_time = QLabel("0/0")
        self._lbl_time.setStyleSheet("color: #aaa; font-size: 13px;")
        self._lbl_time.setFixedWidth(100)
        self._lbl_time.setAlignment(Qt.AlignCenter)
        bar_layout.addWidget(self._lbl_time)

        layout.addWidget(bar)

    # --- Public API ---

    def set_frames(self, frame_paths: list[str], fps: int = 4):
        self.stop()
        self._fps = fps
        self._pixmaps = []
        for path in frame_paths:
            img = cv2.imread(path)
            if img is not None:
                img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                h, w, ch = img.shape
                qimg = QImage(img.data, w, h, ch * w, QImage.Format_RGB888)
                self._pixmaps.append(QPixmap.fromImage(qimg.copy()))

        total = len(self._pixmaps)
        self._slider.setRange(0, max(total - 1, 0))
        self._current_idx = 0
        self._update_time_label()

        if self._pixmaps:
            self._display_frame(0)
            self._playing = True
            self._btn_play.setText("⏸")
            self._timer.start(int(1000 / self._fps))

    def update_fps(self, fps: int):
        self._fps = fps
        self._update_time_label()
        if self._playing and self._pixmaps:
            self._timer.setInterval(int(1000 / self._fps))

    def stop(self):
        self._timer.stop()
        self._pixmaps = []
        self._current_idx = 0
        self._playing = False
        self._dragging = False
        self._slider.setRange(0, 0)
        self._lbl_time.setText("0/0")
        self._image_label.clear()
        self._image_label.setText("拖拽或点击导入视频")
        self._btn_play.setText("▶")

    # --- Playback ---

    def _advance(self):
        if not self._pixmaps:
            return
        self._current_idx = (self._current_idx + 1) % len(self._pixmaps)
        self._slider.blockSignals(True)
        self._slider.setValue(self._current_idx)
        self._slider.blockSignals(False)
        self._display_frame(self._current_idx)
        self._update_time_label()
        self.frame_changed.emit(self._current_idx)

    def _display_frame(self, idx):
        pixmap = self._pixmaps[idx].scaled(
            self._image_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation,
        )
        self._image_label.setPixmap(pixmap)

    def _toggle_play(self):
        if not self._pixmaps:
            return
        self._playing = not self._playing
        if self._playing:
            self._btn_play.setText("⏸")
            self._timer.start(int(1000 / self._fps))
        else:
            self._btn_play.setText("▶")
            self._timer.stop()

    # --- Slider ---

    def _on_slider_pressed(self):
        self._dragging = True
        if self._playing:
            self._timer.stop()

    def _on_slider_released(self):
        self._dragging = False
        if self._playing:
            self._timer.start(int(1000 / self._fps))

    def _on_slider_moved(self, value: int):
        if not self._pixmaps:
            return
        self._current_idx = value
        self._display_frame(value)
        self._update_time_label()

    def _update_time_label(self):
        total = len(self._pixmaps)
        if total == 0 or self._fps == 0:
            self._lbl_time.setText("0/0")
            return
        cur = _format_time(self._current_idx / self._fps)
        dur = _format_time(total / self._fps)
        self._lbl_time.setText(f"{cur} / {dur}")

    # --- Resize ---

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._pixmaps:
            self._display_frame(self._current_idx)
