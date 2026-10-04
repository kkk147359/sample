"""秋の夜の虫の声（ピアノなし）の合成。実録音の測定（REFERENCES.md、tools/insects.py）に合わせた点：
- 日本の秋の夜の録音（#365257 柏、#42211 中野）は、何種類もの虫が重なった「合唱」。
  強い声は 1.9〜2.7kHz、3.3〜4.4kHz、10〜13kHz あたり。声は1秒に5〜30回の細かい「脈」の連なりで、
  鳴く・休むの周期は 0.4〜1.5秒（短く鳴く虫）と 3〜10秒（長く鳴き続ける虫）。
- 合唱になっている録音は急な音が少ない（上位1% 4〜5dB）。1匹だけが近くで鳴く録音は 19〜28dB と急な音が多い。
  眠るための音なので、近くの1匹が目立ちすぎないよう「少し離れたところの合唱」にする。
- 10kHz を超える高い声は耳につきやすいので、いちばん高い声も 7kHz 前後までにし、全体に高い音を少し下げる。
- 下地として、夜の空気のごく小さなサー音（150Hz より下は切る）を入れる。

声の種類（鳴き方の型）は実在の種の名前をうたわず、測った値の範囲から作る。
render_block(t0, dur, seed, voices) で区間ごとに書き出せる（各虫の鳴く時刻は全体で先に決めるので継ぎ目なし）。
"""
import numpy as np
from scipy.signal import butter, fftconvolve, sosfilt

SR = 44100

# 鳴き方の型：声の高さ(Hz)、脈の速さ(回/秒)、1回の鳴き(秒)、鳴く間隔(秒)、脈の中で音が出ている割合
TYPES = {
    # 短く「リッ、リッ」と鳴く（実録音 3.8〜4.4kHz、脈 15〜24回/秒、周期 0.7〜0.8秒）
    "short": {"f": (3800, 4500), "rate": (15, 24), "len": (0.12, 0.3), "gap": (0.6, 1.0), "duty": 0.55},
    # 「リーー」と長めに震わせる（実録音 2.3〜2.7kHz、脈 28回/秒、数秒続いて休む）
    "trill": {"f": (2300, 2800), "rate": (25, 30), "len": (1.5, 4.0), "gap": (3.0, 8.0), "duty": 0.6},
    # 鈴を振るように「リーン」と短く澄んだ声（4.5〜5kHz、脈が速く、ほとんど続いて聞こえる）
    "bell": {"f": (4500, 5000), "rate": (40, 60), "len": (0.4, 0.8), "gap": (1.0, 2.2), "duty": 0.75},
    # 遠くの高い声の合唱（実録音では 10〜13kHz だが、耳につかないよう 6〜7kHz に下げる）
    "high": {"f": (6000, 7000), "rate": (8, 12), "len": (2.0, 6.0), "gap": (4.0, 10.0), "duty": 0.5},
}
# 何匹いるか（近い・遠い）。遠いほど小さく、高い音が減り、響きが多い
POP = [("short", 5), ("trill", 3), ("bell", 6), ("high", 6)]


# 型ごとの音量の補正（「リーン」と澄んだ声を主役に、低めの長い声は控えめに）
LEVEL_ADJ = {"short": 0.0, "trill": -5.0, "bell": 1.0, "high": -3.0}


def make_voices(seed):
    r = np.random.default_rng([seed, 1])
    v = []
    for kind, n in POP:
        tp = TYPES[kind]
        for i in range(n):
            dist = r.uniform(0.3, 1.0)  # 1 が遠い
            v.append({"kind": kind, "f": r.uniform(*tp["f"]), "rate": r.uniform(*tp["rate"]),
                      "level": -6 - 14 * dist + r.normal(0, 1.5) + LEVEL_ADJ[kind], "dist": dist, "pan": r.uniform(-0.8, 0.8),
                      "seed": int(r.integers(1 << 30))})
    return v


def events(voice, total):
    """この虫が鳴く時刻と長さ。ときどき長く休む（実録音でも声が増えたり減ったりする）"""
    tp = TYPES[voice["kind"]]
    r = np.random.default_rng([voice["seed"], 2])
    t, ev = r.uniform(0, 5), []
    on = True
    while t < total:
        if r.random() < 0.01:
            on = not on  # 数十秒〜数分単位で鳴いたり休んだり
        L = r.uniform(*tp["len"])
        if on:
            ev.append((t, L, r.normal(0, 1.0), voice["f"] * (1 + r.normal(0, 0.004))))
        t += L + r.uniform(*tp["gap"])
    return ev


