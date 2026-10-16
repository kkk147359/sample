"""やわらかいピアノ（生ピアノの実録音の測定に合わせた加算合成）と、その場で作るオリジナルのフレーズ。
音の作り（REFERENCES.md の実録音の値に合わせる）：
- 1音は2〜3本の弦。弦ごとに1〜2セントずらし、ゆっくりしたうなりを出す。
- 倍音は弦の硬さで少しずつ高くなる（f_k = k f0 sqrt(1 + B k^2)）。
- 減衰は2段（打鍵直後の速い減衰と、そのあとの長い余韻）。高い倍音ほど早く消える。
- 打鍵位置（弦の1/8付近）で一部の倍音が弱まる。弱く弾くほど高い倍音が少ない（やわらかい音色）。
- 打鍵の小さなノイズ（ハンマーと鍵盤の音）を -30dB 前後で入れる。
- ペダル：和音の間は音を伸ばし、ほかの弦の共鳴を小さく足す（響きは room() でまとめてかける）。
フレーズ：既存曲・MIDI・サンプルは使わない。和音は調の中をランダムに歩き（同じ進行の繰り返しを避ける）、
右手は近い音へ動く短い句を、間（ま）を多くとって置く。シードごとに別の曲になる。
"""
import numpy as np
from scipy.signal import butter, sosfilt, fftconvolve

SR = 44100


