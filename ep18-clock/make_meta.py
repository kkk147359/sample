"""ep18/19（古い柱時計の振り子の音）のタイトル・説明文・タグを作り、ブランド規定と照合する。
使い方: python3 make_meta.py  → meta_1h.json / meta_8h.json
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tools"))
import meta  # noqa: E402

THEME = {
    "main": "古い柱時計の振り子の音",
    "elements": "コチコチだけ・チャイムなし",
    "use": "睡眠用",
    "theme_tag": "柱時計",
    "intro": [
        "古い柱時計の振り子が、コチ、コチと時をきざむ音を{h}。",
        "木の箱にやわらかく響く振り子の音だけを収めました。時報のチャイムは鳴りません。",
        "最初の10秒だけ夜の和室の柱時計を映したあと、画面は真っ暗になるので、まぶしくありません。",
    ],
    "sound": [
        "高い音をおさえ、一打ずつ強さや響きを少しずつ変えて、機械的なくり返しに聞こえないようにしています。",
        "静かな部屋で、時計の音だけを聞きながら眠りたい夜にどうぞ。",
    ],
    "emoji": "🕰 柱時計の振り子　🔕 チャイムなし",
    "en": "{en} of an old pendulum wall clock ticking softly in a quiet room, with no chime, for sleep.",
    "tags": ["柱時計", "振り子時計", "時計の音", "振り子の音", "コチコチ", "チクタク", "環境音", "睡眠", "寝る前",
             "clock ticking", "pendulum clock", "ticking clock sound"],
}

if __name__ == "__main__":
    meta.write_and_check(THEME, os.path.dirname(os.path.abspath(__file__)))
