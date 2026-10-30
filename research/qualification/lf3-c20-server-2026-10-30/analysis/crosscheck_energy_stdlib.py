"""Independent stdlib integration control. No NumPy, GPU or CI estimation."""
import bisect,json,math,pathlib,statistics,sys
from telemetry_guard import qualify_samples
from field_freshness import check as fresh
E=pathlib.Path(__file__).resolve().parent.parent/'evidence';complete='--complete' in sys.argv
if (E/'STOP.json').exists():raise SystemExit('STOP is set')
def rows(p):
    result=[]
    for line in p.read_text().splitlines():
        try:result.append(json.loads(line))
        except ValueError:pass
    return result
output=dict(scope='Independent standard-library trapezoid integration of the same observed telemetry; no independent calibrated sensor and no confidence intervals',variants=[])
for v in range(5):
    name=f'server-confirmation-{v}-001';qp=E/(name+'-qualification.json')
    if not qp.exists():
        if complete:raise SystemExit('Incomplete variant')
        continue
    if not json.loads(qp.read_text())['qualified']:raise SystemExit('Unqualified variant')
    d=rows(E/(name+'.log'));ss=rows(E/(name+'-nvml.jsonl'));starts={(r['condition'],r['block']):r for r in d if r.get('type')=='energy_block_begin'};windows=[]
    for end in [r for r in d if r.get('type')=='energy_block_end']:
        a=starts[(end['condition'],end['block'])]['host_monotonic_measured'];b=end['host_monotonic_measured']
        windows.append(dict(condition=end['condition'],begin=a,end=b,event_seconds=end['event_ms_measured']/1000,correct_evaluations_counted=end['correct_evaluations_counted']))
    q=qualify_samples(ss,windows,process_ok=json.loads((E/(name+'.receipt.json')).read_text())['passed_process'],cold_ok=json.loads((E/(name+'-cooldown.json')).read_text())['cold_start_qualified'],conformance_ok=True)
    if not q['qualified'] or not fresh(ss)['passed_metadata_bound']:raise SystemExit('Raw evidence requalification failed')
    ts=[s['monotonic'] for s in ss];power=[s['power_instant_mW_measured']/1000 for s in ss]
    counter=[s['energyCounter_mJ_measured']/1000 for s in ss] if all(s.get('energyCounter_status')==0 for s in ss) else None
    def interp(t,values):
        i=bisect.bisect_left(ts,t)
        if i==0:return values[0]
        if i==len(ts):return values[-1]
        return values[i-1]+(values[i]-values[i-1])*(t-ts[i-1])/(ts[i]-ts[i-1])
    entry=dict(choice_configured=v,conditions=[])
    for condition in ['cold_start','warm']:
        blocks=[]
        for w in [w for w in windows if w['condition']==condition]:
            a,b=w['begin'],w['end'];i=bisect.bisect_right(ts,a);j=bisect.bisect_left(ts,b);xx=[a,*ts[i:j],b];yy=[interp(a,power),*power[i:j],interp(b,power)]
            energy=math.fsum((xx[k+1]-xx[k])*(yy[k]+yy[k+1])/2 for k in range(len(xx)-1));z=dict(board_uJ_per_evaluation_measured=energy/w['correct_evaluations_counted']*1e6)
            if counter is not None:
                cj=interp(b,counter)-interp(a,counter);z.update(counter_uJ_per_evaluation_measured=cj/w['correct_evaluations_counted']*1e6,instant_vs_counter_difference_fraction_measured=(energy-cj)/cj)
            blocks.append(z)
        result=dict(condition=condition,blocks_measured=len(blocks))
        for metric in blocks[0]:result[metric+'_median_measured']=statistics.median(b[metric] for b in blocks)
        entry['conditions'].append(result)
    output['variants'].append(entry)
if complete:
    main=json.loads((E/'server-energy-summary.json').read_text())
    for v,m in zip(output['variants'],main['variants']):
        for c,mc in zip(v['conditions'],m['conditions']):
            for metric in ['board_uJ_per_evaluation_measured','counter_uJ_per_evaluation_measured']:
                if metric+'_median_measured' in c and abs(c[metric+'_median_measured']-mc[metric]['median_measured'])>1e-7:raise SystemExit('Integration controls disagree beyond 1e-7 microjoule arithmetic tolerance; no energy qualification')
    output['matches_primary_point_estimates_within_1e_minus7_microjoule_tolerance']=True
target=E/('server-energy-stdlib-complete.json' if complete else 'server-energy-stdlib-partial-001.json')
with target.open('x') as f:json.dump(output,f,indent=2)
print(json.dumps(output))
