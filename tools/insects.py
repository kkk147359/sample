"""虫の声の録音を測る：鳴き声の高さ（強い帯域の中心）、その帯域の音量のリズム（1秒あたりの脈の数と、鳴く・休むの周期）、
声の帯域とそれ以外（風や遠くの音）の差、1/3オクターブの配分、急な音。
使い方: python3 insects.py <音声ファイル>... （音そのものは保存しない）
"""
import subprocess
import sys

import numpy as np
from scipy.signal import butter, find_peaks, sosfiltfilt

SR = 44100


def load(p, sec=240):
    raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", p, "-t", str(sec), "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"], capture_output=True).stdout
    return np.frombuffer(raw, np.float32).astype(float)


def analyze(p):
    x = load(p)
    N = 1 << 15
    S = np.zeros(N // 2 + 1)
    for s in range(0, len(x) - N, N // 2):
        S += np.abs(np.fft.rfft(x[s : s + N] * np.hanning(N))) ** 2
    F = np.fft.rfftfreq(N, 1 / SR)
    Sd = 10 * np.log10(S + 1e-20)
    sm = np.convolve(Sd, np.ones(301) / 301, "same")  # なだらかな下地
    m = (F > 1500) & (F < 16000)
    pk, pr = find_peaks((Sd - sm) * m, prominence=6, distance=int(300 / (F[1] - F[0])))
    pk = sorted(pk, key=lambda i: -Sd[i])[:4]
    cen = 1000 * 2.0 ** (np.arange(-10, 14) / 3)
    band = [10 * np.log10(S[(F >= c / 2 ** (1 / 6)) & (F < c * 2 ** (1 / 6))].sum() + 1e-20) for c in cen]
    band = np.array(band) - max(band)
    print(f"{p.split('/')[-1]}: {len(x) / SR:.0f}秒  1/3オクターブ(dB) " + " ".join(f"{c / 1000:.1f}k:{b:.0f}" for c, b in zip(cen, band) if c >= 200))
    for i in sorted(pk):
        f0 = F[i]
        bw = max(150, f0 * 0.06)
        y = sosfiltfilt(butter(3, [f0 - bw, f0 + bw], btype="band", fs=SR, output="sos"), x)
        hop = 44  # 1ms
        e = np.sqrt(np.convolve(y ** 2, np.ones(hop) / hop, "same"))[::hop]
        le = 20 * np.log10(e + 1e-9)
        sp = np.abs(np.fft.rfft((e - e.mean()) * np.hanning(len(e))))
        fr = np.fft.rfftfreq(len(e), 1e-3)
        fast = (fr > 5) & (fr < 120)
        slow = (fr > 0.1) & (fr < 5)
        r_fast = fr[fast][np.argmax(sp[fast])]
        r_slow = fr[slow][np.argmax(sp[slow])]
        # 鳴いている割合と、音量の揺れ（0.25秒平均）
        e25 = 20 * np.log10(np.sqrt(np.convolve(y ** 2, np.ones(SR // 4) / (SR // 4), "same"))[:: SR // 4] + 1e-9)
        on = np.mean(le > np.percentile(le, 95) - 10)
        print(f"   声 {f0:.0f}Hz（下地より{Sd[i] - sm[i]:.0f}dB）  脈 {r_fast:.1f}回/秒  鳴く・休むの周期 {1 / r_slow:.1f}秒  "
              f"鳴いている割合 {on * 100:.0f}%  0.25秒ごとの揺れ {np.std(e25):.1f}dB")
    e = 20 * np.log10(np.sqrt(np.convolve(x ** 2, np.ones(4410) / 4410, "same"))[::4410] + 1e-9)
    print(f"   急な音 上位1% {np.percentile(np.diff(e), 99):.1f}dB")


if __name__ == "__main__":
    for p in sys.argv[1:]:
        analyze(p)
