"""試聴版。使い方: python3 trial.py <出力.mp3> [秒数=150] [seed=1] [雨のdB(ピアノ比)=-8]
全体を一定の倍率で -28 LUFS にそろえる（loudnorm の自動調整は使わない）。"""
import subprocess, sys
import numpy as np
import synth_piano as sp
import synth_rain as sr_

SR = sp.SR
LUFS = -28.0
out = sys.argv[1]
dur = float(sys.argv[2]) if len(sys.argv) > 2 else 150
seed = int(sys.argv[3]) if len(sys.argv) > 3 else 1
rain_db = float(sys.argv[4]) if len(sys.argv) > 4 else -8.0
ev = sp.compose(dur - 4, seed)
print(f"ピアノ {len(ev)}音（{len(ev) / dur * 60:.0f}/分）")
pno = sp.room(sp.render(ev, dur, seed), seed)
n = len(pno)
rain = sr_.Bed(seed).next(0.0, n) + sr_.render_events(0.0, dur, sr_.events(dur, seed))
def rms(y): return np.sqrt(np.mean(y ** 2))
# 雨の大きさは「ピアノが鳴っている区間の平均」を基準にする
rain *= rms(pno) / rms(rain) * 10 ** (rain_db / 20)
x = pno + rain
def lufs(y):
    r = subprocess.run(["ffmpeg", "-hide_banner", "-f", "f32le", "-ar", str(SR), "-ac", "2", "-i", "-", "-af", "ebur128", "-f", "null", "-"],
                       input=y.astype("<f4").tobytes(), capture_output=True).stderr.decode()
    return float(r.rsplit("I:", 1)[1].split("LUFS")[0])
x *= 10 ** ((LUFS - lufs(x)) / 20)
fade = int(3 * SR)
x[:fade] *= np.linspace(0, 1, fade)[:, None]
x[-fade:] *= np.linspace(1, 0, fade)[:, None]
print("ピーク %.1f dBFS" % (20 * np.log10(np.abs(x).max())))
pcm = (np.clip(x, -1, 1) * 32767).astype("<i2").tobytes()
args = ["ffmpeg", "-y", "-loglevel", "error", "-f", "s16le", "-ar", str(SR), "-ac", "2", "-i", "-"]
args += ["-c:a", "libmp3lame", "-b:a", "192k", out] if out.endswith(".mp3") else [out]
subprocess.run(args, input=pcm, check=True)
print("wrote", out)
