"""時計の実録音から、打音の「時間×周波数の音量の形」（1/3オクターブ帯域ごとの音量の時間変化）を
チク・タク別に平均して取り出す。音そのもの（波形）は残さず、数十打の平均の音量の形だけを保存する。
使い方: python3 tick_template.py <音声ファイル> <出力.npz>
"""
import subprocess
import sys

import numpy as np
from scipy.signal import butter, find_peaks, sosfiltfilt

SR = 44100
CENTERS = 1000 * 2.0 ** (np.arange(-10, 12) / 3)  # 100Hz〜12.7kHz の22帯域
PRE, POST = 0.005, 0.25
HOP = 16  # 約0.36ms


def load(p):
    raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", p, "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"], capture_output=True).stdout
    return np.frombuffer(raw, np.float32).astype(float)


def onsets(x):
    xb = sosfiltfilt(butter(4, [400, 10000], btype="band", fs=SR, output="sos"), x)
    e = np.sqrt(np.convolve(xb ** 2, np.ones(441) / 441, "same"))[::44]
    le = 20 * np.log10(e + 1e-9)
    pk, _ = find_peaks(le, height=np.percentile(le, 99.5) - 15, distance=300)
    out = []
    hp = sosfiltfilt(butter(2, 1000, btype="high", fs=SR, output="sos"), x)
    for p in pk:
        s = p * 44 - int(0.02 * SR)
        seg = np.abs(hp[max(s, 0) : p * 44 + int(0.01 * SR)])
        if len(seg) < 100:
            continue
        a = np.argmax(seg > 0.25 * seg.max())  # 最初に大きく動いた点を打音の始まりとする
        out.append(max(s, 0) + a)
    return np.array(out)


def band_env(x, on):
    """各帯域の音量（パワー）の時間変化：帯域ごとに2次のバンドパス→2乗→短い平均"""
    n0, n1 = int(PRE * SR), int(POST * SR)
    segs = [x[o - n0 : o + n1] for o in on if o - n0 >= 0 and o + n1 <= len(x)]
    out = []
    for fc in CENTERS:
        sos = butter(2, [fc / 2 ** (1 / 6), min(fc * 2 ** (1 / 6), SR / 2 - 100)], btype="band", fs=SR, output="sos")
        w = max(8, int(SR / fc * 2))  # 低い帯域ほど長めに平均
        acc = []
        for s in segs:
            y = sosfiltfilt(sos, s) ** 2
            y = np.convolve(y, np.ones(w) / w, "same")[::HOP]
            acc.append(y)
        out.append(np.mean(acc, 0))
    return np.array(out), len(segs)


if __name__ == "__main__":
    x = load(sys.argv[1])
    on = onsets(x)
    ioi = np.diff(on) / SR
    res = {"centers": CENTERS, "hop": HOP, "pre": PRE}
    for par in (0, 1):
        env, n = band_env(x, on[par::2])
        res[f"env{par}"] = env
        tot = 10 * np.log10(env.sum(0) + 1e-20)
        tot -= tot.max()
        t = (np.arange(env.shape[1]) * HOP / SR - PRE) * 1000
        print(f"{'チク' if par == 0 else 'タク'}: {n}打の平均  全体の形(ms:dB) " + " ".join(f"{t[i]:.0f}:{tot[i]:.0f}" for i in range(0, len(t), 28)))
    res["ioi"] = np.array([ioi[0::2].mean(), ioi[1::2].mean()])
    res["level_diff"] = 10 * np.log10(res["env1"].sum() / res["env0"].sum())
    print(f"間隔 {res['ioi'][0]:.3f}/{res['ioi'][1]:.3f}s  タクの強さ {res['level_diff']:.1f}dB")
    np.savez_compressed(sys.argv[2], **res)
