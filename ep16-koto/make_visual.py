"""ep16/17 の背景（夜の庭の水琴窟）・サムネイル・冒頭映像を作る。
背景はプログラムで描く：月明かりの竹林を背に、つくばい（石の手水鉢）と筧（竹の樋）。
冒頭映像では、筧からしずくが落ちて水面に波紋が広がる。
使い方:
  python3 make_visual.py bg <出力.png>                   背景（静止）1枚
  python3 make_visual.py thumb <出力.png> <1時間|8時間>   サムネイル
  python3 make_visual.py intro <出力.mp4>                冒頭15秒（10秒から5秒でフェードアウト）
"""
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H = 1920, 1080
FONT_DIR = "/usr/share/fonts/opentype/noto/"
BOLD = (FONT_DIR + "NotoSansCJK-Bold.ttc", 0)
REGULAR = (FONT_DIR + "NotoSansCJK-Regular.ttc", 0)
LIGHT = ("/root/.fonts/NotoSansJP_300Light.ttf", 0)
MAIN = "水琴窟と低い琴の音"
ELEMENTS = "低音の琴・水琴窟"
EN_LINE = "Suikinkutsu & Low Koto  ·  low koto, water-drop chime"

rng = np.random.default_rng(1604)
BASIN_C = (980, 760)  # つくばいの中心
WATER_R = (230, 62)  # 水面の楕円（横・縦の半径）
SPOUT_TIP = (900, 600)  # 筧の先
DROP_X = 905
DROP_Y_WATER = BASIN_C[1] - 6


def font(spec, size):
    return ImageFont.truetype(spec[0], size, index=spec[1])


