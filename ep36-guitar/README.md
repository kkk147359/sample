# ep36/37「冬支度の夜、やさしいガットギター」（試作中）

10/4 の v1（撥弦合成、`../ep16-guitar/`）は「琴に聞こえる、30点」だった。v2 は実際のナイロン弦ギターを録音した音源
（FluidR3_GM.sf2、MIT ライセンス。`apt-get install fluidsynth fluid-soundfont-gm`）でオリジナル曲を鳴らす。

```
pip install numpy scipy mido
python3 compose.py v2.mid 180 36            # 楽譜（調は90秒ごとに A ドリア → D ミクソリディア → E エオリア）
python3 render.py v2.mid v2_raw.wav         # 音源で鳴らす＋部屋の響き＋EQ（70Hz以下カット、120Hz -2.5dB、1kHz -7dB、3kHz以上 -3dB）
ffmpeg -i v2_raw.wav -af "acompressor=threshold=-30dB:ratio=2:attack=8:release=250:knee=6,loudnorm=I=-23:TP=-3:LRA=7" v2.wav
python3 ../tools/guitar_profile.py v2.wav 5 170   # 実録音と同じ物差しで測る
```

実録音14本との比較は `/mnt/project-files/research/ep36_ガットギター_実録音測定.md`。

## 長い版・映像・メタデータ（10/24 社長OK のあと）

| ファイル | 役割 |
|---|---|
| `render_long.py` | 長い版。`python3 render_long.py out/ep36_1h.m4a 3600 3601 160k`／`python3 render_long.py out/ep37_8h.m4a 28800 28801 128k`（8時間版は添付できる大きさにするため音声128k） |
| `make_visual.py` | 背景（灯りを落とした部屋・椅子に立てかけたギター・たたんだ毛布・窓の外に落ちる葉）・サムネイル・冒頭映像 |
| `make_short.py` | ショート（縦28秒、1時間版の1325秒目から）とカバー |
| `make_meta.py` | タイトル・説明文・タグと規定チェック |

組み立て：`python3 ../tools/assemble.py assets/intro.mp4 out/ep36_1h.m4a 3600 out/ep36_1h.mp4`。
検査：`../tools/sudden_long.py`（急な音・無音・4〜5kHz）、`../tools/guitar_profile.py`（実録音との比較）。
