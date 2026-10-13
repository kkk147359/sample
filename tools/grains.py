"""試聴版D の記録と同じ方法：10msごとの音量、背景＝下から20%、背景+10dB超を音の粒とする。"""
import sys, subprocess, numpy as np
from scipy.signal import butter, sosfilt
raw=subprocess.run(["ffmpeg","-loglevel","error","-i",sys.argv[1],"-ac","1","-ar","44100","-f","f32le","-"],capture_output=True).stdout
x=np.frombuffer(raw,np.float32).astype(float); sr=44100; x=x[5*sr:-5*sr]
h=441; e=10*np.log10((x[:len(x)//h*h].reshape(-1,h)**2).mean(1)+1e-12)
bg=np.percentile(e,20); on=e>bg+10
st=np.where(on[1:]&~on[:-1])[0]+1; en=np.where(~on[1:]&on[:-1])[0]+1
if en[0]<st[0]: en=en[1:]
st=st[:len(en)]
ln=(en-st)*10; gap=np.diff(st)*10
hgt=np.array([e[a:b].max()-bg for a,b in zip(st,en)])
# 立ち上がり・減衰（1msごとの包絡）
h2=44; e2=10*np.log10((x[:len(x)//h2*h2].reshape(-1,h2)**2).mean(1)+1e-12)
att=[];dec=[]
for a in st[:400]:
    s=e2[a*10-20:a*10+80]
    if len(s)<100: continue
    p=s.argmax(); b=np.where(s[:p]<s[p]-20)[0]; att.append(p-(b[-1] if len(b) else 0))
    d=np.where(s[p:]<s[p]-20)[0]; dec.append(d[0] if len(d) else 80)
# 粒の帯域
f=np.fft.rfftfreq(4096,1/sr); P=np.zeros(len(f))
for a in st:
    seg=x[a*h-400:a*h+3696]
    if len(seg)==4096: P+=np.abs(np.fft.rfft(seg*np.hanning(4096)))**2
def band(lo,hi): return 10*np.log10(P[(f>=lo)&(f<hi)].sum())
b0=band(300,1000)
pkf=f[(f>150)&(f<2000)][P[(f>150)&(f<2000)].argmax()]
silent=0; run=0
for v in on:
    run = 0 if v else run+1
    if run==100: silent+=1
mins=len(e)/6000
print(f"粒 {len(st)/mins:.0f}回/分  長さ 中央{np.median(ln):.0f}ms 9割{np.percentile(ln,90):.0f}  間隔 中央{np.median(gap):.0f}ms 9割{np.percentile(gap,90):.0f}  高さ 中央{np.median(hgt):.1f} 上位10% {np.percentile(hgt,90):.1f}dB  鳴っている時間{on.mean()*100:.0f}%  1秒以上の無音 {silent}回")
print(f"立ち上がり 中央{np.median(att):.0f}ms  -20dBまで 中央{np.median(dec):.0f}ms  一番強い周波数 {pkf:.0f}Hz  帯域 0/{band(1000,2000)-b0:.1f}/{band(2000,4000)-b0:.1f}/{band(4000,8000)-b0:.1f}dB")
