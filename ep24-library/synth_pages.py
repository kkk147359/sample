"""ep24/25「夜の図書館でページをめくる音」の合成。
実録音の測定（REFERENCES.md）に合わせた1回のめくり：
- 長さ約0.5〜0.8秒。「指でページの端をつまむ／すべらせる」→「持ち上げ（紙がしなるカサッ）」→「ページが動く」→「着地（パサッ）」の
  3段で、実録音でも山が2〜3個ある（#416179・#63318）。
- 紙の音は「細かいパチパチ（0.1〜0.3msの鋭い音）の重なり」でできている。濾波したノイズでは作らない（風の音対策）。
- ゆっくりめくる録音の重心は1.4〜1.8kHz、最大は1.0〜1.6kHz帯、3〜4kHzは-12〜-17dB。速くパラパラめくる録音（重心3〜6kHz）は使わない。
- 4kHzより上はさらに下げる（耳鳴り対策、企画の条件）。
合間：
- 15〜40秒ごとにめくる（企画の条件）。めくる前に指が紙をすべる音を1〜2秒入れ、急な音にならないようにする。
- めくったあと、ときどき手のひらでページをなでる音。数分に1回、本を少し持ち直すやわらかい音。
- 背景は空調などの帯域の広いノイズを使わず、ごく小さな紙・袖のこすれ（まばらなパチパチ）と短い部屋の響きだけ。
render(total, seed) で全体を作る（長い版は区間ごとに render_block）。
"""
import numpy as np
from scipy.signal import butter, sosfilt, fftconvolve

SR = 44100
BED_DB = -16.0  # 背景の大きさ（めくりのある1秒の音量との差）

# 目標の1/3オクターブ配分（1回のめくり全体、最大を0dB）。#416179 と #63318 の平均に、4kHzより上を追加で下げた値。
T_CENT = 1000 * 2.0 ** (np.arange(-9, 11) / 3)  # 125Hz〜10kHz
T_DB = np.array([-15, -17, -17, -14, -14, -12, -7, -6, -5, -3, 0, -2, -6, -8, -13, -16, -19, -22, -25, -29], float)


def _bp(lo, hi, order=2):
    return butter(order, [lo, hi], btype="band", fs=SR, output="sos")


def crackle(n, rate_env, rng, bright=1.0, sigma=0.8, paper=True):
    """細かいパチパチの列。rate_env は1秒あたりの数（長さ n の配列）。"""
    p = np.clip(rate_env / SR, 0, 0.5)
    hit = rng.random(n) < p
    amp = np.exp(rng.normal(0, sigma, n)) * hit
    amp *= np.where(rng.random(n) < 0.5, 1, -1)
    # 1粒は0.1〜0.3msの鋭い音：短い減衰でにじませる
    k = np.exp(-np.arange(int(0.0004 * SR)) / (0.00008 * SR * bright))
    y = fftconvolve(amp, k)[:n]
    if not paper:
        return y
    # 紙のしなりの響き（ゆるい山を3つ、毎回少しずつ違う高さ）
    out = np.zeros(n)
    for fc in rng.uniform([700, 1100, 1700], [1000, 1600, 2600]):
        out += sosfilt(_bp(fc / 1.5, fc * 1.5), y)
    return out + 0.35 * sosfilt(_bp(300, 5000), y)


def env(n, a, d, shape=2.0):
    """立ち上がり a 秒、残りで減衰する形"""
    t = np.arange(n) / SR
    up = np.clip(t / max(a, 1e-3), 0, 1) ** shape
    down = np.clip(1 - (t - a) / max(n / SR - a, 1e-3), 0, 1) ** d
    return np.where(t < a, up, down)


