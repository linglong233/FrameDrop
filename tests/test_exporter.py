import os
import shutil
import cv2
import pytest
from core.exporter import VideoExporter
from core.extractor import FrameExtractor

ffmpeg_available = shutil.which("ffmpeg") is not None
skip_no_ffmpeg = pytest.mark.skipif(
    not ffmpeg_available, reason="FFmpeg not installed"
)


@pytest.fixture
def extracted_frames(test_video, tmp_path):
    ext = FrameExtractor(test_video)
    output_dir = str(tmp_path / "frames")
    paths = ext.extract(interval=2, output_dir=output_dir)
    ext.close()
    return output_dir, paths


class TestExportMP4:
    @skip_no_ffmpeg
    def test_creates_mp4_file(self, extracted_frames, tmp_path):
        frames_dir, _ = extracted_frames
        output = str(tmp_path / "output.mp4")
        exporter = VideoExporter()
        result = exporter.export_mp4(frames_dir, output, fps=8)
        assert os.path.exists(result)
        assert os.path.getsize(result) > 0

    @skip_no_ffmpeg
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
    @skip_no_ffmpeg
    def test_creates_gif_file(self, extracted_frames, tmp_path):
        frames_dir, _ = extracted_frames
        output = str(tmp_path / "output.gif")
        exporter = VideoExporter()
        result = exporter.export_gif(frames_dir, output, fps=8)
        assert os.path.exists(result)
        assert os.path.getsize(result) > 0


class TestFFmpegCheck:
    @skip_no_ffmpeg
    def test_is_available(self):
        exporter = VideoExporter()
        assert exporter.is_available() is True
