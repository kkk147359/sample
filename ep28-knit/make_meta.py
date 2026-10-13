"""ep28/29（竹の棒針で編み物をする音）のタイトル・説明文・タグを作り、ブランド規定と照合する。
使い方: python3 make_meta.py  → meta_1h.json / meta_8h.json
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tools"))
import meta  # noqa: E402

THEME = {
    "main": "竹の棒針で編み物をする音",
    "elements": "毛糸と棒針の音だけ・音楽なし",
    "use": "睡眠・作業用",
    "theme_tag": "編み物",
    "intro": [
        "秋の夜、小さな明かりの下で、竹の棒針でゆっくり編み物をする音を{h}。",
        "毛糸が針の上をすべるやわらかい音と、竹の針どうしが当たる小さな「コツ」という音。ときどき針を持ち替える静かな間が入ります。",
        "最初の10秒だけ編みかけのマフラーと毛糸玉を映したあと、画面は真っ暗になるので、まぶしくありません。",
    ],
    "sound": [
        "本物の編み物の録音を測って、その音の高さや間に合わせて作った、このチャンネルのオリジナルの音です。金属の針の高い音、人の声、急に大きくなる音は入れていません。音楽も入っていません。",
        "眠る前や、静かに作業や考えごとをしたいときのおともにどうぞ。",
    ],
    "emoji": "🧶 毛糸と竹の棒針の音　🕯 夜の小さな明かり　🎵 音楽なし",
    "en": "{en} of slow knitting with bamboo needles on an autumn night: soft yarn and quiet needle taps, with no music, for sleep and focus.",
    "tags": ["編み物", "編み物の音", "棒針", "竹の棒針", "毛糸", "手芸", "秋の夜", "環境音", "作業用BGM", "寝る前",
             "knitting", "knitting sounds", "knitting asmr"],
}

if __name__ == "__main__":
    meta.write_and_check(THEME, os.path.dirname(os.path.abspath(__file__)))
