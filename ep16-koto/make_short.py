"""ep16/17「水琴窟と低い琴の音」のショート（縦 1080×1920、約28秒）を作る。
音は1時間版と同じ曲（シード1001）の一部を切り出す。映像は冒頭映像と同じ夜の庭の水琴窟で、
はっきり聞こえるしずくに合わせて筧からしずくが落ち、波紋が広がる。黒画面だけのショートにはしない（社長方針）。
使い方: python3 make_short.py <出力.mp4> [切り出し開始(秒)=60] [長さ(秒)=28]
"""
import subprocess
import sys
import tempfile

import numpy as np
from PIL import Image, ImageDraw
from scipy.signal import butter, sosfilt

import make_visual as mv
import nature
import render_long as rl
import synth_17gen as gen17

SR = 44100
SW, SH = 1080, 1920
FPS = 24
SEED = 1001  # 1時間版と同じ
FULL = 3600.0
SCENE_X0 = 440  # 横長の場面から、つくばいを中心に 1080×1080 を切り出す
SCENE_Y = 340  # 縦長の画面での場面の上端（下の文字がショートの字幕・チャンネル名に隠れないよう上寄せ）


def audio(a, dur, wav_path):
    """1時間版と同じ曲の [a, a+dur) を書き出し、はっきり聞こえるしずくの時刻（切り出し内の秒）を返す"""
    gen17.rng = np.random.default_rng(SEED)
    events = gen17.compose(FULL)
    drops = nature.suik_events(FULL, np.random.default_rng(SEED + 1))
    # 音量のつり合いは render_long と同じ求め方（最初の5分）
    cal = 300.0
    k = gen17.render_block(events, 0, cal)
    dr = nature.suik_block(drops, 0, cal, 0.0)
    band = sosfilt(butter(4, [900, 3500], btype="band", fs=SR, output="sos"), dr)
    bed = nature.pot_bed(0, len(dr))
    bed_gain = np.sqrt(np.mean(band ** 2)) / np.sqrt(np.mean(bed ** 2)) * 10 ** (rl.BED_DB / 20)
    nat = dr + bed_gain * bed
    nat_gain = np.sqrt(np.mean(k ** 2)) / np.sqrt(np.mean(nat ** 2) * 1.0625) * 10 ** (rl.NAT_DB / 20)
    x = rl._mix_block(0, a, a + dur, events, drops, SEED, nat_gain, bed_gain)
    x = x * 10 ** ((-16.0 - rl.lufs(x)) / 20)  # ショートはスマホで聞くので -16LUFS 前後
    t = np.arange(len(x)) / SR
    x *= np.clip(t / 1.0, 0, 1)[:, None]  # 1秒でフェードイン
    x *= np.clip((dur - t) / 1.5, 0, 1)[:, None] ** 2  # 最後の1.5秒でフェードアウト
    from scipy.io import wavfile
    wavfile.write(wav_path, SR, (np.clip(x, -0.98, 0.98) * 32767).astype(np.int16))
    # 映像のしずく：はっきり聞こえるしずくだけ、0.9秒以上あけて
    vis, last = [], -9.0
    for td, g, _ in drops:
        if a <= td < a + dur and g >= 1.0 and td - last >= 0.9:
            vis.append(td - a)
            last = td
    return vis


def text_layer():
    lay = Image.new("RGBA", (SW, SH), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    d.text((540, 210), mv.MAIN, font=mv.font(mv.LIGHT, 74), fill=(246, 242, 232, 255), anchor="mm")
    d.text((540, 290), "Suikinkutsu & Low Koto", font=mv.font(mv.LIGHT, 34), fill=(224, 220, 210, 255), anchor="mm")
    d.text((540, 1450), "続きは8時間版で", font=mv.font(mv.LIGHT, 54), fill=(246, 242, 232, 255), anchor="mm")
    d.text((540, 1522), "10秒で黒画面・まぶしくない睡眠用BGM", font=mv.font(mv.LIGHT, 34), fill=(210, 206, 198, 255), anchor="mm")
    d.text((540, 1582), "Quiet Hours BGM", font=mv.font(mv.LIGHT, 26), fill=(170, 170, 170, 255), anchor="mm")
    return np.asarray(lay, dtype=float)


def edge_mask():
    """場面の上下 180px を黒へなじませる"""
    y = np.arange(1080, dtype=float)
    m = np.clip(y / 180, 0, 1) * np.clip((1079 - y) / 180, 0, 1)
    m = m * m * (3 - 2 * m)
    return m[:, None, None]


def video(path, wav_path, dur, drops):
    base = mv.base_scene()
    tl = text_layer()
    alpha = tl[..., 3:4] / 255
    em = edge_mask()
    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{SW}x{SH}", "-r", str(FPS), "-i", "-",
                           "-i", wav_path, "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18", "-g", str(FPS * 2),
                           "-c:a", "aac", "-b:a", "256k", "-shortest", "-movflags", "+faststart", path], stdin=subprocess.PIPE)
    n = int(round(dur * FPS))
    for i in range(n):
        t = i / FPS
        f = mv.frame(base, t, drops)[:, SCENE_X0:SCENE_X0 + 1080] * em
        canvas = np.zeros((SH, SW, 3))
        canvas[SCENE_Y:SCENE_Y + 1080] = f
        canvas = canvas * (1 - alpha) + tl[..., :3] * alpha
        fade = min(1.0, t / 0.5, (dur - t) / 0.8)  # 始まりと終わりだけ短く黒からなじませる
        ff.stdin.write((canvas * max(0.0, fade)).astype(np.uint8).tobytes())
        if i % 120 == 0:
            print(f"frame {i}/{n}", flush=True)
    ff.stdin.close()
    ff.wait()


if __name__ == "__main__":
    out = sys.argv[1]
    a = float(sys.argv[2]) if len(sys.argv) > 2 else 60.0
    dur = float(sys.argv[3]) if len(sys.argv) > 3 else 28.0
    with tempfile.TemporaryDirectory() as td:
        wav = f"{td}/short.wav"
        drops = audio(a, dur, wav)
        print(f"drops {len(drops)}", flush=True)
        video(out, wav, dur, drops)
    print("wrote", out)
