# ep38/39「冬へ向かう夜、静かに走る夜行列車の音」

車内の走行音をすべて合成で作る（録音は測定だけに使い、作品には入れない）。実録音の測定は `REFERENCES.md`。

```
pip install numpy scipy pillow
python3 trial.py out.mp3 30 38 -1 35 0.29     # 試聴版（社長OKの D2：時速35km、タタンの間0.29秒、継ぎ目-1dB）
```

| ファイル | 役割 |
|---|---|
| `synth_train.py` | 走行音（整形ノイズ＋帯域ごとのランダムな小さい変化）と継ぎ目の打音・時刻 |
| `trial.py` | 30秒の試聴版。引数で継ぎ目の大きさ・時速・タタンの間を変えられる |
| `render_long.py` | 長い版。`python3 render_long.py out/ep38_1h.m4a 3600 3801 160k`／`python3 render_long.py out/ep39_8h.m4a 28800 3901 128k`（8時間版は添付できる大きさにするため音声128k） |
| `make_visual.py` | 背景（夜行列車の車内から見る窓、遠くの町の灯りが流れる）・サムネイル・冒頭映像 |
| `make_short.py` | ショート（縦28秒、1時間版の1200秒目から）とカバー |
| `make_meta.py` | タイトル・説明文・タグと規定チェック |

組み立て：`python3 ../tools/assemble.py assets/intro.mp4 out/ep38_1h.m4a 3600 out/ep38_1h.mp4`。
検査：`../tools/sudden_long.py`（急な音・無音・4〜5kHz）、`../tools/third_octave.py`・`../tools/joints.py`（実録音との比較）。
