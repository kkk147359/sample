"""ep28/29「竹の棒針で編み物をする音」試聴版D の作り（10/13 社長「最新の試聴版で」）。

試聴版D は別の作業環境（社長PCのChromeで YouTube の実録音を測った会話）で作られ、音源ファイルと
スクリプトはこのリポジトリに届いていない。ここでは社内ボード log「2026-10-12-knit-trialC／D／youtube-measure」
に記録された測定値と作りどおりに組み直す。

実録音（YouTube、木・竹の針 e6v4X7IFcnk・qDQmd9L67Fw）の1音：
- 立ち上がり 10〜13ms（突然のパチではない）、-20dB まで 10〜13ms、長さ 30〜40ms
- 一番強い周波数 約350Hz（木の胴音）。帯域の割合 300〜1kHz 0、1〜2kHz -9.3、2〜4kHz -7.3、4〜8kHz -4.9dB
- 2〜3個ずつ 140〜250ms のまとまりで鳴り、まとまりは 0.74〜0.85秒ごと（1目のリズム）
- 1秒以上の無音なし。粒の高さは背景より中央 12.7〜14.4dB
試聴版D の記録値：立ち上がり12〜13ms、減衰14〜17ms、一番強い周波数420Hz、帯域 0／-8.2／-5.6／-9.4dB、
まとまり3.5〜4個・間隔760〜960ms、約300回/分、背景との差 中央12.2dB、1秒以上の無音0回、-28.4LUFS。
試聴版C から引き継ぐもの：木の当たり音60%＋毛糸の短いこすれ40%（どちらも粒で作り、連続ノイズなし）、
その下にごく小さな粒（毎秒約35個、-14dB）と 300Hz 以下の部屋の空気。
"""
import numpy as np
from scipy.signal import butter, fftconvolve, sosfilt

SR = 44100
HI = (2.6, 1.4, 0.6)  # 当たり音の 1〜2k／2〜4k／4〜7kHz の混ぜ具合
GRAIN = -24  # 小さな粒の大きさ（当たり音に対するdB）
AIR = 0.3  # 部屋の空気の大きさ


def _bp(lo, hi, order=2):
    return butter(order, [lo, hi], btype="band", fs=SR, output="sos")


def _lp(f, order=2):
    return butter(order, f, fs=SR, output="sos")


def _hp(f, order=2):
    return butter(order, f, btype="high", fs=SR, output="sos")


def _env(n, att, dec):
    """立ち上がり att 秒（なめらか）→ 時定数 dec 秒で減衰"""
    t = np.arange(n) / SR
    up = 0.5 - 0.5 * np.cos(np.pi * np.clip(t / att, 0, 1))
    return up * np.exp(-np.clip(t - att, 0, None) / dec)


def wood(rng):
    """木・竹の針の当たり音（胴音 260〜800Hz が主、上の帯域は少しだけ）"""
    n = int(0.08 * SR)
    t = np.arange(n) / SR
    att = rng.uniform(0.008, 0.017)
    dec = rng.uniform(0.0045, 0.0065)  # -20dB まで約 10〜15ms
    x = np.zeros(n)
    for f, a in [(rng.uniform(330, 470), 1.0), (rng.uniform(560, 800), 0.55), (rng.uniform(260, 320), 0.35)]:
        x += a * np.sin(2 * np.pi * f * t + rng.uniform(0, 6.28))
    hi = rng.normal(0, 1, n)
    x += HI[0] * sosfilt(_bp(1000, 2000), hi) + HI[1] * sosfilt(_bp(2000, 4000), hi) + HI[2] * sosfilt(_bp(4000, 7000), hi)
    x *= _env(n, att, dec)
    return x / (np.abs(x).max() + 1e-9)


def yarn(rng):
    """毛糸の短いこすれ（細かい粒の列を短い山の形に、20〜50ms）"""
    n = int(rng.uniform(0.02, 0.05) * SR)
    hit = rng.random(n) < 2500 / SR
    g = np.exp(rng.normal(0, 0.4, n)) * hit * np.where(rng.random(n) < 0.5, 1, -1)
    g = fftconvolve(g, np.exp(-np.arange(40) / 12))[:n]
    g = sosfilt(_bp(500, 3500), g)
    g *= np.sin(np.pi * np.arange(n) / n) ** 1.5
    return g / (np.abs(g).max() + 1e-9)


def schedule(dur, seed):
    """出来事 [(秒, 種類, 強さdB)]。1目＝2〜5個の音が 140〜250ms にまとまり、目は 0.76〜0.96秒ごと。"""
    rng = np.random.default_rng(seed)
    ev = []
    t = 0.5
    per = rng.uniform(0.80, 0.92)
    while t < dur:
        per = np.clip(per + rng.normal(0, 0.02), 0.76, 0.96)  # 速さはゆっくり変わる
        k = int(rng.choice([2, 3, 4, 4, 5], p=[0.1, 0.3, 0.25, 0.2, 0.15]))
        span = rng.uniform(0.18, 0.32)
        offs = np.sort(rng.uniform(0, span, k))
        offs[0] = 0
        lv = rng.normal(0, 1.5)
        for o in offs:
            kind = "wood" if rng.random() < 0.6 else "yarn"
            ev.append((t + o, kind, lv + rng.normal(0, 1.2) - (0 if kind == "wood" else 2.0)))
        t += per * rng.uniform(0.94, 1.06)
    return ev


def render(start, dur, events, seed):
    """[start, start+dur) を描く（長い版で区切って書き出せるよう、出来事ごとに乱数を固定）"""
    n = int(dur * SR)
    pad = int(1.0 * SR)
    y = np.zeros(n + 2 * pad)
    for k, (t0, kind, db) in enumerate(events):
        if t0 < start - 1.0 or t0 > start + dur + 0.5:
            continue
        rng = np.random.default_rng((seed, k))
        s = (wood(rng) if kind == "wood" else yarn(rng) * 0.8) * 10 ** (db / 20)
        i = int((t0 - start) * SR) + pad
        a, b = max(i, 0), min(i + len(s), len(y))
        if b > a:
            y[a:b] += s[a - i : b - i]
    brng = np.random.default_rng((seed, 7, int(round(start * 10))))
    # ごく小さな粒（毎秒約35個、当たり音より約14dB小さい、木のこすれの短い音）
    m = len(y)
    for p in np.where(brng.random(m) < 35 / SR)[0]:
        s = yarn(brng) * 10 ** ((GRAIN + brng.normal(0, 3)) / 20)
        e = min(m, p + len(s))
        y[p:e] += s[: e - p]
    # 300Hz 以下の部屋の空気（高い音を含まない。粒との差が実録音の 12〜14dB 前後になる大きさ）
    y += sosfilt(_lp(300, 2), brng.normal(0, 1, m)) * AIR
    y = sosfilt(_hp(60), y)
    l = y
    r = np.concatenate([np.zeros(18), y[:-18]]) * 0.97 + 0.03 * y  # ほんの少し左右に広がり
    return np.stack([l, r], 1)[pad : pad + n]