def midi_hz(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def note(m, vel, dur, seed):
    """1音（モノラル）。m: MIDI番号, vel: 0〜1（やわらかさ）, dur: 鍵盤を押している秒数（ペダル込み）"""
    r = np.random.default_rng(seed)
    f0 = midi_hz(m)
    # 余韻の長さ（低い音ほど長い）。実録音の単音の減衰に合わせた目安
    t60 = float(np.clip(18 * 2 ** (-(m - 48) / 14), 2.5, 22))
    rel = 0.35  # 離鍵後のダンパーで消える時間
    L = min(dur, t60) + rel + 0.05
    n = int(L * SR)
    t = np.arange(n) / SR
    B = 0.00015 * 2 ** ((m - 60) / 18)  # 弦の硬さ（高音ほど大きい）
    nstr = 3 if m >= 52 else 2
    det = r.normal(0, 1.2, nstr)  # セント
    det -= det.mean()
    kmax = int(min(28, 5200 / f0))
    x = np.zeros(n)
    tilt = 2.4 - 1.0 * vel  # 弱いほど高い倍音が少ない
    pos = 1 / r.uniform(7.5, 8.5)
    for k in range(1, kmax + 1):
        fk = k * f0 * np.sqrt(1 + B * k * k)
        if fk > 7000:
            break
        a = k ** (-tilt) * (0.25 + 0.75 * abs(np.sin(np.pi * k * pos)))
        a *= 1 / (1 + (fk / 1700) ** 2)  # 響板・部屋で高域がやわらぐ
        tau_fast = 0.25 / (1 + 0.15 * (k - 1))
        tau_slow = t60 / 6.9 / (1 + 0.10 * (k - 1) * (f0 / 300) ** 0.3)
        env = 0.55 * np.exp(-t / tau_fast) + 0.45 * np.exp(-t / tau_slow)
        for s in range(nstr):
            fs = fk * 2 ** (det[s] / 1200)
            x += (a / nstr) * env * np.sin(2 * np.pi * fs * t + r.uniform(0, 2 * np.pi))
    # 打鍵の立ち上がり（ハンマーはやわらかいので数ms）
    att = 0.004 + 0.006 * (1 - vel)
    x *= 1 - np.exp(-t / att)
    # ハンマー・鍵盤の小さなノイズ
    nn = int(0.04 * SR)
    th = r.normal(0, 1, nn) * np.exp(-np.arange(nn) / SR / 0.008)
    th = sosfilt(butter(2, [150, 1800], btype="band", fs=SR, output="sos"), th)
    x[:nn] += th * 0.03 * np.sqrt(np.mean(x[: int(0.1 * SR)] ** 2)) / (np.sqrt(np.mean(th ** 2)) + 1e-12)
    # 離鍵
    off = int(min(dur, t60) * SR)
    if off < n:
        x[off:] *= np.exp(-(t[off:] - t[off]) / (rel / 6.9))
    x[-int(0.05 * SR):] *= np.linspace(1, 0, int(0.05 * SR))
    return x * (0.25 + 0.75 * vel)


# ---- フレーズ ----
# 長調の音階（主音からの半音）。調は compose() の key で決める
SCALE = [0, 2, 4, 5, 7, 9, 11]
# 和音の候補（音階の度数）。I ii iii IV V vi と、やわらかい add9・sus の形
CHORDS = {1: [0, 2, 4], 2: [1, 3, 5], 3: [2, 4, 6], 4: [3, 5, 0], 5: [4, 6, 1], 6: [5, 0, 2]}
MOVES = {1: [4, 6, 2, 3, 5], 2: [5, 4, 6], 3: [6, 4, 2], 4: [1, 5, 2, 6], 5: [1, 6, 4], 6: [4, 2, 3, 1]}


def deg_midi(key, deg, octave):
    return key + 12 * octave + SCALE[deg % 7] + 12 * (deg // 7)


def compose(total, seed, key=63, bpm=58):
    """(開始秒, MIDI, 強さ, 長さ秒) のリスト。key=63 は E♭。1分に約60〜80音、句のあとに長めの間"""
    r = np.random.default_rng([seed, 11])
    beat = 60 / bpm
    ev = []
    t = 2.0
    ch = 1
    last_mel = 9  # 右手の度数（主音から数えて、1オクターブ上の3度あたり）
    while t < total:
        bars = int(r.choice([2, 3, 4]))
        for b in range(bars):
            # 和音を選ぶ（直前と同じものは避け、同じ4つ組の繰り返しもしにくい）
            ch = int(r.choice(MOVES[ch]))
            tones = CHORDS[ch]
            bar = 4 * beat * r.uniform(0.95, 1.08)
            # 左手：根音（低すぎない音域）と、5度か3度を少し遅れて
            root = deg_midi(key, tones[0], -2)
            while root < 43:
                root += 12
            vb = r.uniform(0.32, 0.42)
            ev.append((t, root, vb, bar * 1.6))
            if r.random() < 0.8:
                ev.append((t + beat * r.uniform(0.9, 1.6), deg_midi(key, tones[2 if r.random() < 0.6 else 1], -1), vb * 0.85, bar * 1.2))
            # 右手：近い音へ動く2〜4音
            nmel = int(r.choice([2, 3, 3, 4, 4, 5]))
            tm = t + beat * r.uniform(0.0, 1.2)
            for i in range(nmel):
                if r.random() < 0.55:  # 和音の音に寄せる
                    cands = [d for d in range(4, 15) if d % 7 in tones]
                else:
                    cands = list(range(4, 15))
                cands = sorted(cands, key=lambda d: abs(d - last_mel) + r.uniform(0, 1.5))
                d = cands[0] if cands[0] != last_mel or r.random() < 0.2 else cands[1]
                last_mel = d
                m = deg_midi(key, d, 0)
                ev.append((tm, m, r.uniform(0.36, 0.5), beat * r.uniform(1.2, 2.8)))
                tm += beat * float(r.choice([0.5, 1, 1, 1, 1.5, 2]))
                if tm > t + bar:
                    break
            t += bar
        # 句のあとの間（雨だけになる時間）
        t += r.uniform(2.0, 5.0)
        if r.random() < 0.25:
            ch = 1
    return [e for e in ev if e[0] < total]


def render(ev, total, seed):
    """ステレオ。音の高さで少し左右に広げる（低音は左寄り）"""
    n = int(total * SR) + SR
    out = np.zeros((n, 2))
    cache = {}
    for i, (t0, m, v, d) in enumerate(ev):
        x = note(m, v, d, [seed, i])
        s = int(t0 * SR)
        e = min(n, s + len(x))
        pan = np.clip((m - 60) / 30, -0.5, 0.5)
        out[s:e, 0] += x[: e - s] * np.sqrt(0.5 * (1 - pan))
        out[s:e, 1] += x[: e - s] * np.sqrt(0.5 * (1 + pan))
    return out[: int(total * SR)]


def room(x, seed, rt=1.6, wet=0.22):
    """部屋の響き（減衰する雑音のインパルス応答。左右で別の雑音）"""
    r = np.random.default_rng([seed, 99])
    n = int(rt * 1.2 * SR)
    t = np.arange(n) / SR
    out = x.copy() * (1 - wet)
    for c in range(2):
        h = r.normal(0, 1, n) * np.exp(-t / (rt / 6.9))
        h = sosfilt(butter(2, [120, 5000], btype="band", fs=SR, output="sos"), h)
        h /= np.sqrt((h ** 2).sum())
        out[:, c] += wet * fftconvolve(x[:, c], h)[: len(x)]
    return out
