"""Opt-in Linux CPU reproduction from the public research sources. MIT.
No GPU, Laser integration or activation. Eight distinct physical cores required.
"""
import argparse,json,os,pathlib,subprocess,time
p=argparse.ArgumentParser();p.add_argument('results',type=pathlib.Path);p.add_argument('--ack-research',action='store_true',required=True);p.add_argument('--repo',type=pathlib.Path);a=p.parse_args()
here=pathlib.Path(__file__).resolve().parent;repo=(a.repo or here.parents[3]).resolve();out=a.results
if os.name!='posix' or not out.is_absolute() or out.exists():raise SystemExit('Linux and a new absolute results directory required')
lab=repo/'research/qualification/lf3-c20-verifier-2026-10-30';ref=lab/'reference'
if not lab.is_dir():raise SystemExit('Public verifier follow-up sources required')
out.mkdir(parents=True);E=out/'evidence';B=out/'build';E.mkdir();B.mkdir()
allowed=sorted(os.sched_getaffinity(0));cores=[];seen=set();topology={}
for c in allowed:
    root=pathlib.Path(f'/sys/devices/system/cpu/cpu{c}/topology');key=(root.joinpath('physical_package_id').read_text().strip(),root.joinpath('core_id').read_text().strip());topology[str(c)]=key
    if key not in seen:cores.append(c);seen.add(key)
if len(cores)<8:raise SystemExit('Eight distinct allowed physical cores unavailable; no inferred scaling substituted')
cores=cores[:8];os.sched_setaffinity(0,set(cores))
env=dict(os.environ,OMP_NUM_THREADS='8',OMP_PLACES=','.join('{'+str(c)+'}' for c in cores),OMP_PROC_BIND='spread',OMP_DYNAMIC='FALSE',OMP_THREAD_LIMIT='8',OMP_WAIT_POLICY='PASSIVE',GOMP_SPINCOUNT='0',OPENBLAS_NUM_THREADS='1');env.pop('GOMP_CPU_AFFINITY',None)
def save(path,data):path.write_text(json.dumps(data,indent=2)+'\n')
save(E/'reproduction-design.json',dict(scope='Separate opt-in reproduction, not primary timing cohort or modest-machine evidence',CPU_model_measured=next(x.split(':',1)[1].strip() for x in pathlib.Path('/proc/cpuinfo').read_text().splitlines() if x.startswith('model name')),allowed_affinity_measured=allowed,topology_measured=topology,physical_core_cpu_ids_selected=cores,variant_order_configured=[0,1,2,4,8],runtime_configured={k:env[k] for k in ['OMP_NUM_THREADS','OMP_PLACES','OMP_PROC_BIND','OMP_DYNAMIC','OMP_THREAD_LIMIT','OMP_WAIT_POLICY','GOMP_SPINCOUNT']},gcc_version_measured=subprocess.check_output(['gcc','--version'],text=True).splitlines()[0],OpenSSL_version_measured=subprocess.check_output(['openssl','version'],text=True).strip()))
def run(name,cmd,limit=60):
    start=time.monotonic()
    with (E/(name+'.log')).open('x') as f:r=subprocess.run(['timeout','--signal=TERM','--kill-after=5',str(limit),*cmd],cwd=out,env=env,stdout=f,stderr=subprocess.STDOUT,timeout=limit+10)
    save(E/(name+'.receipt.json'),dict(passed_process=r.returncode==0,exit_code=r.returncode,wall_seconds_measured=time.monotonic()-start))
    if r.returncode:raise SystemExit(r.returncode if r.returncode==40 else 'Failed '+name+'; preserve its evidence')
flags=['gcc','-O3','-std=c11','-Wall','-Wextra','-Werror','-fopenmp','-I'+str(ref/'include'),'-I'+str(repo/'include'),'-I'+str(lab/'src')]
run('affinity-build',[*flags,str(here/'cpu_affinity_probe.c'),'-o',str(B/'affinity-probe')]);run('affinity-probe',[str(B/'affinity-probe')])
probe=[json.loads(x) for x in (E/'affinity-probe.log').read_text().splitlines() if x.startswith('{')]
for n in [1,2,4,8]:
    observed=[x for x in probe if x.get('workers_configured')==n];cpus=[x['CPU_measured'] for x in observed]
    if len(observed)!=n or len(set(cpus))!=n or not set(cpus).issubset(cores):raise SystemExit('Observed worker placement invalid')
objects=[]
for source in [repo/'src/photonhash.c',repo/'src/photonhash_launch.c',*sorted((ref/'src').glob('*.c')),lab/'src/bank_openssl.c']:
    target=B/(source.stem+'.o');run('build-'+source.stem,[*flags,'-c',str(source),'-o',str(target)]);objects.append(str(target))
for name in ['server_bank_conformance','cpu_scale_bench']:
    run('link-'+name,[*flags,str(here/(name+'.c')),*objects,'-lcrypto','-o',str(B/name)])
run('server-bank-conformance',[str(B/'server_bank_conformance'),str(repo/'research/qualification/lf3-c20-2026-10-30/c20-experiment-vectors.txt')],180)
run('server-cpu-scale',[str(B/'cpu_scale_bench')],240)
if (E/'STOP.json').exists():raise SystemExit(40)
for name in ['server-bank-conformance','server-cpu-scale']:
    data=[json.loads(x) for x in (E/(name+'.log')).read_text().splitlines() if x.startswith('{')]
    if not data or data[-1].get('type')!='complete':raise SystemExit('Incomplete '+name)
save(out/'publication-reproduction.json',dict(passed_process=True,canonical_vectors_measured=560,whole_bank_comparisons_measured=16,cross_variant_cold_fold_comparisons_measured=124,scope='Public CPU research reproduction only; no activation, low-power or energy claim'))
print('PUBLIC_CPU_SCALE_REPRODUCTION_COMPLETE')
