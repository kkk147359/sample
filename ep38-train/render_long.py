"""長い版の書き出し。音は社長OKの試作D2（10/28）と同じ設定：時速35km（継ぎ目2.6秒ごと）、タタンの間0.29秒、継ぎ目-1dB。
走行音は60秒ずつ別の乱数で作り、2秒の重なりでつなぐ（同じ区間のくり返しはない）。継ぎ目の時刻は全体を一度に決める。
音量は最初の3分を測って -24 LUFS にそろえる倍率を決め、全体に同じ倍率をかける（試作と同じ大きさ）。
使い方: python3 render_long.py <出力.m4a> <秒数> <シード> [音声ビットレート=160k]
"""
import os
import subprocess
import sys
import tempfile
from multiprocessing import Pool

import numpy as np

import synth_train as st

SR = st.SR
BLK, XF = 60.0, 2.0
SPEED_KMH, GAP, CLACK_DB = 35.0, 0.29, -1.0
TARGET = -24.0
FADE_IN, FADE_OUT = 3.0, 6.0
st.SPEED = SPEED_KMH / 3.6
st.AXLE = GAP * st.SPEED
EV = None
SEED = 0


def _init(total, seed):
    global EV, SEED
    SEED = seed
    EV = st.joint_times(total + XF, np.random.default_rng(seed))


def _job(k):
    """k番目の区間（先頭から k*BLK 秒、長さ BLK+XF 秒）。"""
    t0 = k * BLK
    dur = BLK + XF
    rng = np.random.default_rng((SEED, k))
    x = st.rumble(dur, rng, gseed=SEED * 10000 + k)
    x /= np.sqrt((x ** 2).mean())
    n = len(x)
    c = np.zeros((n, 2))
    for j, (te, s) in enumerate(EV):
        if te < t0 - 0.3 or te >= t0 + dur:
            continue
        r = np.random.default_rng((SEED, 7, j))   # 同じ打音は重なり部分でも同じ音になる
        y = st.clack(r, s)
        pan = r.normal(0, 0.08)
        i = int(round((te - t0) * SR))
        a, b = max(0, i), min(n, i + len(y))
        if b <= a:
            continue
        seg = y[a - i: b - i]
        c[a:b, 0] += seg * (1 - pan)
        c[a:b, 1] += seg * (1 + pan)
    c *= 10 ** (CLACK_DB / 20) / 0.25
    return (x + c).astype(np.float32)


def stitch(blocks):
    """重なり2秒を等パワーでつなぎ、各区間の先頭 BLK 秒ぶんを順に返す。"""
    nb, nx = int(BLK * SR), int(XF * SR)
    w = np.sin(np.linspace(0, np.pi / 2, nx))[:, None]
    tail = None
    for y in blocks:
        y = y.copy()
        if tail is not None:
            y[:nx] = tail * np.cos(np.linspace(0, np.pi / 2, nx))[:, None] + y[:nx] * w
        tail = y[nb: nb + nx]
        yield y[:nb]


def lufs(x):
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "a.f32")
        x.astype("<f4").tofile(p)
        r = subprocess.run(["ffmpeg", "-hide_banner", "-f", "f32le", "-ar", str(SR), "-ac", "2", "-i", p, "-af", "ebur128",
                            "-f", "null", "-"], capture_output=True, text=True).stderr
    return float([l for l in r.splitlines() if l.strip().startswith("I:")][-1].split()[1])


if __name__ == "__main__":
    out, total, seed = sys.argv[1], float(sys.argv[2]), int(sys.argv[3])
    br = sys.argv[4] if len(sys.argv) > 4 else "160k"
    nblk = int(np.ceil(total / BLK))
    with Pool(4, initializer=_init, initargs=(total, seed)) as pool:
        head = np.concatenate(list(stitch(pool.map(_job, range(3)))))
        gain = 10 ** ((TARGET - lufs(head)) / 20)
        peak = np.abs(head).max() * gain
        print(f"gain {20 * np.log10(gain):.1f}dB  head peak {20 * np.log10(peak):.1f}dBFS", flush=True)
        af = f"afade=t=in:d={FADE_IN},afade=t=out:st={total - FADE_OUT}:d={FADE_OUT}"
        ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "f32le", "-ar", str(SR), "-ac", "2", "-i", "-",
                               "-af", af, "-t", str(total), "-c:a", "aac", "-b:a", br, out], stdin=subprocess.PIPE)
        pend = []
        mx = 0.0

        def gen():
            for k0 in range(0, nblk, 8):
                for y in pool.map(_job, range(k0, min(nblk, k0 + 8))):
                    yield y
                print(f"  {min(k0 + 8, nblk)}/{nblk}", flush=True)

        for y in stitch(gen()):
            y = y * gain
            mx = max(mx, float(np.abs(y).max()))
            ff.stdin.write(np.clip(y, -0.99, 0.99).astype("<f4").tobytes())
        ff.stdin.close()
        ff.wait()
    print(f"wrote {out}  peak {20 * np.log10(mx):.1f}dBFS")
