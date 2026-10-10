"""ep26/27 の背景（夜の寝室：やわらかい毛布と枕、ベッド脇の小さな明かり、カーテン越しのうすい月明かり）・サムネイル・冒頭映像。
冒頭映像では、毛布が呼吸に合わせてごくゆっくり上下し（約4.5秒周期）、明かりがほんの少しだけゆらぐ。
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
MAIN = "ゆっくりした静かな心音"
ELEMENTS = "心音だけ・音楽なし"
EN_LINE = "Slow, Quiet Heartbeat  ·  heartbeat only, no music"

Y, X = np.mgrid[0:H, 0:W].astype(float)
TEX = 0.6 * brand.noise2d(H, W, 3, 61) + 0.4 * brand.noise2d(H, W, 50, 62)
LAMP = (245, 445)


def smooth(e, w):
    return 0.5 + 0.5 * np.tanh(e / w)


def frame(t):
    breath = np.sin(2 * np.pi * t / 4.5)
    # 壁（暗い、少し青みのあるグレー）
    img = np.stack([16 + 6 * TEX, 15 + 6 * TEX, 22 + 7 * TEX], -1)
    # 窓とカーテン（右上）：月明かりが布越しにうすく
    win = smooth(X - 1260, 6) * smooth(1760 - X, 6) * smooth(Y - 90, 6) * smooth(540 - Y, 6)
    folds = 0.75 + 0.25 * np.sin((X - 1260) / 38 + 2 * brand.noise2d(H, W, 30, 63))
    img += win[..., None] * folds[..., None] * np.array([22, 26, 38])
    # ベッドの頭板（中央奥）
    head = smooth(X - 420, 8) * smooth(1500 - X, 8) * smooth(Y - 360, 8) * smooth(620 - Y, 8)
    img = img * (1 - head[..., None]) + head[..., None] * np.stack([26 + 6 * TEX, 19 + 5 * TEX, 15 + 4 * TEX], -1)
    # 枕（2つ）
    for cx in (720, 1200):
        d = ((X - cx) / 230) ** 2 + ((Y - 610) / 70) ** 2
        p = smooth(1 - d, 0.08)
        shade = 1 - 0.35 * np.clip((Y - 560) / 120, 0, 1)
        img = img * (1 - p[..., None]) + p[..., None] * (np.array([70, 66, 64]) * shade[..., None])
    # 毛布（ベッドの上、手前）：大きくゆるいしわ。上の縁が呼吸でごくわずかに上下
    edge = 660 + 14 * np.sin(X / 260 + 0.6) - 3 * breath
    bl = smooth(Y - edge, 4) * smooth(X - 400, 10)
    wave = np.sin(X / 170 + 1.4 * np.sin(Y / 120) + Y / 210)
    fold_shade = 0.70 + 0.22 * wave + 0.03 * breath * (Y < 860)
    blanket = np.array([66, 54, 68]) * fold_shade[..., None] * (0.92 + 0.1 * TEX[..., None])
    img = img * (1 - bl[..., None]) + bl[..., None] * blanket
    # ベッド脇の小さな台と明かり（左）
    stand = smooth(X - 110, 3) * smooth(370 - X, 3) * smooth(Y - 640, 3) * smooth(900 - Y, 3)
    img = img * (1 - stand[..., None]) + stand[..., None] * np.array([34, 24, 18])
    top = smooth(X - 100, 2) * smooth(380 - X, 2) * smooth(Y - 630, 2) * smooth(650 - Y, 2)
    img = img * (1 - top[..., None]) + top[..., None] * np.array([52, 38, 28])
    stem = smooth(X - (LAMP[0] - 6), 1.5) * smooth(LAMP[0] + 6 - X, 1.5) * smooth(Y - 480, 2) * smooth(632 - Y, 2)
    img = img * (1 - stem[..., None]) + stem[..., None] * np.array([40, 32, 24])
    sh = (Y > 400) & (Y < 490) & (np.abs(X - LAMP[0]) < 55 + (Y - 400) * 0.45)
    shade_l = sh.astype(float)
    img = img * (1 - shade_l[..., None]) + shade_l[..., None] * np.array([150, 104, 60])
    flick = 1 + 0.015 * np.sin(2 * np.pi * 0.27 * t) + 0.008 * np.sin(2 * np.pi * 0.71 * t + 1)
    dl = np.hypot((X - LAMP[0]) / 1.2, (Y - LAMP[1] - 40) / 0.9)
    light = np.exp(-(dl / 520) ** 2) * flick
    img = img * (0.45 + 1.2 * light[..., None]) + light[..., None] * np.array([30, 17, 5])
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
