import os
"""Finite TCP transport conformance, canonical target statuses and frame coalescing."""
import json,pathlib,socket,subprocess,sys,time
R=pathlib.Path(os.environ.get('LF3_STAGE1_ROOT','/workspace/lf3-stage1'));S=R/'src';E=R/'evidence';sys.path.insert(0,str(S))
from network_load import connect,frame,recv_exact
if (E/'STOP.json').exists():raise SystemExit(40)
out=E/'network-wire-001';out.mkdir(exist_ok=False)
fixtures=json.loads((R/'fixtures.json').read_text());targets={p['parent']:int.from_bytes(bytes.fromhex(p['target']),'little') for p in fixtures['parents']}
cases=[]
for line in (R/'public-source/research/qualification/lf3-c20-2026-10-30/c20-experiment-vectors.txt').read_text().splitlines():
    if not line.startswith('case['):continue
    key,value=line.split('=',1);i=int(key[5:key.index(']')]);field=key.split('].',1)[1]
    if i==len(cases):cases.append({})
    cases[i][field]=value
with (out/'server.log').open('x') as log:
    server=subprocess.Popen([sys.executable,str(S/'verifier_server.py'),'--library',str(R/'build/libnetwork_cache.so'),'--fixtures',str(R/'fixtures.json'),'--evidence',str(out/'server'),'--seconds','90'],stdout=log,stderr=subprocess.STDOUT)
    try:
        for _ in range(200):
            if (out/'server/ready.json').exists():break
            if server.poll() is not None:raise RuntimeError('Startup failed')
            time.sleep(.05)
        counts={};start=time.monotonic()
        with connect('127.0.0.1',19090,None,timeout=20) as client:
            for i,c in enumerate(cases):
                request=frame(c)
                for piece in [request[:1],request[1:7],request[7:9],request[9:]]:client.sendall(piece)
                response=recv_exact(client,33);expected=int(int.from_bytes(bytes.fromhex(c['digest']),'little')<targets[c['parent']])
                if response[0]!=expected or response[1:].hex()!=c['digest']:
                    (E/'STOP.json').write_text(json.dumps(dict(reason='Canonical TCP digest/target mismatch',case=i))+'\n');raise SystemExit(40)
                counts[str(expected)]=counts.get(str(expected),0)+1
            c=fixtures['parents'][0]['legitimate_case'];client.sendall(frame(c)*16)
            for i in range(16):
                response=recv_exact(client,33)
                if response[0]!=1 or response[1:].hex()!=c['digest']:
                    (E/'STOP.json').write_text('{"reason":"Coalesced frame digest/target mismatch"}\n');raise SystemExit(40)
        elapsed=time.monotonic()-start;time.sleep(.2);(out/'server/STOP.json').write_text('{"reason":"bounded wire conformance complete"}\n');code=server.wait(timeout=20)
        result=dict(passed=code==0,canonical_TCP_responses_measured=len(cases),strict_target_status_counts_measured=counts,coalesced_valid_frames_measured=16,header_lengths_bytes_configured=sorted({len(bytes.fromhex(c['header'])) for c in cases}),elapsed_s_measured=elapsed,server_exit_code=code)
        (out/'receipt.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
        if code:raise SystemExit(1)
    finally:
        if server.poll() is None:server.terminate();server.wait(timeout=10)
