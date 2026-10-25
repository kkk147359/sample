"""継ぎ目などの打音：300Hz〜3kHzの包絡の自己相関（繰り返しの間隔）と、周囲より8dB・12dB以上大きい打音の回数・間隔。
使い方: python3 joints.py <音声> <開始秒> <秒数>
"""
import sys, subprocess, numpy as np
from scipy.signal import butter, sosfiltfilt, find_peaks
SR=22050
p=sys.argv[1]; ss=float(sys.argv[2]); t=float(sys.argv[3])
x=np.frombuffer(subprocess.run(["ffmpeg","-loglevel","error","-ss",str(ss),"-t",str(t),"-i",p,"-ac","1","-ar",str(SR),"-f","f32le","-"],capture_output=True).stdout,np.float32).astype(float)
y=sosfiltfilt(butter(2,[300,3000],btype='band',fs=SR,output='sos'),x)
h=int(SR*0.005); e=(y[:len(y)//h*h].reshape(-1,h)**2).mean(1); ed=10*np.log10(e+1e-12)
fs=1/0.005
base=np.convolve(ed,np.ones(300)/300,'same'); rel=ed-base
on=np.clip(np.diff(ed,prepend=ed[0]),0,None)
on=on-on.mean(); ac=np.correlate(on,on,'full')[len(on)-1:]; ac/=ac[0]
lags=np.arange(len(ac))/fs
m=(lags>0.06)&(lags<3.0)
pk,_=find_peaks(ac*m,distance=int(0.04*fs))
top=sorted(pk,key=lambda i:-ac[i])[:6]
print(p.split('/')[-1],"自己相関の山:"," ".join(f"{lags[i]:.2f}s({ac[i]:.2f})" for i in sorted(top)))
for th in (8,12):
    q,_=find_peaks(rel,height=th,distance=int(0.05*fs))
    g=np.diff(q/fs)
    print(f"  {th}dB超の打音 {len(q)}回 ({len(q)/t*60:.0f}/分) 間隔中央 {np.median(g) if len(g) else 0:.2f}s  例 {np.round(g[:16],2)}")