def _noise(h, w, scale, seed):
    r = np.random.default_rng(seed)
    small = r.random((h // scale + 2, w // scale + 2))
    img = Image.fromarray((small * 255).astype(np.uint8)).resize((w + scale * 2, h + scale * 2), Image.BICUBIC)
    return np.asarray(img, dtype=float)[:h, :w] / 255


def base_scene():
    """静止した背景（水面の波紋としずく以外）"""
    y, x = np.mgrid[0:H, 0:W].astype(float)
    # 夜空〜奥の暗がり：上は深い藍、下は黒みがかった緑
    t = y / H
    img = np.zeros((H, W, 3))
    img[..., 0] = 10 * (1 - t) + 6 * t
    img[..., 1] = 14 * (1 - t) + 12 * t
    img[..., 2] = 26 * (1 - t) + 10 * t
    # 右上の月明かり（直接は見せず、ぼんやりした光だけ）
    d = np.hypot(x - 1600, y - 90)
    glow = np.exp(-(d / 520) ** 2)
    img += glow[..., None] * np.array([38, 46, 60])

    # 奥の竹林：縦の竹のシルエット（奥ほど暗く・ぼかす）
    bamboo = Image.new("L", (W, H), 0)
    dr = ImageDraw.Draw(bamboo)
    for i in range(46):
        bx = rng.uniform(-40, W + 40)
        bw = rng.uniform(10, 26)
        lean = rng.uniform(-30, 30)
        shade = int(rng.uniform(40, 110))
        dr.polygon([(bx, -10), (bx + bw, -10), (bx + bw + lean, 720), (bx + lean, 720)], fill=shade)
        for ny in np.arange(rng.uniform(40, 140), 700, rng.uniform(120, 190)):
            nx = bx + lean * ny / 720
            dr.line([(nx - 2, ny), (nx + bw + 2, ny)], fill=max(0, shade - 35), width=3)
    bamboo = np.asarray(bamboo.filter(ImageFilter.GaussianBlur(3)), dtype=float) / 255
    fade = np.clip((660 - y) / 160, 0, 1) * (0.6 + 0.8 * glow)
    bamboo_col = np.array([26, 44, 34])
    img = img * (1 - 0.8 * bamboo[..., None] * fade[..., None]) + bamboo[..., None] * fade[..., None] * bamboo_col

    # 地面の苔：620pxより下、緑の濃淡のまだら
    ground = np.clip((y - 600) / 60, 0, 1)
    moss = 0.55 * _noise(H, W, 6, 1) + 0.3 * _noise(H, W, 24, 2) + 0.15 * _noise(H, W, 80, 3)
    moss_col = np.stack([10 + 14 * moss, 22 + 30 * moss, 12 + 14 * moss], axis=-1)
    img = img * (1 - ground[..., None]) + moss_col * ground[..., None]

    # 奥の地面と竹林の境目に、薄い夜霧
    fog = np.exp(-((y - 610) / 45) ** 2) * (0.5 + 0.5 * _noise(H, W, 120, 4))
    img = img + fog[..., None] * np.array([14, 18, 22])

    # 周りの石（ふちが少しでこぼこで、左上から月明かりが当たる）
    stones = [(560, 870, 125, 50), (1430, 890, 165, 62), (1290, 1000, 92, 36), (690, 1015, 115, 42), (1650, 805, 72, 28)]
    for sx, sy, rx, ry in stones:
        img = _stone(img, x, y, sx, sy, rx, ry, seed=int(sx))

    # つくばい：上から見た円い石の鉢。手前に側面、内側に水面へ下がる壁
    cx, cy = BASIN_C
    RX, RY, HGT = 320, 108, 120
    ang = np.arctan2((y - cy) / RY, (x - cx) / RX)
    wob = 1 + 0.025 * np.sin(5 * ang + 1.3) + 0.015 * np.sin(11 * ang + 0.4)  # 自然石のゆがみ
    e_top = np.hypot((x - cx) / RX, (y - cy) / RY) / wob
    e_bot = np.hypot((x - cx) / RX, (y - cy - HGT) / RY) / wob
    within_x = np.abs(x - cx) <= RX * wob
    side = within_x & (y >= cy) & (e_bot <= 1) | within_x & (y >= cy) & (y <= cy + HGT) & (np.abs(x - cx) <= RX * wob * np.sqrt(np.clip(1 - 0, 0, 1)))
    side &= (e_bot <= 1) | (y <= cy + HGT)
    side &= np.abs(x - cx) <= RX * wob
    tex = 0.5 * _noise(H, W, 4, 11) + 0.3 * _noise(H, W, 18, 12) + 0.2 * _noise(H, W, 60, 13)
    # 側面：上は月明かり、下に行くほど暗い。左右の端も暗く
    sh = np.clip(1 - (y - cy) / (HGT + RY), 0.15, 1) * (1 - 0.6 * ((x - cx) / RX) ** 2)
    side_col = np.stack([44 + 34 * tex, 46 + 34 * tex, 48 + 32 * tex], axis=-1) * np.clip(sh, 0.12, 1)[..., None]
    img = np.where((side & (e_top > 1))[..., None], side_col, img)
    # 上面（ふち）：左上ほど明るい
    top = e_top <= 1
    lit = 0.7 + 0.45 * np.clip(-((x - cx) / RX) * 0.5 - ((y - cy) / RY) * 0.7, -0.6, 1)
    top_col = np.stack([58 + 40 * tex, 60 + 40 * tex, 62 + 38 * tex], axis=-1) * lit[..., None]
    img = np.where(top[..., None], top_col, img)
    # 内側の壁：水面に向かって暗くなる（奥側の壁が見える）
    inner = np.hypot((x - cx) / (WATER_R[0] + 34), (y - cy + 6) / (WATER_R[1] + 16)) <= 1
    wall_dark = np.clip((y - (cy - WATER_R[1] - 16)) / (2 * WATER_R[1] + 32), 0, 1)
    wall_col = np.stack([30 + 20 * tex, 31 + 20 * tex, 33 + 20 * tex], axis=-1) * (0.9 - 0.6 * wall_dark)[..., None]
    img = np.where(inner[..., None], wall_col, img)
    # 水面（暗く、月明かりの映り込み）
    water = ((x - cx) / WATER_R[0]) ** 2 + ((y - cy) / WATER_R[1]) ** 2 <= 1
    refl = np.exp(-(((x - cx - 70) / 90) ** 2 + ((y - cy + 14) / 18) ** 2))
    water_col = np.stack([5 + 40 * refl, 9 + 48 * refl, 15 + 60 * refl], axis=-1)
    img = np.where(water[..., None], water_col, img)
    # 鉢の根元に落ちる影
    shadow = np.exp(-(np.hypot((x - cx - 20) / (RX * 1.15), (y - cy - HGT - 8) / (RY * 0.6)) ** 4))
    img = np.where((~(side | top))[..., None], img * (1 - 0.6 * shadow[..., None]), img)

    # 筧（竹の樋）：左の奥から鉢の上へ斜めに。月明かりで上側だけ少し明るい
    im = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8))
    dr = ImageDraw.Draw(im)
    x0, y0 = 260, 470
    x1, y1 = SPOUT_TIP
    for wdt, col in [(26, (20, 30, 18)), (20, (36, 52, 30)), (10, (54, 74, 42)), (4, (78, 100, 60))]:
        off = (26 - wdt) * 0.25
        dr.line([(x0, y0 - off), (x1, y1 - off)], fill=col, width=wdt)
    for k in (0.28, 0.6):
        nx, ny = x0 + (x1 - x0) * k, y0 + (y1 - y0) * k
        dr.line([(nx - 4, ny - 13), (nx + 4, ny + 13)], fill=(16, 24, 14), width=5)
    dr.ellipse([(x1 - 9, y1 - 11), (x1 + 7, y1 + 11)], fill=(14, 18, 12))  # 竹の切り口
    # 筧を支える竹の柱（二本を交差させる）
    for (px0, py0, px1, py1) in [(440, 905, 470, 505), (500, 905, 455, 505)]:
        dr.line([(px0, py0), (px1, py1)], fill=(24, 34, 20), width=16)
        dr.line([(px0 - 3, py0), (px1 - 3, py1)], fill=(44, 60, 36), width=5)
    im = im.filter(ImageFilter.GaussianBlur(0.9))
    img = np.asarray(im, dtype=float)

    # 周辺を暗く（ビネット）と、ごく弱い粒子
    v = np.clip(1 - 0.55 * (((x - W / 2) / (W * 0.62)) ** 2 + ((y - H / 2) / (H * 0.62)) ** 2), 0.25, 1)
    img = img * v[..., None] + rng.normal(0, 1.2, img.shape)
    return np.clip(img, 0, 255)


