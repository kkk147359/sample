"""長い音声の急な音・無音の検査を30分ずつ行う（sudden.py は8時間をまとめて読むとメモリが足りない）。
使い方: python3 sudden_long.py <音声ファイル> <秒数>
急な音：10msごとの音量が直前1.5秒の平均よりどれだけ大きいか（200Hz〜6kHz）。各区切りの先頭5秒は除く。
あわせて1秒ごとの音量（dBFS）の最小と、4〜5kHz帯の割合を出す。
"""
import subprocess
import sys

import numpy as np
from scipy.signal import butter, sosfilt

path, total = sys.argv[1], float(sys.argv[2])
sr, seg = 44100, 1800
sos = butter(2, [200, 6000], btype="band", fs=sr, output="sos")
mx, p99s, mins, r45 = 0.0, [], [], []
for s in range(0, int(total), seg):
    raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-ss", str(max(0, s - 5)), "-t", str(seg + 5), "-i", path,
                          "-ac", "1", "-ar", str(sr), "-f", "f32le", "-"], capture_output=True).stdout
    x = np.frombuffer(raw, np.float32).astype(float)
    y = sosfilt(sos, x)
    h = 441
    e = (y[: len(y) // h * h].reshape(-1, h) ** 2).mean(1)
    prev = np.convolve(e, np.ones(150) / 150)[: len(e)]
    prev = np.concatenate([[e[0]], prev[:-1]])
    j = 10 * np.log10((e + 1e-12) / (prev + 1e-12))[500:]
    if s + seg >= total:
        j = j[:-300]
    mx = max(mx, j.max())
    p99s.append(np.percentile(j, 99))
    core = x[(5 if s else 3) * sr:]
    core = core[: len(core) // sr * sr]
    if s + seg >= total:
        core = core[: -3 * sr]
    w = 10 * np.log10((core.reshape(-1, sr) ** 2).mean(1) + 1e-15)
    mins.append(w.min())
    f = np.fft.rfftfreq(65536, 1 / sr)
    P = np.abs(np.fft.rfft(core[: 65536 * (len(core) // 65536)].reshape(-1, 65536) * np.hanning(65536), axis=1)) ** 2
    r45.append(P[:, (f >= 4000) & (f < 5000)].sum() / P[:, (f > 20)].sum() * 100)
    print(f"  {s // 60:4d}分〜 急な音 上位1% {p99s[-1]:.1f}dB 最大 {j.max():.1f}dB  1秒最小 {w.min():.1f}dBFS  4-5kHz {r45[-1]:.2f}%", flush=True)
print(f"全体: 急な音 最大 {mx:.1f}dB（上位1%の最大 {max(p99s):.1f}dB）、1秒ごとの最小 {min(mins):.1f}dBFS、4〜5kHz 最大 {max(r45):.2f}%")
