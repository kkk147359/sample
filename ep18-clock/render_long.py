"""柱時計＋窓の外の小雨の長い版の書き出し。2分ずつ区切って計算し（4コアで並列）、ffmpeg で AAC（.m4a）にする。
使い方: python3 render_long.py <出力.m4a> <秒数> <シード> [速さ=even100]
音は社長OKの試聴版（trial_mix.py 371070 -2 120 even100 -6 1）と同じ設定：
テンプレート 371070、柔らかい版（soft, 響き0.12）、時計は -6dB、雨は「ふつうの版の時計」より -2dB。
各音の倍率は最初の2分で一度だけ決めて全体に同じ値を使う（区切りで音量が変わらない）。
全体の音量は最初の5分を測って -24LUFS になる倍率をかけ、loudnorm（I=-24, TP=-3）を通す。
"""
import re
import subprocess
import sys
from multiprocessing import Pool

import numpy as np

import rain
from synth_clock import SR, render_block, reverb_ir, schedule

BLK = 120.0
FADE = 3.0
TARGET = -24.0
TPL, RAIN_DB, CLOCK_DB, WET = "371070", -2.0, -6.0, 0.12


def rms(x):
    return np.sqrt(np.mean(x ** 2))


def _sched(total, cfg):
    ts, kinds = schedule(total + 5, cfg["speed"], cfg["seed"])
    return ts, kinds, rain.drop_schedule(total + 5, cfg["seed"])


def calibrate(cfg):
    """最初の2分で、時計（柔らかい版）と雨にかける倍率を決める（試聴版と同じ決め方）"""
    ts, kinds, drops = _sched(BLK, cfg)
    ir = reverb_ir()
    base = {"seed": cfg["seed"], "speed": cfg["speed"], "tpl": TPL, "wet": 0.0}
    c0 = render_block(0.0, BLK, base, ts, kinds, ir)
    c = render_block(0.0, BLK, dict(base, soft=True, wet=WET), ts, kinds, ir)
    r = rain.render_block(0.0, BLK, cfg["seed"], drops)
    return rms(c0) / rms(c) * 10 ** (CLOCK_DB / 20), rms(c0) / rms(r) * 10 ** (RAIN_DB / 20)


def _job(args):
    k, total, cfg, kc, kr = args
    ts, kinds, drops = _sched(total, cfg)
    t0 = k * BLK
    dur = min(BLK, total - t0)
    c = render_block(t0, dur, {"seed": cfg["seed"], "speed": cfg["speed"], "tpl": TPL, "soft": True, "wet": WET}, ts, kinds, reverb_ir())
    r = rain.render_block(t0, dur, cfg["seed"], drops)
    n = min(len(c), len(r))
    x = kc * c[:n] + kr * r[:n]
    t = t0 + np.arange(n) / SR
    g = np.clip(t / FADE, 0, 1) * np.clip((total - t) / FADE, 0, 1)
    return (x * g[:, None]).astype(np.float32)


def lufs(x):
    r = subprocess.run(["ffmpeg", "-f", "f32le", "-ar", str(SR), "-ac", "2", "-i", "-", "-af", "ebur128", "-f", "null", "-"],
                       input=x.astype("<f4").tobytes(), capture_output=True).stderr.decode()
    return float(re.findall(r"I:\s+(-?[\d.]+) LUFS", r)[-1])


if __name__ == "__main__":
    out, total, seed = sys.argv[1], float(sys.argv[2]), int(sys.argv[3])
    cfg = {"seed": seed, "speed": sys.argv[4] if len(sys.argv) > 4 else "even100"}
    kc, kr = calibrate(cfg)
    nblk = int(np.ceil(total / BLK))
    jobs = [(k, total, cfg, kc, kr) for k in range(nblk)]
    with Pool(4) as pool:
        head = np.concatenate(pool.map(_job, jobs[: min(3, nblk)]))
        gain = 10 ** ((TARGET - lufs(head[int(10 * SR):])) / 20)
        print(f"gain {20 * np.log10(gain):.1f}dB  先頭のピーク {20 * np.log10(np.abs(head).max() * gain):.1f}dBFS", flush=True)
        ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "f32le", "-ar", str(SR), "-ac", "2", "-i", "-",
                               "-af", "loudnorm=I=-24:TP=-3:LRA=7", "-ar", str(SR), "-c:a", "aac", "-b:a", "128k", out], stdin=subprocess.PIPE)
        maxpk = 0
        # 8ブロックずつ計算して書く（まとめて先に計算すると、書き出しが追いつかずメモリがあふれる）
        for k0 in range(0, nblk, 8):
            for x in pool.map(_job, jobs[k0 : k0 + 8]):
                x = x * gain
                maxpk = max(maxpk, np.abs(x).max())
                ff.stdin.write(x.astype("<f4").tobytes())
            print(f"  {min(k0 + 8, nblk)}/{nblk}", flush=True)
        ff.stdin.close()
        ff.wait()
    print(f"wrote {out}  loudnorm前の最大ピーク {20 * np.log10(maxpk):.1f}dBFS")
