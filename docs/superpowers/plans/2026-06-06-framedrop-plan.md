# FrameDrop Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Python desktop app that converts videos into stop-motion animations by extracting frames at configurable intervals.

**Architecture:** Single-window PySide6 app with left-side video preview and right-side control panel. Core processing is split into FrameExtractor (OpenCV) and VideoExporter (FFmpeg). Background QThread workers handle extraction/export to keep UI responsive.

**Tech Stack:** Python 3.9+, PySide6, OpenCV, FFmpeg, pytest

---

## File Structure

| File | Responsibility |
|------|----------------|
| `main.py` | Application entry point, FFmpeg startup check |
| `requirements.txt` | Dependencies |
| `core/__init__.py` | Package init |
| `core/extractor.py` | Video metadata reading and frame extraction via OpenCV |
| `core/exporter.py` | FFmpeg-based MP4/GIF export |
| `ui/__init__.py` | Package init |
| `ui/preview_widget.py` | Animated frame preview using QTimer + QPixmap |
| `ui/main_window.py` | Main window layout, controls, QThread workers, orchestration |
| `tests/__init__.py` | Package init |
| `tests/conftest.py` | Shared test fixtures (synthetic video) |
| `tests/test_extractor.py` | FrameExtractor unit tests |
| `tests/test_exporter.py` | VideoExporter unit tests |

---

### Task 1: Project Scaffolding

**Files:**
- Create: `requirements.txt`
- Create: `core/__init__.py`
- Create: `ui/__init__.py`
- Create: `tests/__init__.py`
- Create: `tests/conftest.py`

- [ ] **Step 1: Create directory structure and requirements.txt**

`requirements.txt`:
```
PySide6>=6.5
opencv-python>=4.8
pytest>=7.0
```

- [ ] **Step 2: Create __init__.py files**

Create empty `core/__init__.py`, `ui/__init__.py`, `tests/__init__.py`.

- [ ] **Step 3: Create test fixture — synthetic video**

`tests/conftest.py`:
```python
import cv2
import numpy as np
import pytest


def _create_solid_frame(width, height, index):
    frame = np.zeros((height, width, 3), dtype=np.uint8)
    frame[:] = ((index * 4) % 256, 128, 200)
    cv2.putText(
        frame, str(index), (width // 2 - 20, height // 2 + 20),
        cv2.FONT_HERSHEY_SIMPLEX, 1.5, (255, 255, 255), 3,
    )
    return frame


@pytest.fixture
def test_video(tmp_path):
    video_path = str(tmp_path / "test_video.mp4")
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(video_path, fourcc, 30.0, (320, 240))
    for i in range(60):
        writer.write(_create_solid_frame(320, 240, i))
    writer.release()
    return video_path
```

- [ ] **Step 4: Install dependencies**

Run: `pip install -r requirements.txt`
Expected: All packages installed successfully.

- [ ] **Step 5: Commit**

```bash
git init
git add .
git commit -m "chore: project scaffolding with dependencies and test fixtures"
```

---

### Task 2: FrameExtractor — Core Module

**Files:**
- Create: `core/extractor.py`
- Create: `tests/test_extractor.py`

- [ ] **Step 1: Write failing tests for FrameExtractor**

`tests/test_extractor.py`:
```python
import os
import cv2
import pytest
from core.extractor import FrameExtractor, VideoInfo


class TestGetInfo:
    def test_returns_video_info(self, test_video):
        ext = FrameExtractor(test_video)
        info = ext.get_info()
        assert isinstance(info, VideoInfo)
        assert info.width == 320
        assert info.height == 240
        assert info.fps == pytest.approx(30.0, abs=1.0)
        assert info.frame_count == 60
        assert info.duration > 0
        ext.close()


class TestExtract:
    def test_extracts_at_interval(self, test_video, tmp_path):
        ext = FrameExtractor(test_video)
        output_dir = str(tmp_path / "frames")
        paths = ext.extract(interval=3, output_dir=output_dir)
        assert len(paths) == 20  # 60 / 3
        for p in paths:
            assert os.path.exists(p)
        ext.close()

    def test_extracted_frames_are_valid(self, test_video, tmp_path):
        ext = FrameExtractor(test_video)
        output_dir = str(tmp_path / "frames")
        paths = ext.extract(interval=2, output_dir=output_dir)
        for p in paths:
            img = cv2.imread(p)
            assert img is not None
            assert img.shape[:2] == (240, 320)
        ext.close()

    def test_interval_1_extracts_all(self, test_video, tmp_path):
        ext = FrameExtractor(test_video)
        output_dir = str(tmp_path / "frames")
        paths = ext.extract(interval=1, output_dir=output_dir)
        assert len(paths) == 60
        ext.close()


class TestInvalidInput:
    def test_raises_on_bad_path(self):
        with pytest.raises(ValueError, match="Cannot open video"):
            FrameExtractor("nonexistent.mp4")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_extractor.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'core.extractor'`

