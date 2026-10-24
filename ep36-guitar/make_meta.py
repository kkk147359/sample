"""ep36/37（冬支度の夜、やさしいガットギター）のタイトル・説明文・タグを作り、ブランド規定と照合する。
使い方: python3 make_meta.py  → meta_1h.json / meta_8h.json
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tools"))
import meta  # noqa: E402

THEME = {
    "main": "冬支度の夜、やさしいガットギター",
    "elements": "ガットギターだけ・自然音なし",
    "use": "睡眠・作業用",
    "theme_tag": "ガットギター",
    "intro": [
        "冬支度をはじめる夜に、ナイロン弦のガットギターをゆっくり爪弾いた{h}です。",
        "強い音や急な盛り上がりはなく、同じ速さの静かな旋律がつづきます。",
        "最初の10秒だけ灯りを落とした部屋のギターを映したあと、画面は真っ暗になるので、まぶしくありません。",
    ],
    "sound": [
        "曲はすべてオリジナルです。低い弦の上にやわらかく和音を重ね、ときどき短い旋律が入ります。数分ごとに調と音域が少しずつ変わります。弦のこすれる音、雨や風などの自然音は入れていません。",
        "眠る前のひとときや、静かに作業したい夜のおともにどうぞ。",
    ],
    "emoji": "🎸 やさしいガットギター　🧣 冬支度の夜　🌙 自然音なし",
    "en": "{en} of gentle, slow nylon-string guitar on a quiet night as winter approaches, with no nature sounds, for sleep and work.",
    "tags": ["ガットギター", "クラシックギター", "ギター", "アコースティックギター", "ギターBGM", "睡眠用ギター", "ヒーリングギター",
             "冬支度", "初冬", "秋の夜", "睡眠", "作業用BGM", "nylon guitar", "classical guitar", "relaxing guitar"],
}

if __name__ == "__main__":
    meta.write_and_check(THEME, os.path.dirname(os.path.abspath(__file__)))
