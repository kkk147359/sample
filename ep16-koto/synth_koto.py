"""静かな琴（ep16）合成スクリプト

倍音を1本ずつ重ねるモーダル合成で十三弦の琴を作る。
- 平調子の調弦、旋律は短いフレーズと長い「間」
- 押し手（弾いてから弦を押して音程を上げる）、ゆり（押して揺らす）、合せ爪（オクターブ同時）
- 爪の当たる音は弱めにして、眠りの邪魔をしない
使い方: python3 synth_koto.py <出力wav> [長さ(秒)] [乱数シード]
"""
import sys

import numpy as np
from scipy.io import wavfile
from scipy.signal import butter, fftconvolve, sosfilt

SR = 44100
rng = np.random.default_rng(int(sys.argv[3]) if len(sys.argv) > 3 else 16)

# 平調子（D）：二〜巾の12本。一は五と同じ高さなので低音の支えにだけ使う
HIRA = [55, 57, 58, 62, 63, 67, 69, 70, 74, 75, 79, 81]  # G3 A3 Bb3 D4 Eb4 G4 A4 Bb4 D5 Eb5 G5 A5
# セクションごとの移調（半音）：D → C（低く落ち着かせる）→ D → E
KEYS = [0, -2, 0, 2]


def midi_hz(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def koto_note(midi, vel, length, bend=None, yuri=False):
    """1音。bend=(開始秒, 上げ幅(半音), かける秒) で押し手。"""
    n = int(length * SR)
    t = np.arange(n) / SR
    f0 = midi_hz(midi)
    # 音程の動き（セント単位）
    cents = np.zeros(n)
    if bend:
        b0, semis, dur = bend
        ramp = np.clip((t - b0) / dur, 0, 1)
        cents += 100 * semis * (0.5 - 0.5 * np.cos(np.pi * ramp))
    if yuri:
        depth = 18 * np.clip((t - 0.6) / 1.0, 0, 1)
        cents += depth * np.sin(2 * np.pi * 4.5 * t + rng.uniform(0, 6.28))
    ratio = 2 ** (cents / 1200)
    phase_base = 2 * np.pi * np.cumsum(f0 * ratio) / SR

    # 倍音の配分と減衰は実録音（freesound #223958 Koto C4, CC0）の測定に合わせる：
    # - 弾いた直後は約3.4kHzまで倍音がほぼ同じ強さで並び、その上は下がる
    # - 基音は胴からあまり放射されず、3倍音より15〜26dB弱い（低い周波数ほど弱い）
    # - 減衰は周波数で決まる：800Hz以下 約5〜6秒、1.3kHz 約2秒、1.5kHz以上 0.6〜1秒
    beta = 1 / 11  # 爪で弾く位置（端から全長の約1/11）
    out = np.zeros(n)
    B = 0.00002  # 実測ではほぼ整数倍
    for k in range(1, 40):
        fk = k * np.sqrt(1 + B * k * k)
        fhz = fk * f0
        if fhz > 7000:
            break
        amp = 0.35 + abs(np.sin(k * np.pi * beta))  # 弾く位置による凹凸（極端な谷は作らない）
        amp /= 1 + (fhz / 3700) ** 4  # 約3.5kHzより上は急に下げる
        amp /= 1 + (600 / fhz) ** 3  # 胴の放射：低い周波数ほど弱い
        amp *= np.interp(vel, [0.3, 0.7], [0.9, 1.0]) ** (fhz / 1000)  # やさしく弾くと高域が少し減る
        t60 = np.interp(fhz, [150, 800, 1000, 1300, 2000, 3500, 7000], [6.5, 5.5, 2.6, 1.1, 0.8, 0.55, 0.3])
        env = np.exp(-6.9 * t / t60)
        # 低い倍音にはわずかなうなり（弦の二つの振動方向の差）
        if k <= 4:
            env = env * (1 + 0.12 * np.cos(2 * np.pi * rng.uniform(0.2, 0.6) * t))
        out += amp * env * np.sin(fk * phase_base + rng.uniform(0, 6.28))
    # 立ち上がり：実測のピークは約13ms。6msで立ち上げる
    a = int(0.006 * SR)
    out[:a] *= np.linspace(0, 1, a)
    # 爪の当たる音（ごく弱く、高すぎない帯域）
    click_len = int(0.012 * SR)
    click = rng.standard_normal(click_len) * np.exp(-np.arange(click_len) / (0.003 * SR))
    click = sosfilt(butter(2, [900, 2800], btype="band", fs=SR, output="sos"), click)
    out[:click_len] += 0.08 * vel * click / (np.max(np.abs(click)) + 1e-9)
    # 終わりは自然に消えるまで待たずにフェード
    fade = int(0.8 * SR)
    out[-fade:] *= np.linspace(1, 0, fade) ** 2
    return out * vel / (np.max(np.abs(out)) + 1e-9)


def body(sig):
    """桐の胴の響き：300Hz付近と1kHz付近を少しだけ持ち上げる。"""
    out = sig.copy()
    for lo, hi, g in [(220, 380, 0.15), (850, 1300, 0.08)]:
        out += g * sosfilt(butter(2, [lo, hi], btype="band", fs=SR, output="sos"), sig)
    return out


def tone(sig):
    """低域を整え、4kHzより上をなだらかに削る。"""
    sig = sosfilt(butter(2, 80, btype="high", fs=SR, output="sos"), sig)
    sig = sosfilt(butter(2, 6000, fs=SR, output="sos"), sig)
    return sig


def reverb_ir(seed, rt=2.2):
    """和室〜小さなホール程度の暗めの残響。尾は高域を強く落として風の音にしない。"""
    r = np.random.default_rng(seed)
    n = int(rt * 1.3 * SR)
    t = np.arange(n) / SR
    noise = r.standard_normal(n)
    bright = sosfilt(butter(2, 3200, fs=SR, output="sos"), noise)
    dark = sosfilt(butter(2, 1000, fs=SR, output="sos"), noise)
    mix = np.clip(t / 0.5, 0, 1)
    ir = ((1 - mix) * bright + mix * dark) * np.exp(-6.9 * t / rt)
    ir[: int(0.015 * SR)] = 0
    return ir / np.sqrt(np.sum(ir ** 2))


def compose(total):
    """(時刻, midi, vel, 長さ, bend, yuri) のリスト"""
    events = []
    t = 2.0
    section_len = total / len(KEYS)
    pos = 5  # 弦の位置（HIRAの添字）
    last_sweep = -999
    motif, phrase_start = None, pos
    while t < total - 6:
        sec = min(int(t // section_len), len(KEYS) - 1)
        key = KEYS[sec]
        # セクションCでは少し高めの音域を中心に
        center = 7 if sec == 2 else 5
        # ときどき低い一の弦（D3〜D4）で支える
        if rng.random() < 0.3:
            events.append((t, 50 + key, rng.uniform(0.25, 0.32), 6.0, None, False))
            t += rng.uniform(0.8, 1.4)
        # ごくまれに、ゆっくりした下りのかき鳴らし（流し爪のやさしい版）
        if t - last_sweep > 70 and rng.random() < 0.15:
            start = rng.integers(7, 11)
            for j, s in enumerate(range(start, start - 5, -1)):
                events.append((t + j * 0.22, HIRA[s] + key, 0.28 - 0.02 * j, 4.0, None, False))
            last_sweep = t
            t += 5 * 0.22 + rng.uniform(2.5, 4.0)
            continue
        # 旋律のフレーズ：3〜7音。4割は前のフレーズの形をくり返し、1か所だけ変える（モチーフ）
        top = 10 if sec == 2 else 9
        if motif and rng.random() < 0.4:
            steps = list(motif)
            steps[rng.integers(0, len(steps))] = int(rng.choice([-1, 1, 2]))
            pos = phrase_start
        else:
            steps = list(rng.choice([-2, -1, 1, 2, 3, -3], size=rng.integers(3, 8), p=[0.15, 0.27, 0.25, 0.15, 0.09, 0.09]))
            pos = int(np.clip(pos + (center - pos) // 2, 1, top))
        motif, phrase_start = steps, pos
        rhythm = rng.choice([0.75, 1.0, 1.0, 1.5, 2.0], size=len(steps))
        for i, step in enumerate(steps):
            pos = int(np.clip(pos + step, 1, top))
            m = HIRA[pos] + key
            last = i == len(steps) - 1
            dur_gap = 0 if last else rhythm[i]
            vel = rng.uniform(0.38, 0.55) if not last else rng.uniform(0.33, 0.45)
            bend = None
            # 押し手：次の弦の音が1〜2半音上なら、弾いてから押してその音へ（後押し）
            nxt = HIRA[pos + 1] - HIRA[pos] if pos + 1 < len(HIRA) else 99
            if nxt <= 2 and rng.random() < 0.35:
                bend = (rng.uniform(0.35, 0.7), nxt, rng.uniform(0.18, 0.3))
            ring = 6.0 if last else max(3.5, dur_gap + 2.5)
            events.append((t + rng.normal(0, 0.02), m, vel, ring, bend, last))
            # 合せ爪：フレーズの終わりにときどきオクターブ下を重ねる
            if last and rng.random() < 0.35 and pos >= 4:
                events.append((t + 0.03, m - 12, vel * 0.7, ring, None, False))
            t += dur_gap
        # 間：最後の音の余韻が残っているうちに次へ（1.8〜3.2秒）
        t += rng.uniform(1.8, 3.2)
    return events


def render(total):
    n = int(total * SR) + 8 * SR
    left = np.zeros(n)
    right = np.zeros(n)
    for t, m, vel, dur, bend, yuri in compose(total):
        y = koto_note(m, vel, dur, bend, yuri)
        s = int(max(t, 0) * SR)
        pan = np.interp(m, [50, 84], [0.38, 0.62])  # 奏者から見て低い弦は左、高い弦は右
        left[s : s + len(y)] += y * np.sqrt(1 - pan)
        right[s : s + len(y)] += y * np.sqrt(pan)
    left, right = tone(body(left)), tone(body(right))
    wet_l = fftconvolve(left, reverb_ir(1))[:n]
    wet_r = fftconvolve(right, reverb_ir(2))[:n]
    out = np.stack([left + 0.3 * wet_l, right + 0.3 * wet_r], axis=1)
    out = out[: int(total * SR)]
    fi, fo = int(2 * SR), int(8 * SR)
    out[:fi] *= np.linspace(0, 1, fi)[:, None]
    out[-fo:] *= np.linspace(1, 0, fo)[:, None] ** 2
    return out / np.max(np.abs(out)) * 0.7


if __name__ == "__main__":
    path = sys.argv[1]
    total = float(sys.argv[2]) if len(sys.argv) > 2 else 180
    audio = render(total)
    wavfile.write(path, SR, (audio * 32767).astype(np.int16))
    print(f"wrote {path} ({total:.0f}s)")
