"""ep18/19 のショート（縦 1080×1920、28秒、24fps）とカバー画像を作る。
形は ep16 の水琴窟ショートと同じ：上に題名、中央に冒頭映像と同じ柱時計の場面（振り子が音と同じ1秒ごとに端に届く）、
下に「続きは8時間版で」。音は1時間版の一部（60秒目から28秒）。ショートはスマホで聞かれるので -16LUFS にそろえる（ep16 と同じ）。
使い方: python3 make_short.py <1時間版の音.m4a> <出力.mp4> <カバー.png>
"""
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw

import make_visual as mv
from make_visual import brand

SW, SH, FPS, DUR = 1080, 1920, 24, 28.0
START = 60.0  # 1時間版の何秒目から使うか
# 打音は 0.3 + k 秒（synth_clock.schedule、1秒の一定間隔）。振り子は frame(t) で t = 0.5 + k のとき端に届くので 0.2 秒ずらす
PHASE = 0.5 - ((0.3 - START) % 1.0)
CROP = (980, 40, 1920, 1060)  # 元の場面（1920×1080）から時計のまわりを切り出す
TOP = 330  # 場面を置く高さ
TITLE = "古い柱時計と窓の外の小雨"
EN = "Old Pendulum Wall Clock & Gentle Rain"


def overlay():
    lay = Image.new("RGBA", (SW, SH), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    d.text((SW / 2, 215), TITLE, font=brand.font(brand.LIGHT, 64), fill=(246, 242, 232, 255), anchor="mm")
    d.text((SW / 2, 292), EN, font=brand.font(brand.LIGHT, 32), fill=(224, 220, 210, 255), anchor="mm")
    d.text((SW / 2, 1450), "続きは8時間版で", font=brand.font(brand.LIGHT, 56), fill=(246, 242, 232, 255), anchor="mm")
    d.text((SW / 2, 1528), "10秒で黒画面・まぶしくない睡眠用BGM", font=brand.font(brand.LIGHT, 34), fill=(224, 220, 210, 255), anchor="mm")
    d.text((SW / 2, 1586), "Quiet Hours BGM", font=brand.font(brand.LIGHT, 26), fill=(170, 170, 170, 255), anchor="mm")
    return np.asarray(lay, dtype=float)


def scene_mask(h):
    """場面の上下をなめらかに黒へ"""
    y = np.arange(h)
    m = np.clip(y / 140, 0, 1) * np.clip((h - y) / 180, 0, 1)
    return m[:, None, None]


def short_frame(base, t, ov, mask):
    f = mv.frame(base, t + PHASE, 1.0)
    x0, y0, x1, y1 = CROP
    sc = Image.fromarray(f[y0:y1, x0:x1].astype(np.uint8)).resize((SW, int((y1 - y0) * SW / (x1 - x0))), Image.LANCZOS)
    sc = np.asarray(sc, dtype=float) * mask
    out = np.zeros((SH, SW, 3))
    out[TOP : TOP + sc.shape[0]] = sc
    a = ov[..., 3:4] / 255
    out = out * (1 - a) + ov[..., :3] * a
    fade = min(1.0, t / 0.8, (DUR - t) / 0.8)  # 最初と最後は黒からなめらかに
    return np.clip(out * fade, 0, 255)


if __name__ == "__main__":
    audio, out, cover = sys.argv[1], sys.argv[2], sys.argv[3]
    base = mv.base_scene()
    ov = overlay()
    x0, y0, x1, y1 = CROP
    mask = scene_mask(int((y1 - y0) * SW / (x1 - x0)))
    vid = out + ".video.mp4"
    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{SW}x{SH}", "-r", str(FPS), "-i", "-",
                           "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20", "-g", "48", vid], stdin=subprocess.PIPE)
    for i in range(int(DUR * FPS)):
        ff.stdin.write(short_frame(base, i / FPS, ov, mask).astype(np.uint8).tobytes())
    ff.stdin.close()
    ff.wait()
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", vid, "-ss", str(START), "-t", str(DUR), "-i", audio,
                    "-af", f"afade=t=in:d=0.8,afade=t=out:st={DUR - 1.0}:d=1.0,loudnorm=I=-16:TP=-1.5:LRA=7", "-ar", "44100",
                    "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", out], check=True)
    subprocess.run(["rm", "-f", vid])
    Image.fromarray(short_frame(base, 5.0, ov, mask).astype(np.uint8)).save(cover)
    print("wrote", out, cover)
