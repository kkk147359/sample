"""ep32/33（小鳥来る、晩秋の朝の庭）のタイトル・説明文・タグを作り、ブランド規定と照合する。
使い方: python3 make_meta.py  → meta_1h.json / meta_8h.json
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tools"))
import meta  # noqa: E402

THEME = {
    "main": "小鳥来る、晩秋の朝の庭",
    "elements": "小鳥の声だけ・音楽なし",
    "use": "睡眠・作業用",
    "theme_tag": "小鳥の声",
    "intro": [
        "晩秋の朝、まだ薄暗い庭の遠くから聞こえる小鳥の声を{h}。",
        "秋に渡ってきた小鳥たちが、ときどき短く「チッ」「ツィー」と鳴き交わします。",
        "最初の10秒だけ朝もやの庭と紅葉の枝を映したあと、画面は真っ暗になるので、まぶしくありません。",
    ],
    "sound": [
        "声は遠く、まばらで、高い音が耳に残り続けないように整えました。近くでにぎやかにさえずる声、風の音、低いゴーという音、音楽は入っていません。",
        "静かな朝の空気のなかで、眠る前や、ゆっくり作業したい時間のおともにどうぞ。",
    ],
    "emoji": "🐦 遠くの小鳥の声　🍁 晩秋の朝の庭　🎵 音楽なし",
    "en": "{en} of distant small birds calling now and then in a quiet late-autumn morning garden, with no music, for sleep and work.",
    "tags": ["小鳥の声", "小鳥のさえずり", "鳥の声", "鳥のさえずり", "朝の庭", "晩秋", "秋の朝", "小鳥来る", "自然音", "環境音",
             "睡眠", "作業用BGM", "bird sounds", "birdsong", "morning garden ambience"],
}

if __name__ == "__main__":
    meta.write_and_check(THEME, os.path.dirname(os.path.abspath(__file__)))
