"""ep34/35 の背景（晩秋の夜の庭：落ち葉の積もった地面に静かに雨が降る。石灯籠の明かりがひとつ）・サムネイル・冒頭映像を作る。
冒頭映像では、細い雨がしずかに落ち、灯籠の近くの落ち葉に小さな波紋が出る。まぶしくないよう全体は夜の暗さにする。
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
MAIN = "晩秋の夜、落ち葉に降る静かな雨とピアノ"
ELEMENTS = "雨音・ピアノ"
EN_LINE = "Quiet Rain on Fallen Leaves, Late Autumn Night  ·  rain, soft piano"

Y, X = np.mgrid[0:H, 0:W].astype(float)
TEX = 0.6 * brand.noise2d(H, W, 3, 71) + 0.4 * brand.noise2d(H, W, 50, 72)
LX, LY = 430, 690  # 石灯籠の火袋（明かり）の位置
GROUND = 800 + 18 * np.sin(X / 260) + 10 * brand.noise2d(H, W, 40, 73)


def leaf(d, x, y, s, a, c):
    """もみじの落ち葉（ep32 と同じ形）。地面に寝ているので縦をつぶして描く"""
    up = a - np.pi / 2
    for off, L in [(0, 1.0), (0.85, 0.92), (-0.85, 0.92), (1.65, 0.68), (-1.65, 0.68), (2.3, 0.38), (-2.3, 0.38)]:
        th = up + off
        u = np.linspace(0, 1, 10)
        wdt = 0.26 * L * s * np.sin(np.pi * u ** 0.75)
        cx, cy = x + np.cos(th) * L * s * u, y + 0.45 * np.sin(th) * L * s * u
        nx, ny = -np.sin(th), np.cos(th)
        pts = list(zip(cx + nx * wdt, cy + 0.45 * ny * wdt)) + list(zip((cx - nx * wdt)[::-1], (cy - 0.45 * ny * wdt)[::-1]))
        d.polygon(pts, fill=c)


def base():
    v = np.clip(Y / H, 0, 1)
    sky = np.stack([18 + 22 * v, 22 + 22 * v, 32 + 22 * v], axis=-1) + (TEX[..., None] - 0.5) * 4
    # 遠くの木々（でこぼこの稜線）
    top = 560 + 60 * (brand.noise2d(1, W, 300, 74)[0] - 0.5) * 2 + 24 * (brand.noise2d(1, W, 70, 75)[0] - 0.5) * 2 \
        + 8 * (brand.noise2d(1, W, 14, 76)[0] - 0.5) * 2
    trees = np.clip((Y - top[None, :]) / 14, 0, 1)
    img = sky * (1 - 0.9 * trees[..., None]) + np.array([12, 15, 16]) * 0.9 * trees[..., None]
    # 地面（落ち葉の下地）
    g = Y > GROUND
    img = np.where(g[..., None], np.stack([26 + 8 * TEX, 20 + 6 * TEX, 16 + 5 * TEX], axis=-1), img)
    im = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8))
    d = ImageDraw.Draw(im)
    rng = np.random.default_rng(3401)
    cols = [(120, 40, 24), (138, 62, 28), (104, 34, 26), (150, 90, 40), (90, 52, 30)]
    for _ in range(2600):  # 奥は小さく、手前は大きく
        yy = rng.uniform(790, H + 20)
        k = (yy - 780) / (H - 780)
        xx = rng.uniform(-30, W + 30)
        leaf(d, xx, yy, 7 + 30 * k ** 1.3, rng.uniform(-np.pi, np.pi), tuple(int(c * rng.uniform(0.55, 1.0)) for c in cols[rng.integers(len(cols))]))
    # 石灯籠（シルエット）
    st = (30, 30, 32)
    d.rectangle([LX - 14, LY + 40, LX + 14, 820], fill=st)            # 竿
    d.polygon([(LX - 60, 824), (LX + 60, 824), (LX + 46, 806), (LX - 46, 806)], fill=st)  # 基礎
    d.rectangle([LX - 40, LY - 30, LX + 40, LY + 34], fill=st)        # 火袋
    d.polygon([(LX - 84, LY - 30), (LX + 84, LY - 30), (LX + 30, LY - 72), (LX - 30, LY - 72)], fill=st)  # 笠
    d.ellipse([LX - 12, LY - 92, LX + 12, LY - 68], fill=st)          # 宝珠
    d.rectangle([LX - 30, LY + 34, LX + 30, LY + 46], fill=st)        # 中台
    d.rectangle([LX - 20, LY - 18, LX + 20, LY + 24], fill=(210, 150, 80))  # 火袋の窓（明かり）
    out = np.asarray(im.filter(ImageFilter.GaussianBlur(0.8)), dtype=float)
    # 明かりの広がり（暖かい光が近くの落ち葉を照らす）
    r2 = ((X - LX) / 520) ** 2 + ((Y - (LY + 60)) / 300) ** 2
    glow = np.exp(-r2 * 2.2)
    out = out * (0.55 + 1.3 * glow[..., None]) + np.array([60, 38, 16]) * 0.35 * np.exp(-r2 * 9)[..., None]
    return out


BASE = None
RAIN = None


def rain_layer(t):
    """細い雨のすじ（少し斜め、速く落ちる）。層を3つ重ねて奥行きを出す"""
    global RAIN
    if RAIN is None:
        rng = np.random.default_rng(3402)
        RAIN = [(rng.uniform(0, W, n), rng.uniform(0, H, n), sp, ln, a) for n, sp, ln, a in [(500, 900, 26, 26), (260, 1300, 40, 38), (90, 1800, 60, 50)]]
    lay = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(lay)
    for xs, ys, sp, ln, a in RAIN:
        yy = (ys + sp * t) % (H + 80) - 40
        xx = (xs + 0.12 * sp * t) % W
        for x0, y0 in zip(xx, yy):
            d.line([(x0, y0), (x0 + 0.12 * ln, y0 + ln)], fill=a, width=1)
    return np.asarray(lay.filter(ImageFilter.GaussianBlur(0.6)), dtype=float) / 255


def ripples(t):
    """灯籠の近くの落ち葉に落ちる小さなしずくの波紋"""
    lay = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(lay)
    rng = np.random.default_rng(3403)
    for k in range(240):
        t0 = rng.uniform(-1, 30)
        x0 = LX + rng.normal(0, 260); y0 = rng.uniform(830, 1060)
        u = t - t0
        if 0 <= u < 0.6:
            r = 4 + 34 * u
            d.ellipse([x0 - r, y0 - 0.35 * r, x0 + r, y0 + 0.35 * r], outline=int(70 * (1 - u / 0.6)), width=2)
    return np.asarray(lay, dtype=float) / 255


def frame(t):
    global BASE
    if BASE is None:
        BASE = base()
    img = BASE.copy()
    r = rain_layer(t)
    lit = 0.35 + 0.65 * np.exp(-(((X - LX) / 700) ** 2 + ((Y - LY) / 500) ** 2))  # 明かりの近くの雨ほど見える
    img = img + (np.array([150, 150, 160]) * r * lit)[..., :] if False else img + (r * lit)[..., None] * np.array([150, 150, 160])
    img = img + ripples(t)[..., None] * np.array([200, 170, 130])
    vg = np.clip(1 - 0.5 * (((X - W / 2) / (W * 0.62)) ** 2 + ((Y - H / 2) / (H * 0.62)) ** 2), 0.3, 1)
    img = img * vg[..., None] * 0.9
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
