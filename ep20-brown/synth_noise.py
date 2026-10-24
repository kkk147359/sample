"""ep20/21「やわらかいブラウンノイズ」の合成。
白いノイズに、決めた傾き（1オクターブあたり -6dB＝本来のブラウンノイズ、または -4.5dB）の FIR フィルタをかける。
- 45Hzより下は切る（低音の圧迫感の対策。企画の条件「40〜50Hz以下カット」）
- 8kHzより上はさらになだらかに下げる（シャーという成分を残さない）
- 音量のゆらぎはつけない（ずっと一定）
- 左右は別々のノイズ。corr を指定すると、左右に共通の成分を混ぜて真ん中に寄せる

render_block(i, cfg) で 2^17 サンプルずつ書き出せる（前後のブロックと重ね合わせて継ぎ目なし）。
"""
import numpy as np

SR = 44100
NFIR = 1 << 14
BLOCK = 1 << 17


def design(slope_db_oct, hp=45.0):
    f = np.fft.rfftfreq(NFIR, 1 / SR)
    ref = 100.0
    g = np.where(f > 0, (np.maximum(f, 1) / ref) ** (slope_db_oct / (20 * np.log10(2))), 0)
    g *= 1 / np.sqrt(1 + (hp / np.maximum(f, 1e-3)) ** 8)  # 45Hz 4次の傾きで切る
    g *= 1 / np.sqrt(1 + (f / 8000) ** 2)  # 8kHzより上はさらに-6dB/oct
    h = np.fft.irfft(g, NFIR)
    h = np.roll(h, NFIR // 2) * np.hanning(NFIR)
    return h / np.sqrt((h ** 2).sum())


def _white(seed, i, ch):
    return np.random.default_rng([seed, i, ch]).normal(0, 1, BLOCK)


def render_block(i, cfg, h):
    """i番目のブロック（BLOCKサンプル、ステレオ）。前のブロックの尾を重ね合わせて継ぎ目をなくす"""
    out = np.zeros((BLOCK, 2))
    nf = BLOCK + NFIR
    H = np.fft.rfft(h, nf)
    for j in (i - 1, i):
        if j < 0:
            continue
        chans = []
        for c in range(2):
            w = _white(cfg["seed"], j, c)
            if cfg.get("corr", 0) > 0:
                m = _white(cfg["seed"], j, 9)
                k = cfg["corr"]
                w = np.sqrt(1 - k) * w + np.sqrt(k) * m  # 左右の相関がほぼ k になる
            chans.append(np.fft.irfft(np.fft.rfft(w, nf) * H, nf))
        y = np.stack(chans, axis=1)
        if j == i:
            out += y[:BLOCK]
        else:
            out[: NFIR] += y[BLOCK : BLOCK + NFIR]
    return out
