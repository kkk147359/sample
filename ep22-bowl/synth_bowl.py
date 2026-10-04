"""シンギングボウルの余韻（フェルトのばちで打つ）の合成。
実録音の測定（REFERENCES.md）に合わせた点：
- 倍音の比は基音を1として約 2.8・5.4・8.6・12.3（ボウルの振動の形で決まる。整数倍ではない）。
- どの倍音も2つの近い周波数の組（わずかにゆがんだ円形のため）で、そのずれがうなりになる。
  うなりの速さは実録音で 0.2〜7Hz。低い倍音ほどゆっくりに設定（基音 0.3〜0.6Hz）。
- 減衰（T60）：基音 14〜75秒、2倍音 24〜80秒、上の倍音ほど短く、3kHz以上は2〜5秒。
- 打つ間隔（鳴らし始めどうし）は実録音で約10秒。ここでは 8〜13秒で、無音は出ない。
企画の条件：基音 180〜260Hz、3kHz以上を切る、効能はうたわない。
フェルトのばちなので、立ち上がりは数ms〜十数msとやわらかく、高い倍音は弱め。

render_block(t0, dur, cfg, ev) で区間ごとに書き出せる（打音ごとに乱数を固定）。
"""
import numpy as np
from scipy.signal import fftconvolve, butter, sosfilt

SR = 44100
TAIL = 100.0  # 1打を計算する長さ（秒）。最後の10秒でなめらかに消す

# ボウル：基音、倍音の比、各倍音の強さ(dB)、T60(秒)、うなり(Hz)の範囲
# 10/4 社長「なんか不安になる音」→ v2：短3度（196/233Hz）をやめて完全4度（196/261.3Hz）、うなりを遅く（0.15〜2Hz）。
# 10/4 社長「他のボウルの音と比べて」→ v3（REFERENCES.md の「v2と実録音の比較」）：
# - 実録音（#518705 基音162Hz、#723722）は上の倍音がずっと強く、長く残る。v2 は2倍音 -7dB・3倍音 -28dB・4倍音 -43dB で
#   T60 も 3倍音12秒・4倍音6秒と短く、打ったあとは低い「うなり声」だけが残る、こもった暗い音になっていた。
#   実録音の値（2倍音 -2dB、3倍音 -16dB、4倍音 -26dB、5倍音 -23〜-28dB／T60 基音84〜91秒、2倍音64秒、3倍音38秒、4倍音21秒、5倍音13〜15秒）に寄せた。
# - 瞑想向けの録音 #723722 はうなりが 0.2〜0.7Hz とゆっくりで深さ4〜10dB。v2 の遅いうなりのまま、少しだけ深くした。
BOWLS = [
    {"f0": 196.0, "ratio": [1, 2.81, 5.38, 8.62, 12.3], "db": [0, -3, -15, -25, -29], "t60": [80, 60, 35, 20, 14],
     "beat": [(0.15, 0.25), (0.3, 0.5), (0.4, 0.7), (0.5, 0.9), (0.6, 1.0)]},
    {"f0": 261.3, "ratio": [1, 2.83, 5.45, 8.70, 12.5], "db": [0, -4, -16, -26, -30], "t60": [70, 52, 30, 17, 12],
     "beat": [(0.18, 0.3), (0.3, 0.55), (0.45, 0.75), (0.5, 0.9), (0.6, 1.0)]},
]


def schedule(total, seed):
    """打つ時刻・どのボウルか・強さ(dB)"""
    rng = np.random.default_rng(seed)
    t, ev = 1.0, []
    prev = 0
    while t < total:
        b = prev if rng.random() < 0.65 else 1 - prev  # 同じボウルが続くことが多い
        ev.append((t, b, float(np.clip(rng.normal(0, 1.2), -3, 2))))
        prev = b
        t += rng.uniform(8.0, 13.0)
    return ev


