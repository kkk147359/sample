"""柱時計の短い試聴版を書き出す。使い方: python3 trial.py <出力.mp3> <A|B|テンプレート名> [秒数=90]"""
import subprocess, sys
import numpy as np
from synth_clock import SR, schedule, reverb_ir, render_block

out, speed = sys.argv[1], sys.argv[2]
dur = float(sys.argv[3]) if len(sys.argv) > 3 else 90
cfg = {"seed": 18, "speed": speed, "tpl": speed if speed not in ("A", "B") else "371070", "wet": 0.0 if speed not in ("A", "B") else 0.30}
ts, kinds = schedule(dur + 5, speed, cfg["seed"])
x = render_block(0.0, dur, cfg, ts, kinds, reverb_ir())
x /= np.abs(x).max()
fade = int(3 * SR)
x[:fade] *= np.linspace(0, 1, fade)[:, None]
x[-fade:] *= np.linspace(1, 0, fade)[:, None]
pcm = (x * 0.5 * 32767).astype("<i2").tobytes()
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "s16le", "-ar", str(SR), "-ac", "2", "-i", "-",
                "-af", "loudnorm=I=-24:TP=-3:LRA=7", "-ar", "44100", "-c:a", "libmp3lame", "-b:a", "192k", out], input=pcm, check=True)
print("wrote", out)
