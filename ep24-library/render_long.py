"""図書館の長い版・試聴の書き出し。2分ずつ区切って計算し（4コアで並列）、ffmpeg で書く。
使い方: python3 render_long.py <出力(.m4a|.mp3)> <秒数> <シード>
音色と背景の大きさは、社長に出した試聴版A（render(90, 7)）から求めた補正にそろえる。
音量は最初の6分を測って -24LUFS 付近になる一定の倍率をかけ、ピークは alimiter（-3dBFS、AACにしたあとも0dBを超えないように）で抑える（動的な圧縮はしない）。
"""
import re
import subprocess
import sys
from multiprocessing import Pool

import numpy as np

from synth_pages import SR, bed_unit_rms, calibrate, eq_fir, plan, render_block

BLK = 120.0
FADE = 3.0
TARGET = -26.0  # 試聴版Aと同じ（ページの音を潰さないため、-24 より 2dB 小さい）
G = {}


def _init(total, seed):
    G["cal"] = calibrate()
    G["fir"] = eq_fir(G["cal"]["corr"])
    G["unit"] = bed_unit_rms(seed)
    G["times"] = plan(total, seed)
    G["total"], G["seed"] = total, seed


def _job(k):
    total = G["total"]
    t0 = k * BLK
    dur = min(BLK, total - t0)
    x = render_block(t0, dur, G["seed"], G["times"], G["cal"], G["fir"], G["unit"])
    t = t0 + np.arange(len(x)) / SR
    g = np.clip(t / FADE, 0, 1) * np.clip((total - t) / FADE, 0, 1)
    return (x * g[:, None]).astype(np.float32)


def lufs(x):
    r = subprocess.run(["ffmpeg", "-f", "f32le", "-ar", str(SR), "-ac", "2", "-i", "-", "-af", "ebur128", "-f", "null", "-"],
                       input=x.astype("<f4").tobytes(), capture_output=True).stderr.decode()
    return float(re.findall(r"I:\s+(-?[\d.]+) LUFS", r)[-1])


if __name__ == "__main__":
    out, total, seed = sys.argv[1], float(sys.argv[2]), int(sys.argv[3])
    nblk = int(np.ceil(total / BLK))
    codec = ["-c:a", "libmp3lame", "-b:a", "192k"] if out.endswith(".mp3") else ["-c:a", "aac", "-b:a", "128k"]
    with Pool(4, initializer=_init, initargs=(total, seed)) as pool:
        head = np.concatenate(pool.map(_job, range(min(3, nblk))))
        gain = 10 ** ((TARGET - lufs(head)) / 20)
        print(f"gain {20 * np.log10(gain):.1f}dB", flush=True)
        ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "f32le", "-ar", str(SR), "-ac", "2", "-i", "-",
                               "-af", "alimiter=limit=0.71:attack=5:release=50:level=false", "-ar", str(SR)] + codec + [out],
                              stdin=subprocess.PIPE)
        maxpk = 0
        for k0 in range(0, nblk, 8):
            for x in pool.map(_job, range(k0, min(nblk, k0 + 8))):
                x = x * gain
                maxpk = max(maxpk, np.abs(x).max())
                ff.stdin.write(x.astype("<f4").tobytes())
            print(f"  {min(k0 + 8, nblk)}/{nblk}", flush=True)
        ff.stdin.close()
        ff.wait()
    print(f"wrote {out}  リミッター前の最大ピーク {20 * np.log10(maxpk):.1f}dBFS")
