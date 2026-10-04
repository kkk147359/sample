"""十七絃（低音の箏）合成スクリプト

十七絃そのものの実録音は見つからなかったため、同じ胴の長い箏の仲間である伽耶琴の単音
（freesound spt3125 kayageum1_D2〜D4, CC0）を測定して、低い弦の鳴り方を合わせた。
伽耶琴は指の腹で弾くので、「十七絃を指でやわらかく弾いた音」になる。
- 音のエネルギーは150〜600Hzに集まり、約1.1kHzより上はほとんどない
- 減衰は周波数で決まる：100Hz 約11秒、200Hz 約8.5秒、440Hz 約5秒、800Hz 約2秒、1kHz以上 約1.3秒
- 最低音域の基音は胴から出にくく、2倍音より8〜20dB弱い
調弦は半音を含まない陽音階（D E G A B）。低音域で半音が重なると濁り、圧迫感になるため。
使い方: python3 synth_17gen.py <出力wav> [長さ(秒)] [乱数シード]
"""
import sys

import numpy as np
from scipy.io import wavfile
from scipy.signal import butter, fftconvolve, sosfilt

from synth_koto import SR, midi_hz, reverb_ir

rng = np.random.default_rng(int(sys.argv[3]) if __name__ == "__main__" and len(sys.argv) > 3 else 17)

# 陽音階（D）：D2〜E4 の13本を使う
YO = [38, 40, 43, 45, 47, 50, 52, 55, 57, 59, 62, 64, 67]  # D2 E2 G2 A2 B2 D3 E3 G3 A3 B3 D4 E4 G4
KEYS = [0, -2, 0, 2]  # D → C → D → E


def note(midi, vel, length, bend=None, yuri=False):
    n = int(length * SR)
    t = np.arange(n) / SR
    f0 = midi_hz(midi)
    cents = np.zeros(n)
    if bend:
        b0, semis, dur = bend
        ramp = np.clip((t - b0) / dur, 0, 1)
        cents += 100 * semis * (0.5 - 0.5 * np.cos(np.pi * ramp))
    if yuri:
        depth = 10 * np.clip((t - 0.8) / 1.5, 0, 1)
        cents += depth * np.sin(2 * np.pi * 3.8 * t + rng.uniform(0, 6.28))
    phase_base = 2 * np.pi * np.cumsum(f0 * 2 ** (cents / 1200)) / SR
    beta = 1 / 7  # 指の腹で弦の中ほど寄りを弾く
    out = np.zeros(n)
    for k in range(1, 30):
        fhz = k * f0
        if fhz > 4000:
            break
        amp = (0.4 + abs(np.sin(k * np.pi * beta))) / k ** 1.3  # 実測では2〜3倍音から上が急に弱くなる
        amp /= 1 + (fhz / 1100) ** 4  # 指で弾くので約1.1kHzより上はほとんど出ない
        amp /= 1 + (140 / fhz) ** 3  # 胴の放射：約150Hzより下が弱い
        amp *= np.interp(vel, [0.3, 0.7], [0.85, 1.0]) ** (fhz / 500)
        t60 = np.interp(fhz, [70, 100, 200, 300, 440, 600, 800, 1000, 2000], [10, 11, 8.5, 6.5, 5.0, 3.8, 2.0, 1.3, 0.8])
        env = np.exp(-6.9 * t / t60)
        if k <= 3:
            env = env * (1 + 0.1 * np.cos(2 * np.pi * rng.uniform(0.15, 0.4) * t))
        out += amp * env * np.sin(k * phase_base + rng.uniform(0, 6.28))
    # 立ち上がり：指の腹なので爪より少しゆっくり（12ms）。爪の当たる音はない
    a = int(0.012 * SR)
    out[:a] *= np.linspace(0, 1, a) ** 1.5
    fade = int(1.2 * SR)
    out[-fade:] *= np.linspace(1, 0, fade) ** 2
    return out * vel / (np.max(np.abs(out)) + 1e-9)


