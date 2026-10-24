"""ep20/21 の背景（夜の部屋、閉じたカーテン越しにぼんやり透ける街灯の光）・サムネイル・冒頭映像を作る。
「外の物音をやさしく隠す」イメージ。冒頭映像ではカーテンがごくゆっくり揺れる。
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
MAIN = "やわらかいブラウンノイズ"
ELEMENTS = "低音ひかえめ・ずっと一定・物音をやさしく隠す"
EN_LINE = "Soft Brown Noise  ·  gentle low end, steady all night"

Y, X = np.mgrid[0:H, 0:W].astype(float)
TEX = 0.6 * brand.noise2d(H, W, 2, 21) + 0.4 * brand.noise2d(H, W, 30, 22)
FOLD_N = brand.noise2d(H, W, 300, 23)
GRAIN = np.random.default_rng(2020)
# カーテンが掛かる窓の範囲
L, R, T, B = 380, 1540, 70, 960


def scene(t):
    # 部屋の壁：ほぼ黒に近い藍
    img = np.stack([10 + 4 * TEX, 11 + 4 * TEX, 16 + 5 * TEX], axis=-1)
    # カーテン越しの街灯：右上寄りの温かい光が、カーテン全体ににじむ
    glow = np.exp(-(((X - 1130) / 620) ** 2 + ((Y - 330) / 520) ** 2))
    inside = (X > L) & (X < R) & (Y > T) & (Y < B)
    # ひだ：場所によって幅が違う縦のひだ。t でごくゆっくり揺れる
    sway = 6 * np.sin(2 * np.pi * t / 9.0) * ((Y - T) / (B - T)) ** 2
    phase = (X + sway) / 118 + 0.9 * FOLD_N + 0.05 * np.sin(Y / 300)
    fold = 0.5 + 0.5 * np.sin(2 * np.pi * phase) + 0.18 * np.sin(2 * np.pi * phase * 2.3 + 1.0)
    fold = np.clip(fold, 0, 1.2)
    cloth = (0.55 + 0.45 * fold) * (0.12 + 1.0 * glow) * (0.94 + 0.12 * TEX)
    # 左右2枚のカーテンの合わせ目から、細く光がもれる
    gap = np.exp(-((X + sway * 0.5 - 1010) / 8) ** 2) * (0.5 + 0.5 * glow)
    cloth = cloth + 0.55 * gap
    cur = np.stack([150 * cloth, 104 * cloth, 66 * cloth], axis=-1)
    # 裾は少し暗く、床に近いところで光が弱まる
    hem = np.clip((B - Y) / 220, 0.35, 1)
    cur *= hem[..., None]
    img = np.where(inside[..., None], cur, img)
    # カーテンの左右の外側にもれる光（壁にうっすら）
    spill = np.exp(-(np.minimum(np.abs(X - L), np.abs(X - R)) / 90) ** 2) * glow * (~inside) * ((Y > T) & (Y < B))
    img += spill[..., None] * np.array([40, 28, 18])
    # カーテンレール
    img[(Y > T - 16) & (Y < T) & (X > L - 40) & (X < R + 40)] = np.array([30, 26, 24])
    # 床とベッドの端のシルエット
    img[Y > 1000] *= 0.4
    v = np.clip(1 - 0.55 * (((X - W / 2) / (W * 0.62)) ** 2 + ((Y - H / 2) / (H * 0.62)) ** 2), 0.25, 1)
    img = img * v[..., None] + GRAIN.normal(0, 1.0, img.shape)
    return np.clip(img, 0, 255)


if __name__ == "__main__":
    cmd, out = sys.argv[1], sys.argv[2]
    if cmd == "bg":
        Image.fromarray(scene(0.0).astype(np.uint8)).save(out)
    elif cmd == "thumb":
        brand.thumbnail(scene(0.0), out, MAIN, ELEMENTS, sys.argv[3])
    elif cmd == "intro":
        brand.intro(scene, out, MAIN, EN_LINE)
    print("wrote", out)
