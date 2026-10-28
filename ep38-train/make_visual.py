"""ep38/39 の背景（冬へ向かう夜の夜行列車：灯りを落とした車内から見る窓。遠くの町の灯りがゆっくり流れ、近くの灯りはときどき速く過ぎる。
窓の隅にうっすら霜、手前に座席の背もたれ）・サムネイル・冒頭映像を作る。まぶしくないよう全体は夜の暗さにする。
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
MAIN = "冬へ向かう夜、静かに走る夜行列車の音"
ELEMENTS = "列車の走行音だけ・音楽なし"
EN_LINE = "A Quiet Night Train Toward Winter  ·  train sounds only"

Y, X = np.mgrid[0:H, 0:W].astype(float)
WIN = (230, 150, 1690, 720)   # 窓
HORIZON = 545
BASE = None


def base():
    """車内（壁・天井の灯り・窓枠・座席）。窓の中は frame で描く"""
    tex = 0.6 * brand.noise2d(H, W, 3, 381) + 0.4 * brand.noise2d(H, W, 50, 382)
    img = np.zeros((H, W, 3))
    img[:] = np.array([22, 24, 32]) + (tex[..., None] - 0.5) * 6
    # 天井の灯り（上の中央、暖かい色でかすか）
    g = np.exp(-(((X - 960) / 900) ** 2 + ((Y + 120) / 260) ** 2))
    img += np.array([60, 44, 26]) * g[..., None]
    # 壁の横の線（荷物棚の下）
    img[118:126] *= 0.55
    img[126:132] += 8
    pil = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8))
    d = ImageDraw.Draw(pil)
    x0, y0, x1, y1 = WIN
    d.rounded_rectangle([x0 - 26, y0 - 26, x1 + 26, y1 + 26], radius=58, fill=(38, 40, 48))
    d.rounded_rectangle([x0 - 10, y0 - 10, x1 + 10, y1 + 10], radius=46, fill=(14, 15, 20))
    # 窓の下の小さなテーブル
    d.rectangle([x0 + 40, y1 + 40, x1 - 40, y1 + 58], fill=(46, 36, 30))
    d.rectangle([x0 + 40, y1 + 58, x1 - 40, y1 + 64], fill=(24, 20, 18))
    # 座席の背もたれ（左右手前）
    for cx, w in ((150, 330), (1770, 330)):
        d.rounded_rectangle([cx - w // 2, 700, cx + w // 2, H + 80], radius=60, fill=(30, 36, 58))
        d.rounded_rectangle([cx - w // 2 + 22, 760, cx + w // 2 - 22, H + 80], radius=46, fill=(36, 44, 70))
        d.rounded_rectangle([cx - w // 2 + 40, 690, cx + w // 2 - 40, 742], radius=22, fill=(118, 116, 112))  # 枕カバー
    return np.asarray(pil, dtype=float)


R = np.random.default_rng(38)
# 遠くの町の灯り（ゆっくり）・中くらい・近く（速い）
FAR = [(R.uniform(0, 6000), R.uniform(HORIZON - 30, HORIZON + 22), R.uniform(0.25, 1.0), R.random() < 0.7) for _ in range(260)]
MID = [(R.uniform(0, 9000), R.uniform(HORIZON + 10, HORIZON + 80), R.uniform(0.3, 1.0), R.random() < 0.8) for _ in range(70)]
POLES = [R.uniform(0, 24000) for _ in range(6)]
STARS = [(R.uniform(0, 3000), R.uniform(150, 420), R.uniform(0.2, 0.7)) for _ in range(90)]


def window_layer(t):
    x0, y0, x1, y1 = WIN
    w, h = x1 - x0, y1 - y0
    yy = np.arange(h)[:, None] + y0
    sky = np.zeros((h, w, 3))
    k = np.clip((yy - y0) / (HORIZON - y0), 0, 1)
    k = k[..., None]
    sky[:] = (np.array([6, 9, 22]) * (1 - k) + np.array([18, 22, 40]) * k)
    ground = yy > HORIZON
    sky = np.where(ground[..., None], np.array([7, 8, 12]) + 0 * sky, sky)
    pts = Image.new("RGB", (w, h))
    d = ImageDraw.Draw(pts)
    for sx, sy, b in STARS:
        x = (sx - 3 * t) % 3000 - 600
        if 0 <= x < w:
            v = int(150 * b)
            d.point((x, sy - y0), fill=(v, v, int(v * 1.05)))
    # 遠くの山の稜線
    ridge = HORIZON - 14 - 18 * brand.noise2d(1, 6000, 300, 383)[0]
    for sx, sy, b, warm in FAR:
        x = (sx - 22 * t) % 6000 - 2000
        if -4 <= x < w + 4:
            c = (255, 196, 120) if warm else (220, 228, 255)
            r = 1.3 + b
            d.ellipse([x - r, sy - y0 - r, x + r, sy - y0 + r], fill=tuple(int(v * b * 0.8) for v in c))
    for sx, sy, b, warm in MID:
        x = (sx - 70 * t) % 9000 - 3000
        if -10 <= x < w + 10:
            c = (255, 186, 110) if warm else (210, 222, 255)
            d.ellipse([x - 3, sy - y0 - 3, x + 3, sy - y0 + 3], fill=tuple(int(v * b * 0.75) for v in c))
    glow = np.asarray(pts.filter(ImageFilter.GaussianBlur(5)), dtype=float) * 2.2
    core = np.asarray(pts.filter(ImageFilter.GaussianBlur(0.8)), dtype=float)
    img = sky + glow + core * 0.9
    # 稜線より上の灯りは山に隠れる（遠くの山のシルエット）
    rx = ((np.arange(w) + 22 * t * 0.6) % 6000).astype(int)
    mount = (yy - y0) > (ridge[rx][None, :] - y0)
    img = np.where((mount & ~ground)[..., None], np.array([9, 11, 18]) + 0.35 * glow, img)
    # 近くの電柱（ときどき速く通り過ぎる、ぼけた暗い影）
    for px in POLES:
        x = (px - 900 * t) % 24000 - 2000
        if -80 < x < w + 80:
            band = np.exp(-((np.arange(w) - x) / 26) ** 2)
            img *= (1 - 0.75 * band)[None, :, None]
    # 窓の隅の霜とガラスの映り込み
    fx = np.arange(w)[None, :]
    fy = np.arange(h)[:, None]
    frost = np.exp(-np.minimum(np.minimum(fx, w - fx), 9e9) / 60) * np.exp(-(h - fy) / 70) * (0.5 + brand.noise2d(h, w, 9, 384))
    img += 40 * frost[..., None] * np.array([0.8, 0.9, 1.0])
    refl = np.exp(-(((fx - w * 0.5) / (w * 0.5)) ** 2 + ((fy + 60) / 220) ** 2))
    img += np.array([24, 18, 12]) * refl[..., None]
    return img


def frame(t):
    global BASE
    if BASE is None:
        BASE = base()
    img = BASE.copy()
    x0, y0, x1, y1 = WIN
    mask = Image.new("L", (W, H))
    ImageDraw.Draw(mask).rounded_rectangle([x0, y0, x1, y1], radius=40, fill=255)
    m = (np.asarray(mask, dtype=float) / 255)[..., None]
    win = np.zeros_like(img)
    win[y0:y1, x0:x1] = window_layer(t)
    img = img * (1 - m) + win * m
    vg = np.clip(1 - 0.55 * (((X - W / 2) / (W * 0.62)) ** 2 + ((Y - H / 2) / (H * 0.62)) ** 2), 0.3, 1)
    img = img * vg[..., None]
    return np.clip(img + np.random.default_rng(int(t * 12)).normal(0, 1.0, img.shape), 0, 255)


if __name__ == "__main__":
    cmd, out = sys.argv[1], sys.argv[2]
    if cmd == "bg":
        Image.fromarray(frame(5.0).astype(np.uint8)).save(out)
    elif cmd == "thumb":
        brand.thumbnail(frame(5.0), out, MAIN, ELEMENTS, sys.argv[3])
    elif cmd == "intro":
        brand.intro(frame, out, MAIN, EN_LINE)
    print("wrote", out)
