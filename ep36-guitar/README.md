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
