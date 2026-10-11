"""ep28/29「竹の棒針で編み物をする音」の合成。

実録音（freesound 6本、REFERENCES.md）で分かったこと：
- 手を止めずに編むと、針の打音は 1分に150〜300回、間隔の中央 0.1〜0.25秒、2〜6回ずつのまとまりで出る。
- 木や竹の針（#676397）の打音は 500〜800Hz が最大で、金属針（#505487）は 5kHz 以上が主役（使わない）。
- 毛糸のこすれは 600Hz〜5kHz に平らに広がる。打音とこすれの音量はほぼ同じ。

品質部の条件（ideas i-2026w41-14）に合わせた作り：
- 毛糸がすべる音を主にし、針の音は 3〜6dB 小さく。金属針の明るい音は使わない。
- 一目を「針の打音2つ＋こすれ」のまとまりで扱い、等間隔の列にしない（柱時計の派生に聞こえないように）。
  一目は 0.9〜1.6秒（実録音よりゆっくり）。1段 22〜40目で、段の終わりに 4〜9秒の持ち替え（打音なし、毛糸を引く音と布の音）。
- こすれは帯域を絞った雑音にせず、毛糸の繊維が引っかかる細かい粒の列で作る（風の音にしないため）。
- 4kHz より上はなだらかに下げる（耳鳴りのような音を避ける）。
"""
import numpy as np
from scipy.signal import butter, fftconvolve, sosfilt

SR = 44100
BED = 0.06  # 部屋の空気の大きさ


def _bp(lo, hi, order=2):
    return butter(order, [lo, hi], btype="band", fs=SR, output="sos")


def _lp(f, order=2):
    return butter(order, f, fs=SR, output="sos")


def _hp(f, order=2):
    return butter(order, f, btype="high", fs=SR, output="sos")


def bell(n, rise, fall_start, fall):
    """rise 秒で上がり、fall_start 秒から fall 秒の時定数で下がる山"""
    t = np.arange(n) / SR
    up = 0.5 - 0.5 * np.cos(np.pi * np.clip(t / max(rise, 1e-3), 0, 1))
    down = np.exp(-np.clip(t - fall_start, 0, None) / fall)
    return up * down


def fiber(n, rate, rng):
    """毛糸の繊維が引っかかる細かい粒の列（1粒 0.3〜1.5ms）。rate は1秒あたりの粒の数（配列可）。"""
    p = np.clip(np.broadcast_to(rate, (n,)) / SR, 0, 0.6)
    hit = rng.random(n) < p
    amp = np.exp(rng.normal(0, 0.45, n)) * hit * np.where(rng.random(n) < 0.5, 1, -1)
    # 粒ごとに音色が少しずつ違うよう、4種類の粒の形に振り分ける（決まった色づけで音程感が出ないように）
    m = int(0.0015 * SR)
    out = np.zeros(n)
    which = rng.integers(0, 4, n)
    for j in range(4):
        k = rng.normal(0, 1, m) * np.exp(-np.arange(m) / (rng.uniform(0.0003, 0.0006) * SR))
        out += fftconvolve(amp * (which == j), k)[:n]
    return out


def rub(dur, rng, bright=1.0):
    """毛糸が竹の針の上をすべる音（1回ぶん）"""
    n = int(dur * SR)
    t = np.arange(n) / SR
    # 引く速さで粒の密度が変わる：始めと終わりは少なく、途中が多い
    speed = np.sin(np.pi * np.clip(t / dur, 0, 1)) ** 0.8
    rate = 300 + 2200 * speed * rng.uniform(0.7, 1.2)
    g = fiber(n, rate, rng)
    g = sosfilt(_bp(260 * bright, 2600 * bright, 2), g)
    g += 0.35 * sosfilt(_bp(900 * bright, 4200, 1), fiber(n, rate * 0.6, rng))
    env = bell(n, rng.uniform(0.04, 0.09) * min(1, dur / 0.3), dur * rng.uniform(0.55, 0.75), dur * 0.18)
    return g * env


def tap(rng):
    """竹の針どうしが当たる小さな打音（木の音、余韻 15〜30ms、金属のような響きなし）"""
    n = int(0.09 * SR)
    t = np.arange(n) / SR
    x = np.zeros(n)
    modes = [(rng.uniform(560, 760), rng.uniform(0.018, 0.030), 1.0),
             (rng.uniform(1050, 1400), rng.uniform(0.010, 0.018), 0.55),
             (rng.uniform(1900, 2500), rng.uniform(0.006, 0.010), 0.25),
             (rng.uniform(3000, 3600), rng.uniform(0.003, 0.005), 0.08)]
    for f, d, a in modes:
        x += a * np.sin(2 * np.pi * f * t + rng.uniform(0, 6.28)) * np.exp(-t / d)
    # 竹のこすれ合う短いザラつき
    x += 0.25 * sosfilt(_bp(400, 2500), rng.normal(0, 1, n)) * np.exp(-t / 0.006)
    # やわらかい当たり（立ち上がり 2.5〜4ms）
    att = int(rng.uniform(0.0025, 0.004) * SR)
    x[:att] *= 0.5 - 0.5 * np.cos(np.pi * np.arange(att) / att)
    return x / np.abs(x).max()


