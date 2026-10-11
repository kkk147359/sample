"""編み物の実録音を測る：針の打音（カチ）と毛糸のこすれ（打音の合間）を分けて、
打音の間隔・まとまり（1目ぶんの打音の数）、打音とこすれの音量差、それぞれの1/3オクターブ配分と重心、
全体の重心・平坦度・4〜5kHzの割合、急な音の指標。
使い方: python3 knit.py <音声ファイル> [開始秒] [長さ秒]
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
args += ["-i", sys.argv[1], "-ac", "1", "-ar", str(sr), "-f", "f32le", "-"]
x = np.frombuffer(subprocess.run(args, capture_output=True).stdout, np.float32).astype(float)
x = sosfiltfilt(butter(2, 40, btype="high", fs=sr, output="sos"), x)

# 打音の検出：2kHz以上の包絡（5ms）が直前の中央値より大きく跳ねた所
hp = sosfiltfilt(butter(4, 1500, btype="high", fs=sr, output="sos"), x)
h = int(0.005 * sr)
e = np.sqrt((hp[: len(hp) // h * h].reshape(-1, h) ** 2).mean(1) + 1e-12)
ed = 20 * np.log10(e)
base = np.array([np.median(ed[max(0, i - 100) : i + 1]) for i in range(len(ed))])
pk, _ = find_peaks(ed - base, height=9, distance=int(0.06 / 0.005))
t = pk * 0.005
print(f"== {sys.argv[1].split('/')[-1]}  長さ {len(x)/sr:.1f}秒  打音 {len(t)}回（{len(t)/(len(x)/sr)*60:.0f}回/分）")
if len(t) > 3:
    d = np.diff(t)
    print(f"  間隔 中央 {np.median(d):.2f}秒  25-75% {np.percentile(d,25):.2f}-{np.percentile(d,75):.2f}  0.25秒未満 {(d<0.25).mean()*100:.0f}%  1秒超 {(d>1).mean()*100:.0f}%")
    # まとまり：0.35秒以内に続く打音を1群に
    groups, cur = [], 1
    for v in d:
        if v < 0.35:
            cur += 1
        else:
            groups.append(cur)
            cur = 1
    groups.append(cur)
    g = np.array(groups)
    print(f"  まとまりの打音数 平均 {g.mean():.2f}  分布 1:{(g==1).mean()*100:.0f}% 2:{(g==2).mean()*100:.0f}% 3+:{(g>=3).mean()*100:.0f}%")
    pkv = ed[pk]
    print(f"  打音の強さ ばらつき(SD) {pkv.std():.1f}dB  範囲 {pkv.min()-pkv.max():.1f}dB")

# 打音の区間（各打音の-5ms〜+40ms）とそれ以外（こすれ）
mask = np.zeros(len(x), bool)
for s in t:
    a = int((s - 0.005) * sr)
    mask[max(0, a) : a + int(0.045 * sr)] = True


def third(sig):
    f = np.fft.rfftfreq(4096, 1 / sr)
    if len(sig) < 4096:
        return None
    fr = sig[: len(sig) // 4096 * 4096].reshape(-1, 4096) * np.hanning(4096)
    p = (np.abs(np.fft.rfft(fr, axis=1)) ** 2).mean(0)
    cs = [100 * 2 ** (k / 3) for k in range(-3, 21)]
    out = []
    for c in cs:
        sel = (f >= c / 2 ** (1 / 6)) & (f < c * 2 ** (1 / 6))
        out.append(10 * np.log10(p[sel].sum() + 1e-20))
    out = np.array(out)
    cen = (f * p).sum() / p.sum()
    flat = np.exp(np.mean(np.log(p[1:] + 1e-20))) / p[1:].mean()
    r45 = p[(f >= 4000) & (f < 5000)].sum() / p.sum()
    return cs, out - out.max(), cen, flat, r45, 10 * np.log10(np.mean(sig**2) + 1e-20)


for name, sig in [("打音", x[mask]), ("こすれ", x[~mask]), ("全体", x)]:
    r = third(sig)
    if r is None:
        continue
    cs, o, cen, flat, r45, lv = r
    sel = " ".join(f"{c:.0f}:{v:.0f}" for c, v in zip(cs, o) if c >= 120)
    print(f"  [{name}] 音量 {lv:.1f}dB 重心 {cen:.0f}Hz 平坦度 {flat:.3f} 4-5kHz {r45*100:.1f}%")
    print(f"     1/3oct {sel}")
