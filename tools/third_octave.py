"""1/3オクターブ配分（最大0dB）、帯域ごとのゆらぎ（0.5秒平均の標準偏差）、重心、平坦度、4〜5kHz割合、打音の間隔分布。
使い方: python3 third_octave.py <音声> [開始秒=5] [秒数=60]
"""
import sys, subprocess, numpy as np
from scipy.signal import butter, sosfiltfilt, find_peaks
SR=22050
def load(p):
    raw=subprocess.run(["ffmpeg","-loglevel","error","-i",p,"-ac","1","-ar",str(SR),"-f","f32le","-"],capture_output=True).stdout
    return np.frombuffer(raw,np.float32).astype(float)
p=sys.argv[1]; x=load(p)
ss=float(sys.argv[2]) if len(sys.argv)>2 else 5; t=float(sys.argv[3]) if len(sys.argv)>3 else 60
x=x[int(ss*SR):int((ss+t)*SR)]
win=4096; hop=2048
fr=np.lib.stride_tricks.sliding_window_view(x,win)[::hop]*np.hanning(win)
S=np.abs(np.fft.rfft(fr,axis=1))**2; f=np.fft.rfftfreq(win,1/SR)
cents=[31.5,40,50,63,80,100,125,160,200,250,315,400,500,630,800,1000,1250,1600,2000,2500,3150,4000,5000,6300,8000]
B=np.array([S[:,(f>=c/2**(1/6))&(f<c*2**(1/6))].sum(1) for c in cents])
m=10*np.log10(B.mean(1)+1e-15); m-=m.max()
sm=max(1,int(0.5*SR/hop))
sd=[np.std(10*np.log10(np.convolve(r,np.ones(sm)/sm,'valid')+1e-15)) for r in B]
tot=S.sum(1); cen=np.median((S*f).sum(1)/(tot+1e-15))
pp=S[:,1:]+1e-15; flat=np.median(np.exp(np.log(pp).mean(1))/pp.mean(1))
hf=np.median(S[:,(f>=4000)&(f<5000)].sum(1)/(tot+1e-15))*100
# 継ぎ目：300Hz〜3kHzの包絡の立ち上がり
y=sosfiltfilt(butter(2,[300,3000],btype='band',fs=SR,output='sos'),x)
env=np.sqrt(sosfiltfilt(butter(2,40,fs=SR,output='sos'),y**2).clip(0))
ed=20*np.log10(env+1e-9); base=np.convolve(ed,np.ones(int(1.5*SR))/int(1.5*SR),'same')
rel=ed-base
pk,pr=find_peaks(rel,height=4,distance=int(0.06*SR),prominence=4)
tp=pk/SR; g=np.diff(tp)
print(f"## {p.split('/')[-1]} 区間{ss:.0f}-{ss+t:.0f}s")
print(" 1/3oct:"," ".join(f"{c:g}:{v:.0f}" for c,v in zip(cents,m)))
print(" ゆらぎdB:"," ".join(f"{c:g}:{v:.1f}" for c,v in zip(cents,sd) if c in(63,125,250,500,1000,2000,4000)))
print(f" 重心{cen:.0f}Hz 平坦度{flat:.3f} 4-5kHz {hf:.2f}%  打音数{len(pk)} ({len(pk)/t*60:.0f}/分) 高さ中央{np.median(rel[pk]) if len(pk) else 0:.1f}dB")
if len(g):
    h,e=np.histogram(g,bins=[0,0.08,0.12,0.16,0.2,0.3,0.5,0.8,1.2,1.6,2.0,3,5,99])
    print(" 間隔分布:"," ".join(f"{e[i]:g}-{e[i+1]:g}:{h[i]}" for i in range(len(h)) if h[i]))
    print(" 最初の間隔:",np.round(g[:30],2))
