"""ep30/31「晩秋の夜、遠くの森で鳴くフクロウ」の合成。

実録音（Wikimedia Commons にある xeno-canto の Ural owl＝日本のフクロウと同じ種、スロバキア。REFERENCES.md）で分かったこと：
- オスの「ホー」は基本 330〜350Hz（別の個体 300〜320Hz、380〜410Hz）。音の終わりで 3〜6% 下がる。
- 倍音はとても小さい（2〜4倍音が基本より 16〜31dB 下）。倍音のあいだの息の音は 25〜40dB 下。ほぼ純音。
- 1音は 70〜290ms。立ち上がり 40〜200ms（やわらかい）、-20dB まで 30〜110ms。長い音は途中で一度少しへこむ（2つの山）。
- さえずり：長めの「ホー」1つ → 3.5〜4.5秒あけて → 3〜4音（長・短・短〜長、音の切れ目 0.15〜0.4秒）。
- 巣の近くの呼び声：80〜120ms の音を 0.2秒ごとに 4〜6回。
- メスの「ギャッ」（基本 1.2kHz、倍音が強い）と警戒の声（760Hz、2倍音が強い）は使わない。

笛に聞こえないための作り（審査の注意「純音のホーは笛やオカリナになりやすい」）：
- 長く伸ばさない（実録音どおり最長 0.3秒）。笛の吹き始めの息の「フッ」は入れない。
- 音程を固定しない：入りは 2〜4% 低く、終わりで 3〜6% 下がる。1音ごとに数Hzずれ、ゆっくり細かく揺れる。
- 喉で鳴る声らしく、ごく小さなざらつき（速い揺れ）と、基本のまわりだけの小さな息の音を足す。
- 遠くの森：2kHz より上をなだらかに下げ、森の残響（約1.2秒、こもった音、声より約9dB小さい）を多めに混ぜる。
下地の夜の空気：左右別々のやわらかい雑音（150Hz より下を切り、900Hz より上は下げる）。大きさは一定（風に聞こえないよう揺らさない）。
"""
import numpy as np
from scipy.signal import butter, fftconvolve, sosfilt

SR = 44100
BED_DB = -16.0  # 下地（200Hz〜6kHz の平均）に対し、フクロウの声の強いところとの差の目安
WET = 0.07  # 森の残響の混ぜ具合（声が終わって 50ms 後 -11〜-15dB、200ms 後 -13〜-19dB。実録音 -8〜-17／-14〜-15dB）
RT = 2.6  # 森の残響が 60dB 下がるまでの秒数（実録音の遠くのフクロウ 2.5〜3.0秒、#825822）


def _bp(lo, hi, order=2):
    return butter(order, [lo, hi], btype="band", fs=SR, output="sos")


def _lp(f, order=2):
    return butter(order, f, fs=SR, output="sos")


def _hp(f, order=2):
    return butter(order, f, btype="high", fs=SR, output="sos")


def _smooth_noise(n, rate, rng):
    """rate Hz くらいでゆっくり動く -1〜1 のゆらぎ"""
    k = max(2, int(n / SR * rate) + 2)
    pts = rng.uniform(-1, 1, k)
    return np.interp(np.linspace(0, k - 1, n), np.arange(k), pts)


