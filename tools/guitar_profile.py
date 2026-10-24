"""ギター演奏の録音を1行の数値にまとめる（実録音と試作の比較用）。
帯域の音量（全体比 dB）：胴鳴り 90〜250Hz、中域 250Hz〜1kHz、1〜3kHz、3〜5kHz。重心、4〜5kHz割合、1分の音数、音の間隔の中央値、
急な音（10msごとの音量が直前1.5秒の平均よりどれだけ大きいか、上位1%と最大）、音の立ち上がりの鋭さ（立ち上がり後30msの高域比）。
使い方: python3 guitar_profile.py <音声> [開始秒] [長さ秒]
"""
import subprocess
import sys

import numpy as np
from scipy.signal import butter, find_peaks, sosfilt

p = sys.argv[1]
ss = sys.argv[2] if len(sys.argv) > 2 else "5"
du = sys.argv[3] if len(sys.argv) > 3 else "90"
raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-ss", ss, "-t", du, "-i", p, "-ac", "1", "-ar", "44100", "-f", "f32le", "-"],
                     capture_output=True).stdout
x = np.frombuffer(raw, np.float32).astype(float)
sr = 44100
win, hop = 4096, 2048
fr = np.lib.stride_tricks.sliding_window_view(x, win)[::hop] * np.hanning(win)
S = np.abs(np.fft.rfft(fr, axis=1)) ** 2
f = np.fft.rfftfreq(win, 1 / sr)
tot = S[:, (f > 60) & (f < 10000)].sum()
def band(lo, hi):
    return 10 * np.log10(S[:, (f >= lo) & (f < hi)].sum() / tot + 1e-12)
cen = np.median((S * f).sum(1) / (S.sum(1) + 1e-12))
loud = S.sum(1) > np.percentile(S.sum(1), 30)
r45 = np.median(S[loud][:, (f >= 4000) & (f < 5000)].sum(1) / S[loud].sum(1)) * 100
# 音数
h2, w2 = 256, 1024
fr2 = np.lib.stride_tricks.sliding_window_view(x, w2)[::h2] * np.hanning(w2)
S2 = np.abs(np.fft.rfft(fr2, axis=1))
flux = np.maximum(np.diff(np.log1p(100 * S2), axis=0), 0).sum(1)
flux = np.convolve(flux, np.ones(3) / 3, "same")
pk, _ = find_peaks(flux, height=np.median(flux) + 2.5 * np.std(flux), distance=int(0.08 * sr / h2))
dur = len(x) / sr
ioi = np.median(np.diff(pk)) * h2 / sr if len(pk) > 2 else 0
# 急な音
y = sosfilt(butter(2, [200, 6000], btype="band", fs=sr, output="sos"), x)
e = np.sqrt(np.convolve(y ** 2, np.ones(441) / 441, "valid")[::441] + 1e-12)
db = 20 * np.log10(e)
k = 150
ref = np.array([20 * np.log10(np.mean(e[i - k:i]) + 1e-12) for i in range(k, len(e))])
jump = db[k:] - ref
jump = jump[db[k:] > db.max() - 40]
# 立ち上がりの明るさ：音の頭30msの 2〜5kHz / 全体
fb = (f > 2000) & (f < 5000)
att = []
for i in pk:
    s0 = i * h2
    seg = x[s0:s0 + 1323]
    if len(seg) < 1323:
        continue
    A = np.abs(np.fft.rfft(seg * np.hanning(len(seg)))) ** 2
    fa = np.fft.rfftfreq(len(seg), 1 / sr)
    att.append(10 * np.log10(A[(fa > 2000) & (fa < 5000)].sum() / (A[fa > 60].sum() + 1e-12) + 1e-12))
print(f"body90-250 {band(90,250):6.1f}  mid250-1k {band(250,1000):6.1f}  1-3k {band(1000,3000):6.1f}  3-5k {band(3000,5000):6.1f}  "
      f"重心 {cen:5.0f}Hz  4-5k {r45:.2f}%  音数 {len(pk)/dur*60:5.1f}/分  間隔 {ioi:.2f}s  急 p99 {np.percentile(jump,99):4.1f} max {jump.max():4.1f}dB  "
      f"頭2-5k {np.median(att) if att else 0:5.1f}dB")
