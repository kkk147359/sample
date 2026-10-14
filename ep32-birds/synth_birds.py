"""ep32/33「小鳥来る、晩秋の朝の庭」の合成。

実録音（freesound の人が録った録音。小鳥の声15本・朝の庭の空気13本。REFERENCES.md）で分かったこと：
- 小鳥の声の中心は 3〜5kHz（企画審査の指摘どおり）。近くで録った声は、声のある時間の 4〜5kHz が 23〜67%、
  ファイル全体の 4〜5kHz の割合（0.1秒ごとの中央）も 7〜31% と大きい。
- ところが、遠くの小鳥（東京の公園・富士山麓の森・高山の寺の録音 #75273 #440604 #842030 #381180）は
  1声 20〜55ms と短く、1分に 10〜50声、鳴っている時間は全体の 0〜3%、2秒以上の休みが 20〜33%。
  背景との差は 10〜18dB。ファイル全体の 4〜5kHz の割合は中央 0.01〜0.65%、90% でも 0.6〜3.1%。
  → 「遠くで、ときどき、短く」鳴かせれば、4〜5kHz が続く耳鳴りにならない。
- 日本の公園・森の小鳥（#381180 #440604 #31947）は声の 53〜72% が 3〜4kHz、4〜5kHz は 4〜8%。
  声の高さは 3〜4kHz を中心に、低めの声（2.1〜2.8kHz、#257442 #75273 #381180）を混ぜる。
- 声の形：チッ（25〜60ms、少し下がる）、ツィー（100〜150ms、1〜1.5kHz 下がる：メジロの録音 #54186 は中央 -1.46kHz）、
  チュン（75〜150ms、3.1〜4.2kHz、ざらつきがあり 300〜500Hz 下がる：スズメ #23892 #383160）、
  低めの声（120ms〜、2.1〜2.7kHz、#257442）。立ち上がりは中央 10〜40ms、一続きの声の間は 0.22〜0.47秒。
- 朝の庭の空気（鳴き声のない間）：1/3オクターブで 1〜4kHz は最大より 6〜19dB 下。録音の多くは 80Hz 以下に
  車や風のゴーが 20〜90% あるが、社長の嫌う「風のような音」「低音の圧迫感」になるので入れない（120Hz より下を切る）。
  0.25秒ごとのゆらぎ 1.1〜2.7dB、5秒ごと 0.3〜2.6dB。小さな物音はほぼない。外の響きは 1.2〜2.0秒。
"""
import numpy as np
from scipy.signal import butter, fftconvolve, sosfilt

SR = 44100
BED_DB = -15.0  # 声の強いところ（10ms）に対する、下地の 1.5〜8kHz の大きさの目安
WET = 0.10  # 庭の響きの混ぜ具合
RT = 1.5  # 響きが 60dB 下がるまでの秒数（実録音 1.2〜2.0秒）


def _lp(f, order=2):
    return butter(order, f, fs=SR, output="sos")


def _hp(f, order=2):
    return butter(order, f, btype="high", fs=SR, output="sos")


def _bp(lo, hi, order=2):
    return butter(order, [lo, hi], btype="band", fs=SR, output="sos")


def _smooth(n, rate, rng):
    k = max(2, int(n / SR * rate) + 2)
    return np.interp(np.linspace(0, k - 1, n), np.arange(k), rng.uniform(-1, 1, k))


def _env(n, rise, rng, decay_shape=1.6):
    """やわらかい立ち上がり（rise 秒）と、なだらかな終わり"""
    t = np.arange(n) / SR
    a = np.clip(t / rise, 0, 1)
    a = 0.5 - 0.5 * np.cos(np.pi * a)
    u = np.clip((t - rise) / max(t[-1] - rise, 1e-3), 0, 1)
    return a * (1 - u) ** decay_shape


def _tone(f, rng, h2=-24.0, h3=-34.0):
    ph = 2 * np.pi * np.cumsum(f) / SR + rng.uniform(0, 6.28)
    return np.sin(ph) + 10 ** (h2 / 20) * np.sin(2 * ph + 1.0) + 10 ** (h3 / 20) * np.sin(3 * ph + 2.0)


