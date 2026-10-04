"""ep18/19「古い柱時計の振り子の音」の合成。
実録音の測定（REFERENCES.md）に合わせた打音：
- チクとタクで間隔が違う（例 0.57秒／0.63秒）。間隔のゆらぎは数ms。
- 1打は「主な打音」＋8〜30msあとの小さな追い打ち（がんぎ車の歯が爪に当たり直す音）でできている。
- 金属の部品の響き（600Hz〜2.7kHz、30〜60msで減衰）と、木の箱の響き（100〜600Hz、少し長め）。
- 平均の音量の形：最大から 20ms で約-10dB、55ms で約-20dB、120ms で約-30dB。
- チクとタクで音色と強さが少し違う（2〜3dB）。1打ごとに音量±1.5dB、響きの高さ・強さ・減衰を少しずつ変える（同じ打音のコピーにしない）。
- 3.5kHzより上はなだらかに下げる（耳鳴り感の対策、企画の条件）。部屋の空気音（ノイズ）は入れない。響きは静かな和室程度の短い残響だけ。

render_block(t0, dur, cfg) で区間ごとに書き出せる。打音ごとに乱数を固定しているので、区切りをまたいでも同じ波形になる。
"""
import numpy as np
from scipy.signal import butter, sosfilt, fftconvolve

SR = 44100

# 速さ：A＝柱時計（1分に約100打）、B＝ゆっくり（大きな振り子、1分に約60打）
SPEEDS = {"A": (0.57, 0.63), "B": (0.97, 1.03)}

# v2（10/4 社長「時計の音とはかけ離れている」を受けて作り直し）
# v1 は減衰する正弦波（響きの山）だけで作ったため、音が「ピッ」という音程のある音になっていた。
# 実録音の打音は、1打の中に細かいカチカチ（0.1〜0.3msの鋭い音）が数ms のあいだに何度も続く、雑音に近い音
# （20msのスペクトル平坦度：実録音 0.04〜0.26、v1 0.001）。
# v2 は「細かいカチカチの列」×「雑音でできた短い響き（帯域ごとに減衰の速さが違う）」で作り、
# 最後に実録音（#456236 の柱時計）の 1/3 オクターブ配分に合わせる補正フィルタをかける。

# 目標の 1/3 オクターブ配分（打音の直後50ms、最大を0dB）。31.5Hz〜12.7kHz の27帯域。
# #456236（柱時計）のチク／タクをもとに、木の箱の低めの響き（#32937）を 200〜500Hz に少し足し、
# 企画の条件どおり 3kHz より上を 3〜6dB 下げた値。
CENTERS = 1000 * 2.0 ** (np.arange(-15, 12) / 3)
TARGET = {
    0: [-45, -45, -45, -45, -42, -38, -34, -30, -22, -18, -18, -14, -12, -4, 0, -3, -5, -3, -3, -8, -12, -17, -23, -22, -24, -35, -42],
    1: [-45, -45, -45, -45, -42, -38, -34, -30, -24, -20, -20, -18, -14, -3, 0, -2, -4, 0, -2, -7, -10, -15, -15, -20, -22, -30, -33],
}


def schedule(total, speed, seed):
    """打音の時刻と、チク(0)／タク(1)の区別。ゆっくりした振れ幅の変化で間隔がごくわずかに動く"""
    a, b = SPEEDS[speed]
    rng = np.random.default_rng(seed)
    n = max(int(total / ((a + b) / 2)) + 4, 400)
    slow = np.cumsum(rng.normal(0, 1, n))
    slow = (slow - np.convolve(slow, np.ones(301) / 301, "same")) / 40  # 数分単位のごく小さな揺れ
    t, ts, kind = 0.3, [], []
    for i in range(n):
        ts.append(t)
        kind.append(i % 2)
        base = a if i % 2 == 0 else b
        t += base * (1 + 0.0015 * np.tanh(slow[i])) + rng.normal(0, 0.0008)
        if t > total + 1:
            break
    return np.array(ts), np.array(kind)


def _click_train(rng):
    """1打の中の細かいカチカチの時刻と強さ（秒, dB）"""
    out = [(0.0, 0.0)]
    t = 0.0
    for _ in range(rng.integers(3, 7)):  # 最初の約6msに続く細かい音
        t += rng.exponential(0.0011) + 0.0002
        out.append((t, rng.uniform(-9, -1)))
    for _ in range(rng.integers(1, 4)):  # 8〜14ms：がんぎ車が止まる音
        out.append((rng.uniform(0.008, 0.014), rng.uniform(-13, -6)))
    if rng.random() < 0.6:  # 20〜30ms：跳ね返り
        out.append((rng.uniform(0.020, 0.030), rng.uniform(-20, -13)))
    return out


def _bands():
    return [butter(2, [150, 600], btype="band", fs=SR, output="sos"), butter(2, [600, 2500], btype="band", fs=SR, output="sos"),
            butter(2, 2500, btype="high", fs=SR, output="sos")]


BANDS = _bands()
RES = {0: [(794, -6), (1587, -8), (1260, -12)], 1: [(700, -6), (1650, -8), (2100, -12)]}


