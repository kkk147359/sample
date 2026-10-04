"""冒頭15秒の映像＋黒15秒のくり返し＋音 を1本の mp4 にする（映像は再エンコードしない）。
使い方: python3 assemble.py <intro.mp4> <音声.m4a> <秒数> <出力.mp4>
黒の15秒クリップは冒頭映像と同じ設定（H.264, yuv420p, 12fps, GOP 24）で作る。
"""
import os
import subprocess
import sys
import tempfile

intro, audio, total, out = sys.argv[1], sys.argv[2], float(sys.argv[3]), sys.argv[4]
tmp = tempfile.mkdtemp()
black = os.path.join(tmp, "black15.mp4")
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", "color=c=black:s=1920x1080:r=12", "-t", "15",
                "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", "12", "-g", "24", "-crf", "18", black], check=True)
n = int(round((total - 15) / 15))
lst = os.path.join(tmp, "list.txt")
with open(lst, "w") as f:
    f.write(f"file '{os.path.abspath(intro)}'\n" + f"file '{black}'\n" * n)
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst, "-i", audio,
                "-map", "0:v", "-map", "1:a", "-c", "copy", "-shortest", "-movflags", "+faststart", out], check=True)
r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration,size", "-of", "csv=p=0", out], capture_output=True, text=True)
print("wrote", out, r.stdout.strip())