def flap(n, rng):
    """着地のやわらかいパサッ（紙が空気を押す短い音）。250〜1500Hz、40ms程度で減衰。"""
    m = int(0.18 * SR)
    burst = crackle(m, np.full(m, 9000.0), rng, bright=1.6)
    burst = sosfilt(_bp(250, 1600), burst) * np.exp(-np.arange(m) / (0.035 * SR))
    out = np.zeros(n)
    out[: min(n, m)] = burst[: min(n, m)]
    return out


def page_turn(rng):
    """1回のめくり（前の指の音も含む）。(音, めくりの山の位置[秒]) を返す。"""
    pre = rng.uniform(1.0, 1.8)  # 指がページの端をすべる
    lift = rng.uniform(0.22, 0.32)
    move = rng.uniform(0.15, 0.30)
    land = 0.35
    total = pre + lift + move + land + 0.2
    n = int(total * SR)
    t = np.arange(n) / SR
    rate = np.zeros(n)
    lvl = np.zeros(n)
    # 指：だんだん近づく小さなこすれ
    m = t < pre
    rate[m] = rng.uniform(250, 500)
    lvl[m] = 0.20 * np.clip(t[m] / pre, 0, 1) ** 1.2
    # 持ち上げ：紙がしなって細かい音が増える（立ち上がり140〜240ms、急な音を避ける）
    a0 = pre
    m = (t >= a0) & (t < a0 + lift)
    rise = rng.uniform(0.14, 0.24)
    rate[m] = 5000
    lvl[m] = 0.20 + 0.80 * np.clip((t[m] - a0) / rise, 0, 1) ** 1.3
    # 動く：まばらになり、少し小さく
    a1 = a0 + lift
    m = (t >= a1) & (t < a1 + move)
    rate[m] = 1500
    lvl[m] = 0.55 * (1 - 0.5 * (t[m] - a1) / move)
    # 着地のあとの小さな余韻
    a2 = a1 + move
    m = t >= a2
    rate[m] = 600
    lvl[m] = 0.25 * np.exp(-(t[m] - a2) / 0.08)
    sm = int(0.012 * SR)
    lvl = np.convolve(lvl, np.ones(sm) / sm, "same")
    y = crackle(n, rate, rng) * lvl
    f = flap(n - int(a2 * SR), rng) * rng.uniform(0.7, 1.0)
    y[int(a2 * SR):] += f * 2.2
    # 1回ごとに強さ±1.5dB
    y *= 10 ** (rng.normal(0, 0.75) / 20)
    return y, a0 + lift * 0.6


def rub(dur, level, rng):
    """手のひら・指でページをなでる音（ゆっくり出てゆっくり消える）"""
    n = int(dur * SR)
    e = env(n, dur * 0.4, 1.5, 1.5)
    return crackle(n, np.full(n, 700.0), rng, bright=1.3) * e * level


def thump(rng):
    """本を少し持ち直すやわらかい音（低め、急にならないように）"""
    n = int(0.5 * SR)
    y = crackle(n, np.full(n, 4000.0), rng, bright=2.5)
    y = sosfilt(_bp(150, 700), y) * env(n, 0.05, 3.0)
    return y * 0.6


def bed(n, rng):
    """背景：ごく小さな紙・袖のこすれ（まばら）。帯域の広いノイズは使わない。"""
    t = np.arange(n) / SR
    slow = 0.5 + 0.5 * np.sin(2 * np.pi * t / rng.uniform(17, 29) + rng.uniform(0, 6))
    rate = 400 + 300 * slow
    # 粒の大きさをそろえ（目立つ粒を作らない）、紙の響きは通さず、やわらかい布のこすれ程度に
    y = crackle(n, rate, rng, bright=2.0, sigma=0.3, paper=False)
    y = sosfilt(_bp(180, 1400), y)
    return y * (0.75 + 0.25 * slow)