def call(kind, f0, rng):
    """1声。f0 はその個体の基本の高さ"""
    if kind == "chip":  # チッ
        d = rng.uniform(0.028, 0.06)
        n = int(d * SR)
        u = np.linspace(0, 1, n)
        f = f0 * (1 + rng.uniform(0.02, 0.05) * (1 - u)) - rng.uniform(150, 350) * u
        x = _tone(f * (1 + 0.004 * _smooth(n, 60, rng)), rng) * _env(n, rng.uniform(0.008, 0.014), rng, 1.3)
    elif kind == "tsii":  # ツィー（下がる細い声）
        d = rng.uniform(0.10, 0.15)
        n = int(d * SR)
        u = np.linspace(0, 1, n)
        drop = rng.uniform(1000, 1400)
        f = f0 + drop * (1 - u) ** 1.4 - drop * 0.15
        x = _tone(f * (1 + 0.006 * _smooth(n, 30, rng)), rng, -28, -40) * _env(n, rng.uniform(0.018, 0.03), rng, 1.2)
    elif kind == "chun":  # チュン（ざらつき・少し上がって下がる）
        d = rng.uniform(0.075, 0.14)
        n = int(d * SR)
        u = np.linspace(0, 1, n)
        f = f0 + 250 * np.sin(np.pi * np.clip(u / 0.35, 0, 1)) * (u < 0.35) - rng.uniform(300, 500) * np.clip((u - 0.3) / 0.7, 0, 1)
        rough = 1 - 0.35 * (0.5 + 0.5 * np.sin(2 * np.pi * rng.uniform(140, 200) * np.arange(n) / SR))
        x = _tone(f, rng, -18, -30) * rough
        br = sosfilt(_bp(f0 - 700, f0 + 500), rng.normal(0, 1, n))
        x = x + 0.12 * br / (np.std(br) + 1e-9)
        x *= _env(n, rng.uniform(0.012, 0.02), rng, 1.5) 
    elif kind == "low":  # 低めの声（ピーッ、ヨ）：遠い
        parts = []
        d1 = rng.uniform(0.16, 0.24)
        n = int(d1 * SR)
        u = np.linspace(0, 1, n)
        f = f0 * (1 + 0.05 * u - 0.03 * u ** 3)
        parts.append(_tone(f * (1 + 0.005 * _smooth(n, 20, rng)), rng, -20, -32) * _env(n, rng.uniform(0.03, 0.045), rng, 1.0))
        parts.append(np.zeros(int(rng.uniform(0.03, 0.06) * SR)))
        d2 = rng.uniform(0.10, 0.15)
        n = int(d2 * SR)
        u = np.linspace(0, 1, n)
        f = f0 * (1.02 - 0.2 * u)
        parts.append(_tone(f, rng, -20, -32) * _env(n, 0.02, rng, 1.4) * 0.8)
        x = np.concatenate(parts)
    return x


# 庭に来ている小鳥（個体）：声の種類、基本の高さ、左右、遠さ(dB)、一続きの声の数、間（秒）、次に鳴くまで（秒）
BIRDS = [
    ("chip", 3500, -0.35, 0.0, (2, 5), (0.25, 0.45), (6, 22)),
    ("chip", 3250, 0.45, -2.0, (1, 3), (0.28, 0.5), (10, 30)),
    ("tsii", 3400, 0.15, 0.0, (1, 3), (0.5, 0.9), (12, 35)),
    ("chun", 3350, -0.6, -1.0, (2, 4), (0.22, 0.4), (14, 40)),
    ("low", 2450, 0.7, -3.0, (1, 2), (2.5, 4.0), (25, 60)),
]


def schedule(dur, seed):
    """[(時刻, 個体番号, 1声ごとの強さdB)]"""
    rng = np.random.default_rng(seed)
    ev = []
    for b, (kind, f0, pan, dist, nrange, gap, wait) in enumerate(BIRDS):
        t = rng.uniform(1, wait[1] * 0.6)
        while t < dur:
            k = rng.integers(nrange[0], nrange[1] + 1)
            for j in range(k):
                ev.append((t, b, rng.uniform(-4, 0)))
                t += rng.uniform(*gap)
            t += rng.uniform(*wait)
    return sorted(ev)


