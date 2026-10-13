"""鳥の声（フクロウの「ホー」）を1音ずつ測る。

python3 -I tools/hoot.py <file> [低い周波数Hz 高い周波数Hz]

- 10msごとの音量（指定帯域、既定 250〜1500Hz）。背景＝下から20%、背景+10dB を超えた区間を1音とする（30ms未満の切れ目はつなぐ）。
- 1音ごとに：長さ、基本周波数（始め・中・終わり、自己相関）、倍音 2〜4倍の大きさ（基本に対するdB）、
  倍音のあいだの息の音（倍音の山と谷の差）、立ち上がり・-20dBまでの減衰。
- 音と音の間隔、1.5秒以上あいたところで区切ったまとまり（フレーズ）の数・長さ・中の音の数。
"""
import subprocess
import sys

import numpy as np
from scipy.signal import butter, sosfilt

SR = 22050


def load(path):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32).astype(np.float64)


def f0_of(x):
    """自己相関で基本周波数（150〜1200Hz）"""
    x = x - x.mean()
    if len(x) < 512:
        return np.nan
    w = x * np.hanning(len(x))
    r = np.fft.irfft(np.abs(np.fft.rfft(w, 2 * len(w))) ** 2)[: len(w)]
    lo, hi = int(SR / 1200), int(SR / 150)
    k = lo + np.argmax(r[lo:hi])
    return SR / k if r[k] > 0.3 * r[0] else np.nan


def main():
    path = sys.argv[1]
    lo, hi = (float(sys.argv[2]), float(sys.argv[3])) if len(sys.argv) > 3 else (250, 1500)
    x = load(path)
    xb = sosfilt(butter(4, [lo, hi], btype="band", fs=SR, output="sos"), x)
    h = int(0.01 * SR)
    m = len(xb) // h
    lv = 10 * np.log10(np.mean(xb[: m * h].reshape(m, h) ** 2, 1) + 1e-12)
    bg = np.percentile(lv, 20)
    on = lv > bg + 10
    # 30ms 未満の切れ目をつなぐ
    idx = np.where(on)[0]
    segs = []
    for i in idx:
        if segs and i - segs[-1][1] <= 3:
            segs[-1][1] = i
        elif not segs or i > segs[-1][1]:
            segs.append([i, i])
    segs = [s for s in segs if s[1] - s[0] >= 5]  # 50ms 以上
    print(f"{path}: {len(x) / SR:.1f}秒、背景 {bg:.1f}dB、音 {len(segs)}個（帯域 {lo:.0f}〜{hi:.0f}Hz）")
    rows = []
    for a, b in segs:
        s = x[a * h : (b + 1) * h]
        n = len(s)
        thirds = [s[i * n // 3 : (i + 1) * n // 3] for i in range(3)]
        f = [f0_of(t) for t in thirds]
        fm = f0_of(s[n // 4 : 3 * n // 4]) if n > 2048 else f[1]
        spec = np.abs(np.fft.rfft(s * np.hanning(n), 1 << int(np.ceil(np.log2(n * 4)))))
        fr = np.fft.rfftfreq((len(spec) - 1) * 2, 1 / SR)

        def pk(f0):
            sel = (fr > f0 * 0.93) & (fr < f0 * 1.07)
            return 20 * np.log10(spec[sel].max() + 1e-12) if sel.any() else np.nan

        def valley(f0):
            sel = (fr > f0 * 1.4) & (fr < f0 * 1.6)
            return 20 * np.log10(np.median(spec[sel]) + 1e-12) if sel.any() else np.nan

        harm = [pk(k * fm) - pk(fm) for k in (2, 3, 4)] if np.isfinite(fm) else [np.nan] * 3
        breath = pk(fm) - valley(fm) if np.isfinite(fm) else np.nan
        seg_lv = lv[a : b + 1]
        pkk = int(np.argmax(seg_lv))
        att = pkk * 10
        after = np.where(seg_lv[pkk:] < seg_lv[pkk] - 20)[0]
        dec = after[0] * 10 if len(after) else (len(seg_lv) - pkk) * 10
        rows.append(dict(t=a * 0.01, dur=(b - a + 1) * 0.01, f=f, fm=fm, harm=harm, breath=breath,
                         peak=seg_lv.max() - bg, att=att, dec=dec))
    for r in rows:
        f = "／".join("—" if not np.isfinite(v) else f"{v:.0f}" for v in r["f"])
        hs = "／".join("—" if not np.isfinite(v) else f"{v:+.0f}" for v in r["harm"])
        print(f"  {r['t']:7.2f}s 長さ{r['dur'] * 1000:5.0f}ms 基本 {f}Hz 倍音2〜4 {hs}dB 息との差 {r['breath']:.0f}dB "
              f"背景+{r['peak']:.0f}dB 立上{r['att']}ms 減衰{r['dec']}ms")
    if len(rows) > 1:
        t0 = np.array([r["t"] for r in rows])
        ends = np.array([r["t"] + r["dur"] for r in rows])
        gaps = t0[1:] - ends[:-1]
        print(f"  音の切れ目 中央 {np.median(gaps):.2f}秒（{np.percentile(gaps, 10):.2f}〜{np.percentile(gaps, 90):.2f}）")
        cut = np.where(gaps > 1.5)[0]
        starts = np.r_[0, cut + 1]
        stops = np.r_[cut, len(rows) - 1]
        ph = [(t0[s], ends[e], e - s + 1) for s, e in zip(starts, stops)]
        print(f"  まとまり {len(ph)}個：" + "、".join(f"{a:.1f}s〜{b - a:.1f}秒/{k}音" for a, b, k in ph))
        if len(ph) > 1:
            pi = np.diff([p[0] for p in ph])
            print(f"  まとまりの始まりの間隔 中央 {np.median(pi):.1f}秒（{pi.min():.1f}〜{pi.max():.1f}）")


if __name__ == "__main__":
    main()
