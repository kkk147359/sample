"""水琴窟と低い琴の音（ep16）の長い版を書き出す。
2分ずつ区切って計算し、ffmpeg に流し込んで AAC（.m4a）にする。
1時間版と8時間版は乱数シードを変えて別々に作る（8時間版の切り出しにしない）。
使い方: python3 render_long.py <出力.m4a> <長さ(秒)> <乱数シード>
"""
import subprocess
import sys
import tempfile
from multiprocessing import Pool

import numpy as np
from scipy.io import wavfile
from scipy.signal import butter, sosfilt

import nature
import synth_17gen as gen17

SR = 44100
BLOCK = 120.0
NAT_DB = -16  # 水琴窟は琴より約16dB小さく
BED_DB = -10  # 甕の下地はしずくの帯域より約10dB小さく
TARGET_LUFS = -20.0

_state = {}


def _init(events, drops, seed, gains):
    _state.update(events=events, drops=drops, seed=seed, gains=gains)


def _mix_block(i, a, b, events, drops, seed, nat_gain, bed_gain):
    gen17.rng = np.random.default_rng(seed * 100000 + i)
    k = gen17.render_block(events, a, b)
    # 左右の広がりは少し前の音を足して作る。区切りでつながるよう、区間の少し前から計算する
    pre = 0.02
    w = nature.suik_block(drops, max(0.0, a - pre), b, bed_gain)
    off = len(w) - len(k)
    d1, d2, d3 = int(0.0007 * SR), int(0.011 * SR), int(0.017 * SR)
    w = np.concatenate([np.zeros(max(0, d3 - off)), w])
    o = len(w) - len(k)
    l = w[o:] + 0.25 * w[o - d2 : len(w) - d2]
    r = w[o - d1 : len(w) - d1] + 0.25 * w[o - d3 : len(w) - d3]
    return k + nat_gain * np.stack([l, r], axis=1)


def _work(args):
    i, a, b, total = args
    s = _state
    nat_gain, bed_gain, master = s["gains"]
    x = _mix_block(i, a, b, s["events"], s["drops"], s["seed"], nat_gain, bed_gain) * master
    t = a + np.arange(len(x)) / SR
    x *= np.clip(t / 3.0, 0, 1)[:, None]  # 最初の3秒でフェードイン
    x *= np.clip((total - t) / 10.0, 0, 1)[:, None] ** 2  # 最後の10秒でフェードアウト
    return i, (np.clip(x, -0.98, 0.98) * 32767).astype("<i2").tobytes()


def lufs(x):
    with tempfile.NamedTemporaryFile(suffix=".wav") as f:
        wavfile.write(f.name, SR, (np.clip(x, -1, 1) * 32767).astype(np.int16))
        r = subprocess.run(["ffmpeg", "-i", f.name, "-af", "ebur128", "-f", "null", "-"], capture_output=True, text=True).stderr
    return float([l for l in r.splitlines() if l.strip().startswith("I:")][-1].split()[1])


def main(path, total, seed):
    gen17.rng = np.random.default_rng(seed)
    events = gen17.compose(total)
    drops = nature.suik_events(total, np.random.default_rng(seed + 1))
    print(f"notes {len(events)}  drops {len(drops)}", flush=True)

    # 音量の基準を最初の5分（短い版はその長さ）で決める
    cal = min(300.0, total)
    k = gen17.render_block(events, 0, cal)
    dr = nature.suik_block(drops, 0, cal, 0.0)
    band = sosfilt(butter(4, [900, 3500], btype="band", fs=SR, output="sos"), dr)
    bed = nature.pot_bed(0, len(dr))
    bed_gain = np.sqrt(np.mean(band ** 2)) / np.sqrt(np.mean(bed ** 2)) * 10 ** (BED_DB / 20)
    nat = dr + bed_gain * bed
    nat_gain = np.sqrt(np.mean(k ** 2)) / np.sqrt(np.mean(nat ** 2) * 1.0625) * 10 ** (NAT_DB / 20)
    mix = _mix_block(0, 0, cal, events, drops, seed, nat_gain, bed_gain)
    master = 10 ** ((TARGET_LUFS - lufs(mix)) / 20)
    print(f"nat_gain {nat_gain:.4f} bed_gain {bed_gain:.4f} master {master:.3f}", flush=True)

    ff = subprocess.Popen(
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "s16le", "-ar", str(SR), "-ac", "2", "-i", "-",
         "-c:a", "aac", "-b:a", "256k", path], stdin=subprocess.PIPE)
    jobs = []
    a, i = 0.0, 0
    while a < total:
        jobs.append((i, a, min(total, a + BLOCK), total))
        a += BLOCK
        i += 1
    with Pool(4, initializer=_init, initargs=(events, drops, seed, (nat_gain, bed_gain, master))) as pool:
        for i, data in pool.imap(_work, jobs):
            ff.stdin.write(data)
            if i % 10 == 0:
                print(f"block {i + 1}/{len(jobs)}", flush=True)
    ff.stdin.close()
    ff.wait()
    print(f"wrote {path}", flush=True)


if __name__ == "__main__":
    main(sys.argv[1], float(sys.argv[2]), int(sys.argv[3]))
