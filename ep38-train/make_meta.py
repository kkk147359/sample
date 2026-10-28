"""ep38/39（冬へ向かう夜、静かに走る夜行列車の音）のタイトル・説明文・タグを作り、ブランド規定と照合する。
使い方: python3 make_meta.py  → meta_1h.json / meta_8h.json
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tools"))
import meta  # noqa: E402

THEME = {
    "main": "冬へ向かう夜、静かに走る夜行列車の音",
    "elements": "列車の走行音だけ・音楽なし",
    "use": "睡眠・作業用",
    "theme_tag": "夜行列車",
    "intro": [
        "冬へ向かう夜、町の灯りを遠くに見ながら、ゆっくり走る夜行列車の車内の音を{h}収めました。",
        "「ゴー」というやわらかい走行音に、レールの継ぎ目の「タタン」が2秒あまりごとに静かに重なります。",
        "最初の10秒だけ夜の車窓を映したあと、画面は真っ暗になるので、まぶしくありません。",
    ],
    "sound": [
        "ゆっくりした速さで一定に走りつづけ、駅の停車・車内放送・警笛・ブレーキの音は入れていません。低音の圧迫感や風のような音は出ないように整えています。",
        "眠る前のひとときや、静かに作業したい夜のおともにどうぞ。",
    ],
    "emoji": "🚃 夜行列車の走行音　🌃 夜の車窓　🌙 放送・警笛なし",
    "en": "{en} of the quiet rumble and soft rail clacks inside a slow night train heading toward winter, with no announcements or horns, for sleep and work.",
    "tags": ["夜行列車", "電車の音", "列車の音", "走行音", "電車 走行音", "環境音", "寝台列車", "電車 睡眠",
             "冬の夜", "初冬", "睡眠", "作業用BGM", "train sounds", "night train", "train ambience"],
}

if __name__ == "__main__":
    meta.write_and_check(THEME, os.path.dirname(os.path.abspath(__file__)))
