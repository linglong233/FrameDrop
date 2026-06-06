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
        self.cap = None
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
