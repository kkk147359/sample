"""単音の倍音ごとの減衰時間（T60）を推定する。値が非常に大きいものは雑音に埋もれた倍音なので無視する。
使い方: python3 partial_t60.py <音声ファイル> <基音Hz>
"""
import sys, subprocess, numpy as np
p, f0 = sys.argv[1], float(sys.argv[2])
raw=subprocess.run(["ffmpeg","-loglevel","error","-i",p,"-ac","1","-ar","44100","-f","f32le","-"],capture_output=True).stdout
x=np.frombuffer(raw,np.float32).astype(float); sr=44100
on=np.argmax(np.abs(x)>0.1*np.abs(x).max()); x=x[on:]
win=8192; hop=1024
fr=np.lib.stride_tricks.sliding_window_view(x,win)[::hop]*np.hanning(win)
S=np.abs(np.fft.rfft(fr,1<<15,axis=1)); f=np.fft.rfftfreq(1<<15,1/sr); t=np.arange(len(S))*hop/sr
out=[]
for k in range(1,16):
    b=(f>k*f0*0.97)&(f<k*f0*1.03); db=20*np.log10(S[:,b].max(1)+1e-12)
    i0=int(0.15*sr/hop); sel=(t>0.15)&(db>db[i0]-35)&(t<6)
    if sel.sum()<5: continue
    sl=np.polyfit(t[sel],db[sel],1)[0]
    out.append(f"{k*f0:.0f}Hz:{-60/sl if sl<0 else 99:.1f}s")
print(f"len {len(x)/sr:.1f}s  ", "  ".join(out))
