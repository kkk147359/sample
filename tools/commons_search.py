"""Wikimedia Commons で音声ファイルを検索する（回数制限があるので間隔をあけて再試行する）。
使い方: python3 commons_search.py <語> [<語> ...]
"""
import json, sys, time, urllib.parse, urllib.request
UA = {"User-Agent": "QuietHoursResearch/1.0 (sound measurement; contact via claude.ai)"}
def get(url):
    for i in range(4):
        try:
            r = urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30).read()
            return json.loads(r)
        except Exception as e:
            err = e; time.sleep(2 * (i + 1))
    print("ERR", err); return None
for q in sys.argv[1:]:
    u = "https://commons.wikimedia.org/w/api.php?" + urllib.parse.urlencode(dict(action="query", list="search", srsearch=q + " filemime:audio", srnamespace=6, srlimit=20, format="json"))
    d = get(u); time.sleep(1)
    print("==", q)
    if d: [print("  ", r["title"]) for r in d["query"]["search"]]
