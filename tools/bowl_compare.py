"""シンギングボウルの録音（または合成の試聴版）を、聞いた印象に関わる点で比べる。
- 打つ間隔と、1回の打音がどれだけ残っているうちに次を打つか（重なり）
- 音の高さの中心（スペクトル重心）と、1/3オクターブの配分（低い・中くらい・高い）
- いちばん強い倍音どうしの音程（同時に鳴っているボウルの高さの関係）
- 余韻の揺れ（うなり）の深さと速さ：200〜400Hz帯の音量の揺れ
- 無音に近い時間の割合、急な音（0.1秒ごとの音量の上がり方の上位1%）
使い方: python3 bowl_compare.py <音声ファイル>...
音そのものは保存しない（数値だけを出す）。
"""
import subprocess
import sys

import numpy as np
from scipy.signal import butter, find_peaks, sosfiltfilt

SR = 22050


def load(p):
    raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", p, "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"], capture_output=True).stdout
    return np.frombuffer(raw, np.float32).astype(float)


def env_db(x, hop):
    return 20 * np.log10(np.sqrt(np.convolve(x ** 2, np.ones(hop) / hop, "same"))[::hop] + 1e-9)


def analyze(p):
    x = load(p)[: SR * 300]
    dur = len(x) / SR
    e = env_db(x, SR // 10)  # 0.1秒ごと
    top = np.percentile(e, 99)
    de = np.diff(e)
    on, _ = find_peaks(de, height=4, distance=15)
    on = on[e[np.minimum(on + 2, len(e) - 1)] > top - 20]
    gaps = np.diff(on) / 10 if len(on) > 1 else np.array([np.nan])
    # 打つ直前の音量が、直前の打音の最大からどれだけ下がっているか（小さいほど重なっている）
    drop = [e[on[i - 1] : on[i]].max() - e[on[i] - 1] for i in range(1, len(on))]
    quiet = np.mean(e < top - 40)
    sudden = np.percentile(de, 99)
    # スペクトル
    N = 1 << 16
    S = np.zeros(N // 2 + 1)
    for s in range(0, len(x) - N, N // 2):
        S += np.abs(np.fft.rfft(x[s : s + N] * np.hanning(N))) ** 2
    F = np.fft.rfftfreq(N, 1 / SR)
    m = (F > 60) & (F < 10000)
    cen = (F[m] * S[m]).sum() / S[m].sum()
    bands = {"<250": (60, 250), "250-700": (250, 700), "700-2k": (700, 2000), "2k-5k": (2000, 5000), ">5k": (5000, 10000)}
    tot = S[m].sum()
    share = {k: 10 * np.log10(S[(F >= a) & (F < b)].sum() / tot + 1e-12) for k, (a, b) in bands.items()}
    Sd = 10 * np.log10(S + 1e-20)
    pk, _ = find_peaks(Sd * m, prominence=10, distance=int(8 / (F[1] - F[0])))
    pk = sorted(pk, key=lambda i: -Sd[i])[:6]
    fs = sorted(F[pk])
    # うなり：強い倍音1本のまわり（±4Hz）の音量の揺れ
    f1 = F[pk[0]]
    y = sosfiltfilt(butter(2, [f1 - 4, f1 + 4], btype="band", fs=SR, output="sos"), x)
    ey = env_db(y, SR // 50)  # 20ms
    # ゆっくりした減衰を取り除いた揺れ
    k = 50
    trend = np.convolve(ey, np.ones(k) / k, "same")
    r = (ey - trend)[k:-k]
    depth = np.percentile(r, 95) - np.percentile(r, 5)
    sp = np.abs(np.fft.rfft(r * np.hanning(len(r))))
    fr = np.fft.rfftfreq(len(r), 1 / 50)
    mm = (fr > 0.1) & (fr < 10)
    rate = fr[mm][np.argmax(sp[mm])]
    print(f"{p.split('/')[-1]}: {dur:.0f}秒  打った回数 {len(on)}  間隔の中央値 {np.nanmedian(gaps):.1f}秒  "
          f"次を打つまでの減り {np.median(drop) if drop else float('nan'):.0f}dB  ほぼ無音 {quiet * 100:.0f}%  急な音 {sudden:.1f}dB")
    print(f"   重心 {cen:.0f}Hz  配分(dB) " + " ".join(f"{k}:{v:.0f}" for k, v in share.items()))
    print(f"   強い倍音 " + " ".join(f"{f:.0f}" for f in fs) + f"   {f1:.0f}Hzのうなり 深さ{depth:.1f}dB 速さ{rate:.2f}Hz")


if __name__ == "__main__":
    for p in sys.argv[1:]:
        analyze(p)
