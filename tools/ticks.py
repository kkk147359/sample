"""時計のチク・タクを1打ずつ切り出して測る：間隔（チクとタクの非対称）、強さの差とばらつき、立ち上がり、
余韻（-20dBまでの時間×3）、1/3オクターブ配分（打音の直後50ms・共鳴0.05〜0.3秒）、共鳴の山、打音と下地の音量差。
使い方: python3 ticks.py <音声ファイル> [開始秒] [長さ秒]
"""
import subprocess
import sys

import numpy as np
from scipy.signal import butter, find_peaks, sosfiltfilt

sr = 44100
args = ["ffmpeg", "-loglevel", "error"]
if len(sys.argv) > 2:
    args += ["-ss", sys.argv[2]]
if len(sys.argv) > 3:
    args += ["-t", sys.argv[3]]
raw = subprocess.run(args + ["-i", sys.argv[1], "-ac", "1", "-ar", str(sr), "-f", "f32le", "-"], capture_output=True).stdout
x = np.frombuffer(raw, np.float32).astype(float)
dur = len(x) / sr

xb = sosfiltfilt(butter(4, [400, 10000], btype="band", fs=sr, output="sos"), x)
hop = 44  # 1ms
e = np.sqrt(np.convolve(xb ** 2, np.ones(hop) / hop, "same"))[::hop]
le = 20 * np.log10(e + 1e-9)
bg = np.percentile(le, 20)
top = np.percentile(le, 99.5)
# 主な打音だけ拾う（1打の中の小さな追い打ちは拾わない）：最大付近から15dB以内、300ms以上離れたもの
pk, _ = find_peaks(le, height=top - 15, distance=300)
on = pk / 1000.0
print(f"{sys.argv[1].split('/')[-1]}: {len(on)}打 / {dur:.1f}秒（1分に{len(on) / dur * 60:.0f}打）  下地(400Hz〜10kHz) {bg:.1f}dB")
if len(on) < 6:
    sys.exit()
ioi = np.diff(on)
print(f"  間隔 中央値 {np.median(ioi):.3f}s  奇数番目 {ioi[0::2].mean():.3f}s  偶数番目 {ioi[1::2].mean():.3f}s  "
      f"ゆらぎ(標準偏差) {ioi[0::2].std() * 1000:.1f}/{ioi[1::2].std() * 1000:.1f}ms")
lv = le[pk]
print(f"  打音の強さ（下地との差） 中央値 {np.median(lv - bg):.1f}dB  奇数 {lv[0::2].mean() - bg:.1f}dB  偶数 {lv[1::2].mean() - bg:.1f}dB  "
      f"ばらつき {lv[0::2].std():.1f}/{lv[1::2].std():.1f}dB")

centers = 1000 * 2.0 ** (np.arange(-15, 12) / 3)
F = np.fft.rfftfreq(1 << 14, 1 / sr)
rise, t20, sub = [], [], []
specA, specB = {0: [], 1: []}, {0: [], 1: []}
for k, p in enumerate(pk):
    seg = le[p - 30 : p + 400]
    if len(seg) < 430:
        continue
    base = seg[:15].mean()
    lvl = le[p]
    a = np.argmax(seg >= base + 0.1 * (lvl - base))
    rise.append(30 - a)
    tail = seg[30:]
    n = np.argmax(tail < lvl - 20) if (tail < lvl - 20).any() else len(tail)
    t20.append(n)
    # 1打のあとの小さな打音（ガンギ車の2段目の音など）
    sp, _ = find_peaks(seg[32:150], height=lvl - 20, prominence=4)
    sub.append(len(sp))
    s = int(on[k] * sr) - int(0.003 * sr)
    w1 = x[s : s + int(0.05 * sr)]
    w2 = x[s + int(0.05 * sr) : s + int(0.3 * sr)]
    if len(w2) == int(0.25 * sr):
        specA[k % 2].append(np.abs(np.fft.rfft(w1 * np.hanning(len(w1)), 1 << 14)) ** 2)
        specB[k % 2].append(np.abs(np.fft.rfft(w2 * np.hanning(len(w2)), 1 << 14)) ** 2)
print(f"  立ち上がり(10%→最大) 中央値 {np.median(rise):.0f}ms   余韻(-20dBまで) 中央値 {np.median(t20):.0f}ms p90 {np.percentile(t20, 90):.0f}ms   "
      f"1打の中の追い打ち(120ms以内,-20dB以内) 平均 {np.mean(sub):.1f}個")


def thirds(S):
    out = []
    for fc in centers:
        m = (F >= fc / 2 ** (1 / 6)) & (F < fc * 2 ** (1 / 6))
        out.append(10 * np.log10(S[m].sum() + 1e-20))
    return np.array(out)


for name, sp in (("打音の直後50ms", specA), ("共鳴0.05〜0.3秒", specB)):
    for par in (0, 1):
        if not sp[par]:
            continue
        S = np.mean(sp[par], 0)
        t = thirds(S)
        t -= t.max()
        cen = (S * F).sum() / S.sum()
        hf = S[(F >= 3000)].sum() / S.sum()
        print(f"  [{name}・{'奇数' if par == 0 else '偶数'}] 重心 {cen:.0f}Hz  3kHz以上の割合 {hf * 100:.0f}%")
        print("    " + " ".join(f"{fc:.0f}:{v:.0f}" for fc, v in zip(centers, t)))
S = np.mean(specB[0] + specB[1], 0)
Sd = 10 * np.log10(S + 1e-20)
m = (F > 80) & (F < 8000)
pp, _ = find_peaks(Sd[m], prominence=6, distance=int(30 / (F[1] - F[0])))
top = sorted(pp, key=lambda i: -Sd[m][i])[:10]
mx = Sd[m].max()
print("  共鳴の山: " + "  ".join(f"{F[m][i]:.0f}Hz:{Sd[m][i] - mx:.0f}" for i in sorted(top)))

# 1打の平均的な音量の形（1msごと、最大を0dB）：追い打ちの位置と強さ
env = np.mean([10 ** (le[p - 5 : p + 150] / 10) for p in pk if p + 150 < len(le) and p > 5], 0)
envd = 10 * np.log10(env / env.max())
print("  平均の音量の形(ms:dB): " + " ".join(f"{t - 5}:{envd[t]:.0f}" for t in range(0, 155, 5)))
