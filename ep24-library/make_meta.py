"""ep24/25（夜の図書館でページをめくる音）のタイトル・説明文・タグを作り、ブランド規定と照合する。
使い方: python3 make_meta.py  → meta_1h.json / meta_8h.json
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tools"))
import meta  # noqa: E402

THEME = {
    "main": "夜の図書館でページをめくる音",
    "elements": "ページの音だけ・音楽なし",
    "use": "睡眠・作業用",
    "theme_tag": "図書館",
    "intro": [
        "閉館前の静かな図書館で、厚めの本を1枚ずつゆっくりめくる音を{h}。",
        "ページをめくるのは15〜40秒に1回だけ。合間には、紙にふれる指の小さな音が聞こえます。",
        "最初の10秒だけ読書灯の机と開いた本を映したあと、画面は真っ暗になるので、まぶしくありません。",
    ],
    "sound": [
        "空調の音や人の声、急に大きくなる音は入れていません。音楽も入っていません。",
        "読書の秋の夜、眠る前や、静かに考えごとをしたいときのおともにどうぞ。",
    ],
    "emoji": "📖 ページをめくる音　🕯 読書灯の机　🎵 音楽なし",
    "en": "{en} of slow page turning in a quiet library at night, one page at a time, with no music, for sleep and focus.",
    "tags": ["図書館", "ページをめくる音", "本をめくる音", "紙の音", "読書", "読書の秋", "図書館の環境音", "環境音", "作業用BGM",
             "勉強用", "寝る前", "page turning", "library ambience", "book sounds"],
}

if __name__ == "__main__":
    meta.write_and_check(THEME, os.path.dirname(os.path.abspath(__file__)))
