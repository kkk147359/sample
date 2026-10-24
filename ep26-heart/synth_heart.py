"""ゆっくりした静かな心音（10/10 臨時会議 案C）。
実録音3本（freesound #535478 胸にマイク、#108841 61bpm、#185067 聴診器）の測定に合わせる（REFERENCES.md）：
- 1拍は「ドッ（S1）」と「クン（S2）」。S1→S2 は約0.33秒、1音は約100ms、立ち上がり約25ms。
- S2 は S1 より 2〜5dB 小さく、少しだけ高い。S1 は 20〜35ms ずれた2つの山からなる。
- 1/3オクターブ配分：63〜80Hz が最大、125Hz -5dB、200Hz -17dB、315Hz -25dB、500Hz -37dB、それより上は急に下がる。
- キックドラムのような音（正弦波の減衰）にしないため、1音は低域に絞った雑音の短い山で作る。
- 血流の「ザー」（聴診器の雑音）は入れない（風の音になるため）。40Hz より下は切る。
- 拍の合間が完全な無音にならないよう、体の中のごく小さな低い音（200Hz以下、拍の山より約50dB小さい）だけ置く。
- 間隔は1分約60回。呼吸に合わせたゆるいゆらぎ（±3%、約4.5秒周期）と小さな乱れ（±1%）、強さは1拍ごとに±1〜2dB。
"""
import numpy as np
from scipy.signal import butter, sosfilt, fftconvolve

SR = 44100
CENT = np.array([31.5, 40, 50, 63, 80, 100, 125, 160, 200, 250, 315, 400, 500, 630, 800, 1000, 1250, 1600, 2000])
# 実録音3本の平均に近い目標（dB、最大0）
T_DB = np.array([-12, -9, -5, 0, 0, -3, -5, -11, -16, -18, -22, -28, -34, -42, -49, -55, -60, -63, -66], float)
SHIFT = 1.0  # 音の高さ。1.0＝実録音どおり。10/10 社長「もう少しだけ音を高く」→ 1.4（半オクターブ）・2.0（1オクターブ）を試作


def target():
    """目標の配分を SHIFT 倍の高さへずらしたもの（CENT の各点の値）"""
    return np.interp(np.log2(CENT), np.log2(CENT * SHIFT), T_DB, left=-14, right=-70)


def _sos(kind, f, order=2):
    return butter(order, f, btype=kind, fs=SR, output="sos")


def schedule(total, seed, bpm=60.0):
    """各拍の S1 の時刻と強さ（dB）"""
    rng = np.random.default_rng(seed)
    t, out = 1.0, []
    ph = rng.uniform(0, 6.28)
    resp = rng.uniform(4.0, 5.0)
    drift_bpm = bpm
    while t < total - 1.5:
        drift_bpm += rng.normal(0, 0.15)
        drift_bpm += (bpm - drift_bpm) * 0.02
        per = 60.0 / drift_bpm * (1 + 0.03 * np.sin(2 * np.pi * t / resp + ph)) * (1 + rng.normal(0, 0.01))
        out.append((t, float(np.clip(rng.normal(0, 0.7), -1.5, 1.5)), per))
        t += per
    return out


def burst(rng, dur, rise, lp, hp=40):
    n = int(dur * SR)
    tt = np.arange(n) / SR
    w = sosfilt(_sos("low", lp, 4), sosfilt(_sos("high", hp, 2), rng.normal(0, 1, n + 2048)))[2048:]
    env = np.where(tt < rise, 0.5 - 0.5 * np.cos(np.pi * tt / rise), np.exp(-(tt - rise) / (dur * 0.22)))
    return w * env


