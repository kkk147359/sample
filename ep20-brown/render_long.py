"""ブラウンノイズの長い版の書き出し。ブロックごとに計算して重ね合わせ、ffmpeg で AAC（.m4a）にする。
使い方: python3 render_long.py <出力.m4a> <秒数> <シード> <傾き dB/oct> [左右の相関=0]
音量は試聴版と同じ -23LUFS（最初の5分で決め、全体に同じ倍率）。ノイズは一定なので先頭で決めた倍率で最後まで同じ音量になる。
"""
import re
import subprocess
import sys

import numpy as np

from synth_noise import BLOCK, SR, design, render_block

TARGET = -23.0
FADE = 3.0


def lufs(x):
    r = subprocess.run(["ffmpeg", "-f", "f32le", "-ar", str(SR), "-ac", "2", "-i", "-", "-af", "ebur128", "-f", "null", "-"],
                       input=x.astype("<f4").tobytes(), capture_output=True).stderr.decode()
    return float(re.findall(r"I:\s+(-?[\d.]+) LUFS", r)[-1])


if __name__ == "__main__":
    out, total, seed, slope = sys.argv[1], float(sys.argv[2]), int(sys.argv[3]), float(sys.argv[4])
    corr = float(sys.argv[5]) if len(sys.argv) > 5 else 0.0
    cfg = {"seed": seed, "corr": corr}
    h = design(slope)
    n = int(total * SR)
    nblk = n // BLOCK + 1
    head = np.concatenate([render_block(i, cfg, h) for i in range(int(300 * SR) // BLOCK)])
    gain = 10 ** ((TARGET - lufs(head[int(5 * SR):])) / 20)
    print(f"gain {20 * np.log10(gain):.1f}dB", flush=True)
    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "f32le", "-ar", str(SR), "-ac", "2", "-i", "-",
                           "-c:a", "aac", "-b:a", "128k", out], stdin=subprocess.PIPE)
    maxpk = 0
    for i in range(nblk):
        x = render_block(i, cfg, h) * gain
        s = i * BLOCK
        if s >= n:
            break
        x = x[: n - s]
        t = (s + np.arange(len(x))) / SR
        x *= (np.clip(t / FADE, 0, 1) * np.clip((total - t) / FADE, 0, 1))[:, None]
        maxpk = max(maxpk, np.abs(x).max())
        ff.stdin.write(np.clip(x, -1, 1).astype("<f4").tobytes())
    ff.stdin.close()
    ff.wait()
    print(f"wrote {out}  最大ピーク {20 * np.log10(maxpk):.1f}dBFS")