- [ ] **Step 3: Implement FrameExtractor**

`core/extractor.py`:
```python
import cv2
import os
from dataclasses import dataclass
from pathlib import Path


@dataclass
class VideoInfo:
    width: int
    height: int
    fps: float
    frame_count: int
    duration: float


class FrameExtractor:
    SUPPORTED_FORMATS = {".mp4", ".avi", ".mov", ".mkv"}

    def __init__(self, video_path: str):
        path = Path(video_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {video_path}")
        if path.suffix.lower() not in self.SUPPORTED_FORMATS:
            raise ValueError(f"Unsupported format: {path.suffix}")
        self.cap = cv2.VideoCapture(video_path)
        if not self.cap.isOpened():
            raise ValueError(f"Cannot open video: {video_path}")

    def get_info(self) -> VideoInfo:
        fps = self.cap.get(cv2.CAP_PROP_FPS)
        frame_count = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        duration = frame_count / fps if fps > 0 else 0
        return VideoInfo(
            width=width, height=height, fps=fps,
            frame_count=frame_count, duration=duration,
        )

    def extract(self, interval: int, output_dir: str) -> list[str]:
        os.makedirs(output_dir, exist_ok=True)
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
        paths = []
        frame_idx = 0
        while True:
            ret, frame = self.cap.read()
            if not ret:
                break
            if frame_idx % interval == 0:
                path = os.path.join(output_dir, f"frame_{len(paths):04d}.png")
                cv2.imwrite(path, frame)
                paths.append(path)
            frame_idx += 1
        return paths

    def close(self):
        if self.cap is not None:
            self.cap.release()
            self.cap = None

    def __del__(self):
        self.close()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_extractor.py -v`
Expected: All 5 tests PASS

- [ ] **Step 5: Commit**

```bash
git add core/extractor.py tests/test_extractor.py
git commit -m "feat: FrameExtractor with OpenCV frame extraction"
```

---

### Task 3: VideoExporter — Core Module

**Files:**
- Create: `core/exporter.py`
- Create: `tests/test_exporter.py`

- [ ] **Step 1: Write failing tests for VideoExporter**

`tests/test_exporter.py`:
```python
import os
import cv2
import pytest
from core.exporter import VideoExporter
from core.extractor import FrameExtractor


@pytest.fixture
def extracted_frames(test_video, tmp_path):
    ext = FrameExtractor(test_video)
    output_dir = str(tmp_path / "frames")
    paths = ext.extract(interval=2, output_dir=output_dir)
    ext.close()
    return output_dir, paths


class TestExportMP4:
    def test_creates_mp4_file(self, extracted_frames, tmp_path):
        frames_dir, _ = extracted_frames
        output = str(tmp_path / "output.mp4")
        exporter = VideoExporter()
        result = exporter.export_mp4(frames_dir, output, fps=8)
        assert os.path.exists(result)
        assert os.path.getsize(result) > 0

    def test_mp4_has_correct_frame_count(self, extracted_frames, tmp_path):
        frames_dir, _ = extracted_frames
        output = str(tmp_path / "output.mp4")
        exporter = VideoExporter()
        exporter.export_mp4(frames_dir, output, fps=8)
        cap = cv2.VideoCapture(output)
        count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        cap.release()
        assert count == 30  # 60 frames / interval 2


class TestExportGIF:
    def test_creates_gif_file(self, extracted_frames, tmp_path):
        frames_dir, _ = extracted_frames
        output = str(tmp_path / "output.gif")
        exporter = VideoExporter()
        result = exporter.export_gif(frames_dir, output, fps=8)
        assert os.path.exists(result)
        assert os.path.getsize(result) > 0


class TestFFmpegCheck:
    def test_is_available(self):
        exporter = VideoExporter()
        assert exporter.is_available() is True
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_exporter.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'core.exporter'`

