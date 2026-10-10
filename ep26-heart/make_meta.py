"""ep26/27（ゆっくりした静かな心音）のタイトル・説明文・タグを作り、ブランド規定と照合する。
使い方: python3 make_meta.py  → meta_1h.json / meta_8h.json
効能（落ち着く・泣き止む等）はうたわない（品質チェック部の条件）。
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tools"))
import meta  # noqa: E402

THEME = {
    "main": "ゆっくりした静かな心音",
    "elements": "心音だけ・音楽なし",
    "use": "睡眠用",
    "theme_tag": "心音",
    "intro": [
        "1分に約60回の、ゆっくりした「ドッ・クン」という心音を{h}。",
        "本物の心音の録音を測って、その音の高さや響きに合わせて作った、このチャンネルのオリジナルの音です。",
        "最初の10秒だけ夜の寝室を映したあと、画面は真っ暗になるので、まぶしくありません。",
    ],
    "sound": [
        "血流の「ザー」という音や、急に大きくなる音は入れていません。音楽も入っていません。",
        "低めのやわらかい音なので、イヤホンや枕元のスピーカーで、小さめの音量でどうぞ。",
    ],
    "emoji": "🤍 心音だけ　🌙 夜の寝室　🎵 音楽なし",
    "en": "{en} of a slow, quiet heartbeat at about 60 beats per minute, with no music, for sleep.",
    "tags": ["心音", "心臓の音", "鼓動", "心拍", "ハートビート", "心音 睡眠", "寝る前", "環境音", "heartbeat",
             "heartbeat sound", "slow heartbeat"],
}

if __name__ == "__main__":
    meta.write_and_check(THEME, os.path.dirname(os.path.abspath(__file__)))
