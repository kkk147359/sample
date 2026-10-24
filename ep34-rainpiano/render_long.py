"""長い版の書き出し。ピアノと落ち葉の粒は2分ずつ区切って計算し（4コアで並列。1音ごとの音は番号で決まるので境目でもつながる）、
雨の下地は区切らずに FIR で作り続ける（境目で途切れない）。ffmpeg で AAC（.m4a）にする。
使い方: python3 render_long.py <出力.m4a> <秒数> <シード> [雨のdB(ピアノ比)=-8]
音は社長OKの試聴版C（10/17）と同じ設定。曲（和音・句の並び）だけシードで変わる。同じ区間のくり返しはない。
音量：最初の6分を測り、雨の大きさ（ピアノ比）と -28LUFS になる一定の倍率を決めて全体にかける（loudnorm は使わない）。
"""
import re
import subprocess
import sys
from multiprocessing import Pool

import numpy as np

import synth_piano as sp
import synth_rain as sr_

SR = sp.SR
BLK = 120.0
PRE = 3.0    # 部屋の響きのため、区間の前3秒から計算して捨てる
LOOK = 28.0  # これより前に弾いた音は区間に届かない（最長の余韻 22秒＋離鍵）
FADE = 3.0
TARGET = -28.0
EV = PEV = None
SEED = None


def _init(total, seed):
    global EV, PEV, SEED
    SEED = seed
    EV = sp.compose(total - 4, seed)
    PEV = sr_.events(total + 1, seed)


def _job(args):
    k, total = args
    t0 = k * BLK
    dur = min(BLK, total - t0)
    a = max(0.0, t0 - PRE)
    n = int(round((t0 + dur - a) * SR))
    x = np.zeros((n, 2))
    for i, (ts, m, v, d) in enumerate(EV):
        if ts < a - LOOK or ts >= t0 + dur:
            continue
        y = sp.note(m, v, d, [SEED, i])
        s = int(round((ts - a) * SR))
        lo, hi = max(s, 0), min(n, s + len(y))
        if hi <= lo:
            continue
        pan = np.clip((m - 60) / 30, -0.5, 0.5)
        seg = y[lo - s: hi - s]
        x[lo:hi, 0] += seg * np.sqrt(0.5 * (1 - pan))
        x[lo:hi, 1] += seg * np.sqrt(0.5 * (1 + pan))
    x = sp.room(x, SEED)
    skip = int(round((t0 - a) * SR))
    pno = x[skip: skip + int(round(dur * SR))]
    pat = sr_.render_events(t0, dur, PEV)
    m = min(len(pno), len(pat))
    return pno[:m].astype(np.float32), pat[:m].astype(np.float32)


def lufs(x):
    r = subprocess.run(["ffmpeg", "-f", "f32le", "-ar", str(SR), "-ac", "2", "-i", "-", "-af", "ebur128", "-f", "null", "-"],
                       input=x.astype("<f4").tobytes(), capture_output=True).stderr.decode()
    return float(re.findall(r"I:\s+(-?[\d.]+) LUFS", r)[-1])


def rms(y):
    return np.sqrt(np.mean(np.asarray(y, dtype=float) ** 2))


if __name__ == "__main__":
    out, total, seed = sys.argv[1], float(sys.argv[2]), int(sys.argv[3])
    rain_db = float(sys.argv[4]) if len(sys.argv) > 4 else -8.0
    nblk = int(np.ceil(total / BLK))
    jobs = [(k, total) for k in range(nblk)]
    with Pool(4, initializer=_init, initargs=(total, seed)) as pool:
        head = pool.map(_job, jobs[:3])
        pno = np.concatenate([h[0] for h in head])
        bed = sr_.Bed(seed)
        rain = np.concatenate([h[1] for h in head]) + bed.next(0.0, len(pno))
        rg = rms(pno) / rms(rain) * 10 ** (rain_db / 20)
        mix = pno + rain * rg
        gain = 10 ** ((TARGET - lufs(mix[int(10 * SR):])) / 20)
        print(f"rain {20 * np.log10(rg):.1f}dB  gain {20 * np.log10(gain):.1f}dB", flush=True)
        bed = sr_.Bed(seed)  # 作り直して先頭から
        ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "f32le", "-ar", str(SR), "-ac", "2", "-i", "-",
                               "-c:a", "aac", "-b:a", "160k", out], stdin=subprocess.PIPE)
        maxpk = 0
        t = 0.0
        for k0 in range(0, nblk, 8):
            for p, q in pool.map(_job, jobs[k0: k0 + 8]):
                n = len(p)
                tt = t + np.arange(n) / SR
                g = np.clip(tt / FADE, 0, 1) * np.clip((total - tt) / FADE, 0, 1)
                y = (p + (q + bed.next(t, n)) * rg) * gain * g[:, None]
                maxpk = max(maxpk, np.abs(y).max())
                ff.stdin.write(y.astype("<f4").tobytes())
                t += n / SR
            print(f"  {min(k0 + 8, nblk)}/{nblk}", flush=True)
        ff.stdin.close()
        ff.wait()
    print(f"wrote {out}  最大ピーク {20 * np.log10(maxpk):.1f}dBFS")
