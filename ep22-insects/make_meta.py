"""ep22/23（秋の夜の虫の声）のタイトル・説明文・タグを作り、ブランド規定と照合する。
使い方: python3 make_meta.py  → meta_1h.json / meta_8h.json
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tools"))
import meta  # noqa: E402

THEME = {
    "main": "秋の夜の虫の声",
    "elements": "2種類だけ・ゆっくりした鳴き声",
    "use": "睡眠用",
    "theme_tag": "虫の声",
    "intro": [
        "秋の夜、少し離れた草むらから聞こえる虫の声を{h}。",
        "「リッ……リッ……」と短くゆっくり鳴く虫と、「リーー……」とやわらかく伸ばす虫の、2種類だけにしぼりました。",
        "最初の10秒だけ月夜のすすき野原を映したあと、画面は真っ暗になるので、まぶしくありません。",
    ],
    "sound": [
        "高すぎる声や低すぎる声、速く震える声は入れず、すぐ近くで鳴いて目立つ虫もいません。音楽は入っていません。",
        "窓を少し開けた秋の夜のように、静かに過ごしたい夜のおともにどうぞ。",
    ],
    "emoji": "🦗 秋の虫の声　🌕 月夜の草むら　🎵 音楽なし",
    "en": "{en} of gentle autumn night insects, just two slow and soft voices from a nearby field, with no music, for sleep.",
    "tags": ["虫の声", "秋の虫", "虫の音", "虫の鳴き声", "秋の夜長", "秋の夜", "自然音", "環境音", "睡眠", "寝る前",
             "insect sounds", "crickets at night", "autumn night ambience"],
}

if __name__ == "__main__":
    meta.write_and_check(THEME, os.path.dirname(os.path.abspath(__file__)))
