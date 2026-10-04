"""環境音の測定：1/3オクターブの音量と時間ゆらぎ、重心、平坦度、瞬間的な音（1秒あたりの回数と間隔）、定常的な共鳴の山。
使い方: python3 ambience.py <音声ファイル>
"""
import sys, subprocess, numpy as np
from scipy.signal import find_peaks
raw = subprocess.run(["ffmpeg","-loglevel","error","-i",sys.argv[1],"-ac","1","-ar","44100","-f","f32le","-"],capture_output=True).stdout
x=np.frombuffer(raw,np.float32).astype(float); sr=44100
hop=512; win=2048
fr=np.lib.stride_tricks.sliding_window_view(x,win)[::hop]*np.hanning(win)
S=np.abs(np.fft.rfft(fr,axis=1))**2; f=np.fft.rfftfreq(win,1/sr)
centers=1000*2.0**(np.arange(-14,11)/3)
mean=S.mean(0); tot=mean.sum()
print("1/3oct rel dB (max=0) / temporal fluct (std dB, 0.25s):")
rows=[]
for fc in centers:
    m=(f>=fc/2**(1/6))&(f<fc*2**(1/6)); b=S[:,m].sum(1)
    k=int(.25*sr/hop); bb=np.convolve(b,np.ones(k)/k,'valid')
    rows.append((fc,10*np.log10(b.mean()+1e-15),np.std(10*np.log10(bb+1e-15))))
mx=max(r[1] for r in rows)
print("  ".join(f"{fc:.0f}:{l-mx:.0f}/{sd:.1f}" for fc,l,sd in rows))
cen=(S*f).sum(1)/S.sum(1); print("centroid median %.0f Hz" % np.median(cen))
p=S[:,1:]+1e-15; fl=np.exp(np.log(p).mean(1))/p.mean(1); print("flatness median %.3f" % np.median(fl))
# transient events
e=S[:,(f>500)].sum(1); le=10*np.log10(e+1e-15)
d=np.diff(le); thr=np.percentile(d,99.0)
pk,_=find_peaks(d,height=max(thr,6),distance=int(0.03*sr/hop))
dur=len(x)/sr; print(f"transients(>6dB jumps) {len(pk)} in {dur:.0f}s = {len(pk)/dur:.2f}/s")
if len(pk)>2:
    ioi=np.diff(pk)*hop/sr; print("  interval s p10 %.2f median %.2f p90 %.2f" % tuple(np.percentile(ioi,[10,50,90])))
# strongest stationary peaks in average spectrum (for resonances)
L=10*np.log10(mean+1e-15); m=(f>100)&(f<8000)
pp,_=find_peaks(L[m],prominence=6)
top=sorted(pp,key=lambda i:-L[m][i])[:10]
print("resonant peaks:", "  ".join(f"{f[m][i]:.0f}Hz({L[m][i]-L[m].max():.0f})" for i in sorted(top)))
rms=np.sqrt((x[:len(x)//sr*sr].reshape(-1,sr)**2).mean(1)); dd=20*np.log10(rms+1e-9)
print("1s RMS dBFS p10 %.1f median %.1f p90 %.1f" % tuple(np.percentile(dd,[10,50,90])))
