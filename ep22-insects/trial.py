"""虫の声の試聴版。使い方: python3 trial.py <出力.mp3> [秒数=120] [シード=22]"""
import subprocess, sys
import numpy as np
from synth_insects import SR, make_voices, events, render_block, reverb_ir

out = sys.argv[1]
dur = float(sys.argv[2]) if len(sys.argv) > 2 else 120
seed = int(sys.argv[3]) if len(sys.argv) > 3 else 22
v = make_voices(seed)
evs = [events(x, dur + 5) for x in v]
x = render_block(0.0, dur, seed, v, evs, reverb_ir())
x /= np.abs(x).max()
fade = int(4 * SR)
x[:fade] *= np.linspace(0, 1, fade)[:, None]
x[-fade:] *= np.linspace(1, 0, fade)[:, None]
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "f32le", "-ar", str(SR), "-ac", "2", "-i", "-",
                "-af", "loudnorm=I=-24:TP=-3:LRA=7", "-ar", "44100", "-c:a", "libmp3lame", "-b:a", "192k", out],
               input=(x * 0.5).astype("<f4").tobytes(), check=True)
print("wrote", out)
