"""音源の測定：1/3オクターブの音量配分、帯域ごとのゆらぎ、重心周波数、スペクトル平坦度。
使い方: python3 analyze.py <wav>
"""
import sys

import numpy as np
from scipy.io import wavfile

sr, x = wavfile.read(sys.argv[1])
x = x.astype(np.float64)
if x.ndim == 2:
    x = x.mean(axis=1)
x /= 32768
x = x[int(5 * sr) : -int(8 * sr)]  # フェード部分を除く

win = 4096
hop = 2048
frames = np.lib.stride_tricks.sliding_window_view(x, win)[::hop] * np.hanning(win)
spec = np.abs(np.fft.rfft(frames, axis=1)) ** 2
freqs = np.fft.rfftfreq(win, 1 / sr)

centers = 1000 * 2.0 ** (np.arange(-17, 11) / 3)  # 20Hz〜10kHz
bands = []
for fc in centers:
    lo, hi = fc / 2 ** (1 / 6), fc * 2 ** (1 / 6)
    m = (freqs >= lo) & (freqs < hi)
    bands.append(spec[:, m].sum(axis=1))
bands = np.array(bands)  # (帯域, 時間)
db = 10 * np.log10(bands + 1e-15)
mean_db = 10 * np.log10(bands.mean(axis=1) + 1e-15)
peak = mean_db.max()

print("1/3オクターブ（最大帯域を0dBとした相対値）／時間ゆらぎ(標準偏差dB, 0.5秒平均)")
smooth = max(1, int(0.5 * sr / hop))
for fc, m, row in zip(centers, mean_db, db):
    r = np.convolve(10 ** (row / 10), np.ones(smooth) / smooth, mode="valid")
    sd = np.std(10 * np.log10(r + 1e-15))
    print(f"{fc:8.0f}Hz {m - peak:6.1f}dB  ゆらぎ{sd:5.1f}dB")

total = spec.sum(axis=1)
centroid = (spec * freqs).sum(axis=1) / (total + 1e-15)
p = spec[:, 1:] + 1e-15
flat = np.exp(np.log(p).mean(axis=1)) / p.mean(axis=1)
print(f"重心周波数 中央値 {np.median(centroid):.0f}Hz")
print(f"スペクトル平坦度 中央値 {np.median(flat):.3f}")
hf = spec[:, (freqs >= 4000) & (freqs < 5000)].sum(axis=1) / (total + 1e-15)
print(f"4〜5kHz帯の割合 中央値 {np.median(hf) * 100:.2f}%  最大 {hf.max() * 100:.2f}%")
rms = np.sqrt(np.mean(x ** 2))
print(f"RMS {20 * np.log10(rms):.1f}dBFS  ピーク {20 * np.log10(np.max(np.abs(x))):.1f}dBFS")
