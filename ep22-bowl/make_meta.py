"""ep22/23（シンギングボウルの余韻）のタイトル・説明文・タグを作り、ブランド規定と照合する。
使い方: python3 make_meta.py  → meta_1h.json / meta_8h.json
企画の条件：周波数やヒーリングの効能はうたわない。
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tools"))
import meta  # noqa: E402

THEME = {
    "main": "シンギングボウルの余韻",
    "elements": "ひとつずつゆっくり・高音ひかえめ",
    "use": "睡眠用",
    "theme_tag": "シンギングボウル",
    "intro": [
        "フェルトのばちでそっと打ったシンギングボウルの余韻を{h}。",
        "ひとつ鳴らすごとに、響きがゆっくり揺れながら消えていきます。",
        "最初の10秒だけ夜の部屋のシンギングボウルを映したあと、画面は真っ暗になるので、まぶしくありません。",
    ],
    "sound": [
        "高い音をおさえ、打った瞬間もやわらかく鳴るようにしています。響きが途切れて静かになりすぎることもありません。",
        "眠りにつくまでの時間や、静かに過ごしたい夜のおともにどうぞ。",
    ],
    "emoji": "🥣 シンギングボウル　🌙 ひとつずつゆっくり",
    "en": "{en} of a softly struck singing bowl, one slow strike at a time, with gentle high tones, for sleep.",
    "tags": ["シンギングボウル", "シンギングボール", "ボウルの音", "余韻", "倍音", "環境音", "睡眠", "寝る前",
             "singing bowl", "singing bowl sleep", "tibetan bowl"],
}

if __name__ == "__main__":
    meta.write_and_check(THEME, os.path.dirname(os.path.abspath(__file__)))