def hoot(rng, dur, f0, twin=False):
    """フクロウのオスの「ホー」1音"""
    n = int(dur * SR)
    t = np.arange(n) / SR
    u = t / dur
    # 音程：入りは少し低く、すぐ本来の高さへ、終わりで下がる。ゆっくり細かく揺れる
    lo_in = rng.uniform(0.02, 0.04)
    fall = rng.uniform(0.03, 0.06)
    shape = 1 - lo_in * np.exp(-u / 0.12) - fall * np.clip((u - 0.6) / 0.4, 0, 1) ** 1.5
    wob = 0.006 * _smooth_noise(n, 9, rng)
    f = f0 * shape * (1 + wob)
    ph = 2 * np.pi * np.cumsum(f) / SR + rng.uniform(0, 6.28)
    x = np.sin(ph)
    for k, db in [(2, rng.uniform(-22, -17)), (3, rng.uniform(-24, -19)), (4, rng.uniform(-27, -22))]:
        x += 10 ** (db / 20) * np.sin(k * ph + rng.uniform(0, 6.28))
    # 喉のざらつき（速い小さな揺れ）
    x *= 1 + 0.06 * sosfilt(_bp(25, 60), rng.normal(0, 1, n)) / 0.25
    # 基本のまわりだけの小さな息の音（-28dB 前後）
    br = sosfilt(_bp(f0 * 0.7, f0 * 1.6), rng.normal(0, 1, n))
    x += 10 ** (rng.uniform(-30, -26) / 20) * br / (np.std(br) + 1e-9) * 0.7
    # 大きさ：やわらかく入り、やわらかく消える。長い音は途中で一度へこむ
    att = min(dur * 0.45, rng.uniform(0.05, 0.12))
    rel = min(dur * 0.4, rng.uniform(0.05, 0.10))
    env = np.minimum(1, np.minimum(t / att, (dur - t) / rel)).clip(0, 1)
    env = np.sin(0.5 * np.pi * env) ** 2
    if twin:
        env *= 1 - rng.uniform(0.35, 0.55) * np.exp(-((u - rng.uniform(0.45, 0.6)) / 0.1) ** 2)
    return x * env


def schedule(dur, seed):
    """出来事 [(秒, 種類, 個体, 強さdB)]。40〜120秒に1回ほど鳴く。ときどき続けてもう一度、ときどき遠くの別の個体が応える。"""
    rng = np.random.default_rng(seed)
    ev = []
    t = rng.uniform(12, 25)
    while t < dur - 10:
        kind = rng.choice(["song", "song", "song", "half", "intro", "nest"], p=[0.25, 0.2, 0.15, 0.2, 0.1, 0.1])
        lv = rng.normal(0, 1.5)
        ev.append((t, str(kind), 0, lv))
        if rng.random() < 0.3:  # 少しあけてもう一度（実録音のまとまりの間隔 4〜6秒の倍くらい）
            ev.append((t + rng.uniform(8, 16), str(rng.choice(["song", "half"])), 0, lv - rng.uniform(0, 2)))
        if rng.random() < 0.2:  # 遠くの別の個体が応える
            ev.append((t + rng.uniform(10, 25), str(rng.choice(["song", "half", "intro"])), 1, lv - rng.uniform(6, 9)))
        t += float(np.exp(rng.uniform(np.log(40), np.log(120))))
    return sorted(ev)


VOICE = [(330, 352), (298, 318)]  # 個体ごとの基本の高さ


def phrase(kind, who, rng):
    """1回の鳴き声を [(秒, 長さ, 基本Hz, 2つ山, 強さdB)] で"""
    f0 = rng.uniform(*VOICE[who])
    notes = []
    t = 0.0
    if kind in ("song", "intro"):
        notes.append((0.0, rng.uniform(0.22, 0.29), f0 * rng.uniform(1.0, 1.02), True, 0.0))
        t = rng.uniform(3.5, 4.5)
    if kind in ("song", "half"):
        seq = [(rng.uniform(0.15, 0.22), True, 0.0), (rng.uniform(0.08, 0.12), False, -2.0), (rng.uniform(0.09, 0.13), False, -1.5)]
        if rng.random() < 0.6:
            seq.append((rng.uniform(0.15, 0.23), True, -1.0))
        for d, tw, db in seq:
            notes.append((t, d, f0 * rng.uniform(0.985, 1.015), tw, db + rng.normal(0, 0.8)))
            t += d + rng.uniform(0.15, 0.40)
    if kind == "nest":
        for i in range(int(rng.integers(4, 7))):
            notes.append((t, rng.uniform(0.08, 0.12), f0 * 0.97 * rng.uniform(0.99, 1.01), False, -3.0 - 0.5 * i + rng.normal(0, 0.6)))
            t += rng.uniform(0.19, 0.22)
    return notes