def _body(rng, kind, n):
    """雑音でできた短い響き：低い帯域ほど長く残る（150〜600Hz 18ms、600Hz〜2.5kHz 6ms、2.5kHz〜 2ms）＋弱い金属の響き"""
    t = np.arange(n) / SR
    out = np.zeros(n)
    for sos, tau, db in zip(BANDS, (0.018, 0.006, 0.002), (-4, 0, -2)):
        tau *= np.exp(rng.normal(0, 0.15))
        out += 10 ** (db / 20) * sosfilt(sos, rng.normal(0, 1, n)) * np.exp(-t / tau)
    for f, db in RES[kind]:
        f *= 1 + rng.normal(0, 0.008)
        bp = butter(1, [f / 1.03, f * 1.03], btype="band", fs=SR, output="sos")
        out += 10 ** ((db + rng.normal(0, 1.5)) / 20) * sosfilt(bp, rng.normal(0, 1, n)) * np.exp(-t / 0.014)
    return out


def raw_hit(kind, seed):
    rng = np.random.default_rng(seed)
    n = int(0.25 * SR)
    exc = np.zeros(n)
    for dt, db in _click_train(rng):
        w = rng.uniform(0.00008, 0.0002)
        m = int(6 * w * SR) + 2
        tt = (np.arange(m) - m / 2) / SR
        c = rng.normal(0, 1, m) * np.exp(-0.5 * (tt / w) ** 2)
        s = int(dt * SR)
        exc[s : s + m] += 10 ** (db / 20) * c[: n - s]
    body = _body(rng, kind, int(0.12 * SR))
    h = np.convolve(exc, body)[:n]
    return h + 0.5 * exc  # 鋭い音そのものも少し残す


EQ = {}


def _thirds(x):
    S = np.abs(np.fft.rfft(x * np.hanning(len(x)), 1 << 14)) ** 2
    F = np.fft.rfftfreq(1 << 14, 1 / SR)
    return np.array([10 * np.log10(S[(F >= fc / 2 ** (1 / 6)) & (F < fc * 2 ** (1 / 6))].sum() + 1e-20) for fc in CENTERS])


def eq_fir(kind):
    """生の打音40個の平均配分を目標に合わせる最小位相の補正フィルタ（打音の前に響きが出ないように最小位相）"""
    if kind in EQ:
        return EQ[kind]
    from scipy.signal import firwin2, minimum_phase
    acc = []
    for i in range(40):
        h = raw_hit(kind, 990000 + i)
        acc.append(10 ** (_thirds(h[: int(0.05 * SR)]) / 10))
    cur = 10 * np.log10(np.mean(acc, 0))
    cur -= cur.max()
    corr = np.clip(np.array(TARGET[kind]) - cur, -30, 24)
    f = np.concatenate([[0], CENTERS, [SR / 2]])
    g = 10 ** (np.concatenate([[corr[0]], corr, [corr[-1] - 12]]) / 20)
    lin = firwin2(2047, f / (SR / 2), g)
    EQ[kind] = minimum_phase(lin, method="homomorphic", n_fft=1 << 15)
    return EQ[kind]


def one_hit(kind, seed, level_db):
    h = raw_hit(kind, seed)
    y = np.convolve(h, eq_fir(kind))[: len(h)]
    # 細かいカチカチの並び方で強さが大きく変わらないよう、最初の30msの大きさでそろえる
    # （ばらつきは level_db で ±0.5dB 程度だけつける。最終の音量は書き出し時に決める）
    y /= np.sqrt(np.mean(y[: int(0.03 * SR)] ** 2)) * 20
    return y * 10 ** (level_db / 20)


def reverb_ir(seed=7, seconds=0.5, t60=0.32):
    """静かな和室程度の短い残響（左右で別）"""
    rng = np.random.default_rng(seed)
    n = int(seconds * SR)
    t = np.arange(n) / SR
    ir = np.zeros((n, 2))
    lp = butter(2, 2500, fs=SR, output="sos")
    for c in range(2):
        ir[:, c] = sosfilt(lp, rng.normal(0, 1, n)) * np.exp(-6.9 * t / t60)
        ir[: int(0.006 * SR), c] = 0  # 最初の反射まで6ms
        ir[:, c] /= np.sqrt((ir[:, c] ** 2).sum())
    return ir


TONE = None


def tone_filter():
    """60Hz以下を切る（高い音の調整は打音の補正フィルタで済ませる）"""
    global TONE
    if TONE is None:
        TONE = (None, butter(2, 60, btype="high", fs=SR, output="sos"))
    return TONE


def render_block(t0, dur, cfg, ts, kinds, ir):
    """t0秒からdur秒ぶんのステレオ（float, -1〜1想定の前の生の値）。前後0.5秒の打音も含めて計算する"""
    pad = 1.0
    n = int(dur * SR)
    buf = np.zeros(int((dur + pad * 2) * SR))
    start = t0 - pad
    sel = np.where((ts > start - 0.45) & (ts < t0 + dur + pad))[0]
    for i in sel:
        k = kinds[i]
        rng = np.random.default_rng(cfg["seed"] * 100003 + i)
        lvl = (0 if k == 0 else -2.0) + rng.normal(0, 0.5)
        lvl = float(np.clip(lvl, -4.5, 1.0))
        h = one_hit(k, cfg["seed"] * 7919 + i, lvl)
        s = int(round((ts[i] - start) * SR))
        a, b = max(s, 0), min(s + len(h), len(buf))
        if b > a:
            buf[a:b] += h[a - s : b - s]
    lp, hp = tone_filter()
    # フィルタを区切りに依存させないため、前に余白をとって計算し、余白を捨てる
    dry = sosfilt(hp, buf)
    wet = np.stack([fftconvolve(dry, ir[:, c])[: len(dry)] for c in range(2)], axis=1)
    # 時計は部屋の中央より少し左。左右で響きの強さをわずかに変える
    st = np.stack([dry * 1.0, dry * 0.86], axis=1) + 0.30 * wet
    a = int(pad * SR)
    return st[a : a + n]
