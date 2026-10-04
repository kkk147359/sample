"""ep18/19 の背景（夜の和室の柱に掛かった古い柱時計）・サムネイル・冒頭映像を作る。
冒頭映像では、ガラス窓の中の振り子が音と同じ速さで揺れる。
使い方:
  python3 make_visual.py bg <出力.png>
  python3 make_visual.py thumb <出力.png> <1時間|8時間>
  python3 make_visual.py intro <出力.mp4> [打音の間隔(秒)=0.6]
"""
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tools"))
import brand  # noqa: E402

W, H = brand.W, brand.H
MAIN = "古い柱時計の振り子の音"
ELEMENTS = "コチコチだけ・チャイムなし"
EN_LINE = "Old Pendulum Wall Clock  ·  ticking only, no chime"

CX = 1480  # 柱と時計の中心
DIAL_C = (CX, 330)
DIAL_R = 132
WIN = (CX - 118, 520, CX + 118, 900)  # 振り子のガラス窓
PIVOT = (CX, 470)
ROD = 330
rng = np.random.default_rng(1804)


def base_scene():
    y, x = np.mgrid[0:H, 0:W].astype(float)
    # 漆喰の壁：暗い藍がかった灰色、左下の行灯の光で温かく
    tex = 0.6 * brand.noise2d(H, W, 3, 1) + 0.4 * brand.noise2d(H, W, 40, 2)
    img = np.stack([22 + 8 * tex, 22 + 8 * tex, 28 + 8 * tex], axis=-1)
    lamp = np.exp(-(np.hypot(x - 260, y - 900) / 900) ** 2)
    img += lamp[..., None] * np.array([70, 48, 24])
    # 長押（なげし）：上の横木
    nag = (y > 70) & (y < 112)
    wood_t = 0.5 * brand.noise2d(H, W, 2, 3) + 0.5 * np.sin(x / 7 + 3 * brand.noise2d(H, W, 50, 4)) * 0.5 + 0.5
    nag_col = np.stack([40 + 16 * wood_t, 27 + 10 * wood_t, 17 + 6 * wood_t], axis=-1) * (0.7 + 0.6 * lamp[..., None])
    img = np.where(nag[..., None], nag_col, img)
    img[(y >= 112) & (y < 118)] *= 0.55
    # 柱：時計が掛かる縦の木
    pil = np.abs(x - CX) < 92
    grain = 0.5 + 0.5 * np.sin(x / 3.5 + 6 * brand.noise2d(H, W, 60, 5) + y / 400)
    pil_col = np.stack([46 + 18 * grain, 31 + 11 * grain, 20 + 6 * grain], axis=-1)
    pil_col *= (0.75 + 0.45 * np.clip((CX - x) / 92, -1, 1) * 0.5)[..., None]  # 左側が少し明るい
    img = np.where(pil[..., None], pil_col, img)
    # 畳の縁と床
    floor = y > 1010
    img = np.where(floor[..., None], np.stack([30 + 10 * tex, 32 + 10 * tex, 18 + 6 * tex], axis=-1) * (0.8 + 0.8 * lamp[..., None]), img)
    img[(y > 1004) & (y <= 1012)] = np.array([18, 14, 12])

    im = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8))
    d = ImageDraw.Draw(im)
    # 時計の箱（濃い木）。上の飾り屋根、文字盤の箱、振り子の箱
    case_dark, case_mid, case_hi = (34, 20, 12), (58, 35, 20), (92, 60, 34)
    d.polygon([(CX - 170, 178), (CX, 128), (CX + 170, 178)], fill=case_mid, outline=case_hi)
    d.rectangle([CX - 175, 176, CX + 175, 190], fill=case_hi)
    d.rectangle([CX - 165, 190, CX + 165, 478], fill=case_mid)
    d.rectangle([CX - 150, 478, CX + 150, 938], fill=case_mid)
    d.rectangle([CX - 160, 470, CX + 160, 486], fill=case_hi)
    d.rectangle([CX - 160, 930, CX + 160, 946], fill=case_hi)
    d.polygon([(CX - 150, 946), (CX + 150, 946), (CX + 110, 985), (CX - 110, 985)], fill=case_dark)
    # 文字盤（古い象牙色、月明かりではなく行灯の光で少し黄ばむ）
    d.ellipse([DIAL_C[0] - DIAL_R - 14, DIAL_C[1] - DIAL_R - 14, DIAL_C[0] + DIAL_R + 14, DIAL_C[1] + DIAL_R + 14], fill=(120, 92, 50))
    d.ellipse([DIAL_C[0] - DIAL_R, DIAL_C[1] - DIAL_R, DIAL_C[0] + DIAL_R, DIAL_C[1] + DIAL_R], fill=(150, 138, 112))
    for k in range(60):
        a = np.pi / 2 - k * np.pi / 30
        r0 = DIAL_R - (16 if k % 5 == 0 else 8)
        w = 4 if k % 5 == 0 else 1
        d.line([(DIAL_C[0] + r0 * np.cos(a), DIAL_C[1] - r0 * np.sin(a)), (DIAL_C[0] + (DIAL_R - 4) * np.cos(a), DIAL_C[1] - (DIAL_R - 4) * np.sin(a))], fill=(40, 32, 26), width=w)
    roman = ["XII", "I", "II", "III", "IIII", "V", "VI", "VII", "VIII", "IX", "X", "XI"]
    fnt = brand.font(brand.REGULAR, 20)
    for k, s in enumerate(roman):
        a = np.pi / 2 - k * np.pi / 6
        r = DIAL_R - 36
        d.text((DIAL_C[0] + r * np.cos(a), DIAL_C[1] - r * np.sin(a)), s, font=fnt, fill=(44, 36, 30), anchor="mm")
    # 針：夜の11時10分ごろ
    for ang, ln, wd in ((np.pi / 2 - (11 + 10 / 60) * np.pi / 6, 70, 7), (np.pi / 2 - 10 * np.pi / 30, 104, 4)):
        d.line([DIAL_C, (DIAL_C[0] + ln * np.cos(ang), DIAL_C[1] - ln * np.sin(ang))], fill=(26, 22, 20), width=wd)
    d.ellipse([DIAL_C[0] - 7, DIAL_C[1] - 7, DIAL_C[0] + 7, DIAL_C[1] + 7], fill=(30, 26, 22))
    # ねじ穴2つ
    for dx in (-50, 50):
        d.ellipse([DIAL_C[0] + dx - 7, DIAL_C[1] + 52, DIAL_C[0] + dx + 7, DIAL_C[1] + 66], fill=(90, 80, 64), outline=(40, 34, 28))
    # 振り子の窓の中（奥は暗い）
    d.rectangle(WIN, fill=(16, 11, 8))
    im = im.filter(ImageFilter.GaussianBlur(0.8))
    img = np.asarray(im, dtype=float)
    # 文字盤のガラスの映り込み（左上の弧）
    dd = np.hypot(x - DIAL_C[0] + 40, y - DIAL_C[1] + 40)
    img += (np.exp(-((dd - 90) / 10) ** 2) * ((x < DIAL_C[0]) & (y < DIAL_C[1])) * 0.35)[..., None] * np.array([80, 80, 80])
    # 全体を暗く（夜）＋ビネット
    v = np.clip(1 - 0.5 * (((x - W / 2) / (W * 0.62)) ** 2 + ((y - H / 2) / (H * 0.62)) ** 2), 0.3, 1)
    img = img * 0.82 * v[..., None] + rng.normal(0, 1.0, img.shape)
    return np.clip(img, 0, 255)


