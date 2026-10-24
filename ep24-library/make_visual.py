"""ep24/25 の背景（夜の図書館：書架と、読書灯に照らされた机の上の開いた本）・サムネイル・冒頭映像を作る。
冒頭映像では、読書灯の光がごくわずかにゆらぎ、4〜7秒目に右のページが1枚ゆっくりめくられる。
使い方:
  python3 make_visual.py bg <出力.png>
  python3 make_visual.py thumb <出力.png> <1時間|8時間>
  python3 make_visual.py intro <出力.mp4>
"""
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tools"))
import brand  # noqa: E402

W, H = brand.W, brand.H
MAIN = "夜の図書館でページをめくる音"
ELEMENTS = "ページの音だけ・音楽なし"
EN_LINE = "Night Library  ·  slow page turning, no music"

Y, X = np.mgrid[0:H, 0:W].astype(float)
TEX = 0.6 * brand.noise2d(H, W, 2, 51) + 0.4 * brand.noise2d(H, W, 40, 52)
rng = np.random.default_rng(2401)
LAMP = (430, 520)  # 読書灯の光の中心（机の上）
DESK_Y = 720
# 本の形（机の上で手前に向かって少し広がる台形）。のど（中央の折り目）は x=1180
SPINE_X, BOOK_TOP, BOOK_BOT = 1180, 800, 990
HALF_TOP, HALF_BOT = 300, 340


def shelves():
    img = np.stack([12 + 5 * TEX, 9 + 4 * TEX, 7 + 3 * TEX], axis=-1)
    # 棚板と本の背表紙（暗い色の列）
    for row, (y0, y1) in enumerate([(40, 230), (250, 440), (460, 650)]):
        x = 0.0
        while x < W:
            w = rng.uniform(18, 46)
            h = rng.uniform(0.72, 0.98) * (y1 - y0)
            c = np.array(rng.choice([[46, 22, 18], [24, 34, 30], [40, 34, 22], [28, 26, 40], [52, 40, 26]])) * rng.uniform(0.6, 1.1)
            m = (X >= x) & (X < x + w - 2) & (Y > y1 - h) & (Y < y1)
            img[m] = c * (0.85 + 0.25 * TEX[m][:, None])
            x += w + rng.uniform(0, 6)
        img[(Y >= y1) & (Y < y1 + 14)] = np.array([30, 21, 14])
    return img


def desk(img):
    m = Y >= DESK_Y
    wood = np.stack([34 + 10 * TEX, 22 + 6 * TEX, 14 + 4 * TEX], axis=-1)
    grain = 0.9 + 0.1 * np.sin(X / 23 + 6 * brand.noise2d(H, W, 8, 53))
    img[m] = (wood * grain[..., None])[m]
    img[(Y >= DESK_Y) & (Y < DESK_Y + 6)] = np.array([52, 36, 24])
    return img


def page_poly(side, frac=None):
    """左右のページの四隅。frac（0〜1）を渡すと、のどを軸にめくられている途中のページ"""
    def corner(dx_top, dx_bot, lift=0.0):
        return [(SPINE_X, BOOK_TOP), (SPINE_X + dx_top, BOOK_TOP - lift), (SPINE_X + dx_bot, BOOK_BOT - lift), (SPINE_X, BOOK_BOT)]
    if frac is None:
        s = -1 if side == "L" else 1
        return corner(s * HALF_TOP, s * HALF_BOT)
    a = np.pi * frac
    # 紙はまっすぐ立たず、ゆるく反る：自由な端は少し遅れてついてくる
    curl = 90 * np.sin(a)
    return corner(np.cos(a) * HALF_TOP + curl * 0.8, np.cos(a) * HALF_BOT + curl, lift=np.sin(a) * 230)


def base():
    img = desk(shelves())
    return img


BASE = None


def frame(t):
    global BASE
    if BASE is None:
        BASE = base()
    im = Image.fromarray(np.clip(BASE, 0, 255).astype(np.uint8))
    d = ImageDraw.Draw(im)
    # 読書灯（左）：細い柱と傘
    d.line([(LAMP[0] - 60, DESK_Y + 40), (LAMP[0] - 60, 430)], fill=(40, 34, 26), width=10)
    d.polygon([(LAMP[0] - 170, 470), (LAMP[0] + 60, 470), (LAMP[0] + 10, 380), (LAMP[0] - 120, 380)], fill=(58, 46, 26))
    # 本の下の影と、紙の厚み
    d.polygon([(SPINE_X - HALF_BOT - 10, BOOK_BOT + 14), (SPINE_X + HALF_BOT + 10, BOOK_BOT + 14),
               (SPINE_X + HALF_TOP + 10, BOOK_TOP + 6), (SPINE_X - HALF_TOP - 10, BOOK_TOP + 6)], fill=(16, 10, 6))
    paper = (196, 184, 156)
    d.polygon(page_poly("L"), fill=paper)
    d.polygon(page_poly("R"), fill=paper)
    # 文字の行（細いうすい線）
    for side in (-1, 1):
        for k in range(14):
            u = (k + 1) / 15
            y = BOOK_TOP + u * (BOOK_BOT - BOOK_TOP)
            half = HALF_TOP + u * (HALF_BOT - HALF_TOP)
            x0, x1 = SPINE_X + side * 30, SPINE_X + side * (half - 30)
            d.line([(min(x0, x1), y), (max(x0, x1), y)], fill=(150, 140, 118), width=2)
    # 4〜7秒目：右のページが1枚めくられる
    if 4.0 <= t <= 7.0:
        f = (t - 4.0) / 3.0
        f = 0.5 - 0.5 * np.cos(np.pi * f)
        pts = page_poly("R", f)
        shade = int(196 - 50 * np.sin(np.pi * f))
        d.polygon(pts, fill=(shade, shade - 12, shade - 38))
    elif t > 7.0:
        pass
    d.line([(SPINE_X, BOOK_TOP), (SPINE_X, BOOK_BOT)], fill=(120, 108, 86), width=3)
    img = np.asarray(im.filter(ImageFilter.GaussianBlur(1.0)), dtype=float)
    # 読書灯のあたたかい光（ごくわずかにゆらぐ）
    flick = 1 + 0.02 * np.sin(2 * np.pi * 0.31 * t) + 0.01 * np.sin(2 * np.pi * 0.83 * t + 1)
    dl = np.hypot((X - LAMP[0] - 300) / 1.25, (Y - 860) / 0.75)
    light = np.exp(-(dl / 620) ** 2) * flick
    img = img * (0.35 + 1.15 * light[..., None]) + light[..., None] * np.array([26, 16, 4])
    vg = np.clip(1 - 0.55 * (((X - W / 2) / (W * 0.62)) ** 2 + ((Y - H / 2) / (H * 0.62)) ** 2), 0.25, 1)
    img = img * vg[..., None]
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
