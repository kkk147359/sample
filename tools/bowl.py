"""シンギングボウル（打って鳴らすもの）を測る：打った回数と間隔、倍音（周波数・基音との比・強さ）、
倍音ごとの減衰（dB/秒→T60）、うなり（倍音の音量が揺れる速さ）、立ち上がり、3kHz以上の割合。
使い方: python3 bowl.py <音声ファイル>
"""
import subprocess
import sys

import numpy as np
from scipy.signal import find_peaks

sr = 44100
raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", sys.argv[1], "-ac", "1", "-ar", str(sr), "-f", "f32le", "-"], capture_output=True).stdout
x = np.frombuffer(raw, np.float32).astype(float)
dur = len(x) / sr
hop = 441
e = 20 * np.log10(np.sqrt(np.convolve(x ** 2, np.ones(hop) / hop, "same"))[::hop] + 1e-9)
de = np.diff(e)
on, _ = find_peaks(de, height=6, distance=int(1.5 * sr / hop))
on = [o for o in on if e[min(o + 5, len(e) - 1)] > e.max() - 30]
print(f"{sys.argv[1].split('/')[-1]}: {dur:.1f}秒、打った回数 {len(on)}  時刻 {[round(o * hop / sr, 1) for o in on][:12]}")
if len(on) > 1:
    print(f"  打つ間隔 中央値 {np.median(np.diff(on)) * hop / sr:.1f}秒")
o = on[0] if on else int(np.argmax(e))
s = o * hop
# 立ち上がり：10%→最大
seg = np.abs(x[s : s + int(0.5 * sr)])
env = np.convolve(seg, np.ones(44) / 44, "same")
pk = np.argmax(env)
a = np.argmax(env > 0.1 * env[pk])
print(f"  立ち上がり(10%→最大) {(pk - a) / sr * 1000:.0f}ms")
end = (on[1] * hop) if len(on) > 1 else len(x)
y = x[s:end]
w = y[int(0.3 * sr) : int(2.3 * sr)]
N = 1 << 18
S = 20 * np.log10(np.abs(np.fft.rfft(w * np.hanning(len(w)), N)) + 1e-12)
F = np.fft.rfftfreq(N, 1 / sr)
m = (F > 80) & (F < 12000)
p, _ = find_peaks(S[m], prominence=12, distance=int(15 / (F[1] - F[0])))
p = sorted(p, key=lambda i: -S[m][i])[:8]
p = sorted(p)
ff = F[m][p]
lv = S[m][p] - S[m][p].max()
f0 = ff[np.argmax(lv > -25)] if len(ff) else 0
print("  倍音（周波数Hz・基音との比・強さdB・減衰T60秒・うなりHz）:")
win, hp2 = 8192, 2048
frames = np.lib.stride_tricks.sliding_window_view(y[: int(min(len(y), 20 * sr))], win)[::hp2] * np.hanning(win)
SP = np.abs(np.fft.rfft(frames, 1 << 15, axis=1))
FF = np.fft.rfftfreq(1 << 15, 1 / sr)
t = np.arange(len(SP)) * hp2 / sr
for f, l in zip(ff, lv):
    b = (FF > f * 0.993) & (FF < f * 1.007)
    db = 20 * np.log10(SP[:, b].max(1) + 1e-12)
    sel = (t > 0.5) & (t < min(12, t[-1])) & (db > db.max() - 40)
    if sel.sum() > 5:
        slope = np.polyfit(t[sel], db[sel], 1)[0]
        t60 = -60 / slope if slope < 0 else np.inf
        resid = db[sel] - np.polyval(np.polyfit(t[sel], db[sel], 1), t[sel])
        spec = np.abs(np.fft.rfft(resid * np.hanning(len(resid)), 1024))
        fm = np.fft.rfftfreq(1024, hp2 / sr)
        mm = (fm > 0.15) & (fm < 8)
        beat = fm[mm][np.argmax(spec[mm])] if mm.any() else 0
        depth = resid.std()
    else:
        t60, beat, depth = np.nan, 0, 0
    print(f"    {f:7.1f}Hz  比{f / f0 if f0 else 0:5.2f}  {l:6.1f}dB  T60 {t60:5.1f}s  うなり {beat:.2f}Hz（深さ{depth:.1f}dB）")
tot = (10 ** (S[m] / 10)).sum()
hf = (10 ** (S[(F >= 3000) & (F < 12000)] / 10)).sum() / tot
print(f"  3kHz以上の割合 {hf * 100:.1f}%   基音 {f0:.1f}Hz")