def garden_ir(rng, rt=RT):
    n = int(rt * 1.2 * SR)
    t = np.arange(n) / SR
    out = []
    for _ in range(2):
        r = rng.normal(0, 1, n) * np.exp(-6.9 * t / rt)
        r = 0.6 * sosfilt(_lp(3000), r) + 0.4 * sosfilt(_lp(1200), r)  # 外の響きは高い音ほど早く消える
        r[: int(0.015 * SR)] *= np.linspace(0, 1, int(0.015 * SR))
        out.append(r / np.sqrt((r ** 2).sum()))
    return out


# 朝の庭の空気（1/3オクターブ、最大=0dB）。実録音の鳴き声のない間（#408192 #341388 #249737 #188164 #440604 #842030 #75273）の
# 中ほどに合わせ、120Hz より下（車・風のゴー）は入れない。
AIR_SHAPE = [(60, -50), (100, -30), (125, -16), (160, -8), (200, -4), (250, -2), (315, -1), (400, 0), (500, -1), (630, -3),
             (800, -5), (1000, -6), (1250, -8), (1600, -10), (2000, -12), (2500, -14), (3150, -15), (4000, -17),
             (5000, -20), (6300, -23), (8000, -26), (10000, -31), (14000, -40)]


def garden_air(n, rng):
    w = rng.normal(0, 1, n)
    f = np.fft.rfftfreq(n, 1 / SR)
    fs, db = np.array(AIR_SHAPE, float).T
    g = np.interp(np.log(np.maximum(f, 20)), np.log(fs), db, left=-60, right=-50) - 10 * np.log10(np.maximum(f, 20) / 400)
    b = np.fft.irfft(np.fft.rfft(w) * 10 ** (g / 20), n)
    b /= np.std(b) + 1e-12
    # ごくゆっくりした小さなゆれ（風のうねりにならない程度：±1.5dB 前後。実録音の5秒ごとのゆらぎ 0.3〜2.6dB）
    return b * 10 ** (1.5 * _smooth(n, 0.08, rng) / 20)


def render(start, dur, events, seed):
    n = int(dur * SR)
    pad = int(3.0 * SR)
    L = np.zeros(n + 2 * pad)
    R = np.zeros(n + 2 * pad)
    for k, (t0, b, db) in enumerate(events):
        if t0 < start - 3 or t0 > start + dur + 0.5:
            continue
        kind, f0, pan, dist, *_ = BIRDS[b]
        rng = np.random.default_rng((seed, k))
        s = call(kind, f0 * (1 + rng.uniform(-0.02, 0.02)), rng) * 10 ** ((db + dist) / 20)
        # 遠いほど高い音が少し弱まる
        if dist < -1.5:
            s = 0.6 * s + 0.4 * sosfilt(_lp(2800, 1), s)
        i = int((t0 - start) * SR) + pad
        a, e = max(i, 0), min(i + len(s), len(L))
        if e > a:
            gl, gr = np.sqrt(0.5 * (1 - pan)), np.sqrt(0.5 * (1 + pan))
            L[a:e] += gl * s[a - i: e - i]
            R[a:e] += gr * s[a - i: e - i]
    irs = garden_ir(np.random.default_rng(seed + 7))
    mono = 0.5 * (L + R)
    st = [L + WET * fftconvolve(mono, irs[0])[: len(L)], R + WET * fftconvolve(mono, irs[1])[: len(R)]]
    ref = 0.5  # 1声の強いところの目安
    out = []
    for c in range(2):
        bed = garden_air(len(L), np.random.default_rng((seed, c, int(round(start * 10)))))
        # 下地の 1.5〜8kHz の大きさを基準に合わせる
        hb = np.sqrt(np.mean(sosfilt(_bp(1500, 8000), bed[: 20 * SR]) ** 2))
        bed *= ref * 10 ** (BED_DB / 20) / (hb + 1e-12)
        out.append(st[c] + bed)
    return np.stack(out, 1)[pad: pad + n]
