import subprocess
import sys
from pathlib import Path

import imageio_ffmpeg


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: convert-demo-video.py <input.webm> <output.mp4>", file=sys.stderr)
        return 1

    input_path = Path(sys.argv[1]).resolve()
    output_path = Path(sys.argv[2]).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    command = [
        ffmpeg_exe,
        "-y",
        "-i",
        str(input_path),
        "-vf",
        "scale=1600:900:flags=lanczos,format=yuv420p",
        "-c:v",
        "libx264",
        "-preset",
        "medium",
        "-crf",
        "22",
        "-movflags",
        "+faststart",
        "-an",
        str(output_path),
    ]

    completed = subprocess.run(command, capture_output=True, text=True)
    if completed.returncode != 0:
      print(completed.stderr, file=sys.stderr)
      return completed.returncode

    print(output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
