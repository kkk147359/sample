"""ep28/29「竹の棒針で編み物をする音」試聴版F（10/13 社長：E は「針には聞こえません」）。

E の失敗：針の音を 300〜600Hz の胴音だけ・立ち上がり 15〜25ms にしたため、木の小さな太鼓のような「コト」になり、
細い竹の棒どうしが当たる音の特徴（短く硬い当たりと、細い棒の高めの響き）が消えた。

F の作り（実録音 YouTube 木・竹の針の帯域 300〜1k 0／1〜2k -9.3／2〜4k -7.3／4〜8k -4.9dB に寄せる）：
- 当たり「カチ」：立ち上がり 1.5〜3ms の短い当たりで、細い棒の響き（1.1〜1.6kHz、2.4〜3.4kHz）を 8〜20ms だけ。
  胴の響き（450〜700Hz）を下に少し。4kHz より上は実録音より少し控えめ（眠る用）。
- 針どうしがこすれ合う「スッ」：1目に1回、60〜150ms、細かい粒の列で作る（連続ノイズにしない）。当たりより 8〜12dB 小さい。
- 1目 1.15〜1.4秒ごと（E と同じゆっくり）、1目に 当たり2〜3個＋こすれ1回。段の終わりに 4〜7秒の持ち替え。
- 下地は E と同じブラウンノイズ（100Hz 以下と 2kHz 以上をなだらかに下げ、大きさ一定）。
"""
import numpy as np
from scipy.signal import fftconvolve, sosfilt

from synth_knit_e import SR, _bp, _env, _hp, _lp, brown

BED_DB = -14.0  # 下地のブラウンノイズ（当たりの強いところ＝10msごとの上位1%に対するdB）
SLIDE_DB = -10.0  # こすれ合う音（当たりに対するdB）


def click(rng):
    """細い竹の棒どうしが当たる「カチ」"""
    n = int(0.06 * SR)
    t = np.arange(n) / SR
    x = np.zeros(n)
    for f, d, a in [(rng.uniform(1100, 1600), rng.uniform(0.008, 0.014), 0.45),
                    (rng.uniform(2400, 3400), rng.uniform(0.005, 0.009), 0.7),
                    (rng.uniform(450, 700), rng.uniform(0.012, 0.020), 0.9)]:
        x += a * np.sin(2 * np.pi * f * t + rng.uniform(0, 6.28)) * np.exp(-t / d)
    # 当たった瞬間の短いザラつき（1〜2ms）
    x += 1.2 * sosfilt(_bp(800, 7000), rng.normal(0, 1, n)) * np.exp(-t / 0.0012)
    x += 1.4 * sosfilt(_bp(4000, 7500), rng.normal(0, 1, n)) * np.exp(-t / 0.0025)  # 細い棒の硬さ（4kHz より上は実録音より約10dB控えめ）
    att = int(rng.uniform(0.0015, 0.003) * SR)
    x[:att] *= 0.5 - 0.5 * np.cos(np.pi * np.arange(att) / att)
    x = 0.75 * x + 0.25 * sosfilt(_lp(3500, 1), x)  # 4kHz より上をなだらかに下げる
    return x / (np.abs(x).max() + 1e-9)


def slide(rng):
    """針どうしがこすれ合う「スッ」（細かい粒の列、60〜150ms）"""
    n = int(rng.uniform(0.06, 0.15) * SR)
    hit = rng.random(n) < 3000 / SR
    g = np.exp(rng.normal(0, 0.35, n)) * hit * np.where(rng.random(n) < 0.5, 1, -1)
    g = fftconvolve(g, np.exp(-np.arange(30) / 8))[:n]
    g = sosfilt(_bp(1000, 3500), g)
    g *= np.sin(np.pi * np.arange(n) / n) ** 2
    return g / (np.abs(g).max() + 1e-9)


def schedule(dur, seed):
    """出来事 [(秒, 種類, 強さdB)]"""
    rng = np.random.default_rng(seed)
    ev = []
    t = 1.0
    while t < dur:
        per = rng.uniform(1.15, 1.40)
        for i in range(int(rng.integers(20, 35))):
            lv = rng.normal(0, 1.0) - max(0, 2 - i) * 3  # 段の始めは小さく入る
            ev.append((t, "click", lv))
            s0 = t + rng.uniform(0.06, 0.12)
            ev.append((s0, "slide", lv + SLIDE_DB + rng.normal(0, 1.0)))
            t2 = s0 + rng.uniform(0.10, 0.20)
            ev.append((t2, "click", lv - rng.uniform(2, 4)))
            if rng.random() < 0.4:
                ev.append((t2 + rng.uniform(0.08, 0.15), "click", lv - rng.uniform(5, 8)))
            t += per * rng.uniform(0.93, 1.07)
            if t >= dur:
                break
        t += rng.uniform(4.0, 7.0)
    return ev


def render(start, dur, events, seed):
    n = int(dur * SR)
    pad = int(1.0 * SR)
    y = np.zeros(n + 2 * pad)
    for k, (t0, kind, db) in enumerate(events):
        if t0 < start - 1.0 or t0 > start + dur + 0.5:
            continue
        rng = np.random.default_rng((seed, k))
        s = (click(rng) if kind == "click" else slide(rng)) * 10 ** (db / 20)
        i = int((t0 - start) * SR) + pad
        a, b = max(i, 0), min(i + len(s), len(y))
        if b > a:
            y[a:b] += s[a - i : b - i]
    # 小さな部屋の響き（短く、やわらかく）
    rr = np.random.default_rng(seed + 99)
    ir = rr.normal(0, 1, int(0.3 * SR)) * np.exp(-np.arange(int(0.3 * SR)) / (0.05 * SR))
    ir = sosfilt(_lp(2500), ir)
    ir[0] = 0
    y = y + 0.06 * fftconvolve(y, ir / np.abs(ir).max())[: len(y)]
    y = sosfilt(_hp(150), y)
    ref = 10 ** (-6.0 / 20)  # 当たりの 10ms ごとの上位1% の目安（下地の大きさの基準）
    out = []
    for ch in range(2):
        bed = brown(len(y), np.random.default_rng((seed, ch, int(round(start * 10)))))
        bed *= ref * 10 ** (BED_DB / 20) / (np.std(bed) + 1e-12)
        out.append(y + bed)
    return np.stack(out, 1)[pad : pad + n]
