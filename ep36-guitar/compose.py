"""冬支度の夜、やさしいガットギター：オリジナル曲の楽譜（MIDI）を作る。

撥弦合成は琴に聞こえたため（v1、30点）、実際のナイロン弦ギターを録音した音源（FluidR3_GM / MuseScore_General、MIT）で
鳴らす前提で、ギターらしい弾き方（低音弦の上に和音を分散させる、3度・6度で重ねる、音を重ねて鳴らしたままにする）で書く。
定番進行（I–V–vi–IV・カノン・禁じられた遊び風の三連・グリーンスリーブス風）は使わない。
使い方: python3 compose.py <出力.mid> <長さ(秒)> [乱数シード]
"""
import sys

import mido
import numpy as np

out, length = sys.argv[1], float(sys.argv[2])
rng = np.random.default_rng(int(sys.argv[3]) if len(sys.argv) > 3 else 36)
TPB = 960

# 調ごとの和音（低音, 上の和音の構成音）。旋法的な進行で、小節数のそろわないフレーズに分ける。
# MIDI 番号：A2=45 … E5=76 の範囲に収める。
KEYS = {
    "A_dorian": [  # Am9 – D/F# – Fmaj7 – Em7 – G6 – Dm9 – Esus4 – Am(add9)
        (45, [57, 60, 64, 71]), (42, [57, 62, 66, 69]), (41, [57, 60, 64, 65]), (40, [55, 59, 62, 67]),
        (43, [55, 59, 64, 67]), (50, [57, 60, 65, 64]), (40, [57, 59, 64, 69]), (45, [59, 60, 64, 69]),
    ],
    "D_mixo": [  # D(add9) – Am7/C – G/B – Em9 – Cmaj7 – A7sus4 – Bm7 – D/A
        (50, [57, 62, 64, 66]), (48, [55, 60, 64, 67]), (47, [55, 59, 62, 67]), (52, [55, 59, 62, 66]),
        (48, [55, 59, 64, 67]), (45, [55, 57, 62, 64]), (47, [57, 62, 66, 69]), (45, [57, 62, 66, 69]),
    ],
    "E_aeolian": [  # Em9 – Cmaj7 – Am7 – Bm7 – G/D – Cmaj9 – D6 – Em
        (52, [59, 62, 66, 67]), (48, [55, 59, 64, 67]), (45, [57, 60, 64, 67]), (47, [57, 62, 66, 69]),
        (50, [55, 59, 62, 67]), (48, [55, 59, 62, 64]), (50, [57, 59, 62, 66]), (52, [55, 59, 64, 71]),
    ],
}
ORDER = ["A_dorian", "D_mixo", "E_aeolian"]
SECTION = 90.0  # 秒ごとに調と音域を変える（試聴版は90秒ごと）

events = []  # (秒, 音, 強さ, 長さ秒)


def scale_of(chord_tones):
    return sorted(set(t % 12 for t in chord_tones))


t = 1.5
sec_i = 0
prev_melody = None
while t < length - 6:
    key = ORDER[int(t // SECTION) % len(ORDER)]
    chords = KEYS[key]
    # フレーズは 3・5・4・6 小節などそろえない
    phrase = int(rng.choice([3, 4, 5, 6, 7]))
    start = int(rng.integers(0, len(chords)))
    for b in range(phrase):
        if t >= length - 6:
            break
        bass, upper = chords[(start + b) % len(chords)]
        bpm = rng.uniform(54, 60)
        beat = 60 / bpm
        bar = 4 * beat
        # 低音（親指）：小節の頭。ときどき2拍目裏にもう一度
        events.append((t, bass, rng.uniform(40, 47) * (0.72 if b == 0 else 1.0), bar * 1.6))
        if b == phrase - 1:  # フレーズの終わり：和音を重ねて鳴らしたままにし、次のフレーズまで音が途切れないようにする
            for k2, nt in enumerate(upper[:3]):
                events.append((t + 3.0 * beat + 0.06 * k2, nt, rng.uniform(30, 36), bar * 1.8))
        # 分散和音：パターンをその都度変える（三連の型に固定しない）
        n_notes = int(rng.choice([3, 4, 4, 5, 6]))
        slots = np.sort(rng.choice(np.arange(1, 8), size=min(n_notes, 7), replace=False)) * (beat / 2)
        tones = list(upper)
        rng.shuffle(tones)
        for k, s in enumerate(slots):
            note = tones[k % len(tones)]
            jitter = rng.normal(0, 0.025)
            events.append((t + s + jitter, note, rng.uniform(34, 44), bar * rng.uniform(0.9, 1.4)))
        # ときどき短い旋律（3度・6度で重ねることもある）
        if rng.random() < 0.35:
            pool = [n + 12 for n in upper if 62 <= n + 12 <= 76] + [n for n in upper if n >= 64]
            if pool:
                m = int(rng.choice(pool))
                if prev_melody is not None and abs(m - prev_melody) > 7:
                    m = int(min(pool, key=lambda p: abs(p - prev_melody)))
                prev_melody = m
                mt = t + beat * rng.choice([1.0, 1.5, 2.0])
                events.append((mt, m, rng.uniform(42, 50), bar))
                if rng.random() < 0.4:  # 6度下を重ねる
                    events.append((mt + 0.02, m - 9 if (m - 9) % 12 in scale_of(upper + [bass]) else m - 8, rng.uniform(34, 42), bar))
        # ためらい（ルバート）：小節の終わりで少し伸ばす
        t += bar * rng.uniform(1.0, 1.08)
    # フレーズの終わりは少し間をあける（ただし無音は2秒以内。前の音が鳴ったまま）
    t += rng.uniform(0.1, 0.5)

# 音域の確認（A2〜E5）
events = [(max(0.0, a), int(np.clip(n, 45, 76)), v, d) for a, n, v, d in events]

mid = mido.MidiFile(ticks_per_beat=TPB)
tr = mido.MidiTrack()
mid.tracks.append(tr)
tr.append(mido.MetaMessage("set_tempo", tempo=1_000_000, time=0))  # 1拍=1秒（時間は秒で書く）
tr.append(mido.Message("program_change", program=24, time=0))  # Acoustic Guitar (nylon)
msgs = []
for a, n, v, d in events:
    msgs.append((a, 1, mido.Message("note_on", note=n, velocity=int(v))))
    msgs.append((a + d, 0, mido.Message("note_off", note=n, velocity=0)))
msgs.sort(key=lambda m: (m[0], m[1]))
now = 0
for a, _, m in msgs:
    tick = int(round(a * TPB))
    m.time = max(0, tick - now)
    now = max(now, tick)
    tr.append(m)
mid.save(out)
print(f"{len(events)} notes, {now / TPB:.0f}s")
