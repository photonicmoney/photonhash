import os
"""Fixed full-capacity liveness stress: 16 sources, 64 connections, no reserved lane."""
import json,pathlib,subprocess,sys,time
R=pathlib.Path(os.environ.get('LF3_STAGE1_ROOT','/workspace/lf3-stage1'));E=R/'evidence';S=R/'src';out=E/'network-saturated-001';out.mkdir(exist_ok=False)
if (E/'STOP.json').exists():raise SystemExit(40)
with (out/'server.log').open('x') as log:
    server=subprocess.Popen([sys.executable,str(S/'verifier_server.py'),'--library',str(R/'build/libnetwork_cache.so'),'--fixtures',str(R/'fixtures.json'),'--evidence',str(out/'server'),'--seconds','155'],stdout=log,stderr=subprocess.STDOUT)
    try:
        for _ in range(200):
            if (out/'server/ready.json').exists():break
            if server.poll() is not None:raise RuntimeError('Startup failed')
            time.sleep(.05)
        with (out/'clients.log').open('x') as clientlog:client=subprocess.run([sys.executable,str(S/'network_load.py'),'--host','127.0.0.1','--port','19090','--fixtures',str(R/'fixtures.json'),'--out',str(out/'clients.json'),'--mode','saturated','--seconds','120','--ack-owned-target'],stdout=clientlog,stderr=subprocess.STDOUT,timeout=148)
        time.sleep(1);(out/'server/STOP.json').write_text('{"reason":"bounded full-capacity phase complete"}\n');code=server.wait(timeout=25)
        summary=json.loads((out/'server/server-summary.json').read_text());n=summary['native_measured'];h=summary['high_water_measured']
        passed=client.returncode==code==0 and h['connections']==64 and h['sources']==16 and h['pending']<=64 and n['high_water']==2 and n['coefficient_bytes']<=268435456 and summary['rss_peak_KiB_measured']<=524288
        result=dict(passed=passed,server_exit_code=code,client_exit_code=client.returncode,full_capacity_reached_measured=h['connections']==64 and h['sources']==16,fixed_duration_s_configured=120,legitimate_clients_configured=4,hostile_clients_configured=60)
        (out/'receipt.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
        if client.returncode==40:(E/'STOP.json').write_text('{"reason":"Full-capacity correctness stop"}\n');raise SystemExit(40)
        if not passed:raise SystemExit(1)
    finally:
        if server.poll() is None:server.terminate();server.wait(timeout=10)
