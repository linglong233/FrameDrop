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
        with pytest.raises((ValueError, FileNotFoundError)):
            FrameExtractor("nonexistent.mp4")
