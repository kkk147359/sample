"""しずく（水琴窟など）を1滴ずつ切り出して測る：1分あたりの数、間隔、立ち上がり、周りとの音量差、余韻、平均スペクトルの山。
使い方: python3 drops.py <音声ファイル>
"""
import sys, subprocess, numpy as np
from scipy.signal import find_peaks, butter, sosfiltfilt
def load(p):
    raw=subprocess.run(["ffmpeg","-loglevel","error","-i",p,"-ac","1","-ar","44100","-f","f32le","-"],capture_output=True).stdout
    return np.frombuffer(raw,np.float32).astype(float)
sr=44100; x=load(sys.argv[1])
# drop band 900-3500 Hz
xb=sosfiltfilt(butter(4,[900,3500],btype='band',fs=sr,output='sos'),x)
hop=220  # 5ms
e=np.sqrt(np.convolve(xb**2,np.ones(hop)/hop,'same'))[::hop]; le=20*np.log10(e+1e-9)
bg=np.percentile(le,30)
d=np.diff(le)
pk,_=find_peaks(d,height=4,distance=int(0.12*sr/hop))
pk=[p for p in pk if le[min(p+4,len(le)-1)]>bg+8]
on=np.array(pk)*hop/sr
dur=len(x)/sr
print(f"drops {len(on)} in {dur:.0f}s ({len(on)/dur*60:.0f}/min); background(900-3.5k) {bg:.1f}dB")
ioi=np.diff(on); print("interval p10 %.2f p25 %.2f median %.2f p75 %.2f p90 %.2f" % tuple(np.percentile(ioi,[10,25,50,75,90])))
rise=[];peakdb=[];t60=[];specs=[]
F=np.fft.rfftfreq(1<<15,1/sr)
for t in on:
    i=int(t*sr/hop)
    seg=le[i-2:i+200]
    if len(seg)<200: continue
    pkk=np.argmax(seg[:30]); peakdb.append(seg[pkk]-bg)
    base=seg[0]; lvl=seg[pkk]
    r10=base+0.1*(lvl-base); r90=base+0.9*(lvl-base)
    a=np.argmax(seg>=r10); b=np.argmax(seg>=r90); rise.append((b-a)*hop/sr*1000)
    tail=seg[pkk:]; above=tail>lvl-20
    n20=np.argmin(above) if not above.all() else len(tail)
    t60.append(n20*hop/sr*3)
    s=int(t*sr); w=x[s:s+int(0.4*sr)]
    if len(w)==int(0.4*sr): specs.append(np.abs(np.fft.rfft(w*np.hanning(len(w)),1<<15))**2)
print("rise 10-90%% ms: median %.1f p10 %.1f p90 %.1f" % (np.median(rise),np.percentile(rise,10),np.percentile(rise,90)))
print("drop peak above background dB: median %.1f p90 %.1f max %.1f" % (np.median(peakdb),np.percentile(peakdb,90),max(peakdb)))
print("decay T60 (from -20dB) s: median %.2f p10 %.2f p90 %.2f" % (np.median(t60),np.percentile(t60,10),np.percentile(t60,90)))
S=10*np.log10(np.mean(specs,0)+1e-15); m=(F>300)&(F<6000); S-=S[m].max()
pp,_=find_peaks(S[m],prominence=4,distance=40)
top=sorted(pp,key=lambda i:-S[m][i])[:12]
print("avg drop spectrum peaks:", "  ".join(f"{F[m][i]:.0f}({S[m][i]:.0f})" for i in sorted(top)))
cen=[(sp[m]*F[m]).sum()/sp[m].sum() for sp in specs]; print("drop centroid median %.0f Hz" % np.median(cen))
