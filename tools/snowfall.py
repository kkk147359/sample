"""枝から落ちる雪を1回ずつ切り出して測る：回数・間隔、長さ、立ち上がり、背景との差、
すべり（前半）と着地「ドフッ」（最後の山）の帯域配分、背景の重心・平坦度、4〜5kHz割合。
使い方: python3 snowfall.py <音声ファイル> [しきい値dB=8]
"""
import sys, subprocess, numpy as np
from scipy.signal import butter, sosfiltfilt
SR = 22050
def load(p):
    raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", p, "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"], capture_output=True).stdout
    return np.frombuffer(raw, np.float32).astype(float)
x = load(sys.argv[1]); th = float(sys.argv[2]) if len(sys.argv) > 2 else 8
xb = sosfiltfilt(butter(2, [80, 6000], btype='band', fs=SR, output='sos'), x)
hop = int(0.01 * SR)
e = (xb[:len(xb) // hop * hop].reshape(-1, hop) ** 2).mean(1)
le = 10 * np.log10(np.convolve(e, np.ones(3) / 3, 'same') + 1e-12)
bg = np.percentile(le, 20)
on = le > bg + th
# 0.3秒以内の切れ目はつなぐ
ev = []; i = 0
while i < len(on):
    if on[i]:
        j = i
        while j < len(on) and (on[j] or on[j:j + 30].any()): j += 1
        if j - i >= 5: ev.append((i, j))
        i = j
    else: i += 1
def bands(seg):
    S = np.abs(np.fft.rfft(seg * np.hanning(len(seg)))) ** 2; f = np.fft.rfftfreq(len(seg), 1 / SR)
    tot = S.sum() + 1e-15
    return [10 * np.log10(S[(f >= a) & (f < b)].sum() / tot + 1e-15) for a, b in [(50, 100), (100, 400), (400, 2000), (2000, 4000), (4000, 8000)]], (S * f).sum() / tot
print(f"{sys.argv[1].split('/')[-1]}: 長さ {len(x)/SR:.0f}秒  背景(20%点) {bg:.1f}dB  落下 {len(ev)}回")
print(" 開始s  長さs  立上り(-20dB→山)ms  背景差dB  前半重心Hz  着地重心Hz  着地 100-400Hz割合dB  着地の山が最後の1/3")
for a, b in ev:
    seg = le[a:b]; pk = a + int(np.argmax(seg))
    rise = (pk - a) * 10
    s = xb[a * hop:b * hop]; n = len(s)
    first = s[:max(n * 2 // 3, 256)]; last = xb[max(pk * hop - int(0.05 * SR), 0):pk * hop + int(0.1 * SR)]
    _, cf = bands(first); bl, cl = bands(last)
    print(f" {a/100:6.1f} {(b-a)/100:5.2f} {rise:6d} {seg.max()-bg:7.1f} {cf:9.0f} {cl:9.0f} {bl[1]:8.1f}   {'○' if pk >= a + (b - a) * 2 / 3 else '×'}")
if len(ev) > 1:
    g = np.diff([a / 100 for a, _ in ev]); print(f" 間隔 秒: 最短 {g.min():.1f}  中央 {np.median(g):.1f}  最長 {g.max():.1f}")
# 背景（落下のない部分）
mask = np.ones(len(le), bool)
for a, b in ev: mask[max(a - 50, 0):b + 50] = False
bgx = np.concatenate([x[k * hop:(k + 1) * hop] for k in np.where(mask)[0]]) if mask.any() else x
win = 4096; fr = np.lib.stride_tricks.sliding_window_view(bgx, win)[::2048] * np.hanning(win)
S = np.abs(np.fft.rfft(fr, axis=1)) ** 2; f = np.fft.rfftfreq(win, 1 / SR); tot = S.sum(1) + 1e-15
cen = np.median((S * f).sum(1) / tot); pp = S[:, 1:] + 1e-15
flat = np.median(np.exp(np.log(pp).mean(1)) / pp.mean(1)); hf = np.median(S[:, (f >= 4000) & (f < 5000)].sum(1) / tot) * 100
print(f" 背景: 重心 {cen:.0f}Hz  平坦度 {flat:.2f}  4-5kHz {hf:.2f}%  （{mask.mean()*100:.0f}%の区間）")
