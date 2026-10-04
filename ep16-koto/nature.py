"""琴に重ねる自然音（水琴窟・囲炉裏）の合成

どちらも freesound の実録音を測定して数値を決めた（音そのものは使っていない）。
- 水琴窟: #259993 Suikinkutsu at Eikan-do Zenrin-ji（CC BY 3.0）
  しずくは 1.0〜3.2kHz の決まった共鳴（強いのは 1507Hz・1658Hz）で鳴り、0.3〜0.5秒で消える。
  700Hz付近に甕の低い響きがある。
- 囲炉裏: #645460 wood charcoal slow burning（CC0）、#212179 Kettle Boil（CC0）
  炭火はごく小さな「チッ」という点の音だけ（1秒に約0.8回、帯域は広い）。はぜる音はない。
  沸いた湯は150〜250Hz中心の低いゴボゴボ音になるので使わず、沸く前の小さな泡の音だけを作る。
"""
import numpy as np
from scipy.signal import butter, sosfilt

SR = 44100

# 甕の共鳴（実測のピークを 0.945 倍して、いちばん強い 1658Hz を平調子の G6 付近に置く）
POT_MODES = np.array([1012, 1163, 1378, 1507, 1658, 1960, 2390, 2498, 2842, 3230]) * 0.945
POT_LEVELS_DB = np.array([-10, -9, -10, -6, -4, -12, -10, -10, -11, -12])


def suikinkutsu(total, rng, mean_gap=11.0):
    """水琴窟。しずくは数滴のかたまりで、かたまりの間隔は平均 mean_gap 秒。"""
    n = int(total * SR)
    out = np.zeros(n)
    t = rng.uniform(2, 6)
    while t < total - 2:
        for _ in range(rng.choice([1, 1, 2, 3])):
            drop = _drop(rng)
            s = int(t * SR)
            e = min(n, s + len(drop))
            out[s:e] += drop[: e - s]
            t += rng.uniform(0.25, 1.2)  # かたまりの中の間隔（実測の中央値 0.82秒）
        t += rng.exponential(mean_gap - 4) + 4
    return out


def _drop(rng):
    dur = 1.6
    tt = np.arange(int(dur * SR)) / SR
    y = np.zeros_like(tt)
    vel = rng.uniform(0.5, 1.0)
    # しずくが水面に落ちた瞬間の泡の音（周波数がわずかに上がる短い音）
    f = rng.uniform(1300, 2300)
    glide = f * (1 + 0.12 * np.clip(tt / 0.03, 0, 1))
    y += 0.5 * np.sin(2 * np.pi * np.cumsum(glide) / SR) * np.exp(-tt / 0.018)
    # 甕の共鳴：毎回いくつかの共鳴がランダムな強さで鳴る。余韻は1.5秒以内
    for fm, ldb in zip(POT_MODES, POT_LEVELS_DB):
        if rng.random() < 0.6:
            a = 10 ** ((ldb + rng.uniform(-6, 3)) / 20)
            t60 = rng.uniform(0.5, 1.1) * np.interp(fm, [900, 3100], [1.2, 0.7])
            y += a * np.sin(2 * np.pi * fm * (1 + rng.normal(0, 0.002)) * tt + rng.uniform(0, 6.28)) * np.exp(-6.9 * tt / t60)
    # 甕の低い響き（約700Hz）を少しだけ
    y += 0.12 * np.sin(2 * np.pi * rng.uniform(660, 740) * tt) * np.exp(-6.9 * tt / 0.9)
    a = int(0.002 * SR)
    y[:a] *= np.linspace(0, 1, a)
    return vel * y / (np.max(np.abs(y)) + 1e-9)


def irori(total, rng):
    """囲炉裏：鉄瓶の沸く前の小さな泡（チリチリ）と、炭のかすかな「チッ」。帯域の広い連続ノイズは使わない。"""
    n = int(total * SR)
    out = np.zeros(n)
    # 鉄瓶の小さな泡：細かい泡の点の音。密度は数十秒かけてゆっくり上下する（1秒に4〜14個）
    t = 0.5
    while t < total - 0.5:
        density = 9 + 5 * np.sin(2 * np.pi * t / 37 + 1.3) + 1.5 * np.sin(2 * np.pi * t / 11)
        t += rng.exponential(1 / max(density, 2))
        b = _bubble(rng)
        s = int(t * SR)
        e = min(n, s + len(b))
        out[s:e] += b[: e - s] * rng.uniform(0.3, 1.0)
    # 鉄瓶の胴の響き：泡の音を鉄の胴の共鳴に軽く通す（実測の 775Hz・1055Hz 付近）
    body = np.zeros(n)
    for lo, hi, g in [(720, 830, 0.5), (990, 1120, 0.35)]:
        body += g * sosfilt(butter(2, [lo, hi], btype="band", fs=SR, output="sos"), out)
    out = out + body
    # 炭の「チッ」：1秒に約0.8回のごく短い点の音。4〜5kHzが目立たないよう4kHzで丸める
    charcoal = np.zeros(n)
    t = 0.3
    while t < total - 0.1:
        t += rng.exponential(1 / 0.8)
        s = int(t * SR)
        k = int(rng.uniform(0.001, 0.004) * SR)
        if s + k < n:
            charcoal[s : s + k] += rng.standard_normal(k) * np.exp(-np.arange(k) / (k / 3)) * rng.uniform(0.2, 1.0)
    charcoal = sosfilt(butter(2, [1500, 4000], btype="band", fs=SR, output="sos"), charcoal)
    return out / (np.max(np.abs(out)) + 1e-9) + 0.35 * charcoal / (np.max(np.abs(charcoal)) + 1e-9)


def _bubble(rng):
    # 小さな泡ほど高い（Minnaert）。沸く前の泡は小さいので 1.5〜3.2kHz、とても短い
    f = rng.uniform(1500, 3200)
    d = rng.uniform(0.004, 0.012)
    tt = np.arange(int(d * 4 * SR)) / SR
    glide = f * (1 + 0.08 * tt / tt[-1])
    y = np.sin(2 * np.pi * np.cumsum(glide) / SR) * np.exp(-tt / d)
    a = int(0.0008 * SR)
    y[:a] *= np.linspace(0, 1, a)
    # 4〜5kHzが続かないよう、高い泡は弱くする
    return y * np.interp(f, [1500, 2500, 3200], [1.0, 0.7, 0.4])
