"""琴に重ねる自然音（水琴窟・囲炉裏）の合成

どちらも freesound の実録音を測定して数値を決めた（音そのものは使っていない）。
- 水琴窟: #259993 Suikinkutsu at Eikan-do Zenrin-ji（CC BY 3.0）
  しずくを1滴ずつ切り出して測定：1分に約47滴、余韻2〜3秒、共鳴は316〜2860Hzの12個（最強1657Hz）。
- 囲炉裏: #645460 wood charcoal slow burning（CC0）、#212179 Kettle Boil（CC0）
  炭火はごく小さな「チッ」という点の音だけ（1秒に約0.8回、帯域は広い）。はぜる音はない。
  沸いた湯は150〜250Hz中心の低いゴボゴボ音になるので使わず、沸く前の小さな泡の音だけを作る。
"""
import numpy as np
from scipy.signal import butter, sosfilt

SR = 44100

# 甕の共鳴：実録音（永観堂）のしずくを1滴ずつ切り出して平均したスペクトルの山。
# 全体を 0.945 倍して、いちばん強い 1657Hz を陽音階の G6 付近に置く（音階に1つずつ合わせることはしない）
POT_MODES = np.array([316, 380, 499, 875, 1012, 1163, 1382, 1507, 1657, 2487, 2717, 2857]) * 0.945
POT_LEVELS_DB = np.array([-8, -7, -8, -9, -8, -7, -5, -6, 0, -8, -9, -8])


def suik_events(total, rng):
    """水琴窟のしずくの時刻と強さ。実録音の測定：しずくは1分に約47滴（間隔の中央値0.72秒、9割が3秒以内）、
    1滴は周りの響きより約12dB大きいだけで、余韻は2〜3秒。小さなしずくが絶えず重なる響きになる。
    実録音では屋外の環境音がしずくの帯域を埋めているが、環境ノイズは風の音になるので使わず、
    代わりにごく小さなしずく（約-12dB）を間に多く入れて埋める。はっきり聞こえるしずくは4割。"""
    ev = []
    t = rng.uniform(0.2, 0.8)
    while t < total - 0.5:
        g = 1.0 if rng.random() < 0.4 else 10 ** (rng.uniform(-15, -9) / 20)
        ev.append((t, g, int(rng.integers(0, BANK_SIZE))))
        t += float(np.clip(rng.lognormal(np.log(0.38), 0.7), 0.08, 2.5))
    return ev


BANK_SIZE = 400
_bank = None


def drop_bank():
    """しずくの音を400通り作り置きする（長い版を速く作るため。強さは毎回ばらつかせる）"""
    global _bank
    if _bank is None:
        r = np.random.default_rng(259993)
        _bank = [_drop(r) for _ in range(BANK_SIZE)]
    return _bank


def suik_block(events, a, b, bed_gain):
    """[a, b) 秒の水琴窟（しずく＋下地の響き）"""
    bank = drop_bank()
    start = max(0.0, a - 5.0)
    n = int((b - start) * SR) + 1
    out = np.zeros(n)
    for t, g, k in events:
        if t < start or t >= b:
            continue
        d = bank[k]
        s = int((t - start) * SR)
        e = min(n, s + len(d))
        out[s:e] += g * d[: e - s]
    i0 = int((a - start) * SR)
    out = out[i0 : i0 + int((b - a) * SR)]
    return out + bed_gain * pot_bed(a, len(out))


def suikinkutsu(total, rng):
    ev = suik_events(total, rng)
    drops = suik_block(ev, 0, total, 0.0)
    band = sosfilt(butter(4, [900, 3500], btype="band", fs=SR, output="sos"), drops)
    bed = pot_bed(0, len(drops))
    return drops + bed * np.sqrt(np.mean(band ** 2)) / np.sqrt(np.mean(bed ** 2)) * 10 ** (-10 / 20)


# 甕がずっと鳴っている下地の響き（実測：約560・620・750・870Hz、1秒に1回ほどゆっくり揺れる、
# しずくの帯域より約10dB小さい）。ノイズは使わず、ゆれる持続音だけで作る（風の音にしない）。
# 区切って計算してもつながるよう、時刻だけで決まる式にする
BED_FREQS = np.array([561, 623, 748, 874]) * 0.945
_br = np.random.default_rng(748)
BED_LFO = [(_br.uniform(0.4, 1.5, 5), _br.uniform(0, 6.28, 5)) for _ in BED_FREQS]
BED_PHASE = _br.uniform(0, 6.28, len(BED_FREQS))


def pot_bed(a, n):
    tt = a + np.arange(n) / SR
    bed = np.zeros(n)
    for f, (rates, phases), ph in zip(BED_FREQS, BED_LFO, BED_PHASE):
        c = sum(np.sin(2 * np.pi * r * tt + p) for r, p in zip(rates, phases)) / np.sqrt(2.5)
        amp = 10 ** (4 * c / 20)  # 標準偏差 約4dB で揺れる
        bed += amp * np.sin(2 * np.pi * f * tt + ph)
    return bed


def _drop(rng):
    dur = 4.0
    tt = np.arange(int(dur * SR)) / SR
    y = np.zeros_like(tt)
    # 1滴ごとの強さのばらつき（標準偏差 約3dB）
    vel = 10 ** (rng.normal(0, 3) / 20)
    for fm, ldb in zip(POT_MODES, POT_LEVELS_DB):
        if rng.random() < 0.55:
            a = 10 ** ((ldb + rng.uniform(-5, 2)) / 20)
            # 余韻は実測 2〜3秒（低い共鳴ほど長い）
            t60 = rng.uniform(0.8, 1.2) * np.interp(fm, [300, 3000], [3.0, 1.8])
            # 高い共鳴ほど立ち上がりをゆっくりにして、急な「ピン」という音にしない
            att = np.interp(fm, [300, 1000, 2700], [0.02, 0.03, 0.06]) * rng.uniform(0.8, 1.3)
            rise = np.clip(tt / att, 0, 1)
            rise = 0.5 - 0.5 * np.cos(np.pi * rise)
            y += a * rise * np.sin(2 * np.pi * fm * (1 + rng.normal(0, 0.002)) * tt + rng.uniform(0, 6.28)) * np.exp(-6.9 * tt / t60)
    # 水面に落ちた瞬間の泡の音はごく弱く
    f = rng.uniform(1300, 2300)
    y += 0.05 * np.sin(2 * np.pi * np.cumsum(f * (1 + 0.12 * np.clip(tt / 0.03, 0, 1))) / SR) * np.exp(-tt / 0.018)
    # 立ち上がり：急に鳴らないよう 20〜35ms のなめらかな曲線
    a = int(rng.uniform(0.02, 0.035) * SR)
    y[:a] *= 0.5 - 0.5 * np.cos(np.pi * np.linspace(0, 1, a))
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
