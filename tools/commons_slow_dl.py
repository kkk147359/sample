"""Wikimedia Commons の元ファイルを1本ずつゆっくり取得する（429 のときは retry-after 600秒に従い11分待つ）。
名前の一覧はスクリプト内で書き換えて使う。取得した録音は測定後に削除する。
"""
import hashlib, time, urllib.parse, subprocess, os
names={"r02":"3672次_R40走行音_知本~太麻里.wav","r06":"JRH-kiha54_519_Kawayuonsen-Midori_20111231.ogg","r07":"JRH-kiha54_515_Hamakoshimizu-Kitahama_20090531.ogg","r10":"TOSHIBA_Omi_imazu-Shin_asahi_M'_222-3031Dasei.ogg","r11":"JR_west_115_rapid_moha114-1_takamatsu.ogg","r14":"South_Western_Railway_456013_between_Ewell_West_and_Bookham,_Jan_2022.ogg","r15":"JR東日本209系1000番台(豊田⇒日野).ogg","r17":"JRH-kiha54_507_Satturu-Kiyosatocho_20101231.ogg","r18":"Kitami02.OGG","r03":"2023.8.24_1738次_竹中~六家_走行音_最新版.wav","r05":"422次_TEMU2000_普悠瑪自強號_列車走行音_鹿野~台東.wav"}
time.sleep(660)
for tag,n in names.items():
    while True:
        h=hashlib.md5(n.encode()).hexdigest(); q=urllib.parse.quote(n)
        url=f"https://upload.wikimedia.org/wikipedia/commons/{h[0]}/{h[:2]}/{q}"
        dst=f"dl/{tag}.orig"
        r=subprocess.run(["curl","-sS","-m","120","-r","0-6000000","-A","QuietHoursResearch/1.0 (https://www.youtube.com/@QuietHoursBGMjp; measurement only)","-o",dst,"-w","%{http_code}",url],capture_output=True,text=True)
        print(time.strftime("%H:%M:%S"),tag,r.stdout,os.path.getsize(dst),flush=True)
        if r.stdout in("200","206"): time.sleep(90); break
        time.sleep(660)
