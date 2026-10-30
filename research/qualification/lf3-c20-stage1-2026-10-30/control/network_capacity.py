import os
"""Negative control: slot exhaustion is a measured admission limit, not a pass claim."""
import json,pathlib,socket,subprocess,sys,time
R=pathlib.Path(os.environ.get('LF3_STAGE1_ROOT','/workspace/lf3-stage1'));S=R/'src';E=R/'evidence';sys.path.insert(0,str(S))
from network_load import connect,frame,recv_exact
out=E/'network-capacity-001';out.mkdir(exist_ok=False);held=[]
if (E/'STOP.json').exists():raise SystemExit(40)
fixture=json.loads((R/'fixtures.json').read_text());case=fixture['parents'][0]['legitimate_case']
with (out/'server.log').open('x') as log:
    server=subprocess.Popen([sys.executable,str(S/'verifier_server.py'),'--library',str(R/'build/libnetwork_cache.so'),'--fixtures',str(R/'fixtures.json'),'--evidence',str(out/'server'),'--seconds','45'],stdout=log,stderr=subprocess.STDOUT)
    try:
        for _ in range(200):
            if (out/'server/ready.json').exists():break
            if server.poll() is not None:raise RuntimeError('Startup failed')
            time.sleep(.05)
        records=[]
        for cycle in range(3):
            begin=time.monotonic()
            for i in range(64):held.append(connect('127.0.0.1',19090,f'127.60.0.{2+i//4}'))
            time.sleep(.25);refused=False
            try:
                with connect('127.0.0.1',19090,'127.61.0.2') as client:client.sendall(frame(case));recv_exact(client,33)
            except (OSError,EOFError):refused=True
            hold_s=time.monotonic()-begin
            for client in held:client.close()
            held.clear();time.sleep(.1);recover=time.monotonic()
            with connect('127.0.0.1',19090,'127.61.0.2',timeout=20) as client:
                client.sendall(frame(case));answer=recv_exact(client,33)
            if answer[0]!=1 or answer[1:].hex()!=case['digest']:
                (E/'STOP.json').write_text('{"reason":"Capacity recovery digest or target mismatch"}\n');raise SystemExit(40)
            records.append(dict(cycle_configured=cycle,held_connections_configured=64,universal_newcomer_liveness_failed_as_expected_measured=refused,hold_setup_s_measured=hold_s,recovery_s_measured=time.monotonic()-recover))
        time.sleep(.5);(out/'server/STOP.json').write_text('{"reason":"bounded negative control complete"}\n');code=server.wait(timeout=20)
        summary=json.loads((out/'server/server-summary.json').read_text());native=summary['native_measured'];high=summary['high_water_measured']
        passed=code==0 and all(r['universal_newcomer_liveness_failed_as_expected_measured'] for r in records) and high['connections']==64 and high['sources']==16 and native['derivations']==1 and native['verifications']==3 and native['high_water']==1 and summary['rss_peak_KiB_measured']<=524288
        result=dict(negative_control_passed=passed,universal_newcomer_guarantee='FAIL by design: no identity under finite unauthenticated slots',records=records,correct_recovery_responses_measured=3,server_exit_code=code)
        (out/'receipt.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
        if not passed:raise SystemExit(1)
    finally:
        for client in held:client.close()
        if server.poll() is None:server.terminate();server.wait(timeout=10)
