"""freesound の音のページから、試聴用mp3のURL・ライセンス・長さを取り出す。
使い方: python3 freesound_page.py <ページURL> [...]
"""
import re, sys, time, urllib.request, html
UA = {"User-Agent": "Mozilla/5.0 QuietHoursResearch"}
for url in sys.argv[1:]:
    t = urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30).read().decode("utf8", "ignore")
    mp3 = re.findall(r'https://cdn\.freesound\.org/previews/[^"\'\s]+?-hq\.mp3', t)
    lic = re.findall(r'(creativecommons\.org/[a-z/.\-0-9]+|Creative Commons 0|Attribution[^<"]{0,40})', t)
    dur = re.findall(r'(\d+:\d+(?:\.\d+)?)\s*<', t)[:1]
    desc = re.search(r'<meta name="description" content="([^"]*)"', t)
    print(url.split('/sounds/')[1].strip('/'), mp3[:1], sorted(set(lic))[:2], dur, html.unescape(desc.group(1))[:150] if desc else "")
    time.sleep(1)
