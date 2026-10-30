"""Remote-only deterministic reduction. No requests, benchmarks or CUDA calls."""
import collections,json,math,os,pathlib,random,statistics,sys
R=pathlib.Path(os.environ.get('LF3_STAGE1_ROOT','/workspace/lf3-stage1'));E=R/'evidence'
def read(path):return json.loads(path.read_text())
def reduce_matrix():
    receipt=read(E/'matrix-timing-001.receipt.json')
    if not receipt['passed_process']:raise SystemExit('Reject guarded run')
    records=[json.loads(s) for s in (E/'matrix-timing-001.log').read_text().splitlines() if s.startswith('{')]
    if any(r['type']=='STOP' for r in records):raise SystemExit(40)
    if sum(r['type']=='conformance' and r['passed'] for r in records)!=4 or not any(r['type']=='complete' and r['passed'] for r in records):raise SystemExit('Incomplete correctness')
    windows=collections.defaultdict(list);phases=collections.defaultdict(list)
    for r in records:
        if r['type']=='window':windows[r['kind_configured']].append(r)
        if r['type']=='CTA_phase':phases[r['kind_configured']].append(r)
    result=dict(status='Measured kernel/mainloop/epilogue spans; hardware tensor activity unavailable on this host',hardware_counters='OPEN: ERR_NVGPUCTRPERM despite query process exit 0',interpretation='Mainloop includes memory delivery, synchronization and stalls. CTA clock64 proportions are not GPU wall-time fractions. Observer changes barriers/register allocation; no pure multiply share or photonic Amdahl ceiling is inferred.',guard_receipt=receipt,conformance=[r for r in records if r['type']=='conformance'],kernels={})
    rng=random.Random(20261030)
    for kind in range(4):
        rows=windows[kind]
        if len(rows)!=20 or any(r['window_ms_measured']<100 for r in rows):raise SystemExit('Fixed minimum windows violated')
        x=[r['window_ms_measured']/r['repeats_configured'] for r in rows];median=statistics.median(x)
        clusters=[[r['window_ms_measured']/r['repeats_configured'] for r in rows if r['cycle_configured']==c] for c in range(10)]
        boot=sorted(statistics.median([v for i in (rng.randrange(10) for _ in range(10)) for v in clusters[i]]) for _ in range(10000))
        item=dict(windows_measured=len(x),event_seconds_measured=sum(r['window_ms_measured'] for r in rows)/1000,batch_ms_median_measured=median,batch_ms_MAD_measured=statistics.median(abs(v-median) for v in x),median_95pct_CI_ms_inferred=[boot[249],boot[9749]],CI_method='Fixed-seed percentile bootstrap of ten ABBA cycle clusters, 10000 resamples')
        if kind in phases:
            p=phases[kind];item['CTA_records_measured']=len(p)
            for field in ['mainloop_inclusive_cycles_measured','quant_fold_cycles_measured','epilogue_store_cycles_measured']:
                ratio=[100*r[field]/r['span_cycles_measured'] for r in p];item[field.replace('_cycles_measured','_span_percent_median_measured')]=statistics.median(ratio)
            sums={field:sum(r[field] for r in p) for field in ['span_cycles_measured','mainloop_inclusive_cycles_measured','quant_fold_cycles_measured','epilogue_store_cycles_measured']}
            item['aggregate_CTA_cycles_measured']=sums
            item['observer_event_overhead_percent_inferred']=100*(median/result['kernels'][str(kind-2)]['batch_ms_median_measured']-1)
        result['kernels'][str(kind)]=item
    (E/'matrix-statistics.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
def reduce_network():
    result=dict(scope='Isolated actual TCP service, not Laser network integration; role labels never sent',scenarios={})
    for name in ['cold','junk_only','baseline','junk','slow','churn','shared','cross-001','cross-002','capacity','wire','saturated']:
        out=E/('network-'+name+('' if name.startswith('cross-') else '-001'))
        if not out.exists():continue
        s=read(out/'server/server-summary.json');cpath=out/'clients.json';clients=read(cpath) if cpath.exists() else None
        r=dict(native_measured=s['native_measured'],counts_measured=s['counts_measured'],high_water_measured=s['high_water_measured'],rss_peak_KiB_measured=s['rss_peak_KiB_measured'])
        if clients:
            legit=[x for x in clients['records'] if x['role']=='legitimate'];hostile=[x for x in clients['records'] if x['role']=='hostile']
            if (out/'attackers.json').exists():hostile+=read(out/'attackers.json')['records']
            r.update(passed=clients['passed'],legitimate_completions_measured=sum(x['counts_measured'].get('valid_completed',0) for x in legit),maximum_client_p99_s_measured=max((x['p99_logical_latency_s_measured'] for x in legit if x['p99_logical_latency_s_measured'] is not None),default=None),legitimate_clients_measured=len(legit),hostile_responses_measured=sum(x['counts_measured'].get('responses',0) for x in hostile),all_clients_liveness_passed=all(x['liveness_passed'] for x in legit))
        if (out/'receipt.json').exists():r['receipt']=read(out/'receipt.json')
        result['scenarios'][name]=r
    result['liveness_scope']='Finite admitted sources/connections and functioning network/backend. Universal newcomer admission FAILS the documented capacity negative control; shared-NAT/Sybil/link saturation remain external integration concerns.'
    (E/'network-statistics.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
if sys.argv[1]=='matrix':reduce_matrix()
elif sys.argv[1]=='network':reduce_network()
else:raise SystemExit('Explicit reduction mode required')