def room_ir(rng):
    """夜の図書館の短い響き（残響0.6秒程度、高い音ほど早く消える）"""
    n = int(0.9 * SR)
    t = np.arange(n) / SR
    ir = np.zeros((n, 2))
    for ch in range(2):
        r = rng.normal(0, 1, n)
        lo = sosfilt(butter(2, 1500, fs=SR, output="sos"), r) * np.exp(-t / 0.11)
        hi = sosfilt(butter(2, 1500, btype="high", fs=SR, output="sos"), r) * np.exp(-t / 0.05)
        ir[:, ch] = (lo + 0.5 * hi) * np.clip(t / 0.008, 0, 1)
    ir[0, :] = 0
    return ir / np.sqrt((ir ** 2).sum(0)) * 0.20


def eq_to_target(x):
    """全体の1/3オクターブ配分を目標（T_DB）に合わせる（ゼロ位相、FFTで一度に）"""
    n = len(x)
    X = np.fft.rfft(x, axis=0)
    f = np.fft.rfftfreq(n, 1 / SR)
    P = (np.abs(X) ** 2).sum(axis=1) if X.ndim == 2 else np.abs(X) ** 2
    have = np.array([P[(f >= c / 2 ** (1 / 6)) & (f < c * 2 ** (1 / 6))].sum() for c in T_CENT])
    have = 10 * np.log10(have / have.max() + 1e-12)
    corr = np.clip(T_DB - have, -18, 12)
    g_db = np.interp(np.log2(np.maximum(f, 1)), np.log2(T_CENT), corr, left=corr[0], right=corr[-1])
    g_db[f > 12000] -= 12
    g = 10 ** (g_db / 20)
    return np.fft.irfft(X * (g[:, None] if X.ndim == 2 else g), n=n, axis=0)


def schedule(total, rng, first=4.0, lo=15.0, hi=40.0):
    ts, t = [], first
    while t < total:
        ts.append(t)
        t += rng.uniform(lo, hi)
    return ts


def render(total, seed=24, lo=15.0, hi=40.0, first=4.0):
    rng = np.random.default_rng(seed)
    n = int(total * SR)
    dry = np.zeros((n, 2))
    for t0 in schedule(total - 3, rng, first, lo, hi):
        y, _ = page_turn(rng)
        pan = rng.uniform(-0.15, 0.15)
        i = int(t0 * SR)
        j = min(n, i + len(y))
        dry[i:j, 0] += y[: j - i] * (1 - pan)
        dry[i:j, 1] += y[: j - i] * (1 + pan)
        if rng.random() < 0.5:  # めくったあと、ページをなでる
            r = rub(rng.uniform(0.8, 1.6), 0.12, rng)
            k = i + len(y) + int(rng.uniform(0.3, 1.5) * SR)
            j = min(n, k + len(r))
            if k < n:
                dry[k:j] += r[: j - k, None]
        if rng.random() < 0.25:  # 合間の小さな指の音
            r = rub(rng.uniform(0.5, 1.0), 0.06, rng)
            k = i + int(rng.uniform(6, 12) * SR)
            j = min(n, k + len(r))
            if k < n:
                dry[k:j] += r[: j - k, None]
        if rng.random() < 0.12:  # 本を少し持ち直す
            r = thump(rng)
            k = i + int(rng.uniform(8, 14) * SR)
            j = min(n, k + len(r))
            if k < n:
                dry[k:j] += r[: j - k, None]
    # 背景は、めくりのある1秒の音量より BED_DB 小さくそろえる（無音の区間を作らない）
    sec = (dry[: n // SR * SR, 0].reshape(-1, SR) ** 2).mean(1)
    ref = np.percentile(sec[sec > 0], 90) if (sec > 0).any() else 1e-4
    b = bed(n, rng)
    b *= np.sqrt(ref / (b ** 2).mean()) * 10 ** (BED_DB / 20)
    dry[:, 0] += b
    dry[:, 1] += np.roll(b, 37)
    ir = room_ir(rng)
    wet = np.stack([fftconvolve(dry[:, c], ir[:, c])[:n] for c in range(2)], 1)
    out = eq_to_target(dry + wet)
    return out
