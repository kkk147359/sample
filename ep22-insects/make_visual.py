"""ep22/23 の背景（秋の夜の庭：月明かりのすすきと草むら）・サムネイル・冒頭映像を作る。
冒頭映像では、すすきの穂が風でゆっくり揺れ、草むらの奥でごく小さな光の粒（月明かりの露）がまたたく。
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
MAIN = "秋の夜の虫の声"
ELEMENTS = "2種類だけ・ゆっくりした鳴き声"
EN_LINE = "Autumn Night Insects  ·  two gentle voices, slow and soft"

Y, X = np.mgrid[0:H, 0:W].astype(float)
TEX = 0.6 * brand.noise2d(H, W, 2, 41) + 0.4 * brand.noise2d(H, W, 40, 42)
MOON = (1460, 250, 70)
rng = np.random.default_rng(2201)
# すすき：根元の位置、高さ、傾き、穂の向き
STALKS = [(x, rng.uniform(380, 640), rng.uniform(-0.25, 0.1), rng.uniform(0, 2 * np.pi))
          for x in np.sort(rng.uniform(980, 1880, 22))]
DEW = [(rng.uniform(900, 1900), rng.uniform(800, 1000), rng.uniform(0, 2 * np.pi), rng.uniform(0.3, 0.8)) for _ in range(40)]


def sky():
    # 濃い藍色の夜空。月のまわりだけほんのり明るい
    img = np.stack([10 + 6 * TEX, 14 + 7 * TEX, 26 + 10 * TEX], axis=-1)
    d = np.hypot(X - MOON[0], Y - MOON[1])
    glow = np.exp(-(d / 420) ** 2)
    img += glow[..., None] * np.array([34, 38, 46])
    moon = d < MOON[2]
    img = np.where(moon[..., None], np.array([214, 206, 178]) * (0.92 + 0.08 * TEX[..., None]), img)
    # 遠くの低い山なみ
    ridge = 760 + 40 * brand.noise2d(1, W, 6, 43)[0] * 2 - 20
    img = np.where((Y > ridge[None, :])[..., None], np.stack([8 + 3 * TEX, 10 + 3 * TEX, 14 + 4 * TEX], axis=-1), img)
    # 手前の草むら
    grass = Y > 900 + 30 * np.sin(X / 140) + 20 * brand.noise2d(H, W, 20, 44)
    img = np.where(grass[..., None], np.stack([6 + 3 * TEX, 9 + 4 * TEX, 7 + 3 * TEX], axis=-1), img)
    return img


SKY = None


def frame(t):
    global SKY
    if SKY is None:
        SKY = sky()
    im = Image.fromarray(np.clip(SKY, 0, 255).astype(np.uint8))
    d = ImageDraw.Draw(im)
    for x0, h, lean, ph in STALKS:
        sway = 0.05 * np.sin(2 * np.pi * 0.18 * t + ph)  # ゆっくりした風
        a = lean + sway
        y0 = 1000
        pts = [(x0 + np.sin(a * s / 10) * h * s / 10 * 0.6, y0 - h * s / 10) for s in range(11)]
        d.line(pts, fill=(22, 26, 24), width=4)
        # 穂：先がゆるく垂れる細い毛の束。月明かりで銀色に光る
        tx, ty = pts[-1]
        dirx = np.sin(a + 0.35)
        for k in range(16):
            sp = (k - 7.5) / 7.5
            L = 85 - 25 * abs(sp)
            q = [(tx + dirx * L * u * 0.55 + sp * 14 * u + 10 * u * u * np.sign(dirx),
                  ty - 6 + L * u * 0.85 + 18 * u * u) for u in np.linspace(0, 1, 8)]
            c = int(120 + 40 * (1 - abs(sp)))
            d.line(q, fill=(c, c - 4, c - 18), width=2)
        # 葉：根元から弓なりに垂れる
        for side in (-1, 1):
            bx, by = pts[2]
            L = h * 0.45
            q = [(bx + side * L * u, by - L * 0.35 * u + L * 0.6 * u * u) for u in np.linspace(0, 1, 10)]
            d.line(q, fill=(20, 25, 22), width=3)
    img = np.asarray(im.filter(ImageFilter.GaussianBlur(1.2)), dtype=float)
    # 露の光の粒がゆっくりまたたく
    for dx, dy, ph, s in DEW:
        b = s * (0.5 + 0.5 * np.sin(2 * np.pi * 0.25 * t + ph))
        r2 = (X[int(dy) - 6 : int(dy) + 7, int(dx) - 6 : int(dx) + 7] - dx) ** 2 + (Y[int(dy) - 6 : int(dy) + 7, int(dx) - 6 : int(dx) + 7] - dy) ** 2
        img[int(dy) - 6 : int(dy) + 7, int(dx) - 6 : int(dx) + 7] += (np.exp(-r2 / 6) * 120 * b)[..., None] * np.array([0.8, 0.9, 1.0])
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
