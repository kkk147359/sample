"""ep18/19「古い柱時計の振り子の音」の合成。
実録音の測定（REFERENCES.md）に合わせた打音：
- チクとタクで間隔が違う（例 0.57秒／0.63秒）。間隔のゆらぎは数ms。
- 1打は「主な打音」＋8〜30msあとの小さな追い打ち（がんぎ車の歯が爪に当たり直す音）でできている。
- 金属の部品の響き（600Hz〜2.7kHz、30〜60msで減衰）と、木の箱の響き（100〜600Hz、少し長め）。
- 平均の音量の形：最大から 20ms で約-10dB、55ms で約-20dB、120ms で約-30dB。
- チクとタクで音色と強さが少し違う（2〜3dB）。1打ごとに音量±1.5dB、響きの高さ・強さ・減衰を少しずつ変える（同じ打音のコピーにしない）。
- 3.5kHzより上はなだらかに下げる（耳鳴り感の対策、企画の条件）。部屋の空気音（ノイズ）は入れない。響きは静かな和室程度の短い残響だけ。

render_block(t0, dur, cfg) で区間ごとに書き出せる。打音ごとに乱数を固定しているので、区切りをまたいでも同じ波形になる。
"""
import numpy as np
from scipy.signal import butter, sosfilt, fftconvolve

SR = 44100

# 速さ：A＝柱時計（1分に約100打）、B＝ゆっくり（大きな振り子、1分に約60打）
SPEEDS = {"A": (0.57, 0.63), "B": (0.97, 1.03)}

# 金属の部品の響き（Hz, 減衰の時定数 s, 相対の強さ dB）：チク用・タク用で少しずつ違う
METAL = {
    0: [(640, 0.0208, -2), (820, 0.0176, 0), (1010, 0.0144, -5), (1230, 0.0144, -3), (1660, 0.012, -4), (2150, 0.0096, -7),
        (2680, 0.0072, -9), (3240, 0.0056, -6), (3950, 0.004, -11), (4720, 0.0032, -16)],
    1: [(610, 0.0216, 0), (790, 0.0184, -3), (960, 0.0152, -5), (1180, 0.0144, -2), (1730, 0.0112, -6), (2050, 0.0096, -8),
        (2610, 0.0072, -10), (3150, 0.0056, -7), (3830, 0.004, -12), (4600, 0.0032, -17)],
}
# 木の箱の響き（チク・タク共通、箱は同じ）
WOOD = [(104, 0.060, -15), (162, 0.052, -13), (221, 0.046, -10), (340, 0.038, -12), (470, 0.032, -10), (585, 0.028, -11)]


def schedule(total, speed, seed):
    """打音の時刻と、チク(0)／タク(1)の区別。ゆっくりした振れ幅の変化で間隔がごくわずかに動く"""
    a, b = SPEEDS[speed]
    rng = np.random.default_rng(seed)
    n = max(int(total / ((a + b) / 2)) + 4, 400)
    slow = np.cumsum(rng.normal(0, 1, n))
    slow = (slow - np.convolve(slow, np.ones(301) / 301, "same")) / 40  # 数分単位のごく小さな揺れ
    t, ts, kind = 0.3, [], []
    for i in range(n):
        ts.append(t)
        kind.append(i % 2)
        base = a if i % 2 == 0 else b
        t += base * (1 + 0.0015 * np.tanh(slow[i])) + rng.normal(0, 0.0008)
        if t > total + 1:
            break
    return np.array(ts), np.array(kind)


def _modes(t, modes, rng, spread):
    out = np.zeros_like(t)
    for f, tau, db in modes:
        f = f * (1 + rng.normal(0, spread))
        tau = tau * np.exp(rng.normal(0, 0.12))
        amp = 10 ** ((db + rng.normal(0, 1.5)) / 20)
        out += amp * np.exp(-t / tau) * np.sin(2 * np.pi * f * t + rng.uniform(0, 2 * np.pi))
    return out


