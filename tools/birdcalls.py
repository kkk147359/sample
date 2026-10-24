"""小鳥の声の録音を1声ずつ測る（音そのものは保存しない）。

python3 -I tools/birdcalls.py <file> [...]  （各ファイルの先頭 240 秒まで）

- 声の帯域（1.5〜10kHz）の 5ms ごとの音量で、背景（下から20%）+10dB を超えた区間を1声とする
  （20ms 未満の切れ目はつなぐ、10ms 未満の声は捨てる）。
- 1声ごと：長さ、いちばん強い高さ（中央・下10%・上90%）、高さの動き（始め→終わり）、立ち上がり（最大の -20dB から最大まで）、
  背景との差。
- 全体：1分あたりの声の数、声と声の間（中央・10%・90%）、声が鳴っている時間の割合、
  声のある時間の帯域配分（1〜2k / 2〜3k / 3〜4k / 4〜5k / 5〜6k / 6〜8k / 8〜10k、合計=100%）、
  ファイル全体の 4〜5kHz の割合（tools/spectrum.py と同じ定義：0.1 秒ごとの全帯域に対する割合の中央値と 90%）。
"""
import subprocess
import sys

import numpy as np

SR = 44100
WIN, HOP = 1024, 220  # 5ms


def load(path, sec=240):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-t", str(sec), "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32).astype(np.float64)


def analyze(path):
    x = load(path)
    fr = np.lib.stride_tricks.sliding_window_view(x, WIN)[::HOP] * np.hanning(WIN)
    S = np.abs(np.fft.rfft(fr, axis=1)) ** 2
    F = np.fft.rfftfreq(WIN, 1 / SR)
    vb = (F >= 1500) & (F < 10000)
    e = 10 * np.log10(S[:, vb].sum(1) + 1e-14)
    bg = np.percentile(e, 20)
    on = e > bg + 10
    # 20ms 未満の切れ目をつなぐ
    gap = int(0.02 * SR / HOP)
    idx = np.flatnonzero(on)
    segs = []
    if len(idx):
        s = p = idx[0]
        for i in idx[1:]:
            if i - p > gap:
                segs.append((s, p + 1)); s = i
            p = i
        segs.append((s, p + 1))
    segs = [(a, b) for a, b in segs if (b - a) * HOP / SR >= 0.01]
    dt = HOP / SR
    rows = []
    for a, b in segs:
        Sv = S[a:b][:, vb]
        pk = F[vb][np.argmax(Sv, 1)]
        ee = e[a:b]
        m = np.argmax(ee)
        st = np.flatnonzero(ee[: m + 1] < ee[m] - 20)
        rise = (m - (st[-1] if len(st) else 0)) * dt
        n = len(pk)
        k = max(1, n // 4)
        rows.append(((b - a) * dt, np.median(pk), np.percentile(pk, 10), np.percentile(pk, 90),
                     np.median(pk[-k:]) - np.median(pk[:k]), rise, ee.max() - bg))
    dur = len(x) / SR
    print(f"{path.split('/')[-1]}: {dur:.0f}秒  声 {len(rows)}（{len(rows) / dur * 60:.0f}/分）  鳴っている割合 {on.mean() * 100:.0f}%")
    if rows:
        r = np.array(rows)
        q = lambda c, f="{:.0f}": "/".join(f.format(v) for v in np.percentile(r[:, c], [10, 50, 90]))
        print(f"   長さms {'/'.join(f'{v * 1000:.0f}' for v in np.percentile(r[:, 0], [10, 50, 90]))}"
              f"  高さHz {q(1)}  1声の幅(上90-下10)中央 {np.median(r[:, 3] - r[:, 2]):.0f}Hz"
              f"  高さの動き中央 {np.median(r[:, 4]):+.0f}Hz（|動き|中央 {np.median(np.abs(r[:, 4])):.0f}）"
              f"  立ち上がりms {'/'.join(f'{v * 1000:.0f}' for v in np.percentile(r[:, 5], [10, 50, 90]))}"
              f"  背景との差dB {q(6)}")
        starts = np.array([a for a, b in segs]) * dt
        if len(starts) > 2:
            ioi = np.diff(starts)
            print(f"   声の間隔s 10%/中央/90% {np.percentile(ioi, 10):.2f}/{np.median(ioi):.2f}/{np.percentile(ioi, 90):.2f}"
                  f"  2秒以上の休み {np.mean(ioi > 2) * 100:.0f}%")
    edges = [1000, 2000, 3000, 4000, 5000, 6000, 8000, 10000]
    if on.any():
        Sc = S[on].sum(0)
        parts = np.array([Sc[(F >= lo) & (F < hi)].sum() for lo, hi in zip(edges[:-1], edges[1:])])
        parts = parts / parts.sum() * 100
        print("   声のある時間の配分% " + " ".join(f"{lo // 1000}-{hi // 1000}k:{p:.0f}" for lo, hi, p in zip(edges[:-1], edges[1:], parts)))
    # 0.1秒ごとの 4〜5kHz 割合（全帯域比）
    k = int(0.1 * SR / HOP)
    m = len(S) // k
    Sb = S[: m * k].reshape(m, k, -1).sum(1)
    hf = Sb[:, (F >= 4000) & (F < 5000)].sum(1) / (Sb.sum(1) + 1e-14)
    tot = 10 * np.log10(Sb.sum(1) + 1e-14)
    cen = (Sb * F).sum(1) / (Sb.sum(1) + 1e-14)
    print(f"   4〜5kHzの割合 中央 {np.median(hf) * 100:.2f}%  90% {np.percentile(hf, 90) * 100:.1f}%  "
          f"重心 中央 {np.median(cen):.0f}Hz  声の帯域-全体 {np.median(e) - np.median(tot):.1f}dB")


if __name__ == "__main__":
    for p in sys.argv[1:]:
        try:
            analyze(p)
        except Exception as ex:  # 壊れたファイルは飛ばす
            print(p, "ERR", ex)
