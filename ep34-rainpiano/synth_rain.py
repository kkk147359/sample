"""晩秋の夜、落ち葉に降る静かな雨（実録音の測定は REFERENCES.md）。
3つの層でできている：
1. 下地：遠くの雨のサーという音。1/3オクターブ配分を実録音の「森・庭の雨」に合わせ、150Hz以下は切り、3kHz以上は下げる。
   強弱は30〜120秒でゆっくり ±0.5dB だけ（10/17 社長「普通の雨はもっと一定」）。
2. 落ち葉に当たる粒：短い「パラ」という粒を多数。1粒ごとに高さ（共鳴）・強さ・左右が違う。
3. 枝や軒から落ちる大きめのしずく（10/17 社長指示で外した。drip_rate=0）。
render(t0, dur, seed) で区間ごとに書き出せる（各粒は番号で決まるので区切りに依存しない）。
"""
import numpy as np
from scipy.signal import butter, sosfilt, fftconvolve

SR = 44100
CENTERS = 1000 * 2.0 ** (np.arange(-17, 11) / 3)  # 20Hz〜10kHz
# 目標配分（dB、最大帯域=0）。森・庭の静かな雨（#Calm rain, Bourne woods）の形に合わせ、3kHz以上は実録音より4〜5dB下げた。
# 値は測定で校正したもの（tools/ambience.py で 157Hz〜10kHz が目標と ±0.3dB）
TARGET = np.array([-60.0, -50.0, -42.0, -34.0, -26.0, -20.0, -16.0, -13.0, -11.0, -9.0, -5.7, -5.7, -2.9, -3.5, -1.9, -0.6, 0.5, 0.2,
                   -0.3, -0.7, -1.2, -2.5, -5.9, -9.2, -9.7, -10.5, -13.9, -17.3])
NFIR = 1 << 13
PARAMS = dict(
    patter_rate=14.0,    # 落ち葉の粒（1秒あたり）。間隔をそろえ気味にして下地になじませる
    patter_db=3.0,       # 粒の強さ（下地比、dB）
    patter_sigma=0.5,    # 粒の間隔のばらつき（大きいとかたまって聞こえる）
    drip_rate=0.0,       # 大きめのしずく：10/17 社長「ポコンという音はいらない」で外した
    drip_db=15.0,
    mod_slow_db=0.5,     # 30〜120秒でゆっくり変わる少しの強弱（10/17 社長「波打って聞こえる」で 1.2→0.5dB、周期も長く）
    mod_fast_db=0.0,     # 細かなゆらぎは外す（雑音そのもののゆらぎで実録音の 0.9〜1.6dB に届く）
)