def strike_segment(bowl, seed, level_db, a, b):
    """1打の a〜b 秒（打った時刻を0とする）の部分だけを計算する（ステレオ）"""
    rng = np.random.default_rng(seed)
    n = int(round((b - a) * SR))
    t = a + np.arange(n) / SR
    out = np.zeros((n, 2))
    # フェルトのばち：立ち上がり 6〜14ms。高い倍音ほど立ち上がりが短く、弱く鳴る
    rise = rng.uniform(0.006, 0.014)
    tune = 1 + rng.normal(0, 0.0007)  # 同じボウルでもごくわずかに高さが揺れる（温度・打つ場所）
    for k, (r, db, t60, (blo, bhi)) in enumerate(zip(bowl["ratio"], bowl["db"], bowl["t60"], bowl["beat"])):
        f = bowl["f0"] * r * tune
        if f > 2900:
            continue  # 3kHz以上は使わない
        amp = 10 ** ((db + rng.normal(0, 1.5)) / 20)
        t60k = t60 * np.exp(rng.normal(0, 0.08))
        beat = rng.uniform(blo, bhi)
        mix = rng.uniform(0.6, 0.95)  # 組の2つ目の強さ
        att = 1 - np.exp(-np.maximum(t, 0) / (rise / (1 + 0.4 * k)))
        dec = np.exp(-6.91 * np.maximum(t, 0) / t60k) * (t >= 0) * np.clip((TAIL - t) / 10, 0, 1)
        for c in range(2):
            ph1, ph2 = rng.uniform(0, 2 * np.pi, 2)
            pan = 1 + (0.06 if c == 0 else -0.06) * (k % 2 * 2 - 1)
            s = np.sin(2 * np.pi * (f - beat / 2) * t + ph1) + mix * np.sin(2 * np.pi * (f + beat / 2) * t + ph2)
            out[:, c] += pan * amp * att * dec * s
    # ばちが当たる柔らかい音（ごく小さく、低め）
    if a < 0.08:
        m = int(0.08 * SR)
        th = rng.normal(0, 1, m) * np.exp(-np.arange(m) / SR / 0.012)
        th = sosfilt(butter(2, 900, fs=SR, output="sos"), th) * 0.02
        i0 = int(round(-a * SR)) if a < 0 else 0
        j0 = int(round(a * SR)) if a > 0 else 0
        L = min(m - j0, n - i0)
        if L > 0:
            out[i0 : i0 + L] += th[j0 : j0 + L, None]
    return out * 10 ** (level_db / 20)


def reverb_ir(seed=22, seconds=2.5, t60=1.6):
    rng = np.random.default_rng(seed)
    n = int(seconds * SR)
    t = np.arange(n) / SR
    lp = butter(2, 2200, fs=SR, output="sos")
    ir = np.zeros((n, 2))
    for c in range(2):
        ir[:, c] = sosfilt(lp, rng.normal(0, 1, n)) * np.exp(-6.91 * t / t60)
        ir[: int(0.012 * SR), c] = 0
        ir[:, c] /= np.sqrt((ir[:, c] ** 2).sum())
    return ir


def render_block(t0, dur, cfg, ev, ir):
    pad = 3.0
    start = t0 - pad
    n = int(round((dur + pad) * SR))
    buf = np.zeros((n, 2))
    for i, (te, b, lv) in enumerate(ev):
        if te > t0 + dur or te + TAIL < start:
            continue
        a = start - te if start > te else 0.0
        bb = min(t0 + dur - te, TAIL)
        if bb <= a:
            continue
        seg = strike_segment(BOWLS[b], cfg["seed"] * 100003 + i, lv, a, bb)
        s = int(round((te + a - start) * SR))
        L = min(len(seg), n - s)
        buf[s : s + L] += seg[:L]
    wet = np.stack([fftconvolve(buf[:, c], ir[:, c])[:n] for c in range(2)], axis=1)
    y = buf + 0.35 * wet
    return y[int(pad * SR) :]
