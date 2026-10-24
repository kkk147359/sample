# ep32/33「小鳥来る、晩秋の朝の庭」

【黒画面でまぶしくない】小鳥来る、晩秋の朝の庭 1時間／8時間｜小鳥の声だけ・音楽なし｜10秒で真っ暗・睡眠・作業用BGM

| ファイル | 役割 |
|---|---|
| `synth_birds.py` | 遠くの小鳥（5羽）と朝の庭の空気の合成。社長OKの試聴版A（10/14） |
| `trial.py` | 試聴版。`python3 trial.py out.mp3 150 1` |
| `render_long.py` | 長い版。`python3 render_long.py out/ep32_1h.m4a 3600 3201`／`python3 render_long.py out/ep33_8h.m4a 28800 3301` |
| `make_visual.py` | 背景（朝もやの庭・紅葉の枝・小鳥2羽）・サムネイル・冒頭映像 |
| `make_short.py` | ショート（縦28秒、1時間版の115秒目から）とカバー |
| `make_meta.py` | タイトル・説明文・タグと規定チェック |
| `REFERENCES.md` | 測った実録音（小鳥の声15本・朝の庭の空気13本）と、当時の却下理由への対応 |

動画は `python3 ../tools/assemble.py assets/intro.mp4 out/ep32_1h.m4a 3600 out/ep32_1h.mp4`。