def bed_fir():
    f = np.fft.rfftfreq(NFIR, 1 / SR)
    dens = TARGET - 10 * np.log10(CENTERS)
    g = 10 ** (np.interp(np.log10(np.maximum(f, 10)), np.log10(CENTERS), dens) / 20)
    g[f < 150] *= (np.maximum(f[f < 150], 1) / 150) ** 3  # 150Hz以下を切る
    h = np.fft.irfft(g, NFIR)
    h = np.roll(h, NFIR // 2) * np.hanning(NFIR)
    return h / np.sqrt((h ** 2).sum())


def _mod(t, seed, c):
    """ゆらぎ（dB）。正弦の和なので、どこから計算しても同じ値"""
    r = np.random.default_rng([seed, 31])  # 左右で同じ強弱（左右で別に揺れると波打って聞こえる）
    fs = r.uniform(1 / 120, 1 / 30, 5); ps = r.uniform(0, 2 * np.pi, 5)
    ff = r.uniform(0.8, 3.0, 7); pf = r.uniform(0, 2 * np.pi, 7)
    slow = sum(np.sin(2 * np.pi * a * t + b) for a, b in zip(fs, ps)) / np.sqrt(2.5)
    fast = sum(np.sin(2 * np.pi * a * t + b) for a, b in zip(ff, pf)) / np.sqrt(3.5)
    return PARAMS["mod_slow_db"] * slow + PARAMS["mod_fast_db"] * fast


def events(total, seed):
    """(時刻, 種類0=粒/1=しずく, 強さdB, 左右, 番号)"""
    r = np.random.default_rng([seed, 5])
    ev = []
    for kind, rate in ((0, PARAMS["patter_rate"]), (1, PARAMS["drip_rate"])):
        if rate <= 0:
            continue
        t = 0.0
        sig = PARAMS["patter_sigma"] if kind == 0 else 0.85
        while t < total:
            t += r.lognormal(np.log(1 / rate) - sig ** 2 / 2, sig)
            sd = r.normal(0, 2.0 if kind == 0 else 2.5)
            ev.append((t, kind, sd, r.uniform(-0.85, 0.85), int(r.integers(1 << 30))))
    ev.sort()
    return ev


def _patter(sd):
    """落ち葉に当たる粒：乾いた短い音（共鳴 1〜3kHz、減衰 3〜10ms）"""
    r = np.random.default_rng(sd)
    n = int(0.05 * SR); t = np.arange(n) / SR
    x = r.normal(0, 1, n) * (1 - np.exp(-t / 0.0006)) * np.exp(-t / r.uniform(0.003, 0.010))
    fc = r.uniform(900, 2800)
    x = sosfilt(butter(2, [fc / 1.6, fc * 1.6], btype="band", fs=SR, output="sos"), x)
    return x / (np.sqrt(np.mean(x[: int(0.01 * SR)] ** 2)) + 1e-12)


def _drip(sd):
    """枝から落ちる大きめのしずく：丸い「ポト」（共鳴 500〜1400Hz、少し音程が下がる）"""
    r = np.random.default_rng(sd)
    n = int(0.12 * SR); t = np.arange(n) / SR
    f0 = r.uniform(500, 1400)
    ph = 2 * np.pi * np.cumsum(f0 * (1 - 0.15 * (1 - np.exp(-t / 0.02)))) / SR
    tone = np.sin(ph) * np.exp(-t / r.uniform(0.008, 0.02))
    nz = r.normal(0, 1, n) * np.exp(-t / 0.004)
    nz = sosfilt(butter(2, [400, 2600], btype="band", fs=SR, output="sos"), nz)
    x = 0.35 * tone + 0.65 * nz / (np.abs(nz).max() + 1e-12)
    x *= 1 - np.exp(-t / 0.0008)
    return x / (np.sqrt(np.mean(x[: int(0.02 * SR)] ** 2)) + 1e-12)


class Bed:
    """下地を区切りなく作り続ける（FIRの尾を次の区間へ持ち越す）"""
    def __init__(self, seed):
        self.h = bed_fir(); self.seed = seed
        self.rng = [np.random.default_rng((seed, c, 4242)) for c in range(2)]
        self.tail = [np.zeros(len(self.h) - 1) for _ in range(2)]

    def next(self, t0, n):
        out = []
        for c in range(2):
            y = fftconvolve(self.rng[c].normal(0, 1, n), self.h)
            y[: len(self.tail[c])] += self.tail[c]
            self.tail[c] = y[n:]
            tt = t0 + np.arange(n) / SR
            out.append(y[:n] * 10 ** (_mod(tt, self.seed, c) / 20))
        return np.stack(out, 1)


def render_events(t0, dur, ev):
    """粒としずく（下地RMS=1 に対する大きさ）"""
    n = int(round(dur * SR))
    out = np.zeros((n, 2))
    pg = 10 ** (PARAMS["patter_db"] / 20) * 0.35
    dg = 10 ** (PARAMS["drip_db"] / 20) * 0.35
    for td, kind, db, pan, sd in ev:
        if td < t0 - 0.2 or td > t0 + dur:
            continue
        x = (_patter(sd) * pg if kind == 0 else _drip(sd) * dg) * 10 ** (db / 20)
        s = int(round((td - t0) * SR))
        a, b = max(s, 0), min(s + len(x), n)
        if b > a:
            seg = x[a - s: b - s]
            out[a:b, 0] += seg * np.sqrt(0.5 * (1 - pan))
            out[a:b, 1] += seg * np.sqrt(0.5 * (1 + pan))
    return out
