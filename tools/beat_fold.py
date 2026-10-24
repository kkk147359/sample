import sys, subprocess, numpy as np
from scipy.signal import butter, sosfiltfilt
SR=44100
def load(p,ss,t):
    return np.frombuffer(subprocess.run(["ffmpeg","-loglevel","error","-ss",str(ss),"-t",str(t),"-i",p,"-ac","1","-ar",str(SR),"-f","f32le","-"],capture_output=True).stdout,np.float32).astype(float)
p,ss,t=sys.argv[1],float(sys.argv[2]),float(sys.argv[3])
x=load(p,ss,t)
e=np.sqrt(sosfiltfilt(butter(2,20,fs=SR,output="sos"),sosfiltfilt(butter(2,[30,400],btype="band",fs=SR,output="sos"),x)**2).clip(1e-12))
d=e[::441]  # 100 Hz
d=d-d.mean(); ac=np.correlate(d,d,'full')[len(d)-1:]; ac/=ac[0]
lo,hi=40,200; per=lo+np.argmax(ac[lo:hi]); print(p[:8],"period s",per/100,"bpm",6000/per)
# fold
n=len(d)//per; F=(e[::441][:n*per]).reshape(n,per); m=F.mean(0); m=20*np.log10(m/m.max())
i0=np.argmax(m); m=np.roll(m,-i0+10)
print(" folded env dB per 20ms:", " ".join(f"{v:.0f}" for v in m[::2]))
# beat-to-beat interval variability via per-cycle max position
pos=[]
