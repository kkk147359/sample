"""MIDI をナイロン弦ギターの音源で鳴らし、部屋の響き・音の整え（70Hz以下カット、120Hz付近少し下げ、1kHz付近と3kHz以上を下げる）をする。
使い方: python3 render.py <入力.mid> <出力.wav> [音源 sf2/sf3]
このあと ffmpeg で acompressor（急な音をおさえる）と音量合わせをする（README）。長い版は render_long.py。
"""
import subprocess
import sys
import tempfile

import numpy as np
from scipy.io import wavfile
from scipy.signal import butter, fftconvolve, lfilter, sosfilt

SR = 44100
SF = "/usr/share/sounds/sf2/FluidR3_GM.sf2"


def synth(mid, sf=SF):
    """fluidsynth で鳴らす（音源の残響・コーラスは切る）。ステレオ float を返す。"""
    with tempfile.NamedTemporaryFile(suffix=".wav") as tmp:
        subprocess.run(["fluidsynth", "-ni", "-R", "0", "-C", "0", "-g", "0.6", "-r", str(SR), "-F", tmp.name, sf, mid],
                       check=True, capture_output=True)
        _, x = wavfile.read(tmp.name)
    x = x.astype(np.float64) / 32768
    return np.stack([x, x], 1) if x.ndim == 1 else x


def _ir():
    """部屋の響き：灯りを落とした小さな部屋（約1.4秒、高い音ほど早く消える）"""
    rng = np.random.default_rng(7)
    n = int(1.6 * SR)
    tt = np.arange(n) / SR
    ir = []
    for _ in range(2):
        noise = rng.standard_normal(n)
        lo = sosfilt(butter(2, 2500, fs=SR, output="sos"), noise) * np.exp(-tt * 6.9 / 1.4)
        hi = sosfilt(butter(2, 2500, btype="high", fs=SR, output="sos"), noise) * np.exp(-tt * 6.9 / 0.5)
        r = lo + 0.5 * hi
        r[: int(0.012 * SR)] = 0
        ir.append(r / np.sqrt((r ** 2).sum()))
    return ir


IR = _ir()


def peaking(sig, fc, gain_db, q):
    a = 10 ** (gain_db / 40)
    w = 2 * np.pi * fc / SR
    al = np.sin(w) / (2 * q)
    b = np.array([1 + al * a, -2 * np.cos(w), 1 - al * a])
    aa = np.array([1 + al / a, -2 * np.cos(w), 1 - al / a])
    return lfilter(b / aa[0], aa / aa[0], sig, axis=0)


def shelf_high(sig, fc, gain_db):
    a = 10 ** (gain_db / 40)
    w = 2 * np.pi * fc / SR
    al = np.sin(w) / 2 * np.sqrt(2)
    c = np.cos(w)
    b0 = a * ((a + 1) + (a - 1) * c + 2 * np.sqrt(a) * al)
    b1 = -2 * a * ((a - 1) + (a + 1) * c)
    b2 = a * ((a + 1) + (a - 1) * c - 2 * np.sqrt(a) * al)
    a0 = (a + 1) - (a - 1) * c + 2 * np.sqrt(a) * al
    a1 = 2 * ((a - 1) - (a + 1) * c)
    a2 = (a + 1) - (a - 1) * c - 2 * np.sqrt(a) * al
    return lfilter(np.array([b0, b1, b2]) / a0, np.array([1, a1 / a0, a2 / a0]), sig, axis=0)


def process(x):
    """響き＋EQ。入力も出力もステレオ float（音量はそのまま）。"""
    wet = np.stack([fftconvolve(x[:, c], IR[c])[: len(x)] for c in range(2)], 1)
    y = x + 0.22 * wet
    y = sosfilt(butter(2, 70, btype="high", fs=SR, output="sos"), y, axis=0)
    y = peaking(y, 120, -2.5, 1.0)
    y = peaking(y, 1000, -7.0, 1.4)  # 音源の1kHz付近の山を実録音（-19〜-24dB）に合わせる
    y = shelf_high(y, 3000, -3.0)
    return sosfilt(butter(2, 9000, fs=SR, output="sos"), y, axis=0)


if __name__ == "__main__":
    mid, out = sys.argv[1], sys.argv[2]
    y = process(synth(mid, sys.argv[3] if len(sys.argv) > 3 else SF))
    fi, fo = int(3 * SR), int(6 * SR)
    y[:fi] *= np.linspace(0, 1, fi)[:, None] ** 2
    y[-fo:] *= np.linspace(1, 0, fo)[:, None] ** 2
    y /= np.abs(y).max() + 1e-9
    y *= 0.5
    wavfile.write(out, SR, (y * 32767).astype(np.int16))
