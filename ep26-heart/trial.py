"""心音の試聴版。使い方: python3 trial.py <出力.mp3> [秒数=120] [seed=26] [高さ=1.0]"""
import subprocess, sys
import numpy as np
import synth_heart
from synth_heart import SR, schedule, calibrate, eq_fir, body_ir, render_block

out = sys.argv[1]
dur = float(sys.argv[2]) if len(sys.argv) > 2 else 120
seed = int(sys.argv[3]) if len(sys.argv) > 3 else 26
synth_heart.SHIFT = float(sys.argv[4]) if len(sys.argv) > 4 else 1.0
fir = eq_fir(calibrate())
x = render_block(0.0, dur, seed, schedule(dur + 3, seed), fir, body_ir(np.random.default_rng(3)))
x /= np.abs(x).max()
fade = int(3 * SR)
x[:fade] *= np.linspace(0, 1, fade)[:, None]
x[-fade:] *= np.linspace(1, 0, fade)[:, None]
pcm = (x * 0.7 * 32767).astype("<i2").tobytes()
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "s16le", "-ar", str(SR), "-ac", "2", "-i", "-",
                "-af", "loudnorm=I=-28:TP=-3:LRA=7", "-ar", "44100", "-c:a", "libmp3lame", "-b:a", "192k", out], input=pcm, check=True)
print("wrote", out)
