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
SPEEDS = {"A": (0.57, 0.63), "B": (0.97, 1.03),
          # v3：もとにした実録音の間隔（チク→タク、タク→チク）
          "371070": (0.50, 0.70),
          # 10/4 社長「速さはAがよいが一定にしてほしい」：チクもタクも0.60秒ちょうど、揺れなし
          "even060": (0.60, 0.60),
          "even070": (0.70, 0.70),  # 10/4 社長「あと少し遅く」
          "405423": (1.003, 0.998), "453159": (0.494, 0.506), "456236": (0.538, 0.620)}

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
        if a == b:
            t += a  # 一定の速さ：揺れをつけない
        else:
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


# v3（10/4 社長「もう少し現実に近づけて」）
# 実録音の打音から「帯域ごとの音量の時間変化」（tools/tick_template.py、数十打の平均）を取り出し、
# 1打ごとに新しい雑音をその形に沿わせて鳴らす。波形は毎回ちがい、音量の形と音色の配分だけが実録音どおりになる。
# 録音に入っていた部屋の雑音（打音の後ろの一定の音）は帯域ごとに差し引く。
import os

TEMPLATE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates")
TPL = {}
HF_CUT = None


def template(name, soft=False):
    key = (name, soft)
    if key in TPL:
        return TPL[key]
    d = np.load(os.path.join(TEMPLATE_DIR, f"t{name}.npz"))
    cen = d["centers"]
    hop = int(d["hop"])
    envs = []
    for par in (0, 1):
        env = d[f"env{par}"].copy()
        floor = np.median(env[:, -60:-10], axis=1, keepdims=True)  # 最後の約18msを部屋の雑音とみなす
        env = np.clip(env - 1.2 * floor, 0, None)
        # 企画の条件：3.5kHzより上をゆるく下げる（3dB/オクターブ）
        g = np.where(cen > 3500, (cen / 3500) ** (-1.0), 1.0) ** 2
        if soft:  # 10/4 社長「もう少し柔らかく」：2kHzより上をさらに 6dB/オクターブ下げる
            g *= np.where(cen > 2000, (cen / 2000) ** (-2.0), 1.0)
        env *= g[:, None]
        envs.append(env)
    lv = 10 * np.log10(envs[1].sum() / envs[0].sum())
    TPL[key] = {"centers": cen, "hop": hop, "pre": float(d["pre"]), "env": envs, "ioi": d["ioi"], "level_diff": lv}
    return TPL[key]


MASKS = {}


def _masks(n, cen):
    key = (n, len(cen))
    if key not in MASKS:
        f = np.fft.rfftfreq(n, 1 / SR)
        m = []
        for fc in cen:
            lo, hi = fc / 2 ** (1 / 6), fc * 2 ** (1 / 6)
            # 隣の帯域となめらかにつながる台形
            w = np.clip(np.minimum((f - lo / 1.12) / (lo * 0.12), (hi * 1.12 - f) / (hi * 0.12)), 0, 1)
            m.append(w)
        MASKS[key] = np.array(m)
    return MASKS[key]


def one_hit(kind, seed, level_db, tpl="371070", soft=False):
    T = template(tpl, soft)
    rng = np.random.default_rng(seed)
    env = T["env"][kind]
    nb, nt = env.shape
    stretch = np.exp(rng.normal(0, 0.03))  # 打音の長さを±3%ほど揺らす（山の位置はほぼ動かない）
    n = int(nt * T["hop"] * stretch)
    tt = np.arange(n) / stretch / T["hop"]
    m = _masks(n, T["centers"])
    W = np.fft.rfft(rng.normal(0, 1, n))
    out = np.zeros(n)
    gains = 10 ** (rng.normal(0, 1.0, nb) / 20)  # 帯域ごとの強さを±1dBほど変える（同じ音のコピーにしない）
    for k in range(nb):
        carrier = np.fft.irfft(W * m[k], n)
        carrier /= np.sqrt(np.mean(carrier ** 2)) + 1e-12
        e = np.interp(tt, np.arange(nt), env[k])
        out += gains[k] * carrier * np.sqrt(e)
    out /= np.sqrt(T["env"][0].sum(axis=0).max())  # チクの最大を基準にそろえる
    # チクとタクで一番大きい点の位置が違う（例 3.7ms と 1.2ms）ので、山の位置で間隔がそろうように前をそろえる
    pk = [np.argmax(T["env"][q].sum(0)) for q in (0, 1)]
    pre = int((T["pre"] * SR + (pk[kind] - max(pk)) * T["hop"]) * stretch)
    out = out[max(pre, 0):]
    if soft:  # 打った瞬間の鋭さを抑える：山の手前から2.5msかけてなめらかに立ち上げる
        a = max(int(max(pk) * T["hop"] * stretch) - max(pre, 0) - int(0.0015 * SR), 0)
        r = int(0.0025 * SR)
        ramp = np.ones(len(out))
        ramp[:a] = 0
        ramp[a : a + r] = 0.5 - 0.5 * np.cos(np.pi * np.arange(min(r, len(out) - a)) / r)
        out = out * ramp
    return out * 10 ** ((level_db + (T["level_diff"] if kind == 1 else 0)) / 20)


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
        lvl = rng.normal(0, 0.5)
        lvl = float(np.clip(lvl, -4.5, 1.0))
        h = one_hit(k, cfg["seed"] * 7919 + i, lvl, cfg.get("tpl", "371070"), cfg.get("soft", False))
        s = int(round((ts[i] - start) * SR))
        a, b = max(s, 0), min(s + len(h), len(buf))
        if b > a:
            buf[a:b] += h[a - s : b - s]
    lp, hp = tone_filter()
    # フィルタを区切りに依存させないため、前に余白をとって計算し、余白を捨てる
    dry = sosfilt(hp, buf)
    wet = np.stack([fftconvolve(dry, ir[:, c])[: len(dry)] for c in range(2)], axis=1)
    # 時計は部屋の中央より少し左。左右で響きの強さをわずかに変える
    st = np.stack([dry * 1.0, dry * 0.86], axis=1) + cfg.get("wet", 0.30) * wet
    a = int(pad * SR)
    return st[a : a + n]