def frame(base, t, beat):
    """t秒の1コマ。振り子は beat 秒ごとに端に達する（端で打音）"""
    img = Image.fromarray(base.astype(np.uint8))
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    th = np.radians(6.0) * np.sin(np.pi * t / beat)
    ex = PIVOT[0] + ROD * np.sin(th)
    ey = PIVOT[1] + ROD * np.cos(th)
    d.line([PIVOT, (ex, ey)], fill=(120, 96, 52, 255), width=6)
    d.line([PIVOT, (ex, ey)], fill=(170, 140, 80, 255), width=2)
    br = 44
    d.ellipse([ex - br, ey - br, ex + br, ey + br], fill=(140, 108, 50, 255))
    d.ellipse([ex - br + 8, ey - br + 8, ex + br - 8, ey + br - 8], fill=(176, 140, 70, 255))
    d.ellipse([ex - 26, ey - 30, ex - 6, ey - 12], fill=(220, 190, 120, 180))  # 行灯の光の反射
    mask = Image.new("L", (W, H), 0)
    ImageDraw.Draw(mask).rectangle(WIN, fill=255)
    lay.putalpha(Image.fromarray(np.minimum(np.asarray(lay.getchannel("A")), np.asarray(mask))))
    img = Image.alpha_composite(img.convert("RGBA"), lay.filter(ImageFilter.GaussianBlur(0.7))).convert("RGB")
    out = np.asarray(img, dtype=float)
    # 窓のガラスの映り込み
    y, x = np.mgrid[WIN[1] : WIN[3], WIN[0] : WIN[2]].astype(float)
    refl = np.exp(-(((x - WIN[0]) - (y - WIN[1]) * 0.35 - 40) / 18) ** 2) * 0.12
    out[WIN[1] : WIN[3], WIN[0] : WIN[2]] += refl[..., None] * 255
    return np.clip(out, 0, 255)


if __name__ == "__main__":
    cmd, out = sys.argv[1], sys.argv[2]
    base = base_scene()
    if cmd == "bg":
        Image.fromarray(frame(base, 0.0, 0.6).astype(np.uint8)).save(out)
    elif cmd == "thumb":
        brand.thumbnail(frame(base, 0.0, 0.6), out, MAIN, ELEMENTS, sys.argv[3])
    elif cmd == "intro":
        beat = float(sys.argv[3]) if len(sys.argv) > 3 else 0.6
        brand.intro(lambda t: frame(base, t, beat), out, MAIN, EN_LINE)
    print("wrote", out)
