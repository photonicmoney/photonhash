"""Portable CPU-only analysis of stored secondary measurements."""
import json,math,pathlib,random,statistics
import numpy as np
from telemetry_guard import qualify_samples
from field_freshness import check as fresh
E=pathlib.Path(__file__).resolve().parent.parent/'evidence'
if (E/'STOP.json').exists():raise SystemExit('STOP set')
def rows(p):
    result=[]
    for line in p.read_text().splitlines():
        try:result.append(json.loads(line))
        except ValueError:pass
    return result
def stat(values,bootstrap=4000):
    a=np.asarray(values,float);n=len(a)
    if not n or not np.isfinite(a).all():raise SystemExit('Invalid measured statistic; withhold secondary result')
    med=float(np.median(a));rng=np.random.default_rng(0xc200)
    starts=rng.integers(0,n,size=(bootstrap,math.ceil(n/3)));ix=((starts[:,:,None]+np.arange(3))%n).reshape(bootstrap,-1)[:,:n];boot=np.median(a[ix],axis=1)
    return dict(n_blocks_or_samples_measured=n,median_measured=med,MAD_measured=float(np.median(abs(a-med))),median_95CI_inferred_from_measured=np.quantile(boot,[.025,.975]).tolist(),uncertainty=f'{bootstrap} circular moving-block resamples, span 3; conditional on this run, excludes sensor bias and host-population uncertainty')
trap=getattr(np,'trapezoid',None) or np.trapz
out=dict(stage_scope='Exploratory fixed validated vectors; 30 unpaced event seconds per variant, not 600-second confirmation. GEMM plus quantizing epilogue, including XOR for fused. Not pure GEMM or complete attempts. Board energy cannot be assigned to an internal arithmetic component by dividing this isolated result by full-pipeline energy.',stages=[])
if not json.loads((E/'server-stage-complete.json').read_text())['qualified_exploratory']:raise SystemExit('Stages incomplete')
for choice in range(5):
    name=f'server-stage-{choice}-001';saved=json.loads((E/(name+'-qualification.json')).read_text());d=rows(E/(name+'.log'));ss=rows(E/(name+'-nvml.jsonl'))
    q=qualify_samples(ss,[],process_ok=json.loads((E/(name+'.receipt.json')).read_text())['passed_process'],cold_ok=json.loads((E/(name+'-cooldown.json')).read_text())['cold_start_qualified'],conformance_ok=True,required_event_seconds=0)
    if not saved['qualified'] or not q['qualified'] or not fresh(ss)['passed_metadata_bound']:raise SystemExit('Stage telemetry invalid')
    ts=np.array([s['monotonic'] for s in ss]);power=np.array([s['power_instant_mW_measured']/1000 for s in ss]);counter=np.array([s['energyCounter_mJ_measured']/1000 for s in ss]) if all(s.get('energyCounter_status')==0 for s in ss) else None
    if np.any(np.diff(ts)<=0) or (counter is not None and (not np.isfinite(counter).all() or np.any(np.diff(counter)<0))):raise SystemExit('Non-monotonic stage telemetry or invalid counter; withhold result')
    starts={(r['condition'],r['block']):r for r in d if r.get('type')=='energy_block_begin'};blocks=[];previous=None
    for end in [r for r in d if r.get('type')=='energy_block_end']:
        key=(end['condition'],end['block']);a=starts[key]['host_monotonic_measured'];b=end['host_monotonic_measured'];count=end['correct_evaluations_counted'];ev=end['event_ms_measured']/1000
        if key[0]!='stage_only' or not ts[0]<=a<b<=ts[-1] or (previous is not None and a<previous) or not 0<ev<=b-a+.001 or count<=0:raise SystemExit('Stage window invalid')
        previous=b;ww=[r for r in d if r.get('type')=='event_window' and (r['condition'],r['block'])==key]
        if sum(r['correct_evaluations_counted'] for r in ww)!=count:raise SystemExit('Stage denominator inconsistency')
        x=np.r_[a,ts[(ts>a)&(ts<b)],b];J=float(trap(np.interp(x,ts,power),x));z=dict(block_configured=key[1],event_seconds_measured=ev,evaluations_counted_measured=count,wall_seconds_measured=b-a,board_uJ_per_stage_evaluation_measured=J/count*1e6,composite_stage_ms_per_batch_measured=float(np.median([w['last_graph_stage_ms_measured'][1] for w in ww])))
        if counter is not None:
            cj=float(np.interp(b,ts,counter)-np.interp(a,ts,counter))
            if cj<=0:raise SystemExit('Non-positive stage counter energy; withhold result')
            z.update(counter_uJ_per_stage_evaluation_measured=cj/count*1e6,instant_vs_counter_fraction_measured=(J-cj)/cj)
        blocks.append(z)
    if sum(b['event_seconds_measured'] for b in blocks)<30:raise SystemExit('Insufficient stage windows')
    complete=[r for r in d if r.get('type')=='condition_complete' and r.get('passed') is True];validations=[r for r in d if r.get('type')=='validation']
    if len(complete)!=1 or len(validations)!=len(blocks)+1 or not all(r['passed'] for r in validations):raise SystemExit('Stage validation incomplete')
    if complete[0]['correct_evaluations_counted']!=sum(b['evaluations_counted_measured'] for b in blocks):raise SystemExit('Stage completion denominator inconsistency')
    v=dict(choice_configured=choice,name=next(r['name'] for r in d if r.get('type')=='confirmation_design'),event_seconds_measured=sum(b['event_seconds_measured'] for b in blocks),blocks_measured=blocks,temperature_range_C_measured=[min(s['temperature_C_measured'] for s in ss),max(s['temperature_C_measured'] for s in ss)],sm_clock_range_MHz_measured=[min(s['smClock_MHz_measured'] for s in ss),max(s['smClock_MHz_measured'] for s in ss)],power_limit_W_measured=sorted(set(s['powerLimit_mW_measured']/1000 for s in ss)),field_timestamp_freshness_measured=fresh(ss))
    for metric in ['board_uJ_per_stage_evaluation_measured','counter_uJ_per_stage_evaluation_measured','instant_vs_counter_fraction_measured','composite_stage_ms_per_batch_measured']:
        if all(metric in b for b in blocks):v[metric]=stat([b[metric] for b in blocks])
    out['stages'].append(v)
