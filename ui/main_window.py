import os
import shutil
import sys

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QButtonGroup,
    QDoubleSpinBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QRadioButton,
    QSlider,
    QSpinBox,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from core.extractor import FrameExtractor
from core.exporter import VideoExporter
from ui.preview_widget import PreviewWidget

_CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), "temp")


class ExtractionWorker(QThread):
    finished = Signal(list)
    error = Signal(str)

    def __init__(self, video_path: str, video_fps: float,
                 interval_seconds: float, output_dir: str):
        super().__init__()
        self.video_path = video_path
        self.interval = max(1, round(video_fps * interval_seconds))
        self.output_dir = output_dir

    def run(self):
        try:
            ext = FrameExtractor(self.video_path)
            paths = ext.extract(self.interval, self.output_dir)
            ext.close()
            self.finished.emit(paths)
        except Exception as e:
            self.error.emit(str(e))


class ExportWorker(QThread):
    finished = Signal(str)
    error = Signal(str)

    def __init__(self, frames_dir: str, output_path: str, fps: int, fmt: str):
        super().__init__()
        self.frames_dir = frames_dir
        self.output_path = output_path
        self.fps = fps
        self.fmt = fmt

    def run(self):
        try:
            exporter = VideoExporter()
            if self.fmt == "mp4":
                exporter.export_mp4(self.frames_dir, self.output_path, self.fps)
            else:
                exporter.export_gif(self.frames_dir, self.output_path, self.fps)
            self.finished.emit(self.output_path)
        except Exception as e:
            self.error.emit(str(e))


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("FrameDrop - 定格动画工具")
        self.setMinimumSize(900, 600)
        self.setAcceptDrops(True)

        self._video_path: str | None = None
        self._video_info = None
        self._frame_paths: list[str] = []
        self._cache_dir = _CACHE_DIR
        self._extract_seq = 0
        self._current_extract_dir: str | None = None
        self._extraction_worker: ExtractionWorker | None = None
        self._export_worker: ExportWorker | None = None

        # Clean stale cache from previous sessions
        if os.path.exists(self._cache_dir):
            shutil.rmtree(self._cache_dir, ignore_errors=True)

        self._setup_ui()

    def _setup_ui(self):
        self.setStyleSheet("""
            QMainWindow { background-color: #2b2b3d; }
            QLabel { color: #ddd; }
            QPushButton {
                background-color: #3d5af1; color: white;
                border: none; border-radius: 6px;
                padding: 8px 16px; font-size: 14px;
            }
            QPushButton:hover { background-color: #2a4ad1; }
            QPushButton:disabled { background-color: #555; }
            QSlider::groove:horizontal {
                height: 6px; background: #444; border-radius: 3px;
            }
            QSlider::handle:horizontal {
                width: 16px; height: 16px; margin: -5px 0;
                background: #3d5af1; border-radius: 8px;
            }
            QDoubleSpinBox {
                background-color: #3a3a52; color: #fff;
                border: 1px solid #555; border-radius: 6px;
                padding: 6px 10px; font-size: 15px;
                selection-background-color: #3d5af1;
            }
            QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {
                background-color: #4a4a6a; border: none; width: 28px;
            }
            QDoubleSpinBox::up-button:hover, QDoubleSpinBox::down-button:hover {
                background-color: #3d5af1;
            }
            QDoubleSpinBox::up-arrow {
                image: none; border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-bottom: 6px solid #ccc; width: 0; height: 0;
            }
            QDoubleSpinBox::down-arrow {
                image: none; border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 6px solid #ccc; width: 0; height: 0;
            }
            QSpinBox {
                background-color: #3a3a52; color: #fff;
                border: 1px solid #555; border-radius: 6px;
                padding: 6px 10px; font-size: 15px;
                selection-background-color: #3d5af1;
            }
            QSpinBox::up-button, QSpinBox::down-button {
                background-color: #4a4a6a; border: none; width: 20px;
            }
            QSpinBox::up-button:hover, QSpinBox::down-button:hover {
                background-color: #3d5af1;
            }
            QSpinBox::up-arrow {
                image: none; border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-bottom: 5px solid #ccc; width: 0; height: 0;
            }
            QSpinBox::down-arrow {
                image: none; border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 5px solid #ccc; width: 0; height: 0;
            }
            QProgressBar {
                border: none; border-radius: 3px;
                background: #444; text-align: center; color: white;
            }
            QProgressBar::chunk {
                background: #3d5af1; border-radius: 3px;
            }
        """)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)

        # Left: preview
        self.preview = PreviewWidget()
        layout.addWidget(self.preview, stretch=7)

        # Right: controls
        controls = QVBoxLayout()
        controls.setSpacing(12)
        layout.addLayout(controls, stretch=3)

        # Import
        self.btn_import = QPushButton("📂 选择视频")
        self.btn_import.clicked.connect(self._import_video)
        controls.addWidget(self.btn_import)

        self.lbl_filename = QLabel("未选择文件")
        self.lbl_filename.setWordWrap(True)
        controls.addWidget(self.lbl_filename)

        controls.addSpacing(16)

        # Extraction interval
        controls.addWidget(QLabel("抽取间隔 (每隔多少秒抽1帧):"))
        interval_row = QHBoxLayout()
        self.slider_interval = QSlider(Qt.Horizontal)
        self.slider_interval.setRange(1, 3000)
        self.slider_interval.setValue(2)
        self.slider_interval.valueChanged.connect(self._on_slider_interval_changed)
        interval_row.addWidget(self.slider_interval, stretch=3)

        self.spin_extract_interval = QDoubleSpinBox()
        self.spin_extract_interval.setRange(0.1, 300.0)
        self.spin_extract_interval.setValue(0.2)
        self.spin_extract_interval.setSingleStep(0.1)
        self.spin_extract_interval.setDecimals(1)
        self.spin_extract_interval.setFixedWidth(110)
        self.spin_extract_interval.valueChanged.connect(self._on_spin_interval_changed)
        interval_row.addWidget(self.spin_extract_interval)
        interval_row.addWidget(QLabel("秒"))
        controls.addLayout(interval_row)

        controls.addSpacing(8)

        # FPS
        controls.addWidget(QLabel("目标帧率:"))
        fps_row = QHBoxLayout()
        self.slider_fps = QSlider(Qt.Horizontal)
        self.slider_fps.setRange(1, 30)
        self.slider_fps.setValue(4)
        self.slider_fps.valueChanged.connect(self._on_slider_fps_changed)
        fps_row.addWidget(self.slider_fps, stretch=3)

        self.spin_fps = QSpinBox()
        self.spin_fps.setRange(1, 30)
        self.spin_fps.setValue(4)
        self.spin_fps.setFixedWidth(70)
        self.spin_fps.valueChanged.connect(self._on_spin_fps_changed)
        fps_row.addWidget(self.spin_fps)
        fps_row.addWidget(QLabel("FPS"))
        controls.addLayout(fps_row)

        controls.addSpacing(16)

        # Format
        controls.addWidget(QLabel("导出格式:"))
        fmt_layout = QHBoxLayout()
        self.radio_mp4 = QRadioButton("MP4")
        self.radio_gif = QRadioButton("GIF")
        self.radio_mp4.setChecked(True)
        fmt_group = QButtonGroup(self)
        fmt_group.addButton(self.radio_mp4)
        fmt_group.addButton(self.radio_gif)
        fmt_layout.addWidget(self.radio_mp4)
        fmt_layout.addWidget(self.radio_gif)
        controls.addLayout(fmt_layout)

        controls.addSpacing(8)

        # Export
        self.btn_export = QPushButton("▶ 导出")
        self.btn_export.setEnabled(False)
        self.btn_export.clicked.connect(self._export)
        controls.addWidget(self.btn_export)

        self.progress = QProgressBar()
        self.progress.setVisible(False)
        controls.addWidget(self.progress)

        controls.addStretch()

        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("就绪")

    def _clear_all_cache(self):
        self.preview.stop()
        if os.path.exists(self._cache_dir):
            shutil.rmtree(self._cache_dir, ignore_errors=True)
        self._extract_seq = 0
        self._current_extract_dir = None
        self._frame_paths = []

    # --- Drag & Drop ---

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            url = event.mimeData().urls()[0].toLocalFile()
            if url.lower().endswith((".mp4", ".avi", ".mov", ".mkv")):
                event.acceptProposedAction()

    def dropEvent(self, event):
        path = event.mimeData().urls()[0].toLocalFile()
        if not self._try_open_video(path):
            return
        self._clear_all_cache()
        self._video_path = path
        self.lbl_filename.setText(os.path.basename(path))
        self._extract_frames()

    # --- Import ---

    def _import_video(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "选择视频", "",
            "视频文件 (*.mp4 *.avi *.mov *.mkv);;所有文件 (*)",
        )
        if not path:
            return
        if not self._try_open_video(path):
            return
        self._clear_all_cache()
        self._video_path = path
        self.lbl_filename.setText(os.path.basename(path))
        self._extract_frames()

    def _try_open_video(self, path: str) -> bool:
        try:
            ext = FrameExtractor(path)
            self._video_info = ext.get_info()
            ext.close()
            return True
        except Exception as e:
            QMessageBox.critical(self, "错误", f"无法打开视频:\n{e}")
            return False

    # --- Extraction ---

    def _next_extract_dir(self) -> str:
        self._extract_seq += 1
        path = os.path.join(self._cache_dir, str(self._extract_seq))
        os.makedirs(path, exist_ok=True)
        return path

    def _extract_frames(self):
        if not self._video_path:
            return
        self.preview.stop()
        self._current_extract_dir = self._next_extract_dir()
        self.btn_import.setEnabled(False)
        self.btn_export.setEnabled(False)
        self.progress.setRange(0, 0)
        self.progress.setVisible(True)
        self.status_bar.showMessage("正在抽帧...")

        self._extraction_worker = ExtractionWorker(
            self._video_path,
            self._video_info.fps,
            self.spin_extract_interval.value(),
            self._current_extract_dir,
        )
        self._extraction_worker.finished.connect(self._on_extraction_done)
        self._extraction_worker.error.connect(self._on_extraction_error)
        self._extraction_worker.start()

    def _on_extraction_done(self, paths: list[str]):
        self._frame_paths = paths
        self.progress.setVisible(False)
        self.btn_import.setEnabled(True)
        self.btn_export.setEnabled(True)
        self.status_bar.showMessage(
            f"原始: {self._video_info.fps:.0f}FPS "
            f"{self._video_info.width}x{self._video_info.height} | "
            f"抽帧后: {len(paths)} 帧",
        )
        self.preview.set_frames(paths, self.slider_fps.value())

    def _on_extraction_error(self, msg: str):
        self.progress.setVisible(False)
        self.btn_import.setEnabled(True)
        QMessageBox.critical(self, "错误", f"抽帧失败:\n{msg}")

    # --- Slider callbacks ---

    def _on_slider_interval_changed(self, value: int):
        val = value / 10.0
        self.spin_extract_interval.blockSignals(True)
        self.spin_extract_interval.setValue(val)
        self.spin_extract_interval.blockSignals(False)
        if self._video_path and self._video_info:
            self._extract_frames()

    def _on_spin_interval_changed(self, value: float):
        self.slider_interval.blockSignals(True)
        self.slider_interval.setValue(int(value * 10))
        self.slider_interval.blockSignals(False)
        if self._video_path and self._video_info:
            self._extract_frames()

    def _on_slider_fps_changed(self, value: int):
        self.spin_fps.blockSignals(True)
        self.spin_fps.setValue(value)
        self.spin_fps.blockSignals(False)
        self.preview.update_fps(value)

    def _on_spin_fps_changed(self, value: int):
        self.slider_fps.blockSignals(True)
        self.slider_fps.setValue(value)
        self.slider_fps.blockSignals(False)
        self.preview.update_fps(value)

    # --- Export ---

    def _export(self):
        if not self._frame_paths:
            return
        fmt = "mp4" if self.radio_mp4.isChecked() else "gif"
        ext_filter = "MP4 (*.mp4)" if fmt == "mp4" else "GIF (*.gif)"
        path, _ = QFileDialog.getSaveFileName(
            self, "导出", f"output.{fmt}", f"{ext_filter};;所有文件 (*)",
        )
        if not path:
            return
        if os.path.exists(path):
            reply = QMessageBox.question(
                self, "确认覆盖",
                f"文件已存在:\n{path}\n是否覆盖？",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
            )
            if reply != QMessageBox.Yes:
                return

        self.btn_export.setEnabled(False)
        self.progress.setRange(0, 0)
        self.progress.setVisible(True)
        self.status_bar.showMessage("正在导出...")

        self._export_worker = ExportWorker(
            self._current_extract_dir, path, self.slider_fps.value(), fmt,
        )
        self._export_worker.finished.connect(self._on_export_done)
        self._export_worker.error.connect(self._on_export_error)
        self._export_worker.start()

    def _on_export_done(self, path: str):
        self.progress.setVisible(False)
        self.btn_export.setEnabled(True)
        self.status_bar.showMessage(f"导出完成: {path}")
        QMessageBox.information(self, "完成", f"导出成功!\n{path}")

    def _on_export_error(self, msg: str):
        self.progress.setVisible(False)
        self.btn_export.setEnabled(True)
        QMessageBox.critical(self, "错误", f"导出失败:\n{msg}")

    # --- Cleanup ---

    def closeEvent(self, event):
        if self._extraction_worker and self._extraction_worker.isRunning():
            self._extraction_worker.terminate()
            self._extraction_worker.wait()
        if self._export_worker and self._export_worker.isRunning():
            self._export_worker.terminate()
            self._export_worker.wait()
        super().closeEvent(event)

    def cleanup(self):
        import shutil
        try:
            shutil.rmtree(self._cache_dir, ignore_errors=True)
        except OSError:
            pass
