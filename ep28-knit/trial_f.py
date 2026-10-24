"""試聴版F。使い方: python3 trial_f.py <出力.mp3> [秒数=120] [seed=6] [こすれdB=-10（-99でなし）]"""
import subprocess, sys
import numpy as np
import synth_knit_f
from synth_knit_f import SR, render

out = sys.argv[1]
dur = float(sys.argv[2]) if len(sys.argv) > 2 else 120
seed = int(sys.argv[3]) if len(sys.argv) > 3 else 6
synth_knit_f.SLIDE_DB = float(sys.argv[4]) if len(sys.argv) > 4 else -10.0
ev = [e for e in synth_knit_f.schedule(dur + 3, seed) if e[1] == "click" or synth_knit_f.SLIDE_DB > -90]
x = render(0.0, dur, ev, seed)
x /= np.abs(x).max()
fade = int(3 * SR)
x[:fade] *= np.linspace(0, 1, fade)[:, None]
x[-fade:] *= np.linspace(1, 0, fade)[:, None]
pcm = (x * 0.7 * 32767).astype("<i2").tobytes()
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "s16le", "-ar", str(SR), "-ac", "2", "-i", "-",
                "-af", "loudnorm=I=-28:TP=-3:LRA=7", "-ar", "44100", "-c:a", "libmp3lame", "-b:a", "192k", out], input=pcm, check=True)
print("wrote", out)
