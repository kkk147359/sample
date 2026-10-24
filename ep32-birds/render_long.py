"""長い版の書き出し。小鳥の声は2分ずつ区切って計算し（4コアで並列。1声ごとの音は番号で決まるので境目でもつながる）、
朝の庭の空気は区切らずに FIR で作り続ける（境目で途切れない）。ffmpeg で AAC（.m4a）にする。
使い方: python3 render_long.py <出力.m4a> <秒数> <シード>
音は社長OKの試聴版A（10/14）と同じ設定。鳴く順番だけシードで変わる。
音量は試聴版Aと同じく、最初の6分を測って -28LUFS になる一定の倍率を全体にかける（loudnorm は使わない：間の静けさを持ち上げないため）。
"""
import re
import subprocess
import sys
from multiprocessing import Pool

import numpy as np
from scipy.signal import fftconvolve

import synth_birds as sb

SR = sb.SR
BLK = 120.0
FADE = 3.0
TARGET = -28.0
EV = None


def _init(total, seed):
    global EV
    EV = sb.schedule(total + 5, seed)


def _job(args):
    k, total, seed = args
    t0 = k * BLK
    return sb.render(t0, min(BLK, total - t0), EV, seed, with_bed=False).astype(np.float32)


class Bed:
    def __init__(self, seed):
        self.h = sb.air_fir()
        self.g = sb.bed_gain()
        self.rng = [np.random.default_rng((seed, c, 777)) for c in range(2)]
        self.tail = [np.zeros(len(self.h) - 1) for _ in range(2)]
        self.seed = seed

    def next(self, t0, n):
        out = []
        for c in range(2):
            y = fftconvolve(self.rng[c].normal(0, 1, n), self.h)
            y[: len(self.tail[c])] += self.tail[c]
            self.tail[c] = y[n:]
            out.append(y[:n])
        t = t0 + np.arange(n) / SR
        return np.stack(out, 1) * self.g * sb.bed_swell(t, self.seed)[:, None]


def lufs(x):
    r = subprocess.run(["ffmpeg", "-f", "f32le", "-ar", str(SR), "-ac", "2", "-i", "-", "-af", "ebur128", "-f", "null", "-"],
                       input=x.astype("<f4").tobytes(), capture_output=True).stderr.decode()
    return float(re.findall(r"I:\s+(-?[\d.]+) LUFS", r)[-1])


if __name__ == "__main__":
    out, total, seed = sys.argv[1], float(sys.argv[2]), int(sys.argv[3])
    nblk = int(np.ceil(total / BLK))
    jobs = [(k, total, seed) for k in range(nblk)]
    with Pool(4, initializer=_init, initargs=(total, seed)) as pool:
        # 音量の倍率：最初の6分（3ブロック）を同じ作り方で計算して測る
        bed = Bed(seed)
        head = np.concatenate(pool.map(_job, jobs[:3]))
        head = head + bed.next(0.0, len(head))
        gain = 10 ** ((TARGET - lufs(head[int(10 * SR):])) / 20)
        print(f"gain {20 * np.log10(gain):.1f}dB", flush=True)
        bed = Bed(seed)  # 作り直して先頭から
        ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "f32le", "-ar", str(SR), "-ac", "2", "-i", "-",
                               "-c:a", "aac", "-b:a", "160k", out], stdin=subprocess.PIPE)
        maxpk = 0
        t = 0.0
        for k0 in range(0, nblk, 8):
            for x in pool.map(_job, jobs[k0: k0 + 8]):
                n = len(x)
                tt = t + np.arange(n) / SR
                g = np.clip(tt / FADE, 0, 1) * np.clip((total - tt) / FADE, 0, 1)
                y = (x + bed.next(t, n)) * gain * g[:, None]
                maxpk = max(maxpk, np.abs(y).max())
                ff.stdin.write(y.astype("<f4").tobytes())
                t += n / SR
            print(f"  {min(k0 + 8, nblk)}/{nblk}", flush=True)
        ff.stdin.close()
        ff.wait()
    print(f"wrote {out}  最大ピーク {20 * np.log10(maxpk):.1f}dBFS")