cpu=rows(E/'server-cpu-scale.log');design=json.loads((E/'server-cpu-scale-design.json').read_text());conformance=rows(E/'server-bank-conformance.log')
if cpu[-1].get('type')!='complete' or conformance[-1].get('vectors_matched_measured')!=560 or conformance[-1].get('full_bank_comparisons_measured')!=16:raise SystemExit('CPU scaling conformance incomplete')
out['CPU_scope']=dict(scope='Separate shared-server allocation; not dedicated modest or low-power physical-machine evidence',design=design,full_fold_cross_variant_steps_measured=cpu[-1]['full_fold_cross_variant_steps_measured'],bank_conformance_summary_measured=conformance[-1],variants=[])
upload=rows(E/'server-parent-upload.log')
if upload[-1].get('passed') is not True or upload[-1].get('samples_measured')!=31:raise SystemExit('Transfer incomplete')
out['parent_upload']=dict(scope='Pageable expanded bank, eight copies totaling 128 MiB; context startup excluded, 31 repeats of an already-derived bank',host_wall_s_measured=stat([r['host_wall_s_measured'] for r in upload if r.get('type')=='parent_upload'],2000))
for v in [0,1,2,4,8]:
    cold=[r for r in cpu if r.get('type')=='serial_parent_step' and r['variant']==v];cached=[r for r in cpu if r.get('type')=='cached_verify' and r['variant']==v]
    if len(cold)!=31 or len(cached)!=64:raise SystemExit('CPU sample count incomplete')
    q=dict(workers_configured=v or 1,implementation='portable' if v==0 else 'OpenSSL',header_sync_and_turnover_inferred=[])
    for metric in ['bank_wall_s_measured','bank_cpu_s_measured','cold_wall_s_measured','cold_cpu_s_measured']:q[metric]=stat([r[metric] for r in cold],2000)
    q['cached_wall_s_measured']=stat([r['wall_s_measured'] for r in cached],2000)
    for seconds in [10,30,60,150]:
        q['header_sync_and_turnover_inferred'].append(dict(block_interval_s_configured=seconds,elapsed_days_per_chain_year_inferred=365*q['cold_wall_s_measured']['median_measured']/seconds,CPU_days_per_chain_year_inferred=365*q['cold_cpu_s_measured']['median_measured']/seconds,bank_plus_upload_s_inferred=q['bank_wall_s_measured']['median_measured']+out['parent_upload']['host_wall_s_measured']['median_measured'],bank_plus_upload_fraction_of_block_time_inferred=(q['bank_wall_s_measured']['median_measured']+out['parent_upload']['host_wall_s_measured']['median_measured'])/seconds,scope='Hash-only serial parent-dependent projection, not a measured chain sync or miner transition; no pipeline overlap assumed. Network, storage, signatures, state and forks excluded.'))
    out['CPU_scope']['variants'].append(q)
(E/'server-secondary-summary.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps(dict(passed=True,stage_variants_measured=len(out['stages']),CPU_variants_measured=len(out['CPU_scope']['variants']),stage_energy_uJ_measured=[v['board_uJ_per_stage_evaluation_measured']['median_measured'] for v in out['stages']],CPU_bank_seconds_measured=[v['bank_wall_s_measured']['median_measured'] for v in out['CPU_scope']['variants']])))
