"""ep18/19（古い柱時計と窓の外の小雨）のタイトル・説明文・タグを作り、ブランド規定と照合する。
使い方: python3 make_meta.py  → meta_1h.json / meta_8h.json
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tools"))
import meta  # noqa: E402

THEME = {
    "main": "古い柱時計と窓の外の小雨",
    "elements": "1秒ごとのコチコチ・チャイムなし",
    "use": "睡眠用",
    "theme_tag": "柱時計",
    "intro": [
        "古い柱時計の振り子が1秒ごとにコチ、コチと時をきざむ音に、窓の外の静かな小雨を重ねて{h}。",
        "振り子の速さは最後まで一定です。時報のチャイムは鳴りません。",
        "最初の10秒だけ夜の和室の柱時計を映したあと、画面は真っ暗になるので、まぶしくありません。",
    ],
    "sound": [
        "時計の音は小さくやわらかくして高い音をおさえ、一打ずつ強さや響きを少しずつ変えて、機械的なくり返しに聞こえないようにしています。",
        "雨は強くならず、ときどき窓に落ちるしずくの音が混じる程度です。静かな部屋で眠りたい夜にどうぞ。",
    ],
    "emoji": "🕰 柱時計の振り子　🌧 窓の外の小雨　🔕 チャイムなし",
    "en": "{en} of an old pendulum wall clock ticking softly once a second, with gentle rain outside the window and no chime, for sleep.",
    "tags": ["柱時計", "振り子時計", "時計の音", "振り子の音", "コチコチ", "チクタク", "小雨", "雨の音", "環境音", "睡眠", "寝る前",
             "clock ticking", "pendulum clock", "ticking clock sound", "clock and rain"],
}

if __name__ == "__main__":
    meta.write_and_check(THEME, os.path.dirname(os.path.abspath(__file__)))
