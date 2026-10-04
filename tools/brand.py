"""ブランド規定（スキル quiet-hours-bgm-brand）どおりのサムネイル・冒頭映像の共通部分。
テーマごとの違いは「背景」と「言葉」だけにするため、色・フォント・サイズ・位置はここで固定する。
各テーマのスクリプトは背景（numpy の H×W×3 配列、0〜255）を描いて、ここの関数に渡す。
"""
import subprocess

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H = 1920, 1080
FONT_DIR = "/usr/share/fonts/opentype/noto/"
BOLD = (FONT_DIR + "NotoSansCJK-Bold.ttc", 0)
REGULAR = (FONT_DIR + "NotoSansCJK-Regular.ttc", 0)
LIGHT = ("/root/.fonts/NotoSansJP_300Light.ttf", 0)


def font(spec, size):
    return ImageFont.truetype(spec[0], size, index=spec[1])


def thumbnail(base, path, main, elements, hours_label):
    """サムネイル（1280×720）。base は 1920×1080 の背景"""
    bg = Image.fromarray(np.clip(base, 0, 255).astype(np.uint8)).resize((1280, 720), Image.LANCZOS)
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
    while font(BOLD, size).getlength(main) > 1060:
        size -= 2
    fm = font(BOLD, size)
    glow = Image.new("RGBA", bg.size, (0, 0, 0, 0))
    ImageDraw.Draw(glow).text((640, 292), main, font=fm, fill=(0, 0, 0, 200), anchor="mm")
    bg = Image.alpha_composite(bg, glow.filter(ImageFilter.GaussianBlur(10)))
    light = Image.new("RGBA", bg.size, (0, 0, 0, 0))
    ImageDraw.Draw(light).text((640, 292), main, font=fm, fill=(250, 246, 236, 90), anchor="mm")
    bg = Image.alpha_composite(bg, light.filter(ImageFilter.GaussianBlur(10)))
    d = ImageDraw.Draw(bg)
    d.text((640, 292), main, font=fm, fill=(250, 246, 236), anchor="mm")
    d.text((640, 400), elements, font=font(REGULAR, 46), fill=(236, 232, 224), anchor="mm")
    d.rounded_rectangle([520, 460, 760, 546], radius=43, fill=(238, 226, 196))
    d.text((640, 503), hours_label, font=font(BOLD, 50), fill=(30, 26, 40), anchor="mm")
    d.text((1280 - 36, 720 - 30), "Quiet Hours BGM", font=font(REGULAR, 24), fill=(170, 170, 170), anchor="rd")
    bg.convert("RGB").save(path)


def thumb_diff(p1, p8):
    """1時間版と8時間版のサムネイルの差が、時間表記の枠（520,460〜760,546）の中だけか"""
    a = np.asarray(Image.open(p1), dtype=int)
    b = np.asarray(Image.open(p8), dtype=int)
    ys, xs = np.nonzero(np.abs(a - b).sum(axis=2))
    if len(xs) == 0:
        return "差なし（時間表記が同じ？）"
    box = (xs.min(), ys.min(), xs.max(), ys.max())
    ok = xs.min() >= 520 and xs.max() <= 760 and ys.min() >= 460 and ys.max() <= 546
    return f"差の範囲 {box} → {'○ 時間表記の枠の中だけ' if ok else '× 枠の外にも差がある'}"


def text_layer(main, en_line):
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    d.text((960, 510), main, font=font(LIGHT, 64), fill=(246, 242, 232, 255), anchor="mm")
    d.text((960, 585), en_line, font=font(LIGHT, 34), fill=(224, 220, 210, 255), anchor="mm")
    d.text((1860, 1030), "Quiet Hours BGM", font=font(LIGHT, 26), fill=(190, 190, 190, 255), anchor="rs")
    return np.asarray(lay, dtype=float)


def intro(frame_fn, path, main, en_line, fps=12):
    """冒頭15秒（12fps）。frame_fn(t) が t 秒の背景を返す。10秒から5秒かけてフェードアウトし、以降は黒"""
    tl = text_layer(main, en_line)
    alpha = tl[..., 3:4] / 255
    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(fps), "-i", "-",
                           "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", str(fps), "-g", "24", "-crf", "18", path], stdin=subprocess.PIPE)
    for i in range(15 * fps):
        t = i / fps
        f = frame_fn(t)
        f = f * (1 - alpha) + tl[..., :3] * alpha
        fade = 1.0 if t < 10 else max(0.0, 1 - (t - 10) / 5)
        ff.stdin.write(np.clip(f * fade, 0, 255).astype(np.uint8).tobytes())
    ff.stdin.close()
    ff.wait()


def noise2d(h, w, scale, seed):
    r = np.random.default_rng(seed)
    small = r.random((h // scale + 2, w // scale + 2))
    img = Image.fromarray((small * 255).astype(np.uint8)).resize((w + scale * 2, h + scale * 2), Image.BICUBIC)
    return np.asarray(img, dtype=float)[:h, :w] / 255
