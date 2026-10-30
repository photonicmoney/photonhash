import os
"""Fixed local TCP scenarios on the remote CPU pod. Not a live Laser node."""
import json,os,pathlib,subprocess,sys,time
R=pathlib.Path(os.environ.get('LF3_STAGE1_ROOT','/workspace/lf3-stage1'));E=R/'evidence';S=R/'src';py=sys.executable
if (E/'STOP.json').exists():raise SystemExit(40)
if not json.loads((E/'native-conformance.json').read_text())['passed'] or not json.loads((E/'native-allocation-faults-sanitized.receipt.json').read_text())['passed_process']:raise SystemExit('Native qualification prerequisite missing')
deadline=json.loads((R/'control/remote-guard-ready.json').read_text())['deadline_unix']
for mode,seconds in [('cold',10),('junk_only',10),('baseline',60),('junk',60),('slow',60),('churn',60),('shared',60)]:
    if time.time()>deadline-180:raise SystemExit('Insufficient guarded time')
    out=E/('network-'+mode+'-001');out.mkdir(exist_ok=False)
    serverlog=(out/'server.log').open('x');server=subprocess.Popen([py,str(S/'verifier_server.py'),'--library',str(R/'build/libnetwork_cache.so'),'--fixtures',str(R/'fixtures.json'),'--evidence',str(out/'server'),'--seconds',str(seconds+35)],stdout=serverlog,stderr=subprocess.STDOUT,cwd=R)
    try:
        wait=time.monotonic()
        while not (out/'server/ready.json').exists():
            if server.poll() is not None or time.monotonic()-wait>20:raise RuntimeError('Server did not start; retain log')
            time.sleep(.05)
        with (out/'clients.log').open('x') as clientlog:run=subprocess.run([py,str(S/'network_load.py'),'--host','127.0.0.1','--port','19090','--fixtures',str(R/'fixtures.json'),'--out',str(out/'clients.json'),'--mode',mode,'--seconds',str(seconds),'--ack-owned-target'],stdout=clientlog,stderr=subprocess.STDOUT,timeout=seconds+28)
        time.sleep(1);(out/'server/STOP.json').write_text('{"reason":"bounded phase complete"}\n');code=server.wait(timeout=25)
        receipt=dict(passed_process=run.returncode==0 and code==0,client_exit_code=run.returncode,server_exit_code=code,mode_configured=mode)
        if run.returncode==40 or (out/'STOP.json').exists():
            (E/'STOP.json').write_text(json.dumps(dict(reason='Network correctness stop',phase=mode))+'\n');raise SystemExit(40)
        summary=json.loads((out/'server/server-summary.json').read_text());native=summary['native_measured']
        if mode=='junk_only':receipt['zero_native_work']=not native or native.get('derivations',0)==native.get('verifications',0)==0
        if mode=='cold':receipt['one_bank_for_simultaneous_identical_parent']=native.get('derivations')==1 and native.get('verifications')==32
        receipt['bounds_passed']=summary['high_water_measured'].get('connections',0)<=64 and summary['high_water_measured'].get('sources',0)<=16 and summary['high_water_measured'].get('pending',0)<=64 and native.get('high_water',0)<=2 and native.get('coefficient_bytes',0)<=268435456 and summary['rss_peak_KiB_measured']<=512*1024
        receipt['passed']=receipt['passed_process'] and receipt['bounds_passed'] and receipt.get('zero_native_work',True) and receipt.get('one_bank_for_simultaneous_identical_parent',True)
        (out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt),flush=True)
        if not receipt['passed']:raise SystemExit('Phase failed; retain data, no automatic replacement')
    finally:
        if server.poll() is None:server.terminate();server.wait(timeout=10)
        serverlog.close()
(E/'network-local-complete.json').write_text(json.dumps(dict(passed=True,phases_measured=7,scope='Actual remote-host loopback TCP with controlled source addresses; cross-machine evidence is separate'))+'\n')
