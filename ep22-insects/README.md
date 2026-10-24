# ep22/23「秋の夜の虫の声」（10/6公開予定）

【黒画面でまぶしくない】秋の夜の虫の声 1時間／8時間｜2種類だけ・ゆっくりした鳴き声｜10秒で真っ暗・睡眠用BGM

| ファイル | 役割 |
|---|---|
| `synth_insects.py` | 虫の声の合成（v2：2種類・各3匹、3.2〜4.0kHz、脈 10〜14回/秒） |
| `trial.py` | 試聴版（2分）。`python3 trial.py out.mp3` |
| `render_long.py` | 長い版。`python3 render_long.py ep22_1h.m4a 3600 2201`／`python3 render_long.py ep23_8h.m4a 28800 2301`（別シード） |
| `make_visual.py` | 背景（月夜のすすき野原）・サムネイル・冒頭映像（すすきが揺れ、露がまたたく） |
| `make_meta.py` | タイトル・説明文・タグと規定チェック |
| `REFERENCES.md` | 測った実録音 |

動画は `python3 ../tools/assemble.py assets/intro.mp4 ep22_1h.m4a 3600 ep22_1h.mp4`。
