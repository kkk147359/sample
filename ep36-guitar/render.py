"""MIDI をナイロン弦ギターの音源で鳴らし、部屋の響き・音の整え（70Hz以下カット、120Hz付近少し下げ、3kHz以上なだらかに下げる）・音量合わせをする。
使い方: python3 render.py <入力.mid> <出力.wav> [音源 sf2/sf3]
"""
import subprocess
import sys
import tempfile

import numpy as np
from scipy.io import wavfile
from scipy.signal import butter, fftconvolve, sosfilt

mid, out = sys.argv[1], sys.argv[2]
sf = sys.argv[3] if len(sys.argv) > 3 else "/usr/share/sounds/sf2/FluidR3_GM.sf2"
SR = 44100

with tempfile.NamedTemporaryFile(suffix=".wav") as tmp:
    subprocess.run(["fluidsynth", "-ni", "-R", "0", "-C", "0", "-g", "0.6", "-r", str(SR), "-F", tmp.name, sf, mid],
                   check=True, capture_output=True)
    sr, x = wavfile.read(tmp.name)
x = x.astype(np.float64) / 32768
if x.ndim == 1:
    x = np.stack([x, x], 1)

# 部屋の響き：灯りを落とした小さな部屋（約1.4秒、高い音ほど早く消える）
rng = np.random.default_rng(7)
n = int(1.6 * SR)
tt = np.arange(n) / SR
ir = []
for ch in range(2):
    noise = rng.standard_normal(n)
    lo = sosfilt(butter(2, 2500, fs=SR, output="sos"), noise) * np.exp(-tt * 6.9 / 1.4)
    hi = sosfilt(butter(2, 2500, btype="high", fs=SR, output="sos"), noise) * np.exp(-tt * 6.9 / 0.5)
    r = lo + 0.5 * hi
    r[: int(0.012 * SR)] = 0
    ir.append(r / np.sqrt((r ** 2).sum()))
wet = np.stack([fftconvolve(x[:, c], ir[c])[: len(x)] for c in range(2)], 1)
y = x + 0.22 * wet

# 音の整え
y = sosfilt(butter(2, 70, btype="high", fs=SR, output="sos"), y, axis=0)


def peaking(sig, fc, gain_db, q):
    a = 10 ** (gain_db / 40)
    w = 2 * np.pi * fc / SR
    al = np.sin(w) / (2 * q)
    b = [1 + al * a, -2 * np.cos(w), 1 - al * a]
    aa = [1 + al / a, -2 * np.cos(w), 1 - al / a]
    from scipy.signal import lfilter
    return lfilter(np.array(b) / aa[0], np.array(aa) / aa[0], sig, axis=0)


def shelf_high(sig, fc, gain_db):
    from scipy.signal import lfilter
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


y = peaking(y, 120, -2.5, 1.0)
y = peaking(y, 1000, -7.0, 1.4)  # 音源の1kHz付近の山を実録音（-19〜-24dB）に合わせる
y = shelf_high(y, 3000, -3.0)
y = sosfilt(butter(2, 9000, fs=SR, output="sos"), y, axis=0)

# フェード
fi, fo = int(3 * SR), int(6 * SR)
y[:fi] *= np.linspace(0, 1, fi)[:, None] ** 2
y[-fo:] *= np.linspace(1, 0, fo)[:, None] ** 2
y /= np.abs(y).max() + 1e-9
y *= 0.5
wavfile.write(out, SR, (y * 32767).astype(np.int16))
