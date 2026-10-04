"""時計＋窓の外の小雨の試聴版。使い方: python3 trial_mix.py <出力.mp3> <テンプレート名> [雨の大きさdB=-4] [秒数=120] [速さ=テンプレートの間隔]
雨の大きさは、時計（打音）の RMS に対する雨の RMS の差。
"""
import subprocess, sys
import numpy as np
from synth_clock import SR, schedule, reverb_ir, render_block
import rain

out, tpl = sys.argv[1], sys.argv[2]
rdb = float(sys.argv[3]) if len(sys.argv) > 3 else -4.0
dur = float(sys.argv[4]) if len(sys.argv) > 4 else 120
speed = sys.argv[5] if len(sys.argv) > 5 else tpl
cfg = {"seed": 18, "speed": speed, "tpl": tpl, "wet": 0.0}
ts, kinds = schedule(dur + 5, speed, cfg["seed"])
c = render_block(0.0, dur, cfg, ts, kinds, reverb_ir())
r = rain.render_block(0.0, dur, 18, rain.drop_schedule(dur + 5, 18))
r *= np.sqrt(np.mean(c ** 2)) / np.sqrt(np.mean(r ** 2)) * 10 ** (rdb / 20)
x = c + r
x /= np.abs(x).max()
fade = int(4 * SR)
x[:fade] *= np.linspace(0, 1, fade)[:, None]
x[-fade:] *= np.linspace(1, 0, fade)[:, None]
pcm = (x * 0.5 * 32767).astype("<i2").tobytes()
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "s16le", "-ar", str(SR), "-ac", "2", "-i", "-",
                "-af", "loudnorm=I=-24:TP=-3:LRA=7", "-ar", "44100", "-c:a", "libmp3lame", "-b:a", "192k", out], input=pcm, check=True)
print("wrote", out)
