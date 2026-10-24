"""時計の後ろに流す「窓の外の静かな小雨」。実録音（REFERENCES.md）の測定に合わせる：
- 下地：雨のサーという音。1/3オクターブ配分は #392304（窓を開けた室内で録った雨）をもとに、
  社長が嫌う低音の圧迫感を避けるため 150Hz より下を切り、強い雨に聞こえないよう 3kHz より上を少し下げた。
- ゆらぎ：帯域ごとの音量の揺れは実録音で 0.5秒平均の標準偏差 0.5〜1.5dB。ここでは約1dB、数秒単位でゆっくり。
- 雨だれ：#392304 は1分に約48滴、間隔の中央値0.29秒（ばらつき大）、周りより中央値14dB大きい。
  強すぎる雨音にしないため、ここでは1分に約40滴・周りより約9dB に抑える。

render_block(t0, dur, seed) で区間ごとに書き出せる（継ぎ目なし）。
"""
import numpy as np
from scipy.signal import butter, sosfilt

SR = 44100
CENTERS = 1000 * 2.0 ** (np.arange(-17, 11) / 3)
# 目標の配分（dB、20Hz〜10kHz）。#392304 の測定値を下敷きにした値
TARGET = np.array([-60, -50, -42, -34, -26, -18, -10, -4, -2, -1, -1.4, -1.7, -2.2, -1.4, -0.6, -0.5, -0.9, -1.8,
                   -3.3, -5.3, -7.9, -10.5, -13, -15, -17, -18, -20, -26.0])
NFIR = 1 << 13
BLOCK = 1 << 17


NB = 6  # ゆらぎをつける帯域の数
EDGES = [0, 400, 800, 1600, 3200, 6400, 30000]


def _firs():
    """目標の配分のFIRを、ゆらぎ用の6帯域に分けたもの（帯域の境目はなめらかに重ねる）"""
    f = np.fft.rfftfreq(NFIR, 1 / SR)
    # 1/3オクターブの帯域パワーを、1Hzあたりの密度に直して内挿（帯域幅は周波数に比例）
    dens = TARGET - 10 * np.log10(CENTERS)
    g = 10 ** (np.interp(np.log10(np.maximum(f, 10)), np.log10(CENTERS), dens) / 20)
    lf = np.log2(np.maximum(f, 1))
    hs = []
    tot = 0
    for b in range(NB):
        lo = np.log2(max(EDGES[b], 1)) if b > 0 else -99
        hi = np.log2(EDGES[b + 1]) if b < NB - 1 else 99
        w = np.clip(np.minimum(lf - lo + 0.25, hi - lf + 0.25) / 0.5, 0, 1)  # 境目で0.5オクターブかけて入れ替わる
        h = np.fft.irfft(g * np.sqrt(w), NFIR)
        h = np.roll(h, NFIR // 2) * np.hanning(NFIR)
        hs.append(h)
        tot += (h ** 2).sum()
    return [h / np.sqrt(tot) for h in hs]


HB = _firs()


def _mod(t, seed, band):
    """なめらかなゆらぎ（dB）。ランダムな周期の正弦の和なので、どの区間から計算しても同じ値"""
    r = np.random.default_rng([seed, 77, band])
    fr = r.uniform(0.05, 0.4, 6)
    ph = r.uniform(0, 2 * np.pi, 6)
    slow = r.uniform(0.002, 0.006)
    m = sum(np.sin(2 * np.pi * f * t + p) for f, p in zip(fr, ph)) / np.sqrt(3)  # 標準偏差 約1
    return 1.0 * m + 1.5 * np.sin(2 * np.pi * slow * t + ph[0])


def _bed_block(i, seed):
    """i番目のブロックの下地（帯域, サンプル, ステレオ）。前のブロックの尾を重ねて継ぎ目をなくす"""
    out = np.zeros((NB, BLOCK, 2))
    nf = BLOCK + NFIR
    Hf = [np.fft.rfft(h, nf) for h in HB]
    for j in (i - 1, i):
        if j < 0:
            continue
        for c in range(2):
            W = np.fft.rfft(np.random.default_rng([seed, j, c]).normal(0, 1, BLOCK), nf)
            for b in range(NB):
                y = np.fft.irfft(W * Hf[b], nf)
                if j == i:
                    out[b, :, c] += y[:BLOCK]
                else:
                    out[b, :NFIR, c] += y[BLOCK : BLOCK + NFIR]
    return out


def drop_schedule(total, seed):
    r = np.random.default_rng([seed, 5])
    t, ev = 0.0, []
    while t < total:
        t += r.lognormal(np.log(0.9), 0.9)  # 間隔の中央値約0.9秒、ばらつき大（1分に約40滴）
        ev.append((t, r.normal(-1, 2.5), r.uniform(-0.8, 0.8), r.integers(1 << 30)))
    return ev


DROP_DB = 2.0  # 実録音（中央値14dB）より少し控えめ


def _drop(seed):
    r = np.random.default_rng(seed)
    n = int(0.12 * SR)
    t = np.arange(n) / SR
    x = r.normal(0, 1, n) * (1 - np.exp(-t / 0.002)) * np.exp(-t / r.uniform(0.012, 0.03))
    lo = r.uniform(500, 900)
    hi = r.uniform(2200, 3400)
    x = sosfilt(butter(2, [lo, hi], btype="band", fs=SR, output="sos"), x)
    return x / (np.sqrt(np.mean(x[: int(0.02 * SR)] ** 2)) + 1e-12)


def render_block(t0, dur, seed, drops):
    """t0秒からdur秒（ステレオ）。下地のRMSが約1になる大きさ"""
    n = int(round(dur * SR))
    s0 = int(round(t0 * SR))
    i0, i1 = s0 // BLOCK, (s0 + n - 1) // BLOCK
    bed = np.concatenate([_bed_block(i, seed) for i in range(i0, i1 + 1)], axis=1)
    bed = bed[:, s0 - i0 * BLOCK : s0 - i0 * BLOCK + n]
    t = t0 + np.arange(n) / SR
    tt = np.arange(np.floor(t0 * 100), np.ceil((t0 + dur) * 100) + 1) / 100  # 絶対時刻の10ms格子（区切りに依存しない）
    out = np.zeros((n, 2))
    for b in range(NB):
        g = 10 ** (np.interp(t, tt, _mod(tt, seed, b)) / 20)
        out += bed[b] * g[:, None]
    # 雨だれ：周りの雨（900Hz〜3.5kHz）より約9dB大きい程度
    for td, db, pan, sd in drops:
        if td < t0 - 0.15 or td > t0 + dur:
            continue
        d = _drop(sd) * 10 ** ((db + DROP_DB) / 20)
        s = int(round((td - t0) * SR))
        a, b2 = max(s, 0), min(s + len(d), n)
        if b2 > a:
            seg = d[a - s : b2 - s]
            out[a:b2, 0] += seg * np.sqrt(0.5 * (1 - pan))
            out[a:b2, 1] += seg * np.sqrt(0.5 * (1 + pan))
    return out
