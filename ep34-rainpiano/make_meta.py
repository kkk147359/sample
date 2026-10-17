"""ep34/35（晩秋の夜、落ち葉に降る静かな雨とピアノ）のタイトル・説明文・タグを作り、ブランド規定と照合する。
使い方: python3 make_meta.py  → meta_1h.json / meta_8h.json
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tools"))
import meta  # noqa: E402

THEME = {
    "main": "晩秋の夜、落ち葉に降る静かな雨とピアノ",
    "elements": "雨音・ピアノ",
    "use": "睡眠用",
    "theme_tag": "雨音",
    "intro": [
        "晩秋の夜、落ち葉の積もった庭にしずかに降る雨と、やわらかいピアノを{h}。",
        "雨はほぼ一定の音で、ときどき少しだけ強くなったり弱くなったりします。",
        "最初の10秒だけ雨の庭と石灯籠を映したあと、画面は真っ暗になるので、まぶしくありません。",
    ],
    "sound": [
        "ピアノはゆっくり、音と音のあいだを広くとったオリジナルの演奏です。雷、風の音、しずくの大きな音は入れていません。高い音や低い音が耳に残らないように整えました。",
        "雨の音に包まれながら、眠る前のひとときにどうぞ。",
    ],
    "emoji": "🌧 落ち葉に降る静かな雨　🎹 やわらかいピアノ　🍁 晩秋の夜",
    "en": "{en} of quiet rain falling on fallen leaves on a late-autumn night, with slow, soft original piano, for sleep.",
    "tags": ["雨音", "雨の音", "雨音とピアノ", "ピアノ", "睡眠用ピアノ", "落ち葉", "晩秋", "秋の夜", "秋の雨", "ヒーリングピアノ",
             "自然音", "睡眠", "rain sounds", "rain and piano", "relaxing piano"],
}

if __name__ == "__main__":
    meta.write_and_check(THEME, os.path.dirname(os.path.abspath(__file__)))