def schedule(dur, seed):
    """出来事の一覧 [(開始秒, 種類, 強さdB, 長さ)]。一目ずつ、段の終わりに持ち替え。"""
    rng = np.random.default_rng(seed)
    ev = []
    t = 1.0
    while t < dur:
        stitches = int(rng.integers(22, 41))
        base = rng.uniform(1.05, 1.35)  # この段の一目の長さ
        drift = rng.uniform(-0.15, 0.15)
        for i in range(stitches):
            if t >= dur:
                break
            per = base * (1 + drift * (i / stitches - 0.5)) * rng.uniform(0.88, 1.14)
            # 段の始めの3目は手がなじむまで小さく（持ち替えの静かな間のあとに急に鳴らさない）
            lv = rng.normal(0, 1.0) - max(0, 3 - i) * 2.5
            # ① 右の針を目に入れる：小さな打音
            a = rng.uniform(0.0, 0.05)
            ev.append((t + a, "tap", lv - rng.uniform(3.5, 6.0), 0))
            # ② 毛糸をかけてすべらせる：主役のこすれ
            r0 = t + a + rng.uniform(0.06, 0.14)
            rl = rng.uniform(0.28, 0.50)
            ev.append((r0, "rub", lv + rng.normal(0, 0.8), rl))
            # ③ 引き抜く：2つ目の打音（ときどき省く）と短いこすれ
            b = r0 + rl * rng.uniform(0.75, 1.0)
            if rng.random() < 0.8:
                ev.append((b, "tap", lv - rng.uniform(4.5, 7.5), 0))
            ev.append((b + rng.uniform(0.02, 0.06), "rub", lv - rng.uniform(3, 6), rng.uniform(0.12, 0.22)))
            # ときどき手が止まる・毛糸をたぐる
            if rng.random() < 0.07:
                ev.append((t + per, "pull", lv - rng.uniform(5, 8), rng.uniform(0.5, 0.9)))
                per += rng.uniform(0.7, 1.6)
                ev.append((t + per - 0.6, "cloth", lv - rng.uniform(9, 12), 0.9))
            # ④ 次の目へ移る間も、左手の指から毛糸が少しずつ送られる小さなこすれ（目と目の間を無音にしない）
            f0 = b + 0.12
            ev.append((f0, "feed", lv - rng.uniform(9, 12), max(0.3, t + per - f0 + 0.15)))
            t += per
        # 段の終わり：針を持ち替える（打音なし）。毛糸を引く音と、膝の上の編み地が動く音
        p = t + rng.uniform(0.3, 0.8)
        ev.append((p, "cloth", -rng.uniform(5, 8), rng.uniform(0.9, 1.5)))
        p += rng.uniform(1.2, 2.2)
        ev.append((p, "pull", -rng.uniform(4, 7), rng.uniform(0.7, 1.2)))
        if rng.random() < 0.5:
            p += rng.uniform(1.0, 1.8)
            ev.append((p, "pull", -rng.uniform(6, 9), rng.uniform(0.5, 0.9)))
        # 持ち替えの間も無音にしない：ごく小さな布の音をまばらに
        q = t + 0.2
        while q < p + 1.5:
            ev.append((q, "cloth", -rng.uniform(9, 12), rng.uniform(0.7, 1.2)))
            q += rng.uniform(0.5, 0.9)
        t = p + rng.uniform(1.5, 2.6)
    return ev


def cloth(dur, rng):
    """膝の上の編み地が動く、やわらかく低めのこすれ"""
    n = int(dur * SR)
    g = fiber(n, 900, rng)
    g = sosfilt(_bp(180, 1400, 2), g)
    return g * bell(n, dur * 0.35, dur * 0.5, dur * 0.2)


def room_ir(rng):
    """小さな部屋（木の床・布もの）の短い響き。左右で少し違う。"""
    n = int(0.25 * SR)
    t = np.arange(n) / SR
    out = []
    for _ in range(2):
        r = rng.normal(0, 1, n) * np.exp(-t / 0.045)
        r = sosfilt(_lp(3000), r)
        r[0] = 0
        ir = np.zeros(n)
        ir[0] = 1.0
        ir += 0.10 * r / np.abs(r).max()
        out.append(ir)
    return out


def render(start, dur, events, seed):
    """[start, start+dur) を描く（長い版で区切って書き出せるように、出来事ごとに乱数を固定）"""
    n = int(dur * SR)
    pad = int(2.0 * SR)
    y = np.zeros(n + 2 * pad)
    for k, (t0, kind, db, ln) in enumerate(events):
        if t0 < start - 2.0 or t0 > start + dur + 0.5:
            continue
        rng = np.random.default_rng((seed, k))
        if kind == "tap":
            s = tap(rng) * 1.25
        elif kind == "rub":
            s = rub(ln, rng)
        elif kind == "feed":
            s = rub(ln, rng, bright=0.85) * 0.8
        elif kind == "pull":
            s = rub(ln, rng, bright=0.8) * 0.9
        else:
            s = cloth(ln, rng) * 1.2
        s = s * 10 ** (db / 20)
        i = int((t0 - start) * SR) + pad
        a, b = max(i, 0), min(i + len(s), len(y))
        if b > a:
            y[a:b] += s[a - i : b - i]
    # 部屋の空気：300Hz 以下だけのごく小さな音（高い音を含まず、風のように聞こえない）
    bed = sosfilt(_lp(300, 2), np.random.default_rng((seed, int(start * 10))).normal(0, 1, len(y)))
    y += bed * BED
    # 全体：120Hz 以下と 4kHz より上をなだらかに下げる
    y = sosfilt(_hp(120), y)
    y = 0.55 * y + 0.45 * sosfilt(_lp(3200, 1), y)
    irs = room_ir(np.random.default_rng(seed + 99))
    st = np.stack([fftconvolve(y, ir)[: len(y)] for ir in irs], 1)
    return st[pad : pad + n]
