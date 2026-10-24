"""ep32/33 の背景（晩秋の朝の庭：薄明るい朝もや、紅葉した枝に小鳥が2羽）・サムネイル・冒頭映像を作る。
冒頭映像では、朝もやがゆっくり流れ、紅葉の葉がときどき1枚ずつ舞い落ちる。まぶしくないよう、全体は日の出前の薄暗さにする。
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
MAIN = "小鳥来る、晩秋の朝の庭"
ELEMENTS = "小鳥の声だけ・音楽なし"
EN_LINE = "Late Autumn Morning Garden  ·  distant small birds, no music"

Y, X = np.mgrid[0:H, 0:W].astype(float)
TEX = 0.6 * brand.noise2d(H, W, 2, 51) + 0.4 * brand.noise2d(H, W, 40, 52)
rng = np.random.default_rng(3201)


def _branch_points():
    """右上から斜めに入る枝（主枝と小枝）"""
    segs = []
    main = [(2000, 170), (1720, 230), (1480, 300), (1260, 350), (1080, 372)]
    segs.append((main, 16))
    for (x0, y0), ang, L, w in [((1720, 230), 2.4, 220, 8), ((1480, 300), 2.0, 200, 7), ((1480, 300), 3.6, 160, 6),
                                ((1260, 350), 2.2, 150, 5), ((1260, 350), 3.9, 130, 5), ((1640, 250), 4.1, 180, 6)]:
        pts = [(x0 + np.cos(ang) * L * u + 12 * np.sin(5 * u), y0 - np.sin(ang) * L * u + 18 * u * u) for u in np.linspace(0, 1, 8)]
        segs.append((pts, w))
    return segs


BRANCH = _branch_points()
# 葉：枝先のまわりに散らす（位置、大きさ、向き、色）
LEAVES = []
for pts, w in BRANCH:
    for (px, py) in pts[2:]:
        for _ in range(2):
            c = rng.choice([(150, 52, 30), (172, 78, 34), (128, 40, 28), (184, 104, 46)])
            LEAVES.append((px + rng.normal(0, 26), py + rng.normal(0, 20), rng.uniform(15, 23), rng.uniform(-0.9, 0.9), c))
# 小鳥2羽（枝にとまる影）
BIRDS = [(1395, 312, 1.0, 1), (1205, 356, 0.85, -1)]
# 舞い落ちる葉：出る時刻、始まりの位置、揺れ
FALL = [(0.5, 1500, 1.1), (4.0, 1290, 0.8), (7.5, 1640, 1.3), (14.5, 1450, 0.9), (20.0, 1580, 1.2)]  # 15秒以降はショート用


def leaf(d, x, y, s, a, c):
    """もみじの葉：中心から7つの裂片（先がとがり、中ほどがふくらむ）を開き、短い柄をつける"""
    up = a - np.pi / 2
    for off, L in [(0, 1.0), (0.85, 0.92), (-0.85, 0.92), (1.65, 0.68), (-1.65, 0.68), (2.3, 0.38), (-2.3, 0.38)]:
        th = up + off
        u = np.linspace(0, 1, 14)
        wdt = 0.26 * L * s * np.sin(np.pi * u ** 0.75) * (1 + 0.12 * (np.arange(14) % 2))  # ぎざぎざの縁
        cx, cy = x + np.cos(th) * L * s * u, y + np.sin(th) * L * s * u
        nx, ny = -np.sin(th), np.cos(th)
        pts = list(zip(cx + nx * wdt, cy + ny * wdt)) + list(zip((cx - nx * wdt)[::-1], (cy - ny * wdt)[::-1]))
        d.polygon(pts, fill=c)
    d.ellipse([x - 0.22 * s, y - 0.22 * s, x + 0.22 * s, y + 0.22 * s], fill=c)
    d.line([(x, y), (x - np.cos(up) * s * 0.6, y - np.sin(up) * s * 0.6)], fill=c, width=2)


def bird(d, x, y, s, facing, col=(22, 20, 22)):
    """枝にとまる丸い小鳥の影"""
    d.ellipse([x - 26 * s, y - 34 * s, x + 26 * s, y], fill=col)  # 胴
    hx = x + facing * 18 * s
    d.ellipse([hx - 14 * s, y - 48 * s, hx + 14 * s, y - 22 * s], fill=col)  # 頭
    d.polygon([(hx + facing * 12 * s, y - 38 * s), (hx + facing * 24 * s, y - 35 * s), (hx + facing * 12 * s, y - 32 * s)], fill=col)  # くちばし
    tx = x - facing * 24 * s
    d.polygon([(tx, y - 16 * s), (tx - facing * 30 * s, y - 2 * s), (tx - facing * 26 * s, y + 6 * s), (tx + facing * 4 * s, y - 6 * s)], fill=col)  # 尾


def base():
    # 日の出前の空：上は灰青、下（地平近く）がほんのり暖かい
    v = np.clip(Y / H, 0, 1)
    sky = np.stack([62 + 70 * v ** 1.5, 70 + 58 * v ** 1.5, 86 + 30 * v ** 1.5], axis=-1)
    sky += (TEX[..., None] - 0.5) * 6
    # 遠くの庭木（もやにかすむ木々の並び：いくつもの小さな丸みが重なった、でこぼこの稜線）
    xs = np.arange(W, dtype=float)
    top = 700 + 70 * (brand.noise2d(1, W, 260, 54)[0] - 0.5) * 2 + 28 * (brand.noise2d(1, W, 60, 55)[0] - 0.5) * 2 \
        + 10 * (brand.noise2d(1, W, 14, 56)[0] - 0.5) * 2
    trees = np.clip((Y - top[None, :]) / 18, 0, 1)
    trees *= 0.6 + 0.4 * TEX
    tree_col = np.array([46, 52, 50])
    img = sky * (1 - 0.85 * trees[..., None]) + tree_col * 0.85 * trees[..., None]
    # 手前の地面（苔と落ち葉）
    ground = Y > 960 + 25 * np.sin(X / 210) + 15 * brand.noise2d(H, W, 30, 53)
    gcol = np.stack([40 + 10 * TEX, 44 + 10 * TEX, 38 + 8 * TEX], axis=-1)
    img = np.where(ground[..., None], gcol, img)
    return img


BASE = None


MIST_N = {}


def mist(t):
    """横にゆっくり流れる朝もや（2層）"""
    m = np.zeros((H, W))
    for spd, y0, amp, seed in [(6.0, 760, 0.55, 61), (11.0, 880, 0.45, 62)]:
        if seed not in MIST_N:
            MIST_N[seed] = brand.noise2d(H, W + 400, 120, seed)
        n = MIST_N[seed]
        sh = int(spd * t) % 400
        layer = n[:, sh: sh + W]
        band = np.exp(-((Y - y0) / 150) ** 2)
        m += amp * band * (0.4 + 0.6 * layer)
    return np.clip(m, 0, 1)


def frame(t):
    global BASE
    if BASE is None:
        BASE = base()
    img = BASE.copy()
    mc = np.array([150, 150, 156])
    m = mist(t)[..., None]
    img = img * (1 - 0.6 * m) + mc * 0.6 * m
    im = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8))
    d = ImageDraw.Draw(im)
    sway = 3 * np.sin(2 * np.pi * 0.07 * t)  # 枝はほとんど動かない
    for pts, w in BRANCH:
        d.line([(x, y + sway * (2000 - x) / 900) for x, y in pts], fill=(34, 28, 26), width=int(w), joint="curve")
    for x, y, s, a, c in LEAVES:
        leaf(d, x, y + sway * (2000 - x) / 900, s, a + 0.05 * np.sin(2 * np.pi * 0.1 * t + x), tuple(int(v * 0.8) for v in c))
    for x, y, s, f in BIRDS:
        bird(d, x, y + sway * (2000 - x) / 900, s, f)
    for t0, x0, sp in FALL:  # 舞い落ちる葉（6秒かけて）
        u = (t - t0) / 6.0
        if 0 <= u <= 1:
            leaf(d, x0 - 160 * u + 40 * np.sin(2 * np.pi * u * sp), 400 + 520 * u, 15, 6 * u, (140, 60, 34))
    out = np.asarray(im.filter(ImageFilter.GaussianBlur(1.0)), dtype=float)
    vg = np.clip(1 - 0.5 * (((X - W / 2) / (W * 0.62)) ** 2 + ((Y - H / 2) / (H * 0.62)) ** 2), 0.3, 1)
    out = out * vg[..., None] * 0.82  # まぶしくない明るさ（日の出前）
    return np.clip(out + np.random.default_rng(int(t * 12)).normal(0, 1.0, out.shape), 0, 255)


if __name__ == "__main__":
    cmd, out = sys.argv[1], sys.argv[2]
    if cmd == "bg":
        Image.fromarray(frame(1.2).astype(np.uint8)).save(out)
    elif cmd == "thumb":
        brand.thumbnail(frame(3.0), out, MAIN, ELEMENTS, sys.argv[3])
    elif cmd == "intro":
        brand.intro(frame, out, MAIN, EN_LINE)
    print("wrote", out)
