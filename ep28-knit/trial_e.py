"""試聴版E。使い方: python3 trial_e.py <出力.mp3> [秒数=120] [seed=5] [下地dB=-10]"""
import subprocess, sys
import numpy as np
import synth_knit_e
from synth_knit_e import SR, schedule, render

out = sys.argv[1]
dur = float(sys.argv[2]) if len(sys.argv) > 2 else 120
seed = int(sys.argv[3]) if len(sys.argv) > 3 else 5
synth_knit_e.BED_DB = float(sys.argv[4]) if len(sys.argv) > 4 else -10.0
x = render(0.0, dur, schedule(dur + 3, seed), seed)
x /= np.abs(x).max()
fade = int(3 * SR)
x[:fade] *= np.linspace(0, 1, fade)[:, None]
x[-fade:] *= np.linspace(1, 0, fade)[:, None]
pcm = (x * 0.7 * 32767).astype("<i2").tobytes()
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "s16le", "-ar", str(SR), "-ac", "2", "-i", "-",
                "-af", "loudnorm=I=-28:TP=-3:LRA=7", "-ar", "44100", "-c:a", "libmp3lame", "-b:a", "192k", out], input=pcm, check=True)
print("wrote", out)
