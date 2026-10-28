"""夜行列車の車内走行音。実録音（REFERENCES.md）の測定に合わせる：
- 走行音（ゴー）：連続したノイズ。山は125〜250Hz、500Hzで-10dB前後、2kHz以上は-20dB以下。
  帯域ごとのゆらぎは実録音で1〜3dB（0.5秒平均の標準偏差）。ゆっくり波打つ周期的なゆらぎは入れない。
- 継ぎ目（タタン）：300Hz〜3kHzで周囲より+5〜8dB。25mレール×時速60km＝1.5秒ごとに、
  自分の車両の前台車（2軸、軸距2.1m＝0.126秒差）と後台車（13.8m後＝0.83秒後、少し小さい）。
- 空気の音（風に聞こえる）は入れない。70Hz以下は切る。
"""
import numpy as np

SR = 44100
SPEED = 60 / 3.6       # m/s
RAIL = 25.0            # レール1本の長さ（m）
AXLE = 2.1             # 台車の軸距（m）
BOGIE = 13.8           # 台車中心間（m）

# 走行音の目標（1/3オクターブ、最大0dB）。日本の在来線4本（r00 r01 r08 r09）の中央値を基に、
# 100Hz以下は圧迫感を避けて下げ、2kHz以上は4〜5kHzの耳鳴り対策で実録音よりやや下げる。
RUMBLE = {31.5: -60, 40: -50, 50: -40, 63: -26, 80: -16, 100: -10, 125: -5, 160: -2, 200: -2,
          250: 0, 315: -3, 400: -6, 500: -7, 630: -10, 800: -12, 1000: -14, 1250: -18,
          1600: -21, 2000: -24, 2500: -27, 3150: -30, 4000: -34, 5000: -40, 6300: -46,
          8000: -52, 10000: -60, 16000: -80}


def shaped_noise(n, rng, curve):
    """白色ノイズを周波数領域で目標の配分に整形する。"""
    f = np.fft.rfftfreq(n, 1 / SR)
    fc = np.array(sorted(curve))
    g = np.array([curve[c] for c in fc])
    gain_db = np.interp(np.log10(np.maximum(f, 20)), np.log10(fc), g)
    # 1/3オクターブの帯域内エネルギーで指定するので、周波数あたりの密度へ直す（帯域幅∝f）
    gain_db -= 10 * np.log10(np.maximum(f, 20) / 1000)
    X = np.fft.rfft(rng.standard_normal(n)) * 10 ** (gain_db / 20)
    X[f < 55] = 0
    return np.fft.irfft(X, n)


def slow_gain(n, rng, sd_db, tau):
    """ランダムで周期のない音量変化（線路の状態で少し変わる程度）。"""
    k = int(n / (SR * tau)) + 3
    pts = rng.normal(0, sd_db, k)
    pts = np.convolve(pts, np.ones(3) / 3, mode="same")
    t = np.linspace(0, k - 1, n)
    return 10 ** (np.interp(t, np.arange(k), pts) / 20)


def band(x, lo, hi):
    f = np.fft.rfftfreq(len(x), 1 / SR)
    X = np.fft.rfft(x)
    X[(f < lo) | (f >= hi)] = 0
    return np.fft.irfft(X, len(x))


def soft_band(x, lo, hi):
    """なだらかな帯域通過（境目で急に切れないよう、帯域外は1オクターブあたり-12dB）。"""
    f = np.maximum(np.fft.rfftfreq(len(x), 1 / SR), 1)
    g = 1 / (1 + (lo / f) ** 2) / (1 + (f / hi) ** 2)
    return np.fft.irfft(np.fft.rfft(x) * g, len(x))


def rumble(dur, rng, gseed=None):
    n = int(dur * SR)
    out = np.zeros((n, 2))
    for ch in range(2):
        r = rng if ch == 0 else np.random.default_rng(rng.integers(1 << 30))
        x = shaped_noise(n, r, RUMBLE)
        lo, mid, hi = band(x, 0, 200), band(x, 200, 1000), band(x, 1000, SR / 2)
        # 帯域ごとに別のランダムな変化（実録音のゆらぎ1〜3dB）。左右は共通成分を多くして揺れを感じさせない
        g = (11, 12, 13) if gseed is None else (gseed * 10 + 1, gseed * 10 + 2, gseed * 10 + 3)
        out[:, ch] = lo * slow_gain(n, np.random.default_rng(g[0]), 1.2, 1.7) \
            + mid * slow_gain(n, np.random.default_rng(g[1] + ch * (1 if gseed is None else 100000)), 2.0, 0.9) \
            + hi * slow_gain(n, np.random.default_rng(g[2]), 1.4, 1.1)
    return out


def clack(rng, level=1.0):
    """継ぎ目を車輪が越える1打：短い衝撃＋車体の響き（200Hz〜1.5kHz、80〜150Hzの鈍い成分）。"""
    n = int(0.25 * SR)
    t = np.arange(n) / SR
    att = 1 - np.exp(-t / 0.004)              # 立ち上がり約8〜10ms（鋭すぎない）
    burst = rng.standard_normal(n) * att * np.exp(-t / 0.035)
    body = soft_band(burst, 300, 2000)
    thump = np.zeros(n)
    for f0, a, d in ((95 + rng.normal(0, 5), 0.9, 0.06), (180 + rng.normal(0, 8), 0.5, 0.05),
                     (420 + rng.normal(0, 15), 0.35, 0.035), (760 + rng.normal(0, 25), 0.2, 0.03)):
        thump += a * np.sin(2 * np.pi * f0 * t + rng.uniform(0, 6.28)) * att * np.exp(-t / d)
    y = body * 0.8 + thump * 0.25
    return y / (np.abs(y).max() + 1e-9) * level


def joint_times(dur, rng):
    """(時刻, 大きさ) の一覧。速度は±2%程度でゆっくり変わる。時々継ぎ目の目立たない所がある。"""
    ev = []
    pos = rng.uniform(0, RAIL)  # 最初の継ぎ目までの距離
    t = pos / SPEED
    while t < dur + 1:
        v = SPEED * (1 + 0.02 * np.sin(2 * np.pi * t / 47 + 1.3) + rng.normal(0, 0.004))
        strength = 10 ** (rng.normal(0, 1.8) / 20)
        if rng.random() < 0.12:
            strength *= 0.35      # 継ぎ目の段差が小さい所
        a = AXLE / v
        b = BOGIE / v
        ev += [(t, strength), (t + a, strength * 0.88),
               (t + b, strength * 0.62), (t + b + a, strength * 0.55)]
        t += RAIL / v * (1 + rng.normal(0, 0.006))
    return [(x, s) for x, s in ev if x < dur]


def render(dur, seed, clack_db=-2.0):
    rng = np.random.default_rng(seed)
    x = rumble(dur, rng)
    x /= np.sqrt((x ** 2).mean())
    n = len(x)
    c = np.zeros((n, 2))
    for t0, s in joint_times(dur, rng):
        y = clack(rng, s)
        i = int(t0 * SR)
        m = min(len(y), n - i)
        pan = rng.normal(0, 0.08)
        c[i:i + m, 0] += y[:m] * (1 - pan)
        c[i:i + m, 1] += y[:m] * (1 + pan)
    c *= 10 ** (clack_db / 20) / 0.25
    return x + c
