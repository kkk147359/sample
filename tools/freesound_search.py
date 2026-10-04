"""freesound をキーワード検索し、ダウンロード数の多い順に音のIDと題名を出す。
使い方: python3 freesound_search.py <語> [<語> ...]
"""
import re, sys, time, urllib.parse, urllib.request, html
UA = {"User-Agent": "Mozilla/5.0 QuietHoursResearch"}
for q in sys.argv[1:]:
    u = "https://freesound.org/search/?" + urllib.parse.urlencode({"q": q, "s": "Downloads (most first)"})
    t = urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=30).read().decode("utf8", "ignore")
    print("==", q)
    # sound page links + titles + licenses + previews
    items = re.findall(r'href="(/people/[^/]+/sounds/(\d+)/)"[^>]*>\s*([^<]{3,120})<', t)
    seen = set()
    for path, sid, title in items:
        if sid in seen: continue
        seen.add(sid)
        print(f"   {sid} {html.unescape(title.strip())[:70]}  https://freesound.org{path}")
        if len(seen) >= 10: break
    prev = re.findall(r'https://cdn\.freesound\.org/previews/[^"\']+?-hq\.mp3', t)
    print("   previews:", len(set(prev)))
    time.sleep(1.5)