def _chirp(voice, L, f, t):
    """1回の鳴き：脈（細かい音の粒）の連なり。t はその鳴きの始まりからの時刻の配列"""
    tp = TYPES[voice["kind"]]
    ph = (t * voice["rate"]) % 1.0
    duty = tp["duty"]
    pulse = np.where(ph < duty, np.sin(np.pi * ph / duty) ** 2, 0.0)
    edge = np.clip(t / 0.03, 0, 1) * np.clip((L - t) / 0.05, 0, 1)  # 鳴き始めと終わりをなめらかに
    return pulse * edge


def reverb_ir(seed=23, seconds=1.2, t60=0.8):
    r = np.random.default_rng(seed)
    n = int(seconds * SR)
    t = np.arange(n) / SR
    lp = butter(2, 5000, fs=SR, output="sos")
    ir = np.zeros((n, 2))
    for c in range(2):
        ir[:, c] = sosfilt(lp, r.normal(0, 1, n)) * np.exp(-6.91 * t / t60)
        ir[: int(0.01 * SR), c] = 0
        ir[:, c] /= np.sqrt((ir[:, c] ** 2).sum())
    return ir


def _air(t0, n, seed):
    """夜の空気のごく小さなサー音（150Hz〜3kHz、高い音は下げる）。区間の境目でも続くよう絶対時刻で乱数を決める"""
    blk = 1 << 16
    s0 = int(round(t0 * SR))
    i0, i1 = s0 // blk, (s0 + n) // blk + 1
    x = np.concatenate([np.random.default_rng([seed, 9, i + 8]).normal(0, 1, (blk, 2)) for i in range(i0 - 1, i1 + 1)])
    sos = butter(2, [150, 3000], btype="band", fs=SR, output="sos")
    y = sosfilt(sos, x, axis=0)
    off = s0 - (i0 - 1) * blk
    return y[off : off + n]


AIR_DB = -20.0


def render_block(t0, dur, seed, voices, evs, ir):
    pad = 1.5
    start = t0 - pad
    n = int(round((dur + pad) * SR))
    near = np.zeros((n, 2))
    far = np.zeros((n, 2))
    lp = {}
    for v, ev in zip(voices, evs):
        g = 10 ** (v["level"] / 20)
        pl, pr = np.sqrt(0.5 * (1 - v["pan"])), np.sqrt(0.5 * (1 + v["pan"]))
        buf = np.zeros(n)
        for te, L, db, f in ev:
            if te + L < start or te > t0 + dur:
                continue
            a = max(te, start)
            b = min(te + L, t0 + dur)
            ia, ib = int(round((a - start) * SR)), int(round((b - start) * SR))
            if ib <= ia:
                continue
            t = start + np.arange(ia, ib) / SR  # 絶対時刻
            env = _chirp(v, L, f, t - te)
            # 実際の虫の脈は1粒ごとに高さがわずかに下がる（純音の「ピー」に聞こえないように）。
            # 鳴きの始まりからの位相を式で出すので、区間の境目でも途切れない
            tau = t - te
            rt = tau * v["rate"]
            saw_int = (np.floor(rt) * 0.5 + (rt % 1.0) ** 2 / 2) / v["rate"]
            phase = 2 * np.pi * f * (tau - 0.015 * saw_int)
            car = np.sin(phase) + 0.08 * np.sin(2 * phase)
            buf[ia:ib] += env * car * 10 ** (db / 20)
        # 遠い虫ほど高い音が減る
        fc = 9000 - 5000 * v["dist"]
        key = round(fc, -2)
        if key not in lp:
            lp[key] = butter(2, key, fs=SR, output="sos")
        buf = sosfilt(lp[key], buf) * g
        w = v["dist"]
        near[:, 0] += (1 - 0.5 * w) * pl * buf
        near[:, 1] += (1 - 0.5 * w) * pr * buf
        far[:, 0] += w * pl * buf
        far[:, 1] += w * pr * buf
    wet = np.stack([fftconvolve(far[:, c] + 0.2 * near[:, c], ir[:, c])[:n] for c in range(2)], axis=1)
    y = near + 0.9 * wet
    y = y + _air(start, n, seed) * 10 ** (AIR_DB / 20)
    return y[int(pad * SR):]
