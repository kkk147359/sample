"""ep28/29 の背景（秋の夜の部屋：小さな明かりの下のテーブルに、編みかけのマフラーと竹の棒針2本、毛糸玉の入ったかご）・サムネイル・冒頭映像。
冒頭映像では、棒針の先がごくゆっくり動き（約1.2秒周期の小さな揺れ）、明かりがほんの少しだけゆらぐ。
使い方:
  python3 make_visual.py bg <出力.png>
  python3 make_visual.py thumb <出力.png> <1時間|8時間>
  python3 make_visual.py intro <出力.mp4>
"""
import os
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tools"))
import brand  # noqa: E402

W, H = brand.W, brand.H
MAIN = "竹の棒針で編み物をする音"
ELEMENTS = "毛糸と棒針の音だけ・音楽なし"
EN_LINE = "Knitting with Bamboo Needles  ·  yarn and needles only, no music"

Y, X = np.mgrid[0:H, 0:W].astype(float)
TEX = 0.6 * brand.noise2d(H, W, 3, 81) + 0.4 * brand.noise2d(H, W, 50, 82)
LAMP = (1560, 300)


def smooth(e, w):
    return 0.5 + 0.5 * np.tanh(e / w)


def put(img, mask, color):
    m = np.clip(mask, 0, 1)[..., None]
    return img * (1 - m) + m * color


def needle(img, x0, y0, x1, y1, width):
    """竹の棒針（細い棒、先がとがる、うすい節）"""
    dx, dy = x1 - x0, y1 - y0
    ln = np.hypot(dx, dy)
    u = ((X - x0) * dx + (Y - y0) * dy) / ln
    v = np.abs(-(X - x0) * dy + (Y - y0) * dx) / ln
    w = width * np.clip(np.where(u > ln - 90, (ln - u) / 90, 1), 0.05, 1)
    m = smooth(w - v, 1.2) * smooth(u, 2) * smooth(ln - u, 2)
    node = 1 - 0.18 * np.exp(-((np.mod(u, 260) - 130) / 5) ** 2)
    col = np.stack([168 * node, 132 * node, 82 * node], -1) * (0.85 + 0.25 * (1 - v / (width + 1e-3)))[..., None]
    return put(img, m, col)


def frame(t):
    sway = np.sin(2 * np.pi * t / 1.2)
    # 壁（暗い、少し暖かいグレー）
    img = np.stack([20 + 6 * TEX, 17 + 6 * TEX, 18 + 6 * TEX], -1)
    # テーブル（下半分、木目）
    grain = 0.8 + 0.12 * np.sin(Y / 9 + 3 * brand.noise2d(H, W, 40, 83)) + 0.08 * TEX
    table = smooth(Y - 600, 5)
    img = put(img, table, np.stack([62 * grain, 42 * grain, 28 * grain], -1))
    # かごと毛糸玉（左）
    d = ((X - 400) / 300) ** 2 + ((Y - 640) / 120) ** 2
    basket = smooth(1 - d, 0.05) * (Y > 600) + smooth(X - 100, 4) * smooth(700 - X, 4) * smooth(Y - 640, 4) * smooth(900 - Y, 4)
    weave = 0.75 + 0.2 * np.sin(X / 9) * np.sin(Y / 9)
    img = put(img, np.clip(basket, 0, 1), np.stack([70 * weave, 52 * weave, 32 * weave], -1))
    for cx, cy, r, col in [(300, 600, 110, (120, 58, 52)), (480, 590, 120, (160, 140, 110)), (390, 520, 95, (96, 84, 120))]:
        dd = np.hypot(X - cx, Y - cy) / r
        ball = smooth(1 - dd, 0.03)
        strands = 0.82 + 0.14 * np.sin((X - cx) * 0.18 + (Y - cy) * 0.11 + 6 * dd)
        light = 1.05 - 0.45 * np.clip((X - cx + Y - cy) / (2 * r), -1, 1)
        img = put(img, ball, np.array(col) * (strands * light)[..., None])
    # 編みかけのマフラー（中央〜右、テーブルの上に置かれた布）：横の段のうね
    scarf = smooth(X - 780, 10) * smooth(1500 - X, 10) * smooth(Y - (700 + 0.04 * (X - 780)), 6) * smooth(980 - Y, 8)
    rows = 0.78 + 0.16 * np.sin(Y / 6.5) * (0.7 + 0.3 * np.sin(X / 7))
    img = put(img, scarf, np.stack([138 * rows, 96 * rows, 78 * rows], -1))
    # 針にかかった目（マフラーの上の縁）
    loops = smooth(X - 790, 6) * smooth(1490 - X, 6) * np.exp(-((Y - (700 + 0.04 * (X - 780)) + 8) / 12) ** 2)
    img = put(img, loops * (0.6 + 0.4 * np.abs(np.sin(X / 11))), np.array([150, 108, 86]))
    # 毛糸玉から編み地へのびる1本の毛糸（ゆるい弧）
    xs = np.clip((X - 560) / (800 - 560), 0, 1)
    yc = 640 + 65 * xs + 55 * np.sin(np.pi * xs)
    yarn = np.exp(-((Y - yc) / 2.2) ** 2) * smooth(X - 560, 2) * smooth(800 - X, 2)
    img = put(img, yarn * 0.9, np.array([166, 146, 116]))
    # 竹の棒針2本（交差、先がほんの少し揺れる）
    img = needle(img, 700, 720, 1640, 650 + 2.0 * sway, 9)
    img = needle(img, 820, 860, 1600, 560 - 2.5 * sway, 9)
    # 小さな明かり（右上）
    flick = 1 + 0.015 * np.sin(2 * np.pi * 0.27 * t) + 0.008 * np.sin(2 * np.pi * 0.71 * t + 1)
    stem = smooth(X - (LAMP[0] - 7), 1.5) * smooth(LAMP[0] + 7 - X, 1.5) * smooth(Y - 295, 2) * smooth(612 - Y, 2)
    img = put(img, stem, np.array([44, 34, 26]))
    base = np.clip(1 - ((X - LAMP[0]) / 90) ** 2 - ((Y - 612) / 16) ** 2, 0, 1)
    img = put(img, smooth(base, 0.05), np.array([50, 38, 28]))
    sh = (Y > 200) & (Y < 300) & (np.abs(X - LAMP[0]) < 70 + (Y - 200) * 0.5)
    img = put(img, sh.astype(float), np.array([150, 104, 60]))
    dl = np.hypot((X - LAMP[0]) / 1.3, (Y - LAMP[1] - 120) / 0.9)
    light = np.exp(-(dl / 700) ** 2) * flick
    img = img * (0.40 + 1.15 * light[..., None]) + light[..., None] * np.array([28, 16, 5])
    vg = np.clip(1 - 0.6 * (((X - W / 2) / (W * 0.62)) ** 2 + ((Y - H / 2) / (H * 0.62)) ** 2), 0.25, 1)
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
