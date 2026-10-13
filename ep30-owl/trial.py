"""試聴版。使い方: python3 trial.py <出力.mp3> [秒数=150] [seed=1] [下地dB=-16]
音量は一定の倍率で、声の強いところ（10msごとの最大）を -12dBFS にそろえる（loudnorm は使わない：間の静けさを持ち上げないため）。"""
import subprocess, sys
import numpy as np
import synth_owl
from synth_owl import SR, render, schedule

out = sys.argv[1]
dur = float(sys.argv[2]) if len(sys.argv) > 2 else 150
seed = int(sys.argv[3]) if len(sys.argv) > 3 else 1
if len(sys.argv) > 4:
    synth_owl.BED_DB = float(sys.argv[4])
ev = schedule(dur + 3, seed)
print("鳴く時刻:", ", ".join(f"{t:.0f}s {k}{'(遠)' if w else ''}" for t, k, w, _ in ev if t < dur))
x = render(0.0, dur, ev, seed)
h = 441
e = np.sqrt((x[: len(x) // h * h, 0].reshape(-1, h) ** 2).mean(1))
x *= 10 ** (-12 / 20) / (np.sqrt(2) * e.max())
fade = int(3 * SR)
x[:fade] *= np.linspace(0, 1, fade)[:, None]
x[-fade:] *= np.linspace(1, 0, fade)[:, None]
print("ピーク %.1f dBFS" % (20 * np.log10(np.abs(x).max())))
pcm = (np.clip(x, -1, 1) * 32767).astype("<i2").tobytes()
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "s16le", "-ar", str(SR), "-ac", "2", "-i", "-",
                "-c:a", "libmp3lame", "-b:a", "192k", out], input=pcm, check=True)
print("wrote", out)
