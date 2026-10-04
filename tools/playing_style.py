"""演奏の録音から弾き方を測る：1分あたりの音数、音の間隔、3秒以上の間、音域、音程の動き、音量。
使い方: python3 playing_style.py <音声ファイル>
"""
import sys, subprocess, numpy as np
from scipy.signal import find_peaks
raw = subprocess.run(["ffmpeg","-loglevel","error","-i",sys.argv[1],"-ac","1","-ar","22050","-f","f32le","-"],capture_output=True).stdout
x=np.frombuffer(raw,np.float32).astype(float); sr=22050
hop=256; win=1024
fr=np.lib.stride_tricks.sliding_window_view(x,win)[::hop]*np.hanning(win)
S=np.abs(np.fft.rfft(fr,axis=1)); f=np.fft.rfftfreq(win,1/sr)
# spectral flux onset detection
flux=np.maximum(np.diff(np.log1p(100*S),axis=0),0).sum(1)
flux=np.convolve(flux,np.ones(3)/3,'same')
thr=np.median(flux)+2.5*np.std(flux)
p,_=find_peaks(flux,height=thr,distance=int(0.08*sr/hop))
on=p*hop/sr
dur=len(x)/sr
print(f"duration {dur:.0f}s onsets {len(on)}  rate {len(on)/dur*60:.1f}/min")
ioi=np.diff(on)
print("inter-onset s: p10 %.2f p25 %.2f median %.2f p75 %.2f p90 %.2f" % tuple(np.percentile(ioi,[10,25,50,75,90])))
print("gaps >3s: %d, >5s: %d" % ((ioi>3).sum(), (ioi>5).sum()))
# pitch estimate per onset (dominant peak 150-1200 in 0.05-0.25s after onset)
pitches=[]
for t in on:
    i=int((t+0.05)*sr/hop); j=int((t+0.25)*sr/hop)
    if j>=len(S): break
    sp=S[i:j].mean(0); m=(f>150)&(f<1200)
    pitches.append(f[m][np.argmax(sp[m])])
pitches=np.array(pitches)
midi=69+12*np.log2(pitches/440)
print("pitch range (midi p5..p95): %.0f..%.0f, median %.0f" % tuple(np.percentile(midi,[5,95,50])))
iv=np.abs(np.diff(np.round(midi)))
print("interval |semitones| distribution:", {int(k):int((iv==k).sum()) for k in range(0,13)})
# level dynamics
rms=np.sqrt((x[:len(x)//sr*sr].reshape(-1,sr)**2).mean(1)); d=20*np.log10(rms+1e-9)
print("1s RMS dBFS: p10 %.1f median %.1f p90 %.1f" % tuple(np.percentile(d,[10,50,90])))
cen=(S*f).sum(1)/(S.sum(1)+1e-9)
print("centroid median %.0f Hz" % np.median(cen[S.sum(1)>np.percentile(S.sum(1),30)]))
