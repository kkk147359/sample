"""琴＋自然音の試作を書き出す
使い方: python3 scene.py <出力wav> <suikinkutsu|irori|none> [長さ(秒)] [乱数シード] [koto|17gen]
"""
import sys

import numpy as np
from scipy.io import wavfile
from scipy.signal import fftconvolve

import nature
import synth_17gen as gen17
import synth_koto as koto

SR = 44100
# 琴に対する自然音の音量（dB）。品質チェック部の条件：水琴窟は琴より約15dB小さく
LEVEL_DB = {"suikinkutsu": -15, "irori": -19}


def rms(x):
    return np.sqrt(np.mean(x ** 2) + 1e-15)


if __name__ == "__main__":
    path, scene = sys.argv[1], sys.argv[2]
    total = float(sys.argv[3]) if len(sys.argv) > 3 else 60
    rng = np.random.default_rng(int(sys.argv[4]) if len(sys.argv) > 4 else 7)
    inst = sys.argv[5] if len(sys.argv) > 5 else "koto"
    k = gen17.render(total) if inst == "17gen" else koto.render(total)
    out = k.copy()
    if scene != "none":
        mono = nature.suikinkutsu(total, rng) if scene == "suikinkutsu" else nature.irori(total, rng)
        # 左右に少し広げ、琴と同じ部屋の響きを薄くかける
        l = mono + 0.25 * fftconvolve(mono, koto.reverb_ir(11))[: len(mono)]
        r = np.roll(mono, int(0.0007 * SR)) + 0.25 * fftconvolve(mono, koto.reverb_ir(12))[: len(mono)]
        nat = np.stack([l, r], axis=1)
        nat *= rms(k) / rms(nat) * 10 ** (LEVEL_DB[scene] / 20)
        fi = int(2 * SR)
        nat[:fi] *= np.linspace(0, 1, fi)[:, None]
        nat[-fi:] *= np.linspace(1, 0, fi)[:, None]
        out = out + nat
    out = out / np.max(np.abs(out)) * 0.7
    wavfile.write(path, SR, (out * 32767).astype(np.int16))
    print(f"wrote {path} ({scene}, {total:.0f}s)")
