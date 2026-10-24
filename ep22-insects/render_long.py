"""虫の声の長い版の書き出し。2分ずつ区切って計算し（4コアで並列）、ffmpeg で AAC（.m4a）にする。
使い方: python3 render_long.py <出力.m4a> <秒数> <シード>
音は社長OKの試聴版v2（2種類・各3匹）と同じ設定。虫の顔ぶれ（高さ・距離・左右）はシードで決まる。
音量は最初の5分を測って -24LUFS になる倍率を全体にかけ、loudnorm（I=-24, TP=-3）を通す。
"""
import re
import subprocess
import sys
from multiprocessing import Pool

import numpy as np

from synth_insects import SR, events, make_voices, render_block, reverb_ir

BLK = 120.0
FADE = 3.0
TARGET = -24.0


def _job(args):
    k, total, seed = args
    v = make_voices(seed)
    evs = [events(x, total + 5) for x in v]
    t0 = k * BLK
    dur = min(BLK, total - t0)
    x = render_block(t0, dur, seed, v, evs, reverb_ir())
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
    jobs = [(k, total, seed) for k in range(nblk)]
    with Pool(4) as pool:
        head = np.concatenate(pool.map(_job, jobs[: min(3, nblk)]))
        gain = 10 ** ((TARGET - lufs(head[int(10 * SR):])) / 20)
        print(f"gain {20 * np.log10(gain):.1f}dB  先頭のピーク {20 * np.log10(np.abs(head).max() * gain):.1f}dBFS", flush=True)
        ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "f32le", "-ar", str(SR), "-ac", "2", "-i", "-",
                               "-af", "loudnorm=I=-24:TP=-3:LRA=7", "-ar", str(SR), "-c:a", "aac", "-b:a", "128k", out], stdin=subprocess.PIPE)
        maxpk = 0
        # 8ブロックずつ計算して書く（まとめて先に計算すると、書き出しが追いつかずメモリがあふれる）
        for k0 in range(0, nblk, 8):
            for x in pool.map(_job, jobs[k0 : k0 + 8]):
                x = x * gain
                maxpk = max(maxpk, np.abs(x).max())
                ff.stdin.write(x.astype("<f4").tobytes())
            print(f"  {min(k0 + 8, nblk)}/{nblk}", flush=True)
        ff.stdin.close()
        ff.wait()
    print(f"wrote {out}  loudnorm前の最大ピーク {20 * np.log10(maxpk):.1f}dBFS")
