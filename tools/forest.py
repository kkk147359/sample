"""夜の森の録音を、鳴き声のあとの響きと、鳴いていない間の空気に分けて測る。

python3 -I tools/forest.py <file> [声の帯域 低Hz 高Hz（既定 250 1000）]

- 鳴き声：声の帯域の 10ms ごとの音量で、背景（下から20%）+10dB を超えた区間。
- 響き：鳴き声が終わったあと、次の音までの間の音量の下がり方（dB/秒 → 60dB 下がるまでの秒数）と、
  終わって 50ms・200ms 後の音量（鳴き声の最大との差）。前後 1.5 秒に別の音がない鳴き声だけ。
- 間の空気：鳴き声の前後 3 秒を除いたところ。1/3 オクターブの配分（最大＝0dB）、重心、
  音量のゆらぎ（0.25秒ごと・5秒ごとの標準偏差。5秒ごとが大きいと風のようにうねる）、
  1秒あたりの小さな物音（500Hz より上が 6dB 以上はね上がる回数）、1秒ごとの音量。
"""
import subprocess
import sys

import numpy as np
from scipy.signal import butter, find_peaks, sosfilt

SR = 44100


def load(path):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32).astype(np.float64)


def levels(x, h):
    m = len(x) // h
    return 10 * np.log10(np.mean(x[: m * h].reshape(m, h) ** 2, 1) + 1e-14)


def main():
    path = sys.argv[1]
    lo, hi = (float(sys.argv[2]), float(sys.argv[3])) if len(sys.argv) > 3 else (250, 1000)
    x = load(path)
    h = int(0.01 * SR)
    lv = levels(sosfilt(butter(4, [lo, hi], btype="band", fs=SR, output="sos"), x), h)
    bg = np.percentile(lv, 20)
    on = lv > bg + 10
    segs = []
    for i in np.where(on)[0]:
        if segs and i - segs[-1][1] <= 3:
            segs[-1][1] = i
        else:
            segs.append([i, i])
    segs = [s for s in segs if s[1] - s[0] >= 5]
    print(f"{path.split('/')[-1]}: {len(x) / SR:.0f}秒、声の帯域 {lo:.0f}〜{hi:.0f}Hz の背景 {bg:.1f}dB、鳴き声 {len(segs)}個")

    # 響き
    rows = []
    for j, (a, b) in enumerate(segs):
        prev_end = segs[j - 1][1] if j else -999
        nxt = segs[j + 1][0] if j + 1 < len(segs) else len(lv)
        if a - prev_end < 150 or nxt - b < 150:
            continue
        pk = lv[a: b + 1].max()
        if pk - bg < 18:
            continue
        tail = lv[b + 1: min(nxt, b + 300)]
        k = np.where(tail < bg + 3)[0]
        k = k[0] if len(k) else len(tail)
        if k < 4:
            continue
        t = np.arange(k) * 0.01
        slope = np.polyfit(t, tail[:k], 1)[0]
        rows.append((a * 0.01, pk - bg, -60 / slope if slope < 0 else np.inf, tail[min(5, k - 1)] - pk,
                     tail[min(20, k - 1)] - pk, k * 10))
    if rows:
        for r in rows[:12]:
            print(f"  響き {r[0]:7.2f}s 声 背景+{r[1]:.0f}dB  60dB下がるまで {r[2]:.2f}秒  50ms後 {r[3]:+.0f}dB  200ms後 {r[4]:+.0f}dB  背景+3dBまで {r[5]}ms")
        t60 = np.array([r[2] for r in rows if np.isfinite(r[2])])
        if len(t60):
            print(f"  響き 中央 {np.median(t60):.2f}秒（{len(t60)}個、{t60.min():.2f}〜{t60.max():.2f}）")
    else:
        print("  響き：前後があいた大きな鳴き声なし")

    # 間の空気
    mask = np.ones(len(lv), bool)
    for a, b in segs:
        mask[max(0, a - 300): b + 300] = False
    keep = np.repeat(mask, h)[: len(x)]
    q = x[: len(keep)][keep[: len(x)]]
    if len(q) < 5 * SR:
        print("  間の空気：鳴き声のない区間が5秒未満")
        return
    win, hop = 4096, 1024
    fr = np.lib.stride_tricks.sliding_window_view(q, win)[::hop] * np.hanning(win)
    S = np.abs(np.fft.rfft(fr, axis=1)) ** 2
    f = np.fft.rfftfreq(win, 1 / SR)
    centers = 1000 * 2.0 ** (np.arange(-14, 11) / 3)
    band = []
    for fc in centers:
        m = (f >= fc / 2 ** (1 / 6)) & (f < fc * 2 ** (1 / 6))
        band.append(10 * np.log10(S[:, m].sum(1).mean() + 1e-20))
    band = np.array(band) - max(band)
    print(f"  間の空気 {len(q) / SR:.0f}秒：1/3oct（最大=0）")
    print("   " + "  ".join(f"{fc:.0f}:{b:.0f}" for fc, b in zip(centers, band)))
    P = S.mean(0)
    print(f"   重心 {(f * P).sum() / P.sum():.0f}Hz  80Hz以下 {100 * P[f < 80].sum() / P.sum():.1f}%  "
          f"4〜5kHz {100 * P[(f >= 4000) & (f < 5000)].sum() / P.sum():.2f}%")
    l25 = levels(q, int(0.25 * SR))
    l5 = levels(q, int(5 * SR))
    print(f"   ゆらぎ 0.25秒ごと {np.std(l25):.1f}dB・5秒ごと {np.std(l5):.1f}dB")
    e = 10 * np.log10(S[:, f > 500].sum(1) + 1e-20)
    pk, _ = find_peaks(np.diff(e), height=6, distance=int(0.03 * SR / hop))
    print(f"   小さな物音 {len(pk) / (len(q) / SR):.2f}回/秒")
    l1 = levels(q, SR)
    print(f"   1秒ごとの音量 中央 {np.median(l1):.1f}dBFS（声の最大 {lv.max():.1f}dB との差 {lv.max() - np.median(l1):.0f}dB）")


if __name__ == "__main__":
    main()
