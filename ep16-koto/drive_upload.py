"""Google Drive へ大きなファイルを再開可能アップロードで送る。
認証は環境の API credentials（www.googleapis.com に Authorization: Bearer を自動付与）を使う。
使い方:
  python3 drive_upload.py folder <フォルダ名>            → フォルダIDを表示
  python3 drive_upload.py put <フォルダID> <ファイル> [MIME]
"""
import json
import os
import sys
import urllib.request

API = "https://www.googleapis.com"
CHUNK = 32 * 1024 * 1024


def req(method, url, data=None, headers=None):
    r = urllib.request.Request(url, data=data, method=method, headers=headers or {})
    try:
        with urllib.request.urlopen(r, timeout=300) as resp:
            return resp.status, dict(resp.headers), resp.read()
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), e.read()


def folder(name):
    body = json.dumps({"name": name, "mimeType": "application/vnd.google-apps.folder"}).encode()
    st, _, out = req("POST", f"{API}/drive/v3/files?fields=id,webViewLink", body, {"Content-Type": "application/json"})
    print(st, out.decode())


def put(parent, path, mime="video/mp4"):
    size = os.path.getsize(path)
    meta = json.dumps({"name": os.path.basename(path), "parents": [parent]}).encode()
    st, h, out = req("POST", f"{API}/upload/drive/v3/files?uploadType=resumable&fields=id,name,size,webViewLink", meta,
                     {"Content-Type": "application/json; charset=UTF-8", "X-Upload-Content-Type": mime, "X-Upload-Content-Length": str(size)})
    loc = h.get("Location") or h.get("location")
    if not loc:
        sys.exit(f"start failed {st} {out[:300]}")
    with open(path, "rb") as f:
        pos = 0
        while pos < size:
            chunk = f.read(CHUNK)
            end = pos + len(chunk) - 1
            for attempt in range(5):
                st, h, out = req("PUT", loc, chunk, {"Content-Length": str(len(chunk)), "Content-Range": f"bytes {pos}-{end}/{size}"})
                if st in (200, 201, 308):
                    break
                print(f"retry {attempt + 1} status {st}", flush=True)
            else:
                sys.exit(f"upload failed at {pos}: {st} {out[:300]}")
            pos = end + 1
            print(f"{os.path.basename(path)} {pos * 100 // size}%", flush=True)
    print(out.decode())


if __name__ == "__main__":
    if sys.argv[1] == "folder":
        folder(sys.argv[2])
    else:
        put(sys.argv[2], sys.argv[3], sys.argv[4] if len(sys.argv) > 4 else "video/mp4")
