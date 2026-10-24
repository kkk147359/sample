# ep34/35「晩秋の夜、落ち葉に降る静かな雨とピアノ」

【黒画面でまぶしくない】晩秋の夜、落ち葉に降る静かな雨とピアノ 1時間（8時間）｜雨音・ピアノ｜10秒で真っ暗・睡眠用BGM（品質チェック部の修正案）

| ファイル | 役割 |
|---|---|
| `synth_piano.py` | やわらかいピアノ（2〜3本の弦のうなり・倍音のずれ・2段の減衰・打鍵ノイズ・部屋の響き）と、その場で作るオリジナルのフレーズ |
| `synth_rain.py` | 遠くの森の雨（下地）＋落ち葉に当たる小さな粒＋枝から落ちるしずく |
| `trial.py` | 試聴版。`python3 trial.py out.mp3 150 1 -8`（最後は雨の大きさ、ピアノ比dB） |
| `render_long.py` | 長い版。`python3 render_long.py out/ep34_1h.m4a 3600 3501`／`python3 render_long.py out/ep35_8h.m4a 28800 3601` |
| `make_visual.py` | 背景（雨の夜の庭・落ち葉・石灯籠）・サムネイル・冒頭映像 |
| `make_short.py` | ショート（縦28秒、1時間版の947秒目から）とカバー |
| `make_meta.py` | タイトル・説明文・タグと規定チェック |
| `REFERENCES.md` | 測った実録音（雨10本）と、合成との比較 |

検査：`../tools/sudden.py`（急な音）、`../tools/hf_window.py`（4〜5kHz、10秒ごと）、`../tools/piano_metrics.py`（ピアノ）、`../tools/ambience.py` `../tools/drops.py`（雨）。
