"""試聴版。使い方: python3 trial.py <出力.mp3> [秒数=150] [seed=1] [下地dB]
全体を一定の倍率で LUFS 目標にそろえる（loudnorm の自動調整は使わない：間の静けさを持ち上げないため）。"""
import subprocess, sys
import numpy as np
import synth_birds
from synth_birds import SR, render, schedule, BIRDS

LUFS = -28.0
out = sys.argv[1]
dur = float(sys.argv[2]) if len(sys.argv) > 2 else 150
seed = int(sys.argv[3]) if len(sys.argv) > 3 else 1
if len(sys.argv) > 4:
    synth_birds.BED_DB = float(sys.argv[4])
ev = schedule(dur + 3, seed)
ev = [e for e in ev if e[0] < dur - 2]
print(f"声 {len(ev)}（{len(ev) / dur * 60:.0f}/分）", {BIRDS[b][0]: sum(1 for e in ev if e[1] == b) for b in range(len(BIRDS))})
x = render(0.0, dur, ev, seed)
def lufs(y):
    r = subprocess.run(["ffmpeg", "-hide_banner", "-f", "f32le", "-ar", str(SR), "-ac", "2", "-i", "-", "-af", "ebur128", "-f", "null", "-"],
                       input=y.astype("<f4").tobytes(), capture_output=True).stderr.decode()
    return float(r.rsplit("I:", 1)[1].split("LUFS")[0])
x *= 10 ** ((LUFS - lufs(x)) / 20)
fade = int(3 * SR)
x[:fade] *= np.linspace(0, 1, fade)[:, None]
x[-fade:] *= np.linspace(1, 0, fade)[:, None]
print("ピーク %.1f dBFS" % (20 * np.log10(np.abs(x).max())))
pcm = (np.clip(x, -1, 1) * 32767).astype("<i2").tobytes()
args = ["ffmpeg", "-y", "-loglevel", "error", "-f", "s16le", "-ar", str(SR), "-ac", "2", "-i", "-"]
args += ["-c:a", "libmp3lame", "-b:a", "192k", out] if out.endswith(".mp3") else [out]
subprocess.run(args, input=pcm, check=True)
print("wrote", out)
