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