def _stone(img, x, y, sx, sy, rx, ry, seed):
    r = np.random.default_rng(seed)
    ang = np.arctan2((y - sy) / ry, (x - sx) / rx)
    wob = 1 + sum(r.uniform(0.02, 0.07) * np.sin(k * ang + r.uniform(0, 6.28)) for k in (2, 3, 5))
    e = np.hypot((x - sx) / rx, (y - sy) / ry) / wob
    m = e <= 1
    tex = 0.6 * _noise(H, W, 5, seed) + 0.4 * _noise(H, W, 22, seed + 1)
    # 左上から光、下側は地面に沈んで暗い
    lit = 0.55 + 0.5 * np.clip(-((x - sx) / rx) * 0.4 - ((y - sy) / ry) * 0.8, -0.8, 1)
    lit *= np.clip(1.15 - e ** 3 * 0.5, 0.4, 1.1)
    col = np.stack([34 + 26 * tex, 36 + 26 * tex, 38 + 24 * tex], axis=-1) * lit[..., None]
    shadow = np.exp(-(np.hypot((x - sx - 10) / (rx * 1.2), (y - sy - ry * 0.7) / (ry * 0.6)) ** 4))
    img = np.where(m[..., None], img, img * (1 - 0.5 * shadow[..., None]))
    return np.where(m[..., None], col, img)


def frame(base, t, drops):
    """時刻 t 秒の1コマ。drops はしずくが水面に落ちる時刻のリスト"""
    img = base.copy()
    y, x = np.mgrid[0:H, 0:W].astype(float)
    cx, cy = BASIN_C
    water = ((x - cx) / WATER_R[0]) ** 2 + ((y - cy) / WATER_R[1]) ** 2 <= 1
    # 波紋：落ちた点から楕円の輪が広がり、2.5秒で消える
    ring = np.zeros((H, W))
    for td in drops:
        age = t - td
        if 0 <= age < 2.5:
            rr = 8 + 95 * age
            d = np.sqrt(((x - DROP_X) / 1.0) ** 2 + ((y - DROP_Y_WATER) / 0.27) ** 2)
            ring += np.exp(-((d - rr) / 4.5) ** 2) * (1 - age / 2.5) ** 1.5
            ring += 0.5 * np.exp(-((d - rr * 0.6) / 3.5) ** 2) * (1 - age / 2.5) ** 2
    img += (water * ring)[..., None] * np.array([46, 54, 64])
    # 落ちてくるしずく（筧の先から水面まで0.35秒）
    for td in drops:
        age = td - t
        if 0 <= age < 0.35:
            p = 1 - age / 0.35
            dy = SPOUT_TIP[1] + 8 + (DROP_Y_WATER - SPOUT_TIP[1] - 8) * p ** 2
            dd = np.hypot(x - DROP_X, (y - dy) / 1.6)
            img += np.exp(-(dd / 3.2) ** 2)[..., None] * np.array([120, 130, 140])
    # 筧の先にふくらむしずく
    grow = min(1.0, min([(t - td) % 1e9 for td in drops if td <= t] + [9]) / 1.2)
    dd = np.hypot(x - DROP_X, y - (SPOUT_TIP[1] + 8))
    img += (np.exp(-(dd / (1.5 + 2.2 * grow)) ** 2) * 0.8)[..., None] * np.array([110, 120, 130])
    return np.clip(img, 0, 255)


