"""ep24/25「夜の図書館でページをめくる音」v2（10/8 社長「ざざざは図書館の雑音？」「紙をめくる音が本物と全然違う」を受けて作り直し）。

v1 の問題：
- 合間の背景（まばらな粒を帯域で絞ったもの）と、めくる前の1.5〜2.3秒の指のこすれが、続けて「ざざざ」と聞こえていた。
- 紙の音を「粒の列」＋「3つの共鳴（700〜2600Hz）」で作ったため音程感が出て、紙らしいガサッとした広い音にならなかった
  （1回のめくりのスペクトル平坦度：実録音 #416179 0.167・#63318 0.053、v1 0.03〜0.04）。

v2 の作り（実録音のゆっくりめくる2本の測定値に合わせる）：
- 1回は約0.6〜0.9秒で、山が3つ：①持ち上げ（紙がしなるカサッ、立ち上がり100〜220ms）②ページが空気を切る「サッ」
  （なめらかな広い音、150〜300ms、紙のたわみで細かく揺れる）③着地の「パサ」（30〜50msで減衰）。
- 紙の音は広い帯域の音（白色雑音）に、紙が折れ曲がる細かいパチパチを重ねて作る。共鳴の山は付けない。
- 全体の1/3オクターブ配分は実録音の平均（1.0〜1.6kHz最大、2kHz -6dB、3.2kHz -13dB）に合わせ、4kHzより上をさらに下げる。
- めくる直前に、指がページの端にふれる短い音（0.25〜0.45秒、めくりより約13dB小さい）だけ入れる（v1 の長いこすれはやめた）。
- 合間に「ざざざ」と続く背景は入れない。無音にならないよう、300Hz以下のごく小さな部屋の空気だけを置く（高い音を含まない）。
- 合間に、ときどき紙が落ち着く小さな音・指が少し動く音（0.2〜0.5秒、めくりより18〜26dB小さい）。
"""
import numpy as np
from scipy.signal import butter, fftconvolve, sosfilt

SR = 44100

T_CENT = 1000 * 2.0 ** (np.arange(-9, 11) / 3)  # 125Hz〜10kHz
T_DB = np.array([-15, -17, -17, -14, -14, -12, -7, -6, -5, -3, 0, -2, -6, -8, -13, -16, -19, -22, -25, -29], float)
ROOM_DB = -66.0  # 部屋の空気（dBFS、書き出し前の基準での目安）


def _bp(lo, hi, order=2):
    return butter(order, [lo, hi], btype="band", fs=SR, output="sos")


def _lp(f, order=2):
    return butter(order, f, fs=SR, output="sos")


def _hp(f, order=2):
    return butter(order, f, btype="high", fs=SR, output="sos")


def bell(n, peak, rise, fall):
    """peak 秒で最大、rise 秒で上がり fall 秒で下がる、なめらかな山"""
    t = np.arange(n) / SR
    up = 0.5 - 0.5 * np.cos(np.pi * np.clip((t - (peak - rise)) / rise, 0, 1))
    down = np.exp(-np.clip(t - peak, 0, None) / fall)
    return np.where(t < peak, up, down)


def snaps(n, rate, rng):
    """紙が折れ曲がる細かいパチパチ（1粒 0.2〜1ms、広い帯域）"""
    hit = rng.random(n) < np.clip(rate / SR, 0, 0.5)
    amp = np.exp(rng.normal(0, 0.6, n)) * hit * np.where(rng.random(n) < 0.5, 1, -1)
    k = np.exp(-np.arange(int(0.002 * SR)) / (0.0003 * SR))
    return fftconvolve(amp, k)[:n]


def page_turn(rng):
    """1回のめくり（直前の指の音を含む）。音（モノラル）を返す。"""
    touch = rng.uniform(0.25, 0.45)
    gap = rng.uniform(0.05, 0.20)
    lift_rise = rng.uniform(0.10, 0.22)
    lift_len = rng.uniform(0.12, 0.22)
    swish_len = rng.uniform(0.15, 0.30)
    t_lift = touch + gap + lift_rise
    t_swish = t_lift + lift_len * 0.6 + swish_len * 0.5
    t_land = t_lift + lift_len + swish_len
    n = int((t_land + 0.6) * SR)
    t = np.arange(n) / SR
    w = rng.normal(0, 1, n)
    y = np.zeros(n)
    # 指がふれる：やわらかい短いこすれ（めくりより約13dB小さい）
    e = bell(n, touch * 0.6, touch * 0.6, touch * 0.25)
    y += sosfilt(_bp(500, 3000), w) * e * 0.22
    # ①持ち上げ：広い音＋パチパチ（紙がしなる）
    e = bell(n, t_lift, lift_rise, lift_len * 0.45)
    crk = snaps(n, 1500 + 2500 * e, rng)
    y += (sosfilt(_bp(400, 5000), w) * 0.6 + sosfilt(_hp(500), crk) * 0.25) * e * rng.uniform(0.85, 1.0)
    # ②空気を切る「サッ」：なめらかな広い音。紙のたわみで 8〜15Hz の細かい揺れ
    e = bell(n, t_swish, swish_len * 0.5, swish_len * 0.35)
    flut = 1 + 0.3 * np.sin(2 * np.pi * rng.uniform(8, 15) * t + rng.uniform(0, 6))
    y += sosfilt(_lp(2500), sosfilt(_hp(250), w)) * e * flut * rng.uniform(0.55, 0.75)
    # ③着地の「パサ」：低め〜中くらいの短い音、30〜50msで減衰。最後に紙が落ち着く小さなパチパチ
    k0 = int(t_land * SR)
    m = n - k0
    tt = np.arange(m) / SR
    land = sosfilt(_lp(1800), sosfilt(_hp(200), rng.normal(0, 1, m)))
    land *= (1 - np.exp(-tt / 0.004)) * np.exp(-tt / rng.uniform(0.03, 0.05))
    settle = snaps(m, 300 * np.exp(-tt / 0.12), rng) * 0.15
    y[k0:] += (land * rng.uniform(0.7, 0.9) + sosfilt(_hp(400), settle))
    y *= 10 ** (rng.normal(0, 0.75) / 20)  # 1回ごとに強さ±1.5dB
    return y


