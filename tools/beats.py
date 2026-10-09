import sys, subprocess, numpy as np
from scipy.signal import butter, sosfiltfilt, find_peaks
SR=44100
def load(p,ss=0,t=None):
    a=["ffmpeg","-loglevel","error","-ss",str(ss)]+(["-t",str(t)] if t else [])+["-i",p,"-ac","1","-ar",str(SR),"-f","f32le","-"]
    return np.frombuffer(subprocess.run(a,capture_output=True).stdout,np.float32).astype(float)
p=sys.argv[1]; ss=float(sys.argv[2]) if len(sys.argv)>2 else 0; t=float(sys.argv[3]) if len(sys.argv)>3 else None
x=load(p,ss,t); x/=np.abs(x).max()
env=np.sqrt(sosfiltfilt(butter(2,30,fs=SR,output="sos"),sosfiltfilt(butter(2,[20,600],btype="band",fs=SR,output="sos"),x)**2).clip(0))
env_db=20*np.log10(env+1e-6)
pk,_=find_peaks(env,height=env.max()*0.12,distance=int(0.12*SR))
tp=pk/SR; lv=env_db[pk]
print(f"{p[:12]} dur {len(x)/SR:.1f}s  peaks {len(pk)}")
# pair S1/S2: gaps
g=np.diff(tp); print(" gaps(s):", np.round(g[:24],3))
# per-hit duration (above -20dB of its peak), rise time
durs=[];rises=[]
for k in pk:
    th=env[k]*0.1
    a=k
    while a>0 and env[a]>th: a-=1
    b=k
    while b<len(env)-1 and env[b]>th: b+=1
    durs.append((b-a)/SR*1000); rises.append((k-a)/SR*1000)
print(" hit dur ms med", np.median(durs).round(), "rise ms med", np.median(rises).round(), " level spread dB", np.round(lv[:12]-lv.max(),1))
f=np.fft.rfftfreq(len(x),1/SR); P=np.abs(np.fft.rfft(x*np.hanning(len(x))))**2
cents=[20,25,31.5,40,50,63,80,100,125,160,200,250,315,400,500,630,800,1000,1250,1600,2000,3150]
b=[P[(f>=c/2**(1/6))&(f<c*2**(1/6))].sum() for c in cents]; b=10*np.log10(np.array(b)/max(b)+1e-12)
print(" 1/3oct:", " ".join(f"{c}:{v:.0f}" for c,v in zip(cents,b)))
m=f<4000; print(" centroid Hz", (f[m]*P[m]).sum()/P[m].sum())
# floor between beats
print(" floor (10th pct env dB rel peak)", np.percentile(env_db,10)-env_db.max())
