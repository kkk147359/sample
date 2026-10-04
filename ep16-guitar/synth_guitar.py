"""やさしいガットギター（ep16）合成スクリプト

撥弦合成（Karplus-Strong）＋胴鳴り＋暗めの残響で、ナイロン弦のゆっくりしたアルペジオを作る。
使い方: python3 synth_guitar.py <出力wav> [長さ(秒)] [乱数シード]
"""
import sys

import numpy as np
from scipy.io import wavfile
from scipy.signal import butter, fftconvolve, lfilter, sosfilt

SR = 44100
BEAT = 1.0  # BPM60
BAR = 4 * BEAT
rng = np.random.default_rng(int(sys.argv[3]) if len(sys.argv) > 3 else 16)


def midi_hz(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def pluck(midi, vel, length):
    """1音を合成する。vel は 0〜1。"""
    f = midi_hz(midi)
    period = SR / f
    # ループ遅延 = n + 1（3点平均の減衰フィルタ：ナイロン弦らしく高域を早く減衰）+ d（オールパスで微調整）
    n = int(np.floor(period - 1.1))
    d = period - 1.0 - n
    c = (1 - d) / (1 + d)
    # 指の腹で弾く柔らかい励振：強く弾くほど少し明るい
    exc = rng.standard_normal(n)
    cut = 1200 + 1800 * vel
    exc = sosfilt(butter(2, cut, fs=SR, output="sos"), exc)
    # 弾く位置（ブリッジから約15%）の櫛形フィルタ
    k = max(1, int(0.15 * n))
    exc = exc - np.concatenate([np.zeros(k), exc[:-k]])
    exc *= vel / (np.max(np.abs(exc)) + 1e-9)
    x = np.zeros(int(length * SR))
    x[: len(exc)] = exc
    # 減衰：低い弦ほど長く鳴る（T60 約5秒→約2.5秒）
    t60 = np.interp(midi, [40, 76], [5.0, 2.5])
    g = 10 ** (-3 / (t60 * f))
    # Y(1 + c z^-1) = X(1 + c z^-1) + g(0.25 + 0.5z^-1 + 0.25z^-2)(c + z^-1) z^-n Y
    den = np.zeros(n + 4)
    den[0] = 1.0
    den[1] = c
    for i, k in enumerate([0.25 * c, 0.25 + 0.5 * c, 0.5 + 0.25 * c, 0.25]):
        den[n + i] -= g * k
    y = lfilter([1.0, c], den, x)
    return y


def body(sig):
    """胴鳴り：低めの共鳴を軽く足し、低域の圧迫感は出さない。"""
    out = sig.copy()
    for fc, q, gain in [(105, 6, 0.10), (210, 5, 0.12), (400, 4, 0.08)]:
        bw = fc / q
        sos = butter(2, [fc - bw / 2, fc + bw / 2], btype="band", fs=SR, output="sos")
        out += gain * sosfilt(sos, sig)
    return out


def tone(sig):
    """低域を整え、4kHzより上をなだらかに削る。"""
    sig = sosfilt(butter(2, 70, btype="high", fs=SR, output="sos"), sig)
    # 150Hz以下を少し下げる（低音の圧迫感対策）
    low = sosfilt(butter(1, 150, fs=SR, output="sos"), sig)
    sig = sig - 0.3 * low
    # 4kHzから上をなだらかに：1次で3.5kHz、2次で7kHz
    sig = sosfilt(butter(1, 3500, fs=SR, output="sos"), sig)
    sig = sosfilt(butter(2, 7000, fs=SR, output="sos"), sig)
    return sig


def reverb_ir(seed):
    """暗めで短い残響。尾が「風」のようにならないよう高域を時間とともに強く落とす。"""
    r = np.random.default_rng(seed)
    n = int(2.2 * SR)
    t = np.arange(n) / SR
    noise = r.standard_normal(n)
    bright = sosfilt(butter(2, 3000, fs=SR, output="sos"), noise)
    dark = sosfilt(butter(2, 900, fs=SR, output="sos"), noise)
    mix = np.clip(t / 0.4, 0, 1)
    ir = ((1 - mix) * bright + mix * dark) * np.exp(-6.9 * t / 1.8)
    ir[: int(0.012 * SR)] = 0  # 初期反射までの間
    return ir / np.sqrt(np.sum(ir ** 2))


# 和音（MIDI番号、低い順）。セクションごとに調と音域を変える
SECTIONS = [
    # A：D調、中音域
    [[50, 57, 61, 64, 66], [47, 54, 57, 62, 64], [43, 50, 54, 59, 62], [45, 52, 57, 62, 64]],
    # B：C調、少し低めで落ち着かせる
    [[45, 52, 55, 59, 60], [53, 57, 60, 64, 67], [48, 55, 59, 64, 67], [43, 50, 57, 60, 64]],
    # C：D調に戻り、高めの音域に旋律を少し
    [[50, 57, 62, 66, 69], [47, 54, 59, 62, 66], [43, 55, 59, 62, 67], [45, 57, 61, 64, 69]],
    # D：F調、ゆったり
    [[53, 60, 64, 67, 69], [50, 57, 60, 65, 69], [46, 53, 57, 62, 65], [48, 55, 60, 65, 67]],
]
MELODY = {2: [78, 76, 74, 73], 3: [72, 74, 69, 67]}  # セクションC・Dでときどき鳴らす上の音

PATTERNS = [
    [0, None, 2, 3, 1, None, 4, None],
    [0, None, 1, 2, 3, None, None, 2],
    [0, None, 2, None, 4, 3, None, None],
    [0, None, None, 1, 2, None, 3, None],
    [0, None, 3, None, None, None, None, None],  # 間を空ける小節
]


def compose(total):
    bars = int(total // BAR)
    bars_per_section = 12
    events = []  # (時刻, midi, vel, 長さ)
    for b in range(bars):
        sec = (b // bars_per_section) % len(SECTIONS)
        chord = SECTIONS[sec][b % 4]
        t0 = b * BAR
        pat = PATTERNS[rng.integers(0, 4)] if b % 4 != 3 or rng.random() > 0.5 else PATTERNS[4]
        ring = BAR + 0.9
        for i, idx in enumerate(pat):
            if idx is None or (i > 0 and rng.random() < 0.15):
                continue
            t = t0 + i * BEAT / 2 + rng.normal(0, 0.015)
            vel = rng.uniform(0.35, 0.6) if idx > 0 else rng.uniform(0.3, 0.42)
            events.append((max(t, 0), chord[idx], vel, ring - i * BEAT / 2))
        if sec in MELODY and rng.random() < 0.35:
            m = MELODY[sec][b % 4]
            events.append((t0 + 3 * BEAT + rng.normal(0, 0.02), m, rng.uniform(0.3, 0.45), 3.5))
    return events


def render(total):
    n = int(total * SR) + 3 * SR
    left = np.zeros(n)
    right = np.zeros(n)
    for t, m, vel, dur in compose(total):
        y = pluck(m, vel, dur)
        fade = int(0.6 * SR)
        y[-fade:] *= np.linspace(1, 0, fade) ** 2
        s = int(t * SR)
        pan = np.interp(m, [43, 78], [0.42, 0.6])  # 低音はやや左、高音はやや右
        left[s : s + len(y)] += y * np.sqrt(1 - pan)
        right[s : s + len(y)] += y * np.sqrt(pan)
    left, right = tone(body(left)), tone(body(right))
    wet_l = fftconvolve(left, reverb_ir(1))[:n]
    wet_r = fftconvolve(right, reverb_ir(2))[:n]
    out = np.stack([left + 0.22 * wet_l, right + 0.22 * wet_r], axis=1)
    out = out[: int(total * SR)]
    # 頭と終わりのフェード
    fi, fo = int(3 * SR), int(8 * SR)
    out[:fi] *= np.linspace(0, 1, fi)[:, None]
    out[-fo:] *= np.linspace(1, 0, fo)[:, None] ** 2
    return out / np.max(np.abs(out)) * 0.7


if __name__ == "__main__":
    path = sys.argv[1]
    total = float(sys.argv[2]) if len(sys.argv) > 2 else 180
    audio = render(total)
    wavfile.write(path, SR, (audio * 32767).astype(np.int16))
    print(f"wrote {path} ({total:.0f}s)")
