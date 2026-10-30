import os
"""Server half of fixed cross-pod traffic test; external client receipt is separate."""
import json,pathlib,subprocess,sys,time
R=pathlib.Path(os.environ.get('LF3_STAGE1_ROOT','/workspace/lf3-stage1'));E=R/'evidence';S=R/'src';name=sys.argv[2] if len(sys.argv)==3 else 'network-cross-001'
if name not in ['network-cross-001','network-cross-002']:raise SystemExit('Unrecognized preserved trial label')
out=E/name;out.mkdir(exist_ok=False)
if (E/'STOP.json').exists():raise SystemExit(40)
start=float(sys.argv[1]);py=sys.executable
if not 5<start-time.time()<60:raise SystemExit('Require near-future synchronized start')
with (out/'server.log').open('x') as log:
    server=subprocess.Popen([py,str(S/'verifier_server.py'),'--library',str(R/'build/libnetwork_cache.so'),'--fixtures',str(R/'fixtures.json'),'--evidence',str(out/'server'),'--seconds','120'],stdout=log,stderr=subprocess.STDOUT)
    try:
        for _ in range(200):
            if (out/'server/ready.json').exists():break
            if server.poll() is not None:raise RuntimeError('Server startup failed')
            time.sleep(.05)
        else:raise RuntimeError('Server readiness timeout')
        with (out/'attackers.log').open('x') as attacklog:attack=subprocess.run([py,str(S/'network_load.py'),'--host','127.0.0.1','--port','19090','--fixtures',str(R/'fixtures.json'),'--out',str(out/'attackers.json'),'--mode','attack_only','--seconds','60','--start-unix',str(start),'--ack-owned-target'],stdout=attacklog,stderr=subprocess.STDOUT,timeout=110)
        time.sleep(2);(out/'server/STOP.json').write_text('{"reason":"bounded cross-pod phase complete"}\n');code=server.wait(timeout=25)
        summary=json.loads((out/'server/server-summary.json').read_text());native=summary['native_measured'];high=summary['high_water_measured']
        passed=code==attack.returncode==0 and high.get('connections',0)<=64 and high.get('sources',0)<=16 and high.get('pending',0)<=64 and native.get('high_water',0)<=2 and native.get('coefficient_bytes',0)<=268435456 and summary['rss_peak_KiB_measured']<=524288
        receipt=dict(server_and_attack_passed=passed,client_receipt_required=True,start_unix_configured=start,seconds_configured=60,server_exit_code=code,attack_exit_code=attack.returncode)
        (out/'server-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt))
        if attack.returncode==40:(E/'STOP.json').write_text('{"reason":"Cross-pod attacker correctness stop"}\n');raise SystemExit(40)
        if not passed:raise SystemExit(1)
    finally:
        if server.poll() is None:server.terminate();server.wait(timeout=10)
