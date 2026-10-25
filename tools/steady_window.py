"""長い録音から、音量が高く安定した40秒（走行中の区間）を探す。駅・停車・放送の区間を避けるため。
使い方: python3 steady_window.py <音声> [...]
"""
import sys,subprocess,numpy as np
SR=8000
for p in sys.argv[1:]:
    x=np.frombuffer(subprocess.run(["ffmpeg","-loglevel","error","-i",p,"-ac","1","-ar",str(SR),"-f","f32le","-"],capture_output=True).stdout,np.float32)
    n=len(x)//SR; e=10*np.log10((x[:n*SR].reshape(n,SR)**2).mean(1)+1e-12)
    W=40; best=None
    for s in range(3,n-W-3):
        w=e[s:s+W]; sc=w.mean()-2*w.std()
        if best is None or sc>best[0]: best=(sc,s,w.mean(),w.std())
    prof=" ".join(f"{v:.0f}" for v in e[::10])
    print(p,f"len{n}s best start {best[1]}s mean{best[2]:.1f} sd{best[3]:.1f} | 10s毎: {prof}")