def beat(rng, per):
    """1拍（S1＋S2）。長さ約 0.6 秒"""
    n = int(0.75 * SR)
    y = np.zeros(n)
    # S1：2つの山（20〜35ms ずれ）
    a = burst(rng, rng.uniform(0.09, 0.12), rng.uniform(0.024, 0.034), rng.uniform(140, 180) * SHIFT)
    b = burst(rng, rng.uniform(0.07, 0.10), rng.uniform(0.015, 0.025), rng.uniform(150, 200) * SHIFT) * 10 ** (rng.uniform(-4, -1) / 20)
    y[:len(a)] += a
    k = int(rng.uniform(0.020, 0.035) * SR)
    y[k:k + len(b)] += b
    # S2：S1 から約0.33秒（間隔に合わせて少し変わる）、2〜5dB 小さく少し高い
    k2 = int((0.33 * (per / 1.0) ** 0.5 + rng.normal(0, 0.005)) * SR)
    c = burst(rng, rng.uniform(0.07, 0.09), rng.uniform(0.012, 0.02), rng.uniform(190, 240) * SHIFT, hp=50) * 10 ** (rng.uniform(-3.5, -0.5) / 20)
    y[k2:k2 + len(c)] += c
    return y


def calibrate(seed=5, dur=60):
    sch = schedule(dur, seed)
    x = np.zeros(int(dur * SR))
    for i, (t, g, per) in enumerate(sch):
        y = beat(np.random.default_rng([seed, i]), per)
        k = int(t * SR)
        x[k:k + len(y)] += y[:len(x) - k]
    f = np.fft.rfftfreq(len(x), 1 / SR)
    P = np.abs(np.fft.rfft(x)) ** 2
    have = np.array([P[(f >= c / 2 ** (1 / 6)) & (f < c * 2 ** (1 / 6))].sum() for c in CENT])
    have = 10 * np.log10(have / have.max() + 1e-12)
    return np.clip(target() - have, -15, 12)


def eq_fir(corr, taps=8193):
    nf = 1 << 17
    f = np.fft.rfftfreq(nf, 1 / SR)
    g = np.interp(np.log2(np.maximum(f, 1)), np.log2(CENT), corr, left=corr[0], right=corr[-1])
    g[f < 35] -= 24
    h = np.fft.irfft(10 ** (g / 20), n=nf)
    return np.roll(h, taps // 2)[:taps] * np.hanning(taps)


def body_ir(rng):
    """体を通した短いこもった響き（約80ms）"""
    n = int(0.12 * SR)
    t = np.arange(n) / SR
    ir = sosfilt(_sos("low", 250), rng.normal(0, 1, n)) * np.exp(-t / 0.025)
    ir /= np.sqrt((ir ** 2).sum())
    ir[0] += 3.0
    return ir / np.abs(ir).max()


FLOOR = 0.0166  # 拍の合間の小さな音（拍の山より約50dB小さい）


def floor_span(s0, n, seed):
    """1秒ごとに乱数を固定した、200Hz以下のごく小さな音（どこから作っても同じ波形）"""
    k0 = int(np.floor(s0))
    secs = int(np.ceil(s0 + n / SR)) - k0 + 2
    w = np.concatenate([np.random.default_rng([seed, 999, k0 + i]).normal(0, 1, SR) for i in range(secs)])
    y = sosfilt(_sos("low", 200, 4), sosfilt(_sos("high", 45, 2), w))
    a = int(round((s0 - k0) * SR))
    return y[a:a + n]


def render_block(t0, dur, seed, sch, fir, ir):
    pre = 2.0
    s0 = max(0.0, t0 - pre)
    n = int(round((t0 + dur - s0 + 1) * SR))
    x = np.zeros(n)
    for i, (t, g, per) in enumerate(sch):
        if t < s0 - 1 or t > t0 + dur + 1:
            continue
        y = beat(np.random.default_rng([seed, i]), per) * 10 ** (g / 20)
        k = int(round((t - s0) * SR))
        a, b = max(k, 0), min(n, k + len(y))
        if b > a:
            x[a:b] += y[a - k:b - k]
    x = fftconvolve(x, ir)[:n]
    d = len(fir) // 2
    x = fftconvolve(x, fir)[d:d + n]
    x += floor_span(s0, n, seed) * FLOOR
    a = int(round((t0 - s0) * SR))
    m = x[a:a + int(round(dur * SR))]
    return np.stack([m, m], 1)
