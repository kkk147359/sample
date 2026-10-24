"""タイトル・説明文・タグをブランド規定（スキル quiet-hours-bgm-brand）の形で作り、機械的に照合する共通部分。
各テーマの make_meta.py は、テーマ別の文（説明2〜3行、音の説明、要素行、英語の要約、タグ）だけを渡す。
（照合の中身は ep16-koto/make_meta.py の check() と同じ）
"""
import json
import re

PLAYLIST = "黒画面の睡眠用BGM｜Quiet Hours"
COMMON_TAGS = ["黒画面", "真っ暗", "睡眠用BGM", "まぶしくない", "black screen"]


def chapters(hours):
    if hours == 1:
        return ["▼ チャプター", "0:00 はじめから（1時間）", "30:00 残り30分", "45:00 残り15分"]
    return ["▼ チャプター", "0:00 はじめから（8時間）"] + [f"{k}:00:00 残り{8 - k}時間" for k in range(1, 8)]


def build(t, hours):
    """t: テーマの辞書。intro/sound は {h} を含んでよい文のリスト、en は {en} を含む英語の1行"""
    h = f"{hours}時間"
    other = "8時間版" if hours == 1 else "1時間版"
    en = "1 hour" if hours == 1 else "8 hours"
    title = f"【黒画面でまぶしくない】{t['main']} {h}｜{t['elements']}｜10秒で真っ暗・{t['use']}BGM"
    lines = [s.format(h=h) for s in t["intro"]]
    lines += [""] + t["sound"] + [""] + [t["emoji"], f"⏱ {h}　🖤 10秒で黒画面（まぶしくない）", ""]
    lines += chapters(hours) + ["", f"{other}はこちらの再生リストから：{PLAYLIST}", "",
                                "使用している音源・映像は、すべてこのチャンネルのオリジナルです。", "",
                                "チャンネル登録で、あなたの「静かな時間」のおともに。", "▶ Quiet Hours BGM",
                                "https://www.youtube.com/@QuietHoursBGMjp", "", "—", t["en"].format(en=en),
                                "After the first 10 seconds, the screen turns completely black.",
                                "All audio and visuals are original to Quiet Hours BGM.", "",
                                f"#黒画面 #{t['theme_tag']} #睡眠用BGM"]
    length = ["1時間", "1 hour"] if hours == 1 else ["8時間", "8 hours", "朝まで"]
    return {"title": title, "description": "\n".join(lines), "tags": COMMON_TAGS + length + t["tags"]}


def write_and_check(t, outdir="."):
    metas = {hrs: build(t, hrs) for hrs in (1, 8)}
    for hrs, m in metas.items():
        with open(f"{outdir}/meta_{hrs}h.json", "w", encoding="utf-8") as f:
            json.dump(m, f, ensure_ascii=False, indent=2)
    ng = check(metas[1], metas[8], t["theme_tag"])
    print("チェック結果:", "すべて○" if not ng else "×あり")
    for x in ng:
        print("  ×", x)
    for hrs in (1, 8):
        print(metas[hrs]["title"], len(metas[hrs]["title"]), "文字 / タグ", len(",".join(metas[hrs]["tags"])), "文字")
    return metas, ng


def check(m1, m8, theme_tag):
    ng = []
    pat = r"^【黒画面でまぶしくない】(.+) (1時間|8時間)｜(.+)｜10秒で真っ暗・(睡眠用|睡眠・作業用)BGM$"
    parts = {}
    for hours, m in ((1, m1), (8, m8)):
        h = f"{hours}時間"
        mt = re.match(pat, m["title"])
        if not mt or mt.group(2) != h:
            ng.append(f"{h}: タイトル形式")
        else:
            parts[hours] = (mt.group(1), mt.group(3), mt.group(4))
        if len(m["title"]) > 100:
            ng.append(f"{h}: タイトル100文字超")
        d = m["description"].split("\n")
        if not any(h in l for l in d[:3]):
            ng.append(f"{h}: 冒頭3行に時間表記なし")
        if "最初の10秒だけ" not in d[2] or not d[2].endswith("画面は真っ暗になるので、まぶしくありません。"):
            ng.append(f"{h}: 3行目の定型文")
        if f"⏱ {h}　🖤 10秒で黒画面（まぶしくない）" not in d:
            ng.append(f"{h}: ⏱行")
        if any(l not in d for l in chapters(hours)):
            ng.append(f"{h}: チャプター")
        other = "8時間版" if hours == 1 else "1時間版"
        if f"{other}はこちらの再生リストから：{PLAYLIST}" not in d:
            ng.append(f"{h}: 案内行")
        for fixed in ["使用している音源・映像は、すべてこのチャンネルのオリジナルです。", "チャンネル登録で、あなたの「静かな時間」のおともに。",
                      "▶ Quiet Hours BGM", "https://www.youtube.com/@QuietHoursBGMjp", "All audio and visuals are original to Quiet Hours BGM."]:
            if fixed not in d:
                ng.append(f"{h}: 定型文「{fixed[:12]}…」")
        if d[-1] != f"#黒画面 #{theme_tag} #睡眠用BGM":
            ng.append(f"{h}: ハッシュタグ")
        if re.search(r"(治る|効く|効果があります|432Hz|ADHD|改善|集中力が上がる|ヒーリング)", m["description"]):
            ng.append(f"{h}: 効能の表現")
        t = m["tags"]
        for c in COMMON_TAGS:
            if c not in t:
                ng.append(f"{h}: 共通タグ {c}")
        want, bad = (["1時間", "1 hour"], ["8時間", "8 hours", "朝まで"]) if hours == 1 else (["8時間", "8 hours", "朝まで"], ["1時間", "1 hour"])
        ng += [f"{h}: タグ {w} なし" for w in want if w not in t]
        ng += [f"{h}: 逆の長さのタグ {b}" for b in bad if b in t]
        if len(",".join(t)) > 500:
            ng.append(f"{h}: タグ500文字超")
    if len(parts) == 2 and parts[1] != parts[8]:
        ng.append("1時間版と8時間版でメイン・要素・用途が違う")
    strip = lambda s: re.sub(r"(1|8)時間|1 hour|8 hours|（(1|8)時間）", "", s)
    d1 = [l for l in m1["description"].split("\n") if not re.match(r"^\d+:\d", l) and "版はこちら" not in l]
    d8 = [l for l in m8["description"].split("\n") if not re.match(r"^\d+:\d", l) and "版はこちら" not in l]
    if [strip(l) for l in d1] != [strip(l) for l in d8]:
        ng.append("説明文の構成が1時間版と8時間版で違う")
    t1 = [x for x in m1["tags"] if x not in ("1時間", "1 hour")]
    t8 = [x for x in m8["tags"] if x not in ("8時間", "8 hours", "朝まで")]
    if t1 != t8:
        ng.append("テーマ別タグが1時間版と8時間版で違う")
    return ng