def tone(sig):
    """60Hz以下を切り、120Hz付近を少し下げて圧迫感を防ぐ。高域はもともと少ない。"""
    sig = sosfilt(butter(2, 60, btype="high", fs=SR, output="sos"), sig)
    low = sosfilt(butter(2, [90, 160], btype="band", fs=SR, output="sos"), sig)
    sig = sig - 0.35 * low
    return sosfilt(butter(2, 5000, fs=SR, output="sos"), sig)


def compose(total):
    """(時刻, midi, vel, 長さ, bend, yuri)。低音の楽器なので音数は少なく、余韻を聞かせる。"""
    events = []
    t = 1.5
    section_len = total / len(KEYS)
    pos = 6
    motif, phrase_start = None, pos
    while t < total - 8:
        sec = min(int(t // section_len), len(KEYS) - 1)
        key = KEYS[sec]
        center = 7 if sec == 2 else 6  # 中心はE3〜G3。最低音は支えにだけ使う
        # ときどき最低音域で支える（オクターブを同時に：合せ爪）
        if rng.random() < 0.25:
            root = YO[rng.choice([0, 2, 3])] + key
            events.append((t, root, 0.32, 10.0, None, False))
            events.append((t + 0.04, root + 12, 0.24, 9.0, None, False))
            t += rng.uniform(2.0, 3.0)
        if motif and rng.random() < 0.4:
            steps = list(motif)
            steps[rng.integers(0, len(steps))] = int(rng.choice([-1, 1]))
            pos = phrase_start
        else:
            steps = list(rng.choice([0, -2, -1, 1, 2], size=rng.integers(2, 6), p=[0.2, 0.12, 0.3, 0.26, 0.12]))
            pos = int(np.clip(pos + (center - pos) // 2, 3, 11))
        motif, phrase_start = steps, pos
        rhythm = rng.choice([1.0, 1.5, 1.5, 2.0, 2.5], size=len(steps))
        for i, step in enumerate(steps):
            pos = int(np.clip(pos + step, 3, 11))
            m = YO[pos] + key
            last = i == len(steps) - 1
            vel = rng.uniform(0.38, 0.52) if not last else rng.uniform(0.32, 0.42)
            bend = None
            # 押し手は控えめに（全音上の隣の弦へ、15%）
            if pos + 1 < len(YO) and YO[pos + 1] - YO[pos] == 2 and rng.random() < 0.15:
                bend = (rng.uniform(0.5, 0.9), 2, rng.uniform(0.3, 0.45))
            ring = 9.0 if last else max(6.0, rhythm[i] + 4)
            events.append((t + rng.normal(0, 0.025), m, vel, ring, bend, last))
            t += 0 if last else rhythm[i]
        t += rng.uniform(2.5, 4.5)  # 間：低い弦の余韻が長いので琴より長めに取れる
    return events


def render(total):
    n = int(total * SR) + 12 * SR
    left = np.zeros(n)
    right = np.zeros(n)
    for t, m, vel, dur, bend, yuri in compose(total):
        y = note(m, vel, dur, bend, yuri)
        s = int(max(t, 0) * SR)
        pan = np.interp(m, [36, 68], [0.42, 0.58])
        left[s : s + len(y)] += y * np.sqrt(1 - pan)
        right[s : s + len(y)] += y * np.sqrt(pan)
    left, right = tone(left), tone(right)
    wet_l = fftconvolve(left, reverb_ir(3, rt=2.6))[:n]
    wet_r = fftconvolve(right, reverb_ir(4, rt=2.6))[:n]
    out = np.stack([left + 0.28 * wet_l, right + 0.28 * wet_r], axis=1)[: int(total * SR)]
    fi, fo = int(2 * SR), int(8 * SR)
    out[:fi] *= np.linspace(0, 1, fi)[:, None]
    out[-fo:] *= np.linspace(1, 0, fo)[:, None] ** 2
    return out / np.max(np.abs(out)) * 0.7


if __name__ == "__main__":
    path = sys.argv[1]
    total = float(sys.argv[2]) if len(sys.argv) > 2 else 120
    wavfile.write(path, SR, (render(total) * 32767).astype(np.int16))
    print(f"wrote {path} ({total:.0f}s)")
