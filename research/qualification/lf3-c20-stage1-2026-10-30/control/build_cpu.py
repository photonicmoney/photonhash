import os
"""Remote build and finite native qualification. No network load or GPU calls."""
import ctypes,hashlib,json,pathlib,subprocess,sys,time
R=pathlib.Path(os.environ.get('LF3_STAGE1_ROOT','/workspace/lf3-stage1'));S=R/'src';E=R/'evidence';B=R/'build';repo=R/'public-source';lab=repo/'research/qualification/lf3-c20-verifier-2026-10-30';ref=lab/'reference'
sys.path.insert(0,str(S));from verifier_server import Backend,Metrics
def run(name,cmd,limit=90):
    start=time.monotonic()
    with (E/(name+'.log')).open('x') as out:p=subprocess.run(cmd,cwd=R,stdout=out,stderr=subprocess.STDOUT,timeout=limit)
    (E/(name+'.receipt.json')).write_text(json.dumps(dict(passed_process=p.returncode==0,exit_code=p.returncode,wall_seconds_measured=time.monotonic()-start),indent=2)+'\n')
    if p.returncode==40:
        (E/'STOP.json').write_text(json.dumps(dict(reason='Native test reports real hash mismatch',test=name))+'\n');raise SystemExit(40)
    if p.returncode:raise SystemExit('Failed '+name+'; preserve logs')
base=[repo/'src/photonhash.c',repo/'src/photonhash_launch.c',*sorted((ref/'src').glob('*.c')),lab/'src/bank_openssl.c',S/'network_cache.c']
inc=['-I'+str(repo/'include'),'-I'+str(ref/'include'),'-I'+str(lab/'src'),'-I'+str(S)]
flags=['-std=c11','-Wall','-Wextra','-Werror','-fopenmp',*inc]
run('native-build',['gcc','-O3','-fPIC','-shared',*flags,*map(str,base),'-lcrypto','-o',str(B/'libnetwork_cache.so')])
run('native-fault-build',['gcc','-O1','-g','-fsanitize=address,undefined','-fno-omit-frame-pointer',*flags,*map(str,base),str(S/'cache_fault_test.c'),'-Wl,--wrap=malloc','-lcrypto','-o',str(B/'cache_fault_test')])
cases=[]
for line in (repo/'research/qualification/lf3-c20-2026-10-30/c20-experiment-vectors.txt').read_text().splitlines():
    if not line.startswith('case['):continue
    key,value=line.split('=',1);index=int(key[5:key.index(']')]);field=key.split('].',1)[1]
    if index==len(cases):cases.append({})
    cases[index][field]=value
if len(cases)!=560:raise SystemExit('Unexpected canonical set')
parents=[]
for parent in dict.fromkeys(c['parent'] for c in cases):
    chosen=min((c for c in cases if c['parent']==parent),key=lambda c:int.from_bytes(bytes.fromhex(c['digest']),'little'))
    target=(int.from_bytes(bytes.fromhex(chosen['digest']),'little')+1).to_bytes(32,'little').hex()
    parents.append(dict(parent=parent,target=target,legitimate_case=chosen))
(R/'fixtures.json').write_text(json.dumps(dict(scope='Trusted isolated startup fixtures, chosen from frozen canonical vectors; no live chain data',parents=parents),indent=2)+'\n')
backend=Backend(B/'libnetwork_cache.so',parents)
try:
    m=Metrics();backend.lib.nf_snapshot(backend.state,ctypes.byref(m));before=tuple(getattr(m,n) for n,_ in m._fields_)
    if backend.evaluate(bytes([0x37])*32+bytes(8))[0]!=2:raise SystemExit('Unknown-parent precheck failed')
    backend.lib.nf_snapshot(backend.state,ctypes.byref(m))
    if before!=tuple(getattr(m,n) for n,_ in m._fields_):raise SystemExit('Unknown parent changed native cache')
    for i,c in enumerate(cases):
        d=ctypes.create_string_buffer(32);h=ctypes.create_string_buffer(32);f=ctypes.create_string_buffer(2048);header=bytes.fromhex(c['header'])
        rc=backend.lib.nf_eval(backend.state,bytes.fromhex(c['parent']),header,len(header),int(c['nonce']),d,h,f)
        target=next(x['target'] for x in parents if x['parent']==c['parent'])
        expected_rc=int(int.from_bytes(bytes.fromhex(c['digest']),'little')<int.from_bytes(bytes.fromhex(target),'little'))
        if d.raw.hex()!=c['digest'] or h.raw.hex()!=c['h'] or f.raw.hex()!=c['fold'] or rc!=expected_rc:
            (E/'STOP.json').write_text(json.dumps(dict(reason='Canonical native cache trace or target mismatch',case=i))+'\n');raise SystemExit(40)
    backend.lib.nf_snapshot(backend.state,ctypes.byref(m))
    if m.resident>2 or m.high_water>2 or m.coefficient_bytes>268435456:raise SystemExit('Cache bound violated')
    (E/'native-conformance.json').write_text(json.dumps(dict(passed=True,canonical_full_traces_measured=560,parent_classes_measured=len(parents),target_comparisons_measured=560,unknown_parent_zero_work=True,native_metrics_measured={n:getattr(m,n) for n,_ in m._fields_}),indent=2)+'\n')
finally:backend.close()
run('native-allocation-faults-sanitized',[str(B/'cache_fault_test')],240)
(E/'native-source-provenance.json').write_text(json.dumps(dict(sources=[dict(path=str(x.relative_to(R)),SHA256_measured=hashlib.sha256(x.read_bytes()).hexdigest()) for x in base+[S/'cache_fault_test.c',S/'verifier_server.py']],gcc_measured=subprocess.check_output(['gcc','--version'],text=True).splitlines()[0],OpenSSL_measured=subprocess.check_output(['openssl','version'],text=True).strip()),indent=2)+'\n')
print('NATIVE_CACHE_QUALIFICATION_COMPLETE',flush=True)