- [ ] **Step 3: Implement VideoExporter**

`core/exporter.py`:
```python
import os
import shutil
import subprocess


class VideoExporter:
    def __init__(self, ffmpeg_path: str = "ffmpeg"):
        self.ffmpeg_path = ffmpeg_path

    def is_available(self) -> bool:
        return shutil.which(self.ffmpeg_path) is not None

    def export_mp4(self, frames_dir: str, output_path: str, fps: int,
                   frame_pattern: str = "frame_%04d.png") -> str:
        input_pattern = os.path.join(frames_dir, frame_pattern)
        cmd = [
            self.ffmpeg_path, "-y",
            "-r", str(fps),
            "-i", input_pattern,
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            output_path,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"FFmpeg MP4 export failed: {result.stderr}")
        return output_path

    def export_gif(self, frames_dir: str, output_path: str, fps: int,
                   frame_pattern: str = "frame_%04d.png") -> str:
        input_pattern = os.path.join(frames_dir, frame_pattern)
        cmd = [
            self.ffmpeg_path, "-y",
            "-r", str(fps),
            "-i", input_pattern,
            "-vf",
            f"fps={fps},split[s0][s1];[s0]palettegen[p];[s1][p]paletteuse",
            output_path,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"FFmpeg GIF export failed: {result.stderr}")
        return output_path
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_exporter.py -v`
Expected: All 4 tests PASS

- [ ] **Step 5: Commit**

```bash
git add core/exporter.py tests/test_exporter.py
git commit -m "feat: VideoExporter with FFmpeg MP4/GIF export"
```

---

### Task 4: PreviewWidget — UI Component

**Files:**
- Create: `ui/preview_widget.py`

- [ ] **Step 1: Implement PreviewWidget**

`ui/preview_widget.py`:
```python
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
```

- [ ] **Step 2: Manual smoke test**

Create a temporary `test_smoke.py` at project root:
```python
import sys
from PySide6.QtWidgets import QApplication
from ui.preview_widget import PreviewWidget

app = QApplication(sys.argv)
w = PreviewWidget()
w.show()
# Close window manually to exit
app.exec()
```

Run: `python test_smoke.py`
Expected: Window opens showing "拖拽或点击导入视频" with dark background.

- [ ] **Step 3: Remove temp test file, commit**

```bash
del test_smoke.py
git add ui/preview_widget.py
git commit -m "feat: PreviewWidget with animated frame playback"
```

---

### Task 5: MainWindow — Main Application Window

**Files:**
- Create: `ui/main_window.py`

- [ ] **Step 1: Implement MainWindow with QThread workers and full UI**