def forest_ir(rng, rt=RT):
    """遠くの森の残響（こもった、左右で違う）"""
    n = int(rt * 1.3 * SR)
    t = np.arange(n) / SR
    out = []
    for _ in range(2):
        r = rng.normal(0, 1, n) * np.exp(-6.9 * t / rt)
        r = 0.6 * sosfilt(_lp(1200), r) + 0.4 * sosfilt(_lp(500), r)
        r[: int(0.02 * SR)] *= np.linspace(0, 1, int(0.02 * SR))
        out.append(r / np.sqrt((r ** 2).sum()))
    return out


# 間の空気の音の高さの配分（1/3オクターブ、最大=0dB）。実録音の静かな夜の森（freesound #367964）に合わせ、
# 4kHz より上だけは少し控えめにする（サーという音にしない）。
AIR_SHAPE = [(60, -36), (100, -24), (125, -20), (160, -18), (200, -13), (250, -5), (315, -2), (400, 0), (500, -4),
             (630, -6), (800, -7), (1000, -7), (1250, -9), (1600, -11), (2000, -13), (2500, -15), (3150, -17),
             (4000, -20), (5000, -25), (6300, -29), (8000, -33), (12000, -40)]


def night_air(n, rng):
    """夜の空気：AIR_SHAPE の配分のやわらかい雑音。大きさは一定（風に聞こえないよう揺らさない）。"""
    w = rng.normal(0, 1, n)
    W = np.fft.rfft(w)
    f = np.fft.rfftfreq(n, 1 / SR)
    fs, db = np.array(AIR_SHAPE, float).T
    # 1/3オクターブの帯域あたりの値なので、周波数ごとの強さに直す（帯域幅は周波数に比例 → -10log10(f)）
    g_db = np.interp(np.log(np.maximum(f, 20)), np.log(fs), db, left=-60, right=-50) - 10 * np.log10(np.maximum(f, 20) / 400)
    b = np.fft.irfft(W * 10 ** (g_db / 20), n)
    return b / (np.std(b) + 1e-12)


def _band_rms(x):
    return np.sqrt(np.mean(sosfilt(_bp(200, 6000), x) ** 2) + 1e-20)


def render(start, dur, events, seed):
    n = int(dur * SR)
    pad = int(3.0 * SR)
    y = np.zeros(n + 2 * pad)
    pans = []
    for k, (t0, kind, who, db) in enumerate(events):
        if t0 < start - 12 or t0 > start + dur + 0.5:
            continue
        rng = np.random.default_rng((seed, k))
        for (o, d, f0, tw, ndb) in phrase(kind, who, rng):
            s = hoot(rng, d, f0, tw) * 10 ** ((db + ndb) / 20)
            i = int((t0 + o - start) * SR) + pad
            a, b = max(i, 0), min(i + len(s), len(y))
            if b > a:
                y[a:b] += s[a - i: b - i]
    # 遠くの音：2kHz より上をなだらかに下げる
    y = 0.5 * y + 0.5 * sosfilt(_lp(1800, 1), y)
    irs = forest_ir(np.random.default_rng(seed + 7))
    dry = [y * 0.93, y * 0.88]  # 少しだけ左寄り
    st = np.stack([dry[c] + WET * fftconvolve(y, irs[c])[: len(y)] for c in range(2)], 1)
    # 下地の大きさは「声の強いところ」基準で決める（声 1 の 10ms 上位の目安を 0.5 とする）
    ref = 0.5 * 0.7
    out = []
    for c in range(2):
        bed = night_air(len(y), np.random.default_rng((seed, c, int(round(start * 10)))))
        bed *= ref * 10 ** (BED_DB / 20)
        out.append(st[:, c] + bed)
    return np.stack(out, 1)[pad: pad + n]
