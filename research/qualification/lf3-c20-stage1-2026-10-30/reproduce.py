"""Opt-in standalone reproduction on an isolated rented Linux CPU machine. MIT."""
import json,os,pathlib,shutil,subprocess,sys,time
if os.environ.get('LF3_RESEARCH_ACK')!='1':raise SystemExit('Set LF3_RESEARCH_ACK=1 only on an authorized isolated research machine')
package=pathlib.Path(__file__).resolve().parent;repo=package.parents[2]
if len(sys.argv)!=2:raise SystemExit('Usage: reproduce.py /absolute/new/results-directory')
root=pathlib.Path(sys.argv[1])
if not root.is_absolute() or root==repo or repo in root.parents:raise SystemExit('Use a fresh absolute results directory outside the checkout')
root.mkdir(exist_ok=False)
for name in ['src','control','evidence','build']:(root/name).mkdir()
for name in ['network_cache.c','network_cache.h','cache_fault_test.c','verifier_server.py','network_load.py']:shutil.copyfile(package/'src'/name,root/'src'/name)
controls=['build_cpu.py','network_suite.py','network_capacity.py','network_wire.py','network_saturated.py']
for name in controls:shutil.copyfile(package/'control'/name,root/'control'/name)
(root/'public-source').symlink_to(repo,target_is_directory=True)
(root/'control/remote-guard-ready.json').write_text(json.dumps(dict(deadline_unix=time.time()+900,scope='Reproduction process deadline, not a cloud shutdown credential'))+'\n')
env=dict(os.environ,LF3_STAGE1_ROOT=str(root))
for name in controls:
    with (root/'evidence'/('reproduce-'+name+'.log')).open('x') as log:r=subprocess.run([sys.executable,str(root/'control'/name)],stdout=log,stderr=subprocess.STDOUT,env=env,timeout=600)
    if r.returncode:raise SystemExit('Failed '+name+'; retain results, do not replace the run')
print('PUBLIC_STANDALONE_REPRODUCTION_COMPLETE')
