"""ページをめくる音を1回ずつ切り出して測る：長さ、立ち上がり（ピークの-20dB→ピーク）、山の数（持ち上げ＋着地の2段か）、
間隔、1/3オクターブ配分（ピーク基準dB）、重心周波数、スペクトル平坦度、4〜5kHz帯の割合、下地との差。
使い方: python3 pages.py <音声ファイル> [しきい値dB(下地から) 既定12]
"""
import subprocess
import sys

import numpy as np
from scipy.signal import butter, find_peaks, sosfiltfilt

sr = 44100
raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", sys.argv[1], "-ac", "1", "-ar", str(sr), "-f", "f32le", "-"],
                     capture_output=True).stdout
x = np.frombuffer(raw, np.float32).astype(float)
thr_db = float(sys.argv[2]) if len(sys.argv) > 2 else 12.0
x = sosfiltfilt(butter(2, 60, btype="high", fs=sr, output="sos"), x)
h = 441  # 10ms
e = (x[: len(x) // h * h].reshape(-1, h) ** 2).mean(1)
edb = 10 * np.log10(e + 1e-12)
floor = np.percentile(edb, 10)
act = edb > floor + thr_db
# 150ms 以内のすき間はつなぐ
idx = np.where(act)[0]
events = []
if len(idx):
    s = p = idx[0]
    for i in idx[1:]:
        if i - p > 15:
            events.append((s, p)); s = i
        p = i
    events.append((s, p))
events = [(a, b) for a, b in events if b - a >= 8]  # 80ms 以上
cent = 1000 * 2 ** (np.arange(-12, 13) / 3)  # 63Hz〜16kHz
cent = cent[(cent >= 100) & (cent <= 12500)]
print(f"== {sys.argv[1].split('/')[-1]}  {len(x)/sr:.1f}s  下地 {floor:.1f}dB  回数 {len(events)}")
starts = []
allbands = []
for a, b in events:
    seg = x[a * h : (b + 1) * h]
    ed = edb[a : b + 1]
    pk = ed.max()
    pi = ed.argmax()
    rise_from = np.where(ed[: pi + 1] < pk - 20)[0]
    rise = (pi - (rise_from[-1] if len(rise_from) else 0)) * 10
    peaks, _ = find_peaks(ed, prominence=6, distance=8)
    w = np.hanning(len(seg))
    f = np.fft.rfftfreq(len(seg), 1 / sr)
    P = np.abs(np.fft.rfft(seg * w)) ** 2
    bands = np.array([P[(f >= c / 2 ** (1 / 6)) & (f < c * 2 ** (1 / 6))].sum() for c in cent])
    allbands.append(bands)
    m = (f > 100) & (f < 12000)
    centroid = (f[m] * P[m]).sum() / P[m].sum()
    flat = np.exp(np.mean(np.log(P[m] + 1e-20))) / np.mean(P[m])
    r45 = P[(f >= 4000) & (f < 5000)].sum() / P[m].sum() * 100
    starts.append(a * 10 / 1000)
    print(f"  {a*10/1000:7.2f}s 長さ {(b-a+1)*10:4d}ms 立ち上がり {rise:3d}ms 山 {len(peaks)} ピーク {pk-floor:5.1f}dB(下地比) "
          f"重心 {centroid:5.0f}Hz 平坦度 {flat:.3f} 4-5kHz {r45:4.1f}%")
if allbands:
    B = np.sum(allbands, 0)
    B = 10 * np.log10(B / B.max() + 1e-12)
    print("  1/3oct(合計, 最大比dB):", " ".join(f"{c:.0f}:{v:.0f}" for c, v in zip(cent, B)))
if len(starts) > 1:
    d = np.diff(starts)
    print(f"  間隔 中央 {np.median(d):.2f}s 最小 {d.min():.2f}s 最大 {d.max():.2f}s")