def thumbnail(base, path, hours_label):
    """ブランド規定のサムネイル（1280×720）"""
    bg = Image.fromarray(base.astype(np.uint8)).resize((1280, 720), Image.LANCZOS)
    a = np.asarray(bg, dtype=float) / 255
    lum = (0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]).mean()
    a = np.clip(a * (0.19 / lum), 0, 1)
    bg = Image.fromarray((a * 255).astype(np.uint8)).convert("RGBA")
    ov = Image.new("RGBA", bg.size, (0, 0, 0, 0))
    ImageDraw.Draw(ov).ellipse([140, 170, 1140, 600], fill=(0, 0, 0, 90))
    bg = Image.alpha_composite(bg, ov.filter(ImageFilter.GaussianBlur(80)))
    d = ImageDraw.Draw(bg)
    d.rectangle([0, 0, 250, 92], fill=(0, 0, 0, 255))
    d.text((125, 46), "黒画面", font=font(BOLD, 58), fill=(255, 255, 255), anchor="mm")
    size = 104
    while font(BOLD, size).getlength(MAIN) > 1060:
        size -= 2
    fm = font(BOLD, size)
    glow = Image.new("RGBA", bg.size, (0, 0, 0, 0))
    ImageDraw.Draw(glow).text((640, 292), MAIN, font=fm, fill=(0, 0, 0, 200), anchor="mm")
    bg = Image.alpha_composite(bg, glow.filter(ImageFilter.GaussianBlur(10)))
    light = Image.new("RGBA", bg.size, (0, 0, 0, 0))
    ImageDraw.Draw(light).text((640, 292), MAIN, font=fm, fill=(250, 246, 236, 90), anchor="mm")
    bg = Image.alpha_composite(bg, light.filter(ImageFilter.GaussianBlur(10)))
    d = ImageDraw.Draw(bg)
    d.text((640, 292), MAIN, font=fm, fill=(250, 246, 236), anchor="mm")
    d.text((640, 400), ELEMENTS, font=font(REGULAR, 46), fill=(236, 232, 224), anchor="mm")
    d.rounded_rectangle([520, 460, 760, 546], radius=43, fill=(238, 226, 196))
    d.text((640, 503), hours_label, font=font(BOLD, 50), fill=(30, 26, 40), anchor="mm")
    d.text((1280 - 36, 720 - 30), "Quiet Hours BGM", font=font(REGULAR, 24), fill=(170, 170, 170), anchor="rd")
    bg.convert("RGB").save(path)


def text_layer():
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    d.text((960, 510), MAIN, font=font(LIGHT, 64), fill=(246, 242, 232, 255), anchor="mm")
    d.text((960, 585), EN_LINE, font=font(LIGHT, 34), fill=(224, 220, 210, 255), anchor="mm")
    d.text((1860, 1030), "Quiet Hours BGM", font=font(LIGHT, 26), fill=(190, 190, 190, 255), anchor="rs")
    return np.asarray(lay, dtype=float)


def intro(base, path):
    """冒頭15秒（12fps）。10秒から5秒かけてフェードアウトし、以降は黒"""
    fps = 12
    drops = [0.4, 1.9, 2.6, 4.3, 5.8, 6.4, 8.1, 9.6, 10.3, 12.0, 13.4]
    tl = text_layer()
    alpha = tl[..., 3:4] / 255
    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(fps), "-i", "-",
                           "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", str(fps), "-g", "24", "-crf", "18", path], stdin=subprocess.PIPE)
    for i in range(15 * fps):
        t = i / fps
        f = frame(base, t, drops)
        f = f * (1 - alpha) + tl[..., :3] * alpha
        fade = 1.0 if t < 10 else max(0.0, 1 - (t - 10) / 5)
        ff.stdin.write((f * fade).astype(np.uint8).tobytes())
    ff.stdin.close()
    ff.wait()


if __name__ == "__main__":
    cmd, out = sys.argv[1], sys.argv[2]
    base = base_scene()
    if cmd == "bg":
        Image.fromarray(frame(base, 1.0, [0.4]).astype(np.uint8)).save(out)
    elif cmd == "thumb":
        thumbnail(frame(base, 1.0, [0.4]), out, sys.argv[3])
    elif cmd == "intro":
        intro(base, out)
    print("wrote", out)
