"""ep22/23 の背景（暗い部屋の低い台に置いたシンギングボウル）・サムネイル・冒頭映像を作る。
冒頭映像では、打った瞬間からボウルの縁の光がゆっくり揺れ、ごく薄い輪が広がる。
使い方:
  python3 make_visual.py bg <出力.png>
  python3 make_visual.py thumb <出力.png> <1時間|8時間>
  python3 make_visual.py intro <出力.mp4>
"""
import os
import sys

import numpy as np
from PIL import Image, ImageFilter

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tools"))
import brand  # noqa: E402

W, H = brand.W, brand.H
MAIN = "シンギングボウルの余韻"
ELEMENTS = "ひとつずつゆっくり・高音ひかえめ"
EN_LINE = "Singing Bowl Resonance  ·  one slow strike at a time"

Y, X = np.mgrid[0:H, 0:W].astype(float)
TEX = 0.6 * brand.noise2d(H, W, 2, 31) + 0.4 * brand.noise2d(H, W, 40, 32)
BX, BY = 1340, 760  # ボウルの口の中心
RX, RY, DEPTH = 210, 52, 150
STRIKES = [0.6, 10.4]


def base():
    img = np.stack([12 + 5 * TEX, 10 + 4 * TEX, 10 + 4 * TEX], axis=-1)
    light = np.exp(-(((X - 1700) / 900) ** 2 + ((Y - 300) / 700) ** 2))  # 右上から弱い光
    img += light[..., None] * np.array([46, 34, 22])
    # 低い木の台（手前、横長）
    table = (Y > 880) & (Y < 960)
    grain = 0.5 + 0.5 * np.sin(Y / 2.5 + 8 * brand.noise2d(H, W, 90, 33))
    tc = np.stack([44 + 14 * grain, 28 + 9 * grain, 18 + 5 * grain], axis=-1) * (0.6 + 0.8 * light[..., None])
    img = np.where(table[..., None], tc, img)
    img[(Y >= 960) & (Y < 1000)] = img[(Y >= 960) & (Y < 1000)] * 0.3
    img[Y >= 1000] *= 0.5
    # 座布団（えんじ色の丸いクッション）
    cush = ((X - BX) / 290) ** 2 + ((Y - 905) / 50) ** 2 <= 1
    cc = np.stack([70 + 20 * TEX, 22 + 6 * TEX, 26 + 6 * TEX], axis=-1) * (0.55 + 0.6 * np.clip((BX + 200 - X) / 500, 0, 1))[..., None]
    img = np.where(cush[..., None], cc, img)
    # ボウルの外側（真鍮）：口の楕円から下へふくらみ、底はすぼまる
    v = (Y - BY) / DEPTH
    half = RX * np.sqrt(np.clip(1 - np.clip(v, 0, 1) ** 2.2, 0, 1)) * (1 - 0.18 * np.clip(v, 0, 1))
    body = (Y >= BY) & (Y <= BY + DEPTH) & (np.abs(X - BX) <= half)
    u = np.clip((X - BX) / (half + 1e-6), -1, 1)
    shade = 0.35 + 0.65 * np.clip(0.5 + 0.6 * u - 0.3 * v, 0, 1)  # 右側が光る
    spec = np.exp(-((u - 0.55) / 0.08) ** 2) * (1 - 0.6 * v)
    bc = np.stack([150 * shade + 120 * spec, 108 * shade + 96 * spec, 52 * shade + 60 * spec], axis=-1) * (0.9 + 0.1 * TEX[..., None])
    img = np.where(body[..., None], bc, img)
    # 口の内側（暗い）と縁
    e = ((X - BX) / RX) ** 2 + ((Y - BY) / RY) ** 2
    inner = e <= 0.93
    ic = np.stack([40 + 30 * np.clip((X - BX) / RX, 0, 1)] * 3, axis=-1) * np.array([1.0, 0.75, 0.4])
    img = np.where(inner[..., None], ic, img)
    rim = (e > 0.93) & (e <= 1.0)
    img = np.where(rim[..., None], np.array([180, 140, 80]) * (0.6 + 0.5 * np.clip((X - BX) / RX + 0.3, 0, 1))[..., None], img)
    # 横に置いた木のばち（フェルト巻き）
    stick = (np.abs((Y - 872) - (X - 980) * 0.06) < 7) & (X > 820) & (X < 1080)
    img = np.where(stick[..., None], np.array([60, 40, 26]), img)
    felt = ((X - 1088) / 22) ** 2 + ((Y - 878) / 16) ** 2 <= 1
    img = np.where(felt[..., None], np.array([110, 100, 88]), img)
    im = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.0))
    img = np.asarray(im, dtype=float)
    vg = np.clip(1 - 0.55 * (((X - W / 2) / (W * 0.62)) ** 2 + ((Y - H / 2) / (H * 0.62)) ** 2), 0.25, 1)
    return img * vg[..., None]


BASE = None


def frame(t):
    global BASE
    if BASE is None:
        BASE = base()
    img = BASE.copy()
    for ts in STRIKES:
        age = t - ts
        if age < 0:
            continue
        # 縁の光の揺れ（うなりと同じくらいのゆっくりした明滅）
        e = ((X - BX) / RX) ** 2 + ((Y - BY) / RY) ** 2
        rim = np.exp(-((e - 0.965) / 0.05) ** 2) * np.exp(-age / 8) * (0.5 + 0.5 * np.cos(2 * np.pi * 0.4 * age))
        img += rim[..., None] * np.array([60, 46, 24])
        # 薄い輪が広がる
        r = 30 + 160 * age
        d = np.hypot((X - BX) / 1.0, (Y - BY) / 0.42)
        ring = np.exp(-((d - r) / 10) ** 2) * np.exp(-age / 2.2) * 0.5
        img += ring[..., None] * np.array([40, 34, 24])
    return np.clip(img + np.random.default_rng(int(t * 12)).normal(0, 1.0, img.shape), 0, 255)


if __name__ == "__main__":
    cmd, out = sys.argv[1], sys.argv[2]
    if cmd == "bg":
        Image.fromarray(frame(1.2).astype(np.uint8)).save(out)
    elif cmd == "thumb":
        brand.thumbnail(frame(3.0), out, MAIN, ELEMENTS, sys.argv[3])
    elif cmd == "intro":
        brand.intro(frame, out, MAIN, EN_LINE)
    print("wrote", out)
