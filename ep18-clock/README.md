# ep18/19「古い柱時計の振り子の音」

【黒画面でまぶしくない】古い柱時計の振り子の音 1時間／8時間｜コチコチだけ・チャイムなし｜10秒で真っ暗・睡眠用BGM

| ファイル | 役割 |
|---|---|
| `synth_clock.py` | 打音の合成（金属の部品と木の箱の響き、追い打ち、チク／タクの違い、1打ごとのばらつき） |
| `trial.py` | 試聴版（90秒）。`python3 trial.py out.mp3 A` |
| `render_long.py` | 長い版。`python3 render_long.py ep18_1h.m4a 3600 1801 A`（1時間版と8時間版は別シード） |
| `make_visual.py` | 背景（夜の和室の柱時計）・サムネイル・冒頭映像（振り子が揺れる） |
| `make_meta.py` | タイトル・説明文・タグと規定チェック（共通部分は `tools/meta.py`） |
| `REFERENCES.md` | 測った実録音と比較 |

動画は `python3 ../tools/assemble.py assets/intro_A.mp4 ep18_1h.m4a 3600 ep18_1h.mp4`。
