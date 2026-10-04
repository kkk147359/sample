"""単音の録音のスペクトルの山を、弾いた直後・0.15〜0.6秒・1〜2秒の3つの時間で比べる（合成音との比較用）。
使い方: python3 note_peaks.py <音声ファイル>
"""
import sys, subprocess, numpy as np
from scipy.signal import find_peaks
raw = subprocess.run(["ffmpeg","-loglevel","error","-i",sys.argv[1],"-ac","1","-ar","44100","-f","f32le","-"],capture_output=True).stdout
x=np.frombuffer(raw,np.float32).astype(float); sr=44100
on=np.argmax(np.abs(x)>0.1*np.abs(x).max())
for t0,t1 in ((0.0,0.15),(0.15,0.6),(1.0,2.0)):
    seg=x[on+int(t0*sr):on+int(t1*sr)]
    if len(seg)<1000: continue
    S=20*np.log10(np.abs(np.fft.rfft(seg*np.hanning(len(seg)),1<<17))+1e-9); f=np.fft.rfftfreq(1<<17,1/sr)
    m=(f>60)&(f<8000); S=S[m]; f=f[m]; S-=S.max()
    p,_=find_peaks(S,height=-40,distance=int(40/(f[1]-f[0])))
    top=sorted(p,key=lambda i:-S[i])[:14]
    print(f"[{t0}-{t1}s]", "  ".join(f"{f[i]:.0f}Hz:{S[i]:.0f}" for i in sorted(top)))
