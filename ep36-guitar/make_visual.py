"""ep36/37 の背景（冬支度の夜：灯りを落とした部屋。木の椅子に立てかけたガットギターと、たたんだ毛布。窓の外は冷えた夜で、最後の葉がときどき落ちる）・サムネイル・冒頭映像を作る。
冒頭映像では、窓の外を葉がゆっくり落ち、スタンドの灯りがかすかにゆらぐ。まぶしくないよう全体は夜の暗さにする。
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
MAIN = "冬支度の夜、やさしいガットギター"
ELEMENTS = "ガットギターだけ・自然音なし"
EN_LINE = "Gentle Nylon Guitar for a Pre-Winter Night  ·  guitar only"

Y, X = np.mgrid[0:H, 0:W].astype(float)
TEX = 0.6 * brand.noise2d(H, W, 3, 361) + 0.4 * brand.noise2d(H, W, 60, 362)
WIN = (1330, 130, 1770, 620)  # 窓
LAMP = (300, 330)  # スタンドの笠の下（明かりの中心）
FLOOR = 860


def guitar_layer(height=640):
    """ガットギター（クラシックギター）を縦に描き、少し傾けて返す（RGBA）。胴の形は幅の表から作る"""
    S = 2
    L = 900  # 設計上の全長
    gw, gh = 360 * S, (L + 20) * S
    g = Image.new("RGBA", (gw, gh), (0, 0, 0, 0))
    d = ImageDraw.Draw(g)
    cx = gw / 2
    # 胴：上端 y=330、下端 y=880。半幅（上のふくらみ 118・くびれ 92・下のふくらみ 158）
    ys = np.linspace(330, 880, 200)
    ky = [330, 345, 380, 440, 520, 600, 690, 780, 840, 868, 880]
    kw = [0, 70, 108, 118, 98, 112, 154, 158, 140, 95, 0]
    hw = np.interp(ys, ky, kw)
    hw = np.convolve(np.pad(hw, 6, mode="edge"), np.ones(13) / 13, "valid")
    hw[0] = hw[-1] = 0
    left = [(cx - w * S, y * S) for y, w in zip(ys, hw)]
    right = [(cx + w * S, y * S) for y, w in zip(ys[::-1], hw[::-1])]
    d.polygon(left + right, fill=(60, 34, 20, 255))
    inner_l = [(cx - max(w - 7, 0) * S, y * S) for y, w in zip(ys, hw)]
    inner_r = [(cx + max(w - 7, 0) * S, y * S) for y, w in zip(ys[::-1], hw[::-1])]
    d.polygon(inner_l + inner_r, fill=(150, 92, 48, 255))
    # サウンドホールとロゼッタ
    d.ellipse([cx - 50 * S, 470 * S, cx + 50 * S, 570 * S], fill=(118, 70, 36, 255))
    d.ellipse([cx - 42 * S, 478 * S, cx + 42 * S, 562 * S], fill=(14, 10, 8, 255))
    # ブリッジ
    d.rounded_rectangle([cx - 64 * S, 742 * S, cx + 64 * S, 764 * S], radius=6 * S, fill=(44, 26, 16, 255))
    # ネックと指板
    d.rectangle([cx - 24 * S, 40 * S, cx + 24 * S, 380 * S], fill=(92, 56, 30, 255))
    d.rectangle([cx - 20 * S, 40 * S, cx + 20 * S, 470 * S], fill=(36, 24, 18, 255))
    for k in range(1, 12):
        y = 40 * S + int(430 * S * (1 - 0.94 ** k) / (1 - 0.94 ** 12))
        d.line([(cx - 20 * S, y), (cx + 20 * S, y)], fill=(120, 110, 96, 255), width=S)
    # ヘッド（ナイロン弦ギターの、穴の開いたヘッド）
    d.rounded_rectangle([cx - 32 * S, -40 * S + 40 * S, cx + 32 * S, 48 * S], radius=8 * S, fill=(70, 42, 24, 255))
    for sx in (-1, 1):
        d.rectangle([cx + sx * 12 * S - 5 * S, 8 * S, cx + sx * 12 * S + 5 * S, 40 * S], fill=(10, 8, 6, 255))
    for k in range(6):
        x = cx - 15 * S + k * 6 * S
        d.line([(x, 46 * S), (x, 752 * S)], fill=(200, 192, 176, 140), width=S)
    sc = height / (L + 20)
    g = g.resize((int(gw * sc / S * S / S), int(gh * sc / S * S / S)) if False else (int(gw / S * sc), int(gh / S * sc)), Image.LANCZOS)
    a = np.asarray(g, dtype=float)
    yy, xx = np.mgrid[0:a.shape[0], 0:a.shape[1]].astype(float)
    shade = 1.15 - 0.55 * (xx / a.shape[1]) - 0.25 * (yy / a.shape[0])
    a[..., :3] *= shade[..., None]
    g = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), "RGBA")
    return g.rotate(10, resample=Image.BICUBIC, expand=True)


def base():
    v = np.clip(Y / H, 0, 1)
    wall = np.stack([30 + 10 * v, 25 + 8 * v, 24 + 6 * v], axis=-1) + (TEX[..., None] - 0.5) * 5
    floor = np.stack([34 + 6 * TEX, 24 + 5 * TEX, 18 + 4 * TEX], axis=-1)
    img = np.where((Y > FLOOR)[..., None], floor, wall)
    im = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8))
    d = ImageDraw.Draw(im)
    # 床板の目地
    for k in range(9):
        y = FLOOR + 12 + k * k * 3.2
        d.line([(0, y), (W, y)], fill=(24, 17, 13), width=1)
    # 窓（外は冷えた夜空）
    x0, y0, x1, y1 = WIN
    d.rectangle([x0 - 16, y0 - 16, x1 + 16, y1 + 16], fill=(46, 34, 26))
    d.rectangle([x0, y0, x1, y1], fill=(16, 22, 36))
    # 椅子（木の背もたれ椅子、ギターの右うしろ）
    ch = (58, 38, 26)
    d.rectangle([600, 420, 622, 900], fill=ch)        # 後ろ脚・背もたれの柱
    d.rectangle([770, 420, 792, 900], fill=ch)
    for y in (440, 500, 560):                          # 背もたれの横木
        d.rectangle([600, y, 792, y + 16], fill=ch)
    d.polygon([(560, 650), (840, 650), (860, 690), (540, 690)], fill=(70, 46, 30))  # 座面
    d.rectangle([548, 690, 566, 930], fill=ch)
    d.rectangle([834, 690, 852, 930], fill=ch)
    # たたんだ毛布（座面の上に置き、端が座面の右から垂れる。生成りに深緑の線）
    bl = (132, 120, 98)
    d.rounded_rectangle([640, 600, 836, 652], radius=22, fill=bl)
    d.rounded_rectangle([652, 572, 826, 612], radius=18, fill=(142, 130, 106))
    d.polygon([(812, 640), (850, 646), (858, 760), (838, 776), (816, 770)], fill=bl)  # 垂れた端
    for x in (690, 740, 790):
        d.line([(x, 576), (x, 650)], fill=(70, 86, 66), width=4)
    d.line([(656, 626), (832, 626)], fill=(70, 86, 66), width=4)
    d.line([(828, 700), (854, 700)], fill=(70, 86, 66), width=4)
    for k in range(5):  # 垂れた端の房
        d.line([(820 + 8 * k, 772 - 2 * k), (820 + 8 * k, 788 - 2 * k)], fill=(120, 108, 88), width=2)
    # スタンドライト（左。笠は布、灯りは小さく）
    d.line([(LAMP[0], LAMP[1] + 20), (LAMP[0], 905)], fill=(40, 32, 26), width=6)
    d.ellipse([LAMP[0] - 60, 896, LAMP[0] + 60, 916], fill=(36, 28, 22))
    d.polygon([(LAMP[0] - 70, LAMP[1] + 10), (LAMP[0] + 70, LAMP[1] + 10), (LAMP[0] + 44, LAMP[1] - 80), (LAMP[0] - 44, LAMP[1] - 80)], fill=(196, 150, 96))
    # ギター（椅子に立てかける）
    g = guitar_layer()
    im.paste(g, (470, 912 - g.size[1]), g)
    out = np.asarray(im.filter(ImageFilter.GaussianBlur(0.7)), dtype=float)
    return out


BASE = None
LEAVES = None


def lamp_glow(t):
    """スタンドの暖かい明かり。ごくわずかにゆらぐ"""
    k = 1 + 0.015 * np.sin(2 * np.pi * t / 4.3) + 0.01 * np.sin(2 * np.pi * t / 1.7)
    r2 = ((X - LAMP[0]) / 720) ** 2 + ((Y - (LAMP[1] + 260)) / 520) ** 2
    return k * np.exp(-r2 * 2.0)


def window_layer(t):
    """窓の外：星がいくつかと、ゆっくり落ちる最後の葉"""
    global LEAVES
    x0, y0, x1, y1 = WIN
    rng = np.random.default_rng(363)
    if LEAVES is None:
        LEAVES = [(rng.uniform(x0, x1), rng.uniform(0, 1), rng.uniform(25, 45), rng.uniform(0, 6.3), rng.uniform(5, 9)) for _ in range(7)]
    lay = Image.new("RGB", (W, H), (0, 0, 0))
    d = ImageDraw.Draw(lay)
    for _ in range(40):
        sx, sy = rng.uniform(x0, x1), rng.uniform(y0, y0 + 0.6 * (y1 - y0))
        b = int(rng.uniform(40, 110))
        d.point((sx, sy), fill=(b, b, b + 10))
    # 遠くの家並みと木（シルエット）
    d.polygon([(x0, y1), (x0, y1 - 70), (x0 + 90, y1 - 70), (x0 + 140, y1 - 110), (x0 + 190, y1 - 70), (x0 + 260, y1 - 70),
               (x0 + 260, y1 - 95), (x1 - 120, y1 - 95), (x1 - 80, y1 - 150), (x1 - 40, y1 - 95), (x1, y1 - 95), (x1, y1)], fill=(9, 11, 16))
    d.rectangle([x0 + 200, y1 - 60, x0 + 214, y1 - 48], fill=(70, 56, 34))  # 遠くの家の小さな灯り
    for lx, ph, sp, rot, sw in LEAVES:
        y = y0 + ((ph * (y1 - y0) + sp * t) % (y1 - y0))
        x = lx + 18 * np.sin(2 * np.pi * t / sw + rot)
        a = rot + t * 0.6
        pts = [(x + 9 * np.cos(a), y + 4 * np.sin(a)), (x + 3 * np.cos(a + 1.6), y + 5 * np.sin(a + 1.6)),
               (x - 9 * np.cos(a), y - 4 * np.sin(a)), (x - 3 * np.cos(a + 1.6), y - 5 * np.sin(a + 1.6))]
        d.polygon(pts, fill=(96, 60, 30))
    m = np.zeros((H, W, 1))
    m[y0:y1, x0:x1] = 1
    return np.asarray(lay, dtype=float) * m


def frame(t):
    global BASE
    if BASE is None:
        BASE = base()
    img = BASE.copy()
    x0, y0, x1, y1 = WIN
    img[y0:y1, x0:x1] = np.maximum(img[y0:y1, x0:x1] - 0, 0)
    w = window_layer(t)
    inwin = w.sum(-1, keepdims=True) > 0
    img = np.where(inwin, w, img)
    gl = lamp_glow(t)
    img = img * (0.5 + 1.25 * gl[..., None]) + np.array([70, 44, 18]) * 0.45 * (gl ** 3)[..., None]
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