def one_hit(kind, seed, level_db):
    """1打（約0.4秒）。主な打音＋追い打ち2〜3個"""
    rng = np.random.default_rng(seed)
    n = int(0.40 * SR)
    out = np.zeros(n)
    t = np.arange(n) / SR
    subs = [(0.0, 0.0, 1.0)]
    # 追い打ち：がんぎ車が止まる音（8〜14ms・-8dB前後）と、跳ね返り（20〜32ms・-14dB前後）
    subs.append((rng.uniform(0.008, 0.014), float(np.clip(rng.normal(-8, 1), -11, -5)), 0.7))
    subs.append((rng.uniform(0.020, 0.032), rng.normal(-14, 2), 0.5))
    if rng.random() < 0.5:
        subs.append((rng.uniform(0.004, 0.006), rng.normal(-12, 2), 0.6))
    for dt, db, wood_mix in subs:
        s = int(dt * SR)
        tt = t[: n - s]
        x = _modes(tt, METAL[kind], rng, 0.006) + wood_mix * _modes(tt, WOOD, rng, 0.004)
        # 打った瞬間のごく短いこすれ（1〜2ms）
        burst = rng.normal(0, 1, len(tt)) * np.exp(-tt / rng.uniform(0.0006, 0.0012)) * 0.35
        x = x + burst
        # 立ち上がりを約0.8msなめらかに（パチッという鋭さを抑える）
        x *= 1 - np.exp(-tt / 0.0008)
        out[s:] += 10 ** (db / 20) * x
    out *= 10 ** (level_db / 20)
    return out


def reverb_ir(seed=7, seconds=0.5, t60=0.32):
    """静かな和室程度の短い残響（左右で別）"""
    rng = np.random.default_rng(seed)
    n = int(seconds * SR)
    t = np.arange(n) / SR
    ir = np.zeros((n, 2))
    lp = butter(2, 2500, fs=SR, output="sos")
    for c in range(2):
        ir[:, c] = sosfilt(lp, rng.normal(0, 1, n)) * np.exp(-6.9 * t / t60)
        ir[: int(0.006 * SR), c] = 0  # 最初の反射まで6ms
        ir[:, c] /= np.sqrt((ir[:, c] ** 2).sum())
    return ir


TONE = None


def tone_filter():
    """3.5kHzより上をなだらかに（1オクターブ6dB）下げ、60Hz以下を切る"""
    global TONE
    if TONE is None:
        TONE = (butter(1, 3500, fs=SR, output="sos"), butter(2, 60, btype="high", fs=SR, output="sos"))
    return TONE


def render_block(t0, dur, cfg, ts, kinds, ir):
    """t0秒からdur秒ぶんのステレオ（float, -1〜1想定の前の生の値）。前後0.5秒の打音も含めて計算する"""
    pad = 1.0
    n = int(dur * SR)
    buf = np.zeros(int((dur + pad * 2) * SR))
    start = t0 - pad
    sel = np.where((ts > start - 0.45) & (ts < t0 + dur + pad))[0]
    for i in sel:
        k = kinds[i]
        rng = np.random.default_rng(cfg["seed"] * 100003 + i)
        lvl = (0 if k == 0 else -2.5) + rng.normal(0, 0.8)
        lvl = float(np.clip(lvl, -4.5, 1.0))
        h = one_hit(k, cfg["seed"] * 7919 + i, lvl)
        s = int(round((ts[i] - start) * SR))
        a, b = max(s, 0), min(s + len(h), len(buf))
        if b > a:
            buf[a:b] += h[a - s : b - s]
    lp, hp = tone_filter()
    # フィルタを区切りに依存させないため、前に余白をとって計算し、余白を捨てる
    dry = sosfilt(hp, sosfilt(lp, buf))
    wet = np.stack([fftconvolve(dry, ir[:, c])[: len(dry)] for c in range(2)], axis=1)
    # 時計は部屋の中央より少し左。左右で響きの強さをわずかに変える
    st = np.stack([dry * 1.0, dry * 0.86], axis=1) + 0.30 * wet
    a = int(pad * SR)
    return st[a : a + n]
