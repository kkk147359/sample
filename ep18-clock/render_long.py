"""柱時計の長い版の書き出し。2分ずつ区切って計算し（4コアで並列）、ffmpeg で AAC（.m4a）にする。
使い方: python3 render_long.py <出力.m4a> <秒数> <シード> <A|B>
音量は最初の5分を測り、-24LUFS になるよう全体に同じ倍率をかけたうえで、試聴版と同じ
loudnorm（I=-24, TP=-3）を通す。打音のピークが -3dBFS を超えないようにするため。
"""
import re
import subprocess
import sys
from multiprocessing import Pool

import numpy as np

from synth_clock import SR, render_block, reverb_ir, schedule

BLK = 120.0
FADE = 3.0
TARGET = -24.0


def _job(args):
    k, total, cfg = args
    ts, kinds = schedule(total + 5, cfg["speed"], cfg["seed"])
    t0 = k * BLK
    dur = min(BLK, total - t0)
    x = render_block(t0, dur, cfg, ts, kinds, reverb_ir())
    # 最初と最後のフェード
    t = t0 + np.arange(len(x)) / SR
    g = np.clip(t / FADE, 0, 1) * np.clip((total - t) / FADE, 0, 1)
    return (x * g[:, None]).astype(np.float32)


def lufs(x):
    r = subprocess.run(["ffmpeg", "-f", "f32le", "-ar", str(SR), "-ac", "2", "-i", "-", "-af", "ebur128", "-f", "null", "-"],
                       input=x.astype("<f4").tobytes(), capture_output=True).stderr.decode()
    return float(re.findall(r"I:\s+(-?[\d.]+) LUFS", r)[-1])


if __name__ == "__main__":
    out, total, seed, speed = sys.argv[1], float(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
    cfg = {"seed": seed, "speed": speed}
    nblk = int(np.ceil(total / BLK))
    with Pool(4) as pool:
        head = np.concatenate(pool.map(_job, [(k, total, cfg) for k in range(min(3, nblk))]))
        gain = 10 ** ((TARGET - lufs(head[int(10 * SR):])) / 20)
        peak = np.abs(head).max() * gain
        print(f"gain {20 * np.log10(gain):.1f}dB  先頭のピーク {20 * np.log10(peak):.1f}dBFS", flush=True)
        ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "f32le", "-ar", str(SR), "-ac", "2", "-i", "-",
                               "-af", "loudnorm=I=-24:TP=-3:LRA=7", "-ar", str(SR), "-c:a", "aac", "-b:a", "128k", out], stdin=subprocess.PIPE)
        maxpk = 0
        for k, x in enumerate(pool.imap(_job, [(k, total, cfg) for k in range(nblk)])):
            x = x * gain
            maxpk = max(maxpk, np.abs(x).max())
            ff.stdin.write(x.astype("<f4").tobytes())
            if k % 10 == 0:
                print(f"  {k + 1}/{nblk}", flush=True)
        ff.stdin.close()
        ff.wait()
    print(f"wrote {out}  loudnorm前の最大ピーク {20 * np.log10(maxpk):.1f}dBFS")
