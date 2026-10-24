"""時計＋窓の外の小雨の試聴版。
使い方: python3 trial_mix.py <出力.mp3> <テンプレート名> [雨の大きさdB=-4] [秒数=120] [速さ=テンプレートの間隔] [時計を下げるdB=0] [soft=0|1]
雨の大きさは、時計（ふつうの版）の RMS に対する雨の RMS の差。時計を下げるときは雨の大きさ（絶対値）は変えず、
全体の音量も「ふつうの版を -24LUFS にしたときと同じ倍率」で書き出す（時計だけが小さくなる）。
"""
import re, subprocess, sys
import numpy as np
from synth_clock import SR, schedule, reverb_ir, render_block
import rain

out, tpl = sys.argv[1], sys.argv[2]
rdb = float(sys.argv[3]) if len(sys.argv) > 3 else -4.0
dur = float(sys.argv[4]) if len(sys.argv) > 4 else 120
speed = sys.argv[5] if len(sys.argv) > 5 else tpl
cdb = float(sys.argv[6]) if len(sys.argv) > 6 else 0.0
soft = len(sys.argv) > 7 and sys.argv[7] == "1"
ts, kinds = schedule(dur + 5, speed, 18)
ir = reverb_ir()
base = {"seed": 18, "speed": speed, "tpl": tpl, "wet": 0.0}
c0 = render_block(0.0, dur, base, ts, kinds, ir)
r = rain.render_block(0.0, dur, 18, rain.drop_schedule(dur + 5, 18))
r *= np.sqrt(np.mean(c0 ** 2)) / np.sqrt(np.mean(r ** 2)) * 10 ** (rdb / 20)
if soft or cdb:
    c = render_block(0.0, dur, dict(base, soft=soft, wet=0.12 if soft else 0.0), ts, kinds, ir)
    c *= np.sqrt(np.mean(c0 ** 2)) / np.sqrt(np.mean(c ** 2)) * 10 ** (cdb / 20)
else:
    c = c0


def lufs(x):
    e = subprocess.run(["ffmpeg", "-f", "f32le", "-ar", str(SR), "-ac", "2", "-i", "-", "-af", "ebur128", "-f", "null", "-"],
                       input=x.astype("<f4").tobytes(), capture_output=True).stderr.decode()
    return float(re.findall(r"I:\s+(-?[\d.]+) LUFS", e)[-1])


g = 10 ** ((-24 - lufs(c0 + r)) / 20)  # ふつうの版を -24LUFS にする倍率
x = (c + r) * g
fade = int(4 * SR)
x[:fade] *= np.linspace(0, 1, fade)[:, None]
x[-fade:] *= np.linspace(1, 0, fade)[:, None]
print(f"全体 {lufs(x):.1f}LUFS  ピーク {20 * np.log10(np.abs(x).max()):.1f}dBFS")
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "f32le", "-ar", str(SR), "-ac", "2", "-i", "-",
                "-af", "alimiter=limit=0.7:level=false", "-c:a", "libmp3lame", "-b:a", "192k", out], input=x.astype("<f4").tobytes(), check=True)
print("wrote", out)
