import numpy as np, json, sys
sys.path.insert(0,'.')
from ph_indep import bank, vector, N
mats,_ = bank(bytes(32)); rng = np.random.default_rng(1)
def fold(Y): 
    z=np.zeros(N,np.uint8)
    for y in Y: z ^= ((((y+262144)&0xffffffff)>>9)&15).astype(np.uint8)
    return z
T=300; Ys=[]
for n in range(T):
    _,x=vector("C20",b"hdr",n); xf=x.astype(np.float32)
    Ys.append([(M@xf).astype(np.int64) for M in mats])
out={}
for f in [0.001,0.005,0.01,0.02,0.05]:
    ok=0
    for Y in Ys:
        Yp=[y+np.where(rng.random(N)<f, rng.choice([-1,1],N),0) for y in Y]
        ok+= np.array_equal(fold(Y),fold(Yp))
    out[f"pm1_rate_{f}"]={"measured":ok/T,"predicted_exp(-64f)":round(float(np.exp(-64*f)),3)}
for s in [0.25,0.5,1,2]:
    ok=0
    for Y in Ys:
        Yp=[y+np.rint(rng.normal(0,s,N)).astype(np.int64) for y in Y]
        ok+= np.array_equal(fold(Y),fold(Yp))
    out[f"gauss_sigma_{s}"]=ok/T
print(json.dumps(out,indent=1))
