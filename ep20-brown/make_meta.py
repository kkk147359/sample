"""ep20/21（やわらかいブラウンノイズ）のタイトル・説明文・タグを作り、ブランド規定と照合する。
使い方: python3 make_meta.py [-4.5|-6]  → meta_1h.json / meta_8h.json
傾きが -4.5dB/oct（低音ひかえめ）のときは、企画の条件どおり説明文に「低音を抑えています」と書く。
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tools"))
import meta  # noqa: E402

slope = float(sys.argv[1]) if len(sys.argv) > 1 else -4.5
soft_low = slope > -6

THEME = {
    "main": "やわらかいブラウンノイズ",
    "elements": ("低音ひかえめ・" if soft_low else "") + "ずっと一定・物音をやさしく隠す",
    "use": "睡眠・作業用",
    "theme_tag": "ブラウンノイズ",
    "intro": [
        "低い音を中心にした、やわらかいブラウンノイズを{h}。",
        "エアコンや冷蔵庫の音、外の車の音など、気になる生活音をやさしく包んで目立たなくします。",
        "最初の10秒だけ夜のカーテンを映したあと、画面は真っ暗になるので、まぶしくありません。",
    ],
    "sound": [
        ("一般的なブラウンノイズよりも低音を抑えています。" if soft_low else "") + "音量のゆらぎはなく、最後までずっと一定です。",
        "眠るときや、静かに作業したいときのおともにどうぞ。",
    ],
    "emoji": "🟤 ブラウンノイズ　" + ("🔉 低音ひかえめ・ずっと一定" if soft_low else "🔉 ずっと一定"),
    "en": "{en} of soft brown noise" + (" with a gentle low end" if soft_low else "") + ", steady all the way through, to softly mask everyday sounds.",
    "tags": ["ブラウンノイズ", "brown noise", "ノイズ", "生活音", "物音", "環境音", "作業用BGM", "勉強用BGM", "睡眠", "寝る前",
             "sleep noise", "noise for sleeping"],
}

if __name__ == "__main__":
    meta.write_and_check(THEME, os.path.dirname(os.path.abspath(__file__)))
