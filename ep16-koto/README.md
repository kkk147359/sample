# ep16/17「水琴窟と低い琴の音」制作一式

【黒画面でまぶしくない】水琴窟と低い琴の音 1時間／8時間｜低音の琴・水琴窟｜10秒で真っ暗・睡眠用BGM

- 1時間版・8時間版の動画、サムネイル、タイトル・説明文・タグは Google Drive に納品済み
  （tokyogamewire@gmail.com「Quiet Hours BGM ep16-17 水琴窟と低い琴の音」フォルダ）。
- 使った実録音と測定値は `REFERENCES.md`。

## ファイル

| ファイル | 役割 |
|---|---|
| `synth_17gen.py` | 低い琴（十七絃をイメージ）。伽耶琴の単音の測定に合わせた倍音・減衰。陽音階、ゆっくりした立ち上がり。`render_block()` で区間ごとに書き出せる |
| `nature.py` | 水琴窟（しずく400通りの作り置き＋甕の下地の響き）と囲炉裏（不採用）の合成 |
| `render_long.py` | 長い版の書き出し。2分ずつ区切って計算し、ffmpeg で AAC（.m4a）にする |
| `make_visual.py` | 背景（夜の庭の水琴窟）の描画、サムネイル、冒頭15秒の映像 |
| `make_meta.py` | タイトル・説明文・タグを作り、ブランド規定と機械的に照合する |
| `make_short.py` | ショート（縦1080×1920・28秒）。1時間版と同じ曲（シード1001）の59秒目からを切り出し、しずくに合わせて波紋を描く。`python3 make_short.py $W/ep16_short.mp4 58.9 28`（約7分） |
| `drive_upload.py` | Google Drive への再開可能アップロード |
| `scene.py` | 短い試作（琴／十七絃 ＋ 水琴窟／囲炉裏）の書き出し |
| `synth_koto.py` | 普通の箏（平調子）。睡眠には高音が強すぎて不採用。`reverb_ir()` などは十七絃側からも使う |
| `assets/` | サムネイル2枚、冒頭映像 `intro.mp4`、つなぎ用の15秒の黒い映像 `black15.mp4` |
| `proto_*.mp3` / `sample_*.mp3` | 社長に出した試聴版（経緯の記録） |

## 手順

作業用フォルダを `W` とする（大きなファイルはリポジトリに入れない）。

### 1. 音（1時間版と8時間版は別シードで作る。8時間版の切り出しにしない）

```
python3 render_long.py $W/ep16_1h.m4a 3600 1001      # 約12分（4コア）
python3 render_long.py $W/ep17_8h.m4a 28800 8001     # 約90分
```

- 音量は最初の5分で決め、-20LUFS 前後になる（実績：1h -19.7、8h -19.3）。
- 区切りをまたぐ音は前後で同じ波形になるよう、音ごとに乱数を固定している。
  `synth_17gen.render_block()` の中の `rng` の固定を外すと、境目でプチ音が出る。

### 2. 検査

```
python3 ../tools/sudden.py $W/ep16_1h.m4a      # 急な音（最大 17dB 程度まで）
ffmpeg -i $W/ep16_1h.m4a -af ebur128=peak=true -f null -   # 音量・ピーク
ffmpeg -ss 1800 -t 600 -i $W/ep16_1h.m4a $W/mid.wav && python3 ../tools/spectrum.py $W/mid.wav   # 4〜5kHz
```

区切り（120秒ごと）の境目で、サンプル間の差がその前後1秒の99.9パーセンタイルの1.5倍を超えないことも確認した。

### 3. 映像

```
python3 make_visual.py thumb assets/ep16_thumbnail_1h.png 1時間
python3 make_visual.py thumb assets/ep17_thumbnail_8h.png 8時間
python3 make_visual.py intro assets/intro.mp4
```

1時間版と8時間版のサムネイルは画像差分を取り、違いが時間表記の枠（520,460〜760,546）の中だけであることを確認する。

### 4. 動画（冒頭15秒＋黒15秒のくり返し＋音）

```
ffmpeg -f lavfi -i color=c=black:s=1920x1080:r=12 -t 15 -c:v libx264 -pix_fmt yuv420p -r 12 -g 24 -crf 18 $W/black15.mp4
# list_1h.txt: "file 'intro.mp4'" のあとに "file 'black15.mp4'" を 239 行（8時間版は 1919 行）
ffmpeg -f concat -safe 0 -i list_1h.txt -i $W/ep16_1h.m4a -map 0:v -map 1:a -c copy -movflags +faststart $W/ep16_1h.mp4
```

### 5. タイトル・説明文・タグ

```
python3 make_meta.py     # meta_1h.json / meta_8h.json を書き出し、規定チェックが「すべて○」になること
```

### 6. 納品（Google Drive）

セッションのファイル送信は 80MB 以上で失敗した（502/503）。Drive の API で直接送る。

1. クラウド環境のネットワーク設定で `www.googleapis.com` を許可する。
2. 社長に OAuth 2.0 Playground で `https://www.googleapis.com/auth/drive.file` のアクセストークン（1時間有効）を作ってもらい、
   環境の「認証情報」に登録してもらう（許可ウェブサイト `www.googleapis.com`、パスプレフィックスは空、
   ヘッダー `Authorization`・プレフィックス `Bearer`）。トークンはチャットに貼ってもらわない。
3. ```
   python3 drive_upload.py folder "フォルダ名"        # フォルダIDが出る
   python3 drive_upload.py put <フォルダID> $W/ep16_1h.mp4
   ```
   8時間版（約960MB）も数分で送れた。トークンが切れる前に送り終えること。
