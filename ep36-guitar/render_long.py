"""長い版の書き出し。曲は全体を一度に作り（compose.py）、音は2分ずつ区切って fluidsynth で鳴らす（4コアで並列）。
各区間は15秒前から鳴らして捨てるので、前から鳴っている音と響きが境目でつながる。
急な音のおさえと音量合わせは試聴版v2と同じ（acompressor → loudnorm I=-23:TP=-3:LRA=7）で、全体を1本の ffmpeg に流して行う。
使い方: python3 render_long.py <出力.m4a> <秒数> <シード> [音声ビットレート=160k]
音は社長OKの試聴版v2（10/24）と同じ設定。調と音域は150秒ごとに変わる。同じ区間のくり返しはない。
"""
import os
import subprocess
import sys
import tempfile
from multiprocessing import Pool

import numpy as np

import compose as cp
import render as rd

SR = rd.SR
BLK = 120.0
PRE = 15.0
FADE_IN, FADE_OUT = 3.0, 6.0
TARGET = -23.0
COMP = "acompressor=threshold=-30dB:ratio=2:attack=8:release=250:knee=6"
EV = None


def _init(total, seed):
    global EV
    EV = cp.compose(total - 6, seed, section=150.0)


def _job(args):
    k, total = args
    t0 = k * BLK
    dur = min(BLK, total - t0)
    a = max(0.0, t0 - PRE)
    ev = [e for e in EV if a <= e[0] < t0 + dur]
    with tempfile.TemporaryDirectory() as d:
        mid = os.path.join(d, "b.mid")
        cp.write_midi(ev, mid, offset=a)
        x = rd.synth(mid)
    n = int(round((t0 + dur - a) * SR)) + 1
    if len(x) < n:
        x = np.concatenate([x, np.zeros((n - len(x), 2))])
    y = rd.process(x[:n])
    skip = int(round((t0 - a) * SR))
    return (y[skip: skip + int(round(dur * SR))] * 0.5).astype(np.float32)


if __name__ == "__main__":
    out, total, seed = sys.argv[1], float(sys.argv[2]), int(sys.argv[3])
    br = sys.argv[4] if len(sys.argv) > 4 else "160k"
    nblk = int(np.ceil(total / BLK))
    jobs = [(k, total) for k in range(nblk)]
    with Pool(4, initializer=_init, initargs=(total, seed)) as pool:
        # 試聴版と同じ入力の大きさで acompressor に入れる（試聴版は最大値を 0.5 にそろえていた）
        head = np.concatenate(pool.map(_job, jobs[:3]))
        pre = 0.5 / np.abs(head).max()
        print(f"pre-gain {20 * np.log10(pre):.1f}dB", flush=True)
        af = f"volume={pre:.4f},{COMP},loudnorm=I={TARGET}:TP=-3:LRA=7,aresample={SR},afade=t=in:d={FADE_IN},afade=t=out:st={total - FADE_OUT}:d={FADE_OUT}"
        ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "f32le", "-ar", str(SR), "-ac", "2", "-i", "-",
                               "-af", af, "-t", str(total), "-c:a", "aac", "-b:a", br, out], stdin=subprocess.PIPE)
        for k0 in range(0, nblk, 8):
            for y in pool.map(_job, jobs[k0: k0 + 8]):
                ff.stdin.write(y.astype("<f4").tobytes())
            print(f"  {min(k0 + 8, nblk)}/{nblk}", flush=True)
        ff.stdin.close()
        ff.wait()
    print("wrote", out)
