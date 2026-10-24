"""図書館 v2 の書き出し（試聴版・長い版とも同じ方法）。2分ずつ計算（4コア並列）。
使い方: python3 render_v2.py <出力(.mp3|.m4a)> <秒数> <シード>
音量は -24LUFS を目標に一定の倍率をかけ、ピークは alimiter（-3dBFS）で抑える。
部屋の空気は倍率をかけたあとに足す（音量の目標に関係なく、ごく小さいまま）。
"""
import re
import subprocess
import sys
from multiprocessing import Pool

import numpy as np

from synth_pages_v2 import SR, calibrate, eq_fir, plan, render_block, room_ir

BLK = 120.0
FADE = 3.0
TARGET = -24.0
G = {}


def _init(total, seed):
    G["fir"] = eq_fir(calibrate())
    G["ir"] = room_ir(np.random.default_rng(2400))
    G["times"] = plan(total, seed)
    G["total"], G["seed"] = total, seed


def _job(k):
    total = G["total"]
    t0 = k * BLK
    dur = min(BLK, total - t0)
    x = render_block(t0, dur, G["seed"], G["times"], G["fir"], G["ir"])
    t = t0 + np.arange(len(x)) / SR
    g = np.clip(t / FADE, 0, 1) * np.clip((total - t) / FADE, 0, 1)
    return (x * g[:, None]).astype(np.float32)


def lufs(x):
    r = subprocess.run(["ffmpeg", "-f", "f32le", "-ar", str(SR), "-ac", "2", "-i", "-", "-af", "ebur128", "-f", "null", "-"],
                       input=x.astype("<f4").tobytes(), capture_output=True).stderr.decode()
    return float(re.findall(r"I:\s+(-?[\d.]+) LUFS", r)[-1])


if __name__ == "__main__":
    out, total, seed = sys.argv[1], float(sys.argv[2]), int(sys.argv[3])
    nblk = int(np.ceil(total / BLK))
    codec = ["-c:a", "libmp3lame", "-b:a", "192k"] if out.endswith(".mp3") else ["-c:a", "aac", "-b:a", "128k"]
    with Pool(4, initializer=_init, initargs=(total, seed)) as pool:
        head = np.concatenate(pool.map(_job, range(min(3, nblk))))
        gain = 10 ** ((TARGET - lufs(head)) / 20)
        print(f"gain {20 * np.log10(gain):.1f}dB", flush=True)
        ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "f32le", "-ar", str(SR), "-ac", "2", "-i", "-",
                               "-af", "alimiter=limit=0.71:attack=5:release=50:level=false", "-ar", str(SR)] + codec + [out],
                              stdin=subprocess.PIPE)
        maxpk = 0
        for k0 in range(0, nblk, 8):
            for x in pool.map(_job, range(k0, min(nblk, k0 + 8))):
                x = x * gain
                maxpk = max(maxpk, np.abs(x).max())
                ff.stdin.write(x.astype("<f4").tobytes())
            print(f"  {min(k0 + 8, nblk)}/{nblk}", flush=True)
        ff.stdin.close()
        ff.wait()
    print(f"wrote {out}  リミッター前の最大ピーク {20 * np.log10(maxpk):.1f}dBFS")