def small(rng):
    """合間の小さな音（紙が落ち着く・指が少し動く）。0.2〜0.5秒"""
    d = rng.uniform(0.2, 0.5)
    n = int(d * SR)
    e = bell(n, d * 0.4, d * 0.4, d * 0.2)
    y = sosfilt(_bp(400, 2500), rng.normal(0, 1, n)) * e
    return y * 10 ** (rng.uniform(-26, -18) / 20) * 0.7


def room_ir(rng):
    """夜の図書館の短い響き（残響0.6秒程度、高い音ほど早く消える）"""
    n = int(0.9 * SR)
    t = np.arange(n) / SR
    ir = np.zeros((n, 2))
    for ch in range(2):
        r = rng.normal(0, 1, n)
        lo = sosfilt(_lp(1500), r) * np.exp(-t / 0.11)
        hi = sosfilt(_hp(1500), r) * np.exp(-t / 0.05)
        ir[:, ch] = (lo + 0.5 * hi) * np.clip(t / 0.008, 0, 1)
    ir[0, :] = 0
    return ir / np.sqrt((ir ** 2).sum(0)) * 0.14


def plan(total, seed, lo=15.0, hi=40.0, first=4.0):
    rng = np.random.default_rng(seed)
    ts, t = [], first
    while t < total - 3:
        ts.append(t)
        t += rng.uniform(lo, hi)
    return ts


def _events(i, t0, seed):
    """i番目のめくりと、その後の合間の小さな音。(開始秒, 左, 右) のリスト。乱数はめくりごとに固定"""
    rng = np.random.default_rng([seed, i])
    y = page_turn(rng)
    pan = rng.uniform(-0.15, 0.15)
    out = [(t0, y * (1 - pan), y * (1 + pan))]
    for _ in range(rng.integers(0, 3)):
        s = small(rng)
        out.append((t0 + rng.uniform(3, 14), s, s))
    return out


def room_span(s0, s1, seed):
    """部屋の空気（300Hz以下だけ）。1秒ごとに乱数を固定し、どの区間から作っても同じ波形"""
    n = (s1 - s0) * SR
    w = np.concatenate([np.random.default_rng([seed, 777777, s]).normal(0, 1, SR) for s in range(s0, s1)])
    y = sosfilt(_lp(300, 4), sosfilt(_hp(40), w))
    return y / 0.12 * 10 ** (ROOM_DB / 20)


def calibrate(seed=7, dur=240.0):
    """めくりだけを並べて全体の1/3オクターブ配分を測り、目標（T_DB）への補正カーブ（dB）を返す"""
    times = plan(dur, seed, 6, 9)
    n = int(dur * SR)
    x = np.zeros(n)
    for i, te in enumerate(times):
        y = page_turn(np.random.default_rng([seed, i]))
        k = int(te * SR)
        x[k:k + len(y)] += y[: max(0, min(len(y), n - k))]
    f = np.fft.rfftfreq(n, 1 / SR)
    P = np.abs(np.fft.rfft(x)) ** 2
    have = np.array([P[(f >= c / 2 ** (1 / 6)) & (f < c * 2 ** (1 / 6))].sum() for c in T_CENT])
    have = 10 * np.log10(have / have.max() + 1e-12)
    return np.clip(T_DB - have, -18, 12)


def eq_fir(corr, taps=4097):
    nf = 1 << 16
    f = np.fft.rfftfreq(nf, 1 / SR)
    g_db = np.interp(np.log2(np.maximum(f, 1)), np.log2(T_CENT), corr, left=corr[0], right=corr[-1])
    g_db[f > 12000] -= 12
    h = np.fft.irfft(10 ** (g_db / 20), n=nf)
    return np.roll(h, taps // 2)[:taps] * np.hanning(taps)


def render_block(t0, dur, seed, times, fir, ir):
    """t0〜t0+dur 秒。3秒の助走で響きとフィルタを落ち着かせてから切り取る（区間をまたいでも同じ波形）"""
    pre = 3
    s0 = max(0, int(np.floor(t0)) - pre)
    s1 = int(np.ceil(t0 + dur)) + 1
    n = (s1 - s0) * SR
    dry = np.zeros((n, 2))
    for i, te in enumerate(times):
        if te < s0 - 20 or te > s1:
            continue
        for ts, l, r in _events(i, te, seed):
            k = int(round((ts - s0) * SR))
            a, b = max(k, 0), min(n, k + len(l))
            if b > a:
                dry[a:b, 0] += l[a - k:b - k]
                dry[a:b, 1] += r[a - k:b - k]
    x = dry + np.stack([fftconvolve(dry[:, c], ir[:, c])[:n] for c in range(2)], 1)
    d = len(fir) // 2
    x = np.stack([fftconvolve(x[:, c], fir)[d:d + n] for c in range(2)], 1)
    room = room_span(s0, s1 + 1, seed)
    x[:, 0] += room[:n]
    x[:, 1] += room[SR // 3:n + SR // 3]
    a = int(round((t0 - s0) * SR))
    return x[a:a + int(round(dur * SR))]