`ui/main_window.py`:
```python
import os
import tempfile

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QProgressBar,
    QPushButton,
    QRadioButton,
    QSlider,
    QStatusBar,
    QVBoxLayout,
    QWidget,
    QMessageBox,
    QButtonGroup,
)

from core.extractor import FrameExtractor
from core.exporter import VideoExporter
from ui.preview_widget import PreviewWidget


class ExtractionWorker(QThread):
    finished = Signal(list)
    error = Signal(str)

    def __init__(self, video_path: str, interval: int, output_dir: str):
        super().__init__()
        self.video_path = video_path
        self.interval = interval
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

    def __init__(self, frames_dir: str, output_path: str, fps: int,
                 fmt: str):
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
        self._cache_dir = tempfile.mkdtemp(prefix="framedrop_")
        self._extraction_worker: ExtractionWorker | None = None
        self._export_worker: ExportWorker | None = None

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

        # Interval
        controls.addWidget(QLabel("抽帧间隔:"))
        self.slider_interval = QSlider(Qt.Horizontal)
        self.slider_interval.setRange(1, 30)
        self.slider_interval.setValue(2)
        self.slider_interval.setTickPosition(QSlider.TicksBelow)
        self.slider_interval.setTickInterval(1)
        self.slider_interval.valueChanged.connect(self._on_interval_changed)
        controls.addWidget(self.slider_interval)

        self.lbl_interval = QLabel("每 2 帧取 1 帧")
        controls.addWidget(self.lbl_interval)

        controls.addSpacing(8)

        # FPS
        controls.addWidget(QLabel("目标帧率:"))
        self.slider_fps = QSlider(Qt.Horizontal)
        self.slider_fps.setRange(1, 30)
        self.slider_fps.setValue(8)
        self.slider_fps.setTickPosition(QSlider.TicksBelow)
        self.slider_fps.setTickInterval(1)
        self.slider_fps.valueChanged.connect(self._on_fps_changed)
        controls.addWidget(self.slider_fps)

        self.lbl_fps = QLabel("8 FPS")
        controls.addWidget(self.lbl_fps)

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

    def _clear_cache(self):
        for f in os.listdir(self._cache_dir):
            os.remove(os.path.join(self._cache_dir, f))

    def _extract_frames(self):
        if not self._video_path:
            return
        self._clear_cache()
        self.btn_import.setEnabled(False)
        self.btn_export.setEnabled(False)
        self.progress.setRange(0, 0)
        self.progress.setVisible(True)
        self.status_bar.showMessage("正在抽帧...")

        self._extraction_worker = ExtractionWorker(
            self._video_path,
            self.slider_interval.value(),
            self._cache_dir,
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

    def _on_interval_changed(self, value: int):
        self.lbl_interval.setText(f"每 {value} 帧取 1 帧")
        if self._video_path:
            self._extract_frames()

    def _on_fps_changed(self, value: int):
        self.lbl_fps.setText(f"{value} FPS")
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

        self.btn_export.setEnabled(False)
        self.progress.setRange(0, 0)
        self.progress.setVisible(True)
        self.status_bar.showMessage("正在导出...")

        self._export_worker = ExportWorker(
            self._cache_dir, path, self.slider_fps.value(), fmt,
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

    def cleanup(self):
        if os.path.exists(self._cache_dir):
            for f in os.listdir(self._cache_dir):
                os.remove(os.path.join(self._cache_dir, f))
            os.rmdir(self._cache_dir)
```

- [ ] **Step 2: Commit**

```bash
git add ui/main_window.py
git commit -m "feat: MainWindow with import, preview, export, drag-and-drop, dark theme"
```

---

### Task 6: Application Entry Point

**Files:**
- Create: `main.py`

- [ ] **Step 1: Implement main.py with FFmpeg startup check**

`main.py`:
```python
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
```

- [ ] **Step 2: Run all tests**

Run: `pytest tests/ -v`
Expected: All tests PASS

- [ ] **Step 3: Manual integration test**

Run: `python main.py`
Expected:
1. Window opens with dark theme, preview area on left, controls on right
2. Click "选择视频" → pick a video → frames extract, preview plays in loop
3. Adjust interval slider → re-extracts, preview updates
4. Adjust FPS slider → preview speed changes
5. Select GIF → export → file created and playable
6. Select MP4 → export → file created and playable
7. Drag a video onto the window → imports and extracts
8. Close app → temp files cleaned up

- [ ] **Step 4: Commit**

```bash
git add main.py
git commit -m "feat: application entry point with FFmpeg startup check"
```

---

### Task 7: Final Verification

**Files:**
- No new files

- [ ] **Step 1: Run all tests**

Run: `pytest tests/ -v`
Expected: All 9 tests PASS

- [ ] **Step 2: Full manual test**

Run: `python main.py` and verify the complete workflow:
- Import via button and drag-and-drop
- Preview plays correctly
- Both sliders work
- MP4 export works
- GIF export works
- Error dialog shows for invalid files

- [ ] **Step 3: Final commit (if any fixes were needed)**
