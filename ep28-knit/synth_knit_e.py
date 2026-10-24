"""ep28/29「竹の棒針で編み物をする音」試聴版E（10/13 社長「もっと心休まる音に。雑音もブラウンノイズに感じられるように」）。

試聴版D（作り直し）からの変更：
- 針の音をやわらかく、少なく、ゆっくりに：1目 1.1〜1.5秒ごとに 2〜3個（D は 0.76〜0.96秒ごとに 2〜5個）。
  立ち上がり 15〜25ms、高い倍音をさらに下げ、木の胴音（300〜600Hz）だけが「コト」と鳴る。強さのばらつきも小さく。
- 毛糸のこすれの細かい粒は、ほとんど聞こえない大きさまで下げる（ザラザラした粒が雑音に聞こえないように）。
- 下地の雑音は、帯域の広いブラウンノイズ（-6dB/oct）。ただし ep20 で「圧迫感」とされた低音を避けるため、
  100Hz より下をなだらかに切り、2kHz より上もさらに下げる（ゴーではなく、遠くでやわらかく鳴る「サー」の下側）。
  大きさはゆっくり変えない（風の音に聞こえないよう一定）。
- 段の終わりの持ち替え（4〜7秒、針の音なし）は残す。下地があるので無音にはならない。
"""
import numpy as np
from scipy.signal import butter, fftconvolve, sosfilt

SR = 44100
BED_DB = -12.0  # 下地のブラウンノイズの大きさ（針の音の強いところ＝10msごとの上位1%に対するdB）


def _bp(lo, hi, order=2):
    return butter(order, [lo, hi], btype="band", fs=SR, output="sos")


def _lp(f, order=2):
    return butter(order, f, fs=SR, output="sos")


def _hp(f, order=2):
    return butter(order, f, btype="high", fs=SR, output="sos")


def _env(n, att, dec):
    t = np.arange(n) / SR
    up = 0.5 - 0.5 * np.cos(np.pi * np.clip(t / att, 0, 1))
    return up * np.exp(-np.clip(t - att, 0, None) / dec)


def wood(rng):
    """やわらかい木の「コト」（胴音中心、高い音は少しだけ）"""
    n = int(0.12 * SR)
    t = np.arange(n) / SR
    x = np.zeros(n)
    for f, a in [(rng.uniform(300, 420), 1.0), (rng.uniform(480, 620), 0.45), (rng.uniform(220, 280), 0.3)]:
        x += a * np.sin(2 * np.pi * f * t + rng.uniform(0, 6.28))
    x += 0.35 * sosfilt(_bp(800, 1800), rng.normal(0, 1, n))
    x *= _env(n, rng.uniform(0.015, 0.025), rng.uniform(0.008, 0.012))
    x = sosfilt(_lp(2500), x)
    return x / (np.abs(x).max() + 1e-9)


def schedule(dur, seed):
    """出来事 [(秒, 強さdB)]。1目＝2〜3個の「コト」が 0.2〜0.35秒にまとまる。1段 20〜34目のあと持ち替え。"""
    rng = np.random.default_rng(seed)
    ev = []
    t = 1.0
    while t < dur:
        per = rng.uniform(1.15, 1.40)
        for i in range(int(rng.integers(20, 35))):
            k = 2 if rng.random() < 0.6 else 3
            offs = np.sort(rng.uniform(0.0, rng.uniform(0.20, 0.35), k))
            offs[0] = 0
            lv = rng.normal(0, 1.0) - max(0, 2 - i) * 3  # 段の始めは小さく入る
            for j, o in enumerate(offs):
                ev.append((t + o, lv - (0 if j == 0 else rng.uniform(2, 4))))
            t += per * rng.uniform(0.93, 1.07)
            if t >= dur:
                break
        t += rng.uniform(4.0, 7.0)
    return ev


def brown(n, rng):
    """やわらかいブラウンノイズ（-6dB/oct、100Hz より下と 2kHz より上をなだらかに下げる）"""
    w = rng.normal(0, 1, n)
    b = np.cumsum(w)
    b -= np.convolve(b, np.ones(4410) / 4410, mode="same")  # ゆっくりしたずれを除く
    b = sosfilt(_hp(100, 2), b)
    b = sosfilt(_lp(2000, 1), b)
    return b


def render(start, dur, events, seed):
    n = int(dur * SR)
    pad = int(1.0 * SR)
    y = np.zeros(n + 2 * pad)
    for k, (t0, db) in enumerate(events):
        if t0 < start - 1.0 or t0 > start + dur + 0.5:
            continue
        rng = np.random.default_rng((seed, k))
        s = wood(rng) * 10 ** (db / 20)
        i = int((t0 - start) * SR) + pad
        a, b = max(i, 0), min(i + len(s), len(y))
        if b > a:
            y[a:b] += s[a - i : b - i]
    # 小さな部屋の響き（短く、やわらかく）
    rr = np.random.default_rng(seed + 99)
    ir = rr.normal(0, 1, int(0.3 * SR)) * np.exp(-np.arange(int(0.3 * SR)) / (0.06 * SR))
    ir = sosfilt(_lp(1500), ir)
    ir[0] = 0
    y = y + 0.08 * fftconvolve(y, ir / np.abs(ir).max())[: len(y)]
    # 下地：左右で別々のブラウンノイズ（真ん中に固まらず、やわらかく広がる）
    out = []
    for ch in range(2):
        bed = brown(len(y), np.random.default_rng((seed, ch, int(round(start * 10)))))
        bed *= 10 ** ((2.0 + BED_DB) / 20) / (np.std(bed) + 1e-12)  # 針の音（10msごとの上位1%）は約 +2dB
        out.append(y + bed)
    return np.stack(out, 1)[pad : pad + n]
