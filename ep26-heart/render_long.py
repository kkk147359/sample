"""心音（社長OKの試聴版B：高さ1.4倍）の長い版の書き出し。2分ずつ計算（4コア並列）。
使い方: python3 render_long.py <出力(.mp3|.m4a)> <秒数> <シード>　（1時間版 3600 26、8時間版 28800 27）
音量は -28LUFS を目標に一定の倍率をかけ、ピークは alimiter（-3dBFS）で抑える。
拍の合間の小さな音も含めて同じ倍率をかける。
"""
import re
import subprocess
import sys
from multiprocessing import Pool

import numpy as np

import synth_heart
from synth_heart import SR, body_ir, calibrate, eq_fir, render_block, schedule

synth_heart.SHIFT = 1.4  # 10/10 社長が試聴版B（少しだけ高い）を選択

BLK = 120.0
FADE = 3.0
TARGET = -28.0
G = {}


def _init(total, seed):
    G["fir"] = eq_fir(calibrate())
    G["ir"] = body_ir(np.random.default_rng(3))
    G["sch"] = schedule(total + 3, seed)
    G["total"], G["seed"] = total, seed


def _job(k):
    total = G["total"]
    t0 = k * BLK
    dur = min(BLK, total - t0)
    x = render_block(t0, dur, G["seed"], G["sch"], G["fir"], G["ir"])
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
