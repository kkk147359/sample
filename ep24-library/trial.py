"""図書館の試聴版を書き出す。使い方: python3 trial.py <出力.mp3> [秒数=90] [シード=24]"""
import subprocess, sys
import numpy as np
from synth_pages import SR, render

out = sys.argv[1]
dur = float(sys.argv[2]) if len(sys.argv) > 2 else 90
seed = int(sys.argv[3]) if len(sys.argv) > 3 else 24
x = render(dur, seed)
x /= np.abs(x).max()
fade = int(2 * SR)
x[:fade] *= np.linspace(0, 1, fade)[:, None]
x[-fade:] *= np.linspace(1, 0, fade)[:, None]
pcm = (x * 0.5 * 32767).astype("<i2").tobytes()
# 音量は -24LUFS にそろえる（2回測って一定の倍率をかける。動的な圧縮はしない）
r = subprocess.run(["ffmpeg", "-hide_banner", "-f", "s16le", "-ar", str(SR), "-ac", "2", "-i", "-", "-af", "ebur128", "-f", "null", "-"],
                   input=pcm, capture_output=True, text=False).stderr.decode()
lufs = float([l for l in r.splitlines() if "I:" in l][-1].split()[1])
gain = -24 - lufs
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "s16le", "-ar", str(SR), "-ac", "2", "-i", "-",
                "-af", f"volume={gain:.2f}dB,alimiter=limit=0.89:attack=5:release=50:level=false", "-ar", "44100",
                "-c:a", "libmp3lame", "-b:a", "192k", out], input=pcm, check=True)
print("wrote", out)
