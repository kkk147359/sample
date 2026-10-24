"""4〜5kHz帯の割合を、長さを決めた区間ごとに出す（瞬間の最大ではなく、聞いて残る程度を見る）。
使い方: python3 hf_window.py <音声ファイル> [区間秒=10]
"""
import sys, subprocess, numpy as np
raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", sys.argv[1], "-ac", "1", "-ar", "44100", "-f", "f32le", "-"], capture_output=True).stdout
x = np.frombuffer(raw, np.float32).astype(float); sr = 44100
w = float(sys.argv[2]) if len(sys.argv) > 2 else 10
n = int(w * sr); r = []
for i in range(0, len(x) - n + 1, n):
    X = np.abs(np.fft.rfft(x[i:i + n] * np.hanning(n))) ** 2; f = np.fft.rfftfreq(n, 1 / sr)
    r.append(X[(f >= 4000) & (f < 5000)].sum() / X.sum() * 100)
r = np.array(r)
print(f"{sys.argv[1].split('/')[-1]}: 4〜5kHz（{w:.0f}秒ごと） 中央値 {np.median(r):.2f}%  最大 {r.max():.2f}%")
