"""Analyze remote measured CPU logs. Conditional, moving-block uncertainty."""
import collections,json,math,os,pathlib,random,statistics as st
root=pathlib.Path(os.environ.get('LF3_REPRO_ROOT','/workspace/lf3-followup'))
if not root.is_dir():raise SystemExit('Remote workspace required')
def summary(a,seed=0xC200):
    med=st.median(a);rng=random.Random(seed);n=len(a);boot=[]
    for _ in range(2000):
        starts=[rng.randrange(n) for _ in range(math.ceil(n/3))]
        b=[a[(start+j)%n] for start in starts for j in range(3)][:n]
        boot.append(st.median(b))
    boot.sort()
    return dict(n_measured=n,median_measured=med,MAD_measured=st.median(abs(x-med) for x in a),median_95CI_inferred=[boot[49],boot[1950]],uncertainty='2000 circular moving-block resamples, span 3; conditional on this host/run; not hardware-population uncertainty')
rows=[json.loads(x) for x in (root/'evidence/cpu-bench.jsonl').read_text().splitlines()]
if rows[-1].get('type')!='complete':raise SystemExit('Incomplete CPU benchmark')
affinity=sorted(os.sched_getaffinity(0))
topology={str(c):{'core':pathlib.Path(f'/sys/devices/system/cpu/cpu{c}/topology/core_id').read_text().strip(),'package':pathlib.Path(f'/sys/devices/system/cpu/cpu{c}/topology/physical_package_id').read_text().strip()} for c in affinity}
out={'hardware_scope':'CPU-only cloud allocation; not a laptop or low-power physical-machine benchmark. Actual affinity/topology recorded below.','affinity_measured':affinity,'topology_measured':topology,'variant_order_configured':['portable','OpenSSL-1-worker','OpenSSL-2-workers'],'work_scope':'All 8 full matrices, retained seeds and raw-stream checksums; 128 MiB expanded bank. Timings include allocation. Serial parent-dependent headers; no bank reuse on cold path.','variants':[]}
for v in range(3):
    cold=[r for r in rows if r.get('type')=='serial_parent_step' and r['variant']==v]
    cached=[r for r in rows if r.get('type')=='cached_verify' and r['variant']==v]
    q={'variant':out['variant_order_configured'][v]}
    for k in ['bank_wall_s_measured','bank_cpu_s_measured','cold_wall_s_measured','cold_cpu_s_measured']:
        q[k]=summary([r[k] for r in cold])
    q['cached_wall_s_measured']=summary([r['wall_s_measured'] for r in cached])
    q['header_sync_inferred']=[]
    for interval in [10,30,60,150]:
        q['header_sync_inferred'].append({'block_interval_s_configured':interval,'headers_per_365_day_year_inferred':31536000/interval,'elapsed_days_per_chain_year_inferred':365*q['cold_wall_s_measured']['median_measured']/interval,'cpu_days_per_chain_year_inferred':365*q['cold_cpu_s_measured']['median_measured']/interval,'bank_fraction_of_block_time_inferred':q['bank_wall_s_measured']['median_measured']/interval,'limits':'Hash-only serial projection; excludes network, storage, signatures, state and fork work. Uses measured median on this host; not a measured chain sync.'})
    out['variants'].append(q)
(root/'evidence/cpu-statistics.json').write_text(json.dumps(out,indent=2)+'\n')
for q in out['variants']:
    print(json.dumps({'variant':q['variant'],'bank_median_s_measured':q['bank_wall_s_measured']['median_measured'],'cold_median_s_measured':q['cold_wall_s_measured']['median_measured'],'cached_median_s_measured':q['cached_wall_s_measured']['median_measured'],'days_at_10s_inferred':q['header_sync_inferred'][0]['elapsed_days_per_chain_year_inferred']}))
