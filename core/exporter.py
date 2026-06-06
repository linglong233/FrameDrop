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
