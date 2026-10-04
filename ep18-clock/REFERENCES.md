# 測定に使った実録音（freesound.org）

音そのものは作品に使っていない。測定（`tools/ticks.py` `tools/sudden.py`）にだけ使い、作業用の一時フォルダから削除した。

| 録音 | ライセンス | 分かったこと |
|---|---|---|
| #456236 Antique wall clock（straget） | CC BY 4.0 | 間隔 0.54/0.62秒（チクとタクで14%差）、ゆらぎ1.6ms、強さの差約3dB・ばらつき0.5〜1dB。主な帯域630Hz〜2kHz、3kHz -9dB・4kHz -12dB。急な音 上位1% 13.5dB・最大17.7dB |
| #125968 Grandfather clock（Ryding） | CC0 | 間隔 0.57/0.60秒、強さの差約6dB。共鳴の山 100・186・649・738Hz。急な音 上位1% 14.2dB・最大16.6dB |
| #32937 Grandfather Clock（digifishmusic） | CC BY 4.0 | 間隔 1.03/0.98秒、強さの差約2dB。主な帯域500〜630Hz、3kHz -13dB・4kHz -22dB。共鳴 221・476・579Hz。急な音 上位1% 14.6dB・最大18.7dB |
| #414469 Old clock ticking（giddster） | CC0 | 間隔 0.39/0.47秒、ゆらぎ4ms |
| 参考外 | #657255（速い置き時計、0.37秒）・#164080／#18037（間隔が不規則で別の音が混ざる） | 振り子時計の値としては使わず |

共通：1打は「主な打音」のあと 5〜30ms に小さな追い打ちが続く。平均の音量の形は、最大から 20ms で約-10dB、55ms で約-20dB、120ms で約-30dB。

## 合成版（試聴版 A：0.57/0.63秒、B：1.03/0.97秒）

| 項目 | 実録音 | 合成版 |
|---|---|---|
| チクとタクの強さの差・ばらつき | 1〜6dB・0.5〜1.4dB | 約2dB・1.4dB |
| 平均の音量の形 20ms/55ms/120ms | -10/-20/-30dB | -9/-15/-30dB |
| 3.2kHz・4kHz・5kHz（打音の直後50ms） | -9〜-13 / -12〜-22 / -17〜-23dB | -18 / -27 / -36dB（企画の条件どおり実録音より下げた） |
| 急な音 上位1% | 13.5〜14.6dB | A 13.7dB・B 15.2dB |

## v3（10/4 社長「もう少し現実に近づけて」「時計以外の音も欲しい」）

追加で測った柱時計の実録音：#405423 Wall Clock Ticking（straget, CC BY 4.0, 1.00秒）、#371070 Grandads Wall Clock c1926（PAL6, CC0, 0.50/0.71秒）、
#453159 German Clock Tic-Toc（canoeCG, CC0, 0.49/0.51秒）、#253997 Pendulum clock（janacp, CC0）、#533928 Junghans（blackstorm88, CC0）、#329786（visualasylum, CC BY 4.0）。

v3 の打音は、`tools/tick_template.py` で実録音から取り出した「帯域ごとの音量の時間変化」（数十打の平均、`templates/*.npz`、波形は含まない）に、
1打ごとに新しい雑音を沿わせて作る。部屋の雑音は差し引き、3.5kHzより上は 3dB/オクターブ下げた。
平均の音量の形は実録音とほぼ一致（#453159：20ms -13/-12dB、40ms -27/-27dB、60ms -33/-32dB、合成/実録音）。

### 窓の外の小雨（rain.py）

| 録音 | ライセンス | 分かったこと |
|---|---|---|
| #392304 Rain recorded inside with open window（BonnyOrbit） | CC0 | 120Hz〜1.3kHz がほぼ平ら、2kHz -5dB・4kHz -12dB・8kHz -12dB。ゆらぎ 0.8〜3dB。雨だれ 1分に約48滴、周りより中央値14dB |
| #380651 Light rain on street（BonnyOrbit） | CC0 | 1.6kHz 中心、4kHz -6dB・8kHz -11dB、ゆらぎ 0.5〜1dB |
| #557376 Rain from a first floor window（khenshom） | CC0 | 低音が強い（街の音）。8kHzまで -9dB 前後 |
| #81819 Rain on Window, Reverberant room（silencyo） | CC0 | 400Hz〜1.6kHz 中心、ゆらぎ 0.6〜1dB |

合成：#392304 の配分をもとに 150Hz より下を切り（低音の圧迫感対策）、3kHzより上を3〜5dB下げた。ゆらぎ約1dB（数秒単位）。
雨だれは周りより中央値 12.5dB（実録音より控えめ）。急な音は時計＋雨で上位1% 13.3dB・最大16〜17dB。
