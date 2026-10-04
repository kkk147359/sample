"""急な音の度合い：10msごとの音量が、直前1.5秒の平均よりどれだけ大きいか（dB、200Hz〜6kHz）。
使い方: python3 sudden.py <音声ファイル>
"""
import sys, subprocess, numpy as np
from scipy.signal import butter, sosfilt
raw=subprocess.run(["ffmpeg","-loglevel","error","-i",sys.argv[1],"-ac","1","-ar","44100","-f","f32le","-"],capture_output=True).stdout
x=np.frombuffer(raw,np.float32).astype(float); sr=44100
# 耳の感度に近づける（低域と超高域を下げる）
x=sosfilt(butter(2,[200,6000],btype='band',fs=sr,output='sos'),x)
h=441; e=(x[:len(x)//h*h].reshape(-1,h)**2).mean(1)
k=150; prev=np.convolve(e,np.ones(k)/k)[:len(e)]  # 直前1.5秒
prev=np.concatenate([[e[0]],prev[:-1]])
j=10*np.log10((e+1e-12)/(prev+1e-12)); j=j[300:-300]
print(f"{sys.argv[1].split('/')[-1]}: jump p99 {np.percentile(j,99):.1f}dB  max {j.max():.1f}dB  >6dB {(j>6).mean()*100:.2f}%  >10dB {(j>10).sum()} frames")
