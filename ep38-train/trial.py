"""夜行列車の試聴版。使い方: python3 trial.py <出力.mp3> [秒数=30] [seed=38] [継ぎ目dB=-2]"""
import subprocess, sys
import numpy as np
from synth_train import SR, render

out = sys.argv[1]
dur = float(sys.argv[2]) if len(sys.argv) > 2 else 30
seed = int(sys.argv[3]) if len(sys.argv) > 3 else 38
cdb = float(sys.argv[4]) if len(sys.argv) > 4 else -2.0
x = render(dur + 1, seed, cdb)[: int(dur * SR)]
x /= np.abs(x).max()
fade = int(3 * SR)
x[:fade] *= np.linspace(0, 1, fade)[:, None]
x[-fade:] *= np.linspace(1, 0, fade)[:, None]
pcm = (x * 0.7 * 32767).astype("<i2").tobytes()
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "s16le", "-ar", str(SR), "-ac", "2", "-i", "-",
                "-af", "loudnorm=I=-24:TP=-3:LRA=7", "-ar", "44100", "-c:a", "libmp3lame", "-b:a", "192k", out], input=pcm, check=True)
print("wrote", out)
