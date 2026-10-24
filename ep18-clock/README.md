# ep18/19「古い柱時計と窓の外の小雨」

【黒画面でまぶしくない】古い柱時計と窓の外の小雨 1時間／8時間｜1秒ごとのコチコチ・チャイムなし｜10秒で真っ暗・睡眠用BGM

| ファイル | 役割 |
|---|---|
| `synth_clock.py` | 打音の合成（金属の部品と木の箱の響き、追い打ち、チク／タクの違い、1打ごとのばらつき） |
| `trial.py` | 試聴版（90秒）。`python3 trial.py out.mp3 A` |
| `render_long.py` | 長い版。時計（1秒間隔・柔らかい版・-6dB）＋小雨。`python3 render_long.py ep18_1h.m4a 3600 1801`／`python3 render_long.py ep19_8h.m4a 28800 1901`（別シード） |
| `rain.py` | 窓の外の小雨（実録音の帯域配分＋ゆらぎ＋雨だれ） |
| `trial_mix.py` | 時計＋雨の試聴版。社長OK版は `python3 trial_mix.py out.mp3 371070 -2 120 even100 -6 1` |
| `make_visual.py` | 背景（夜の和室の柱時計）・サムネイル・冒頭映像（振り子が揺れる） |
| `make_meta.py` | タイトル・説明文・タグと規定チェック（共通部分は `tools/meta.py`） |
| `REFERENCES.md` | 測った実録音と比較 |

動画は `python3 ../tools/assemble.py assets/intro_A.mp4 ep18_1h.m4a 3600 ep18_1h.mp4`。

冒頭映像は `python3 make_visual.py intro assets/intro_A.mp4 1.0`（振り子が1秒ごとに端に届く）。
