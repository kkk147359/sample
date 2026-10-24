"""ブラウンノイズの聞き比べ用の試聴版（3種類、同じ音量 -23LUFS）を書き出す。
使い方: python3 trial.py <出力フォルダ> [秒数=90]
どれがどれかは社長がブラインドで聞き比べるため、ファイル名は 1・2・3 にして対応は BLIND_KEY.md に書く。
"""
import os, re, subprocess, sys
import numpy as np
from synth_noise import SR, BLOCK, design, render_block

VARIANTS = {  # ファイル番号: (傾き dB/oct, 左右の相関)
    "1": (-4.5, 0.0),
    "2": (-6.0, 0.0),
    "3": (-4.5, 0.6),
}
outdir = sys.argv[1]
dur = float(sys.argv[2]) if len(sys.argv) > 2 else 90
for name, (slope, corr) in VARIANTS.items():
    h = design(slope)
    cfg = {"seed": 2000 + int(name), "corr": corr}
    n = int(dur * SR)
    x = np.concatenate([render_block(i, cfg, h) for i in range(n // BLOCK + 1)])[:n]
    fade = int(3 * SR)
    x[:fade] *= np.linspace(0, 1, fade)[:, None]
    x[-fade:] *= np.linspace(1, 0, fade)[:, None]
    x *= 0.1
    wav = os.path.join(outdir, f"_tmp{name}.f32")
    x.astype("<f4").tofile(wav)
    r = subprocess.run(["ffmpeg", "-f", "f32le", "-ar", str(SR), "-ac", "2", "-i", wav, "-af", "ebur128", "-f", "null", "-"], capture_output=True, text=True).stderr
    lufs = float(re.findall(r"I:\s+(-?[\d.]+) LUFS", r)[-1])
    gain = -23 - lufs
    out = os.path.join(outdir, f"brown_trial_{name}.mp3")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "f32le", "-ar", str(SR), "-ac", "2", "-i", wav, "-af", f"volume={gain:.2f}dB",
                    "-c:a", "libmp3lame", "-b:a", "192k", out], check=True)
    os.remove(wav)
    print(out, f"slope {slope} corr {corr} gain {gain:.1f}dB")
