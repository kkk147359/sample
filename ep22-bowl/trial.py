"""シンギングボウルの試聴版を書き出す。使い方: python3 trial.py <出力.mp3> [秒数=120]"""
import subprocess, sys
import numpy as np
from synth_bowl import SR, schedule, reverb_ir, render_block

out = sys.argv[1]
dur = float(sys.argv[2]) if len(sys.argv) > 2 else 120
cfg = {"seed": 22}
ev = schedule(dur + 5, cfg["seed"])
x = render_block(0.0, dur, cfg, ev, reverb_ir())
x /= np.abs(x).max()
fade = int(4 * SR)
x[-fade:] *= np.linspace(1, 0, fade)[:, None]
pcm = (x * 0.5 * 32767).astype("<i2").tobytes()
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "s16le", "-ar", str(SR), "-ac", "2", "-i", "-",
                "-af", "loudnorm=I=-24:TP=-3:LRA=7", "-ar", "44100", "-c:a", "libmp3lame", "-b:a", "192k", out], input=pcm, check=True)
print("wrote", out)
