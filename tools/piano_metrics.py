"""ピアノの録音の測定（ep28 の実録音検証と同じ指標）：2.8kHz以下の重心、1/3オクターブの 63Hz・1kHz・2kHz 帯（最大帯域比）、
1分あたりの打鍵数、音量の幅（50msごとの音量の10〜90%）。
使い方: python3 piano_metrics.py <音声ファイル> [開始秒] [秒数]
"""
import sys, subprocess, numpy as np
from scipy.signal import find_peaks
a = ["ffmpeg", "-loglevel", "error"]
if len(sys.argv) > 2: a += ["-ss", sys.argv[2]]
if len(sys.argv) > 3: a += ["-t", sys.argv[3]]
raw = subprocess.run(a + ["-i", sys.argv[1], "-ac", "1", "-ar", "44100", "-f", "f32le", "-"], capture_output=True).stdout
x = np.frombuffer(raw, np.float32).astype(float); sr = 44100
win, hop = 4096, 1024
fr = np.lib.stride_tricks.sliding_window_view(x, win)[::hop] * np.hanning(win)
S = np.abs(np.fft.rfft(fr, axis=1)) ** 2; f = np.fft.rfftfreq(win, 1 / sr)
P = S.mean(0)
m = f <= 2800
cen = (P[m] * f[m]).sum() / P[m].sum()
centers = 1000 * 2.0 ** (np.arange(-13, 5) / 3)  # 50Hz〜2.5kHz
bl = {fc: 10 * np.log10(P[(f >= fc / 2 ** (1 / 6)) & (f < fc * 2 ** (1 / 6))].sum() + 1e-15) for fc in centers}
mx = max(bl.values())
def band(fc): return bl[min(bl, key=lambda c: abs(c - fc))] - mx
# 打鍵（スペクトルの増え方）
Sm = np.sqrt(S)
flux = np.maximum(np.diff(np.log1p(100 * Sm[:, f < 5000] / (Sm.max() + 1e-12)), axis=0), 0).sum(1)
flux = np.convolve(flux, np.ones(3) / 3, "same")
pk, _ = find_peaks(flux, height=np.median(flux) + 2.0 * np.std(flux), distance=int(0.08 * sr / hop))
dur = len(x) / sr
h = int(0.05 * sr); e = 10 * np.log10((x[: len(x) // h * h].reshape(-1, h) ** 2).mean(1) + 1e-12)
e = e[e > e.max() - 60]
print(f"{sys.argv[1].split('/')[-1]}: 重心(≤2.8k) {cen:.0f}Hz  63Hz {band(63):.0f}dB  1kHz {band(1000):.0f}dB  2kHz {band(2000):.0f}dB  "
      f"打鍵 {len(pk) / dur * 60:.0f}/分  音量の幅(10-90%) {np.percentile(e, 90) - np.percentile(e, 10):.0f}dB  ({dur:.0f}秒)")
