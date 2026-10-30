"""Remote CPU analysis only. Requalify raw telemetry before admitting a run."""
import argparse,json,math,pathlib
import numpy as np
from telemetry_guard import qualify_samples
from field_freshness import check as check_field_freshness
E=pathlib.Path(__file__).resolve().parent.parent/'evidence';prefix='server-confirmation'
p=argparse.ArgumentParser();p.add_argument('--partial',action='store_true');p.add_argument('--evidence',type=pathlib.Path,default=E);args=p.parse_args();E=args.evidence.resolve()
if not E.is_dir() or (E/'STOP.json').exists():raise SystemExit('Required evidence unavailable or STOP set')
def rows(path):
    result=[]
    for line in path.read_text().splitlines():
        try:result.append(json.loads(line))
        except ValueError:pass
    return result
def stat(values):
    a=np.asarray(values,dtype=float);n=len(a)
    if not n or not np.isfinite(a).all():raise ValueError('Invalid measured statistic')
    median=float(np.median(a));rng=np.random.default_rng(0xc200)
    starts=rng.integers(0,n,size=(4000,math.ceil(n/3)))
    ix=((starts[:,:,None]+np.arange(3))%n).reshape(4000,-1)[:,:n]
    boot=np.median(a[ix],axis=1)
    return dict(n_blocks_measured=n,median_measured=median,MAD_measured=float(np.median(abs(a-median))),min_measured=float(a.min()),max_measured=float(a.max()),median_95CI_inferred_from_measured_blocks=np.quantile(boot,[.025,.975]).tolist(),bootstrap='4000 circular moving-block resamples, span 3; within-run sampling only, excludes sensor calibration and host-population uncertainty')
output=dict(scope='Full unpaced, fresh-nonce complete pipeline at unchanged provider-reported 165 W GPU-board limit. Board energy includes launch/idle gaps within blocks; CPU, PSU, setup and between-block validation excluded.',hardware_cohort='RTX PRO 4500 Blackwell Server Edition; not an RTX 5090 repetition',sensor='10-Hz NVML instantaneous-power trapezoidal integration; sampled average power and energy counter are cross-checks, not independent calibrated instruments.',confirmation_complete=False,variants=[])
trap=getattr(np,'trapezoid',None) or np.trapz
for choice in range(5):
    name=f'{prefix}-{choice}-001';qp=E/(name+'-qualification.json')
    if not qp.exists():
        if args.partial:continue
        raise RuntimeError('Missing qualification '+name)
    saved=json.loads(qp.read_text());receipt=json.loads((E/(name+'.receipt.json')).read_text());data=rows(E/(name+'.log'));ss=rows(E/(name+'-nvml.jsonl'));cold=json.loads((E/(name+'-cooldown.json')).read_text())
    starts={(r['condition'],r['block']):r for r in data if r.get('type')=='energy_block_begin'}
    ends=[r for r in data if r.get('type')=='energy_block_end'];windows=[]
    for end in ends:
        begin=starts[(end['condition'],end['block'])]
        windows.append(dict(condition=end['condition'],begin=begin['host_monotonic_measured'],end=end['host_monotonic_measured'],event_seconds=end['event_ms_measured']/1000,correct_evaluations_counted=end['correct_evaluations_counted']))
    q=qualify_samples(ss,windows,process_ok=receipt['passed_process'],cold_ok=cold['cold_start_qualified'],conformance_ok=json.loads((E/'gpu-conformance-ready.json').read_text())['passed'],required_event_seconds=600)
    complete=[r for r in data if r.get('type')=='condition_complete' and r.get('passed') is True]
    validations=[r for r in data if r.get('type')=='validation']
    if not saved['qualified'] or not q['qualified'] or not saved['confirmation_eligible'] or len(complete)!=2 or not validations or not all(r.get('passed') is True for r in validations):raise RuntimeError('Disqualified run '+name+' '+json.dumps(q))
    freshness=check_field_freshness(ss)
    if not freshness['passed_metadata_bound']:raise RuntimeError('Stale NVML field metadata; withhold energy qualification '+name)
    ts=np.array([s['monotonic'] for s in ss]);power=np.array([s['power_instant_mW_measured']/1000 for s in ss])
    counter_ok=all(s.get('energyCounter_status')==0 and math.isfinite(s.get('energyCounter_mJ_measured',math.nan)) for s in ss)
    average_ok=all(s.get('field_average_status')==0 and s.get('field_average_valueType')==1 and math.isfinite(s.get('power_average_mW_measured',math.nan)) for s in ss)
    counter=np.array([s['energyCounter_mJ_measured']/1000 for s in ss]) if counter_ok else None
    average=np.array([s['power_average_mW_measured']/1000 for s in ss]) if average_ok else None
    if np.any(np.diff(ts)<=0) or (counter_ok and np.any(np.diff(counter)<0)):raise RuntimeError('Non-monotonic telemetry/counter')
    def integrate(a,b,watts):
        if not ts[0]<=a<b<=ts[-1]:raise RuntimeError('Integration outside telemetry')
        x=np.r_[a,ts[(ts>a)&(ts<b)],b]
        return float(trap(np.interp(x,ts,watts),x))
    v=dict(choice_configured=choice,name=next(r['name'] for r in data if r.get('type')=='confirmation_design'),qualification_recomputed=q,qualification_saved=saved,power_limit_W_measured=sorted(set(s['powerLimit_mW_measured']/1000 for s in ss)),counter_supported=counter_ok,average_supported=average_ok,validation_records_measured=len(validations),GPU_reference_full_fold_cases_measured=sum(r['full_batch_fold_cases_measured'] for r in validations),C_reference_full_fold_cases_measured=sum(r['CPU_full_fold_cases_measured'] for r in validations),conditions=[])
    v['NVML_field_timestamp_freshness_measured']=freshness
    for condition in ['cold_start','warm']:
        blocks=[]
        for w in [w for w in windows if w['condition']==condition]:
            a,b=w['begin'],w['end'];key=next(k for k,s in starts.items() if s['host_monotonic_measured']==a)
            ww=[r for r in data if r.get('type')=='event_window' and (r['condition'],r['block'])==key]
            if sum(r['correct_evaluations_counted'] for r in ww)!=w['correct_evaluations_counted']:raise RuntimeError('Denominator inconsistency')
            st=np.array([r['last_graph_stage_ms_measured'] for r in ww]);selected=[s for s in ss if a<=s['monotonic']<=b]
            count=w['correct_evaluations_counted'];J=integrate(a,b,power)
            z=dict(block_configured=key[1],event_seconds_measured=w['event_seconds'],wall_seconds_measured=b-a,evaluations_counted_measured=count,board_J_integrated_from_measured=J,board_uJ_per_evaluation_measured=J/count*1e6,event_evaluations_s_measured=count/w['event_seconds'],elapsed_evaluations_s_measured=count/(b-a),GEMM_plus_epilogue_share_measured=float(np.median(st[:,1]/st[:,4])),GEMM_plus_epilogue_ms_per_batch_measured=float(np.median(st[:,1])),separate_fold_ms_per_batch_measured=float(np.median(st[:,2])),binding_expansion_ms_per_batch_measured=float(np.median(st[:,0])),final_ms_per_batch_measured=float(np.median(st[:,3])),temperature_range_C_measured=[min(s['temperature_C_measured'] for s in selected),max(s['temperature_C_measured'] for s in selected)],sm_clock_range_MHz_measured=[min(s['smClock_MHz_measured'] for s in selected),max(s['smClock_MHz_measured'] for s in selected)],memory_clock_range_MHz_measured=[min(s['memoryClock_MHz_measured'] for s in selected),max(s['memoryClock_MHz_measured'] for s in selected)])
            if counter_ok:
                cj=float(np.interp(b,ts,counter)-np.interp(a,ts,counter))
                if cj<=0:raise RuntimeError('Non-positive energy cross-check')
                z.update(counter_J_continuously_sampled_measured=cj,counter_uJ_per_evaluation_measured=cj/count*1e6,instant_vs_counter_difference_fraction_measured=(J-cj)/cj)
            if average_ok:
                aj=integrate(a,b,average);z['average_power_uJ_per_evaluation_measured']=aj/count*1e6
                if counter_ok:z['average_vs_counter_difference_fraction_measured']=(aj-cj)/cj
            blocks.append(z)
        c=dict(condition=condition,blocks_measured=blocks,event_seconds_measured=sum(b['event_seconds_measured'] for b in blocks),wall_seconds_measured=sum(b['wall_seconds_measured'] for b in blocks),evaluations_counted_measured=sum(b['evaluations_counted_measured'] for b in blocks))
        reported=next(r for r in complete if r['condition']==condition)
        if c['evaluations_counted_measured']!=reported['correct_evaluations_counted']:raise RuntimeError('Condition denominator inconsistency')
        for metric in ['board_uJ_per_evaluation_measured','counter_uJ_per_evaluation_measured','average_power_uJ_per_evaluation_measured','instant_vs_counter_difference_fraction_measured','average_vs_counter_difference_fraction_measured','event_evaluations_s_measured','elapsed_evaluations_s_measured','GEMM_plus_epilogue_share_measured','GEMM_plus_epilogue_ms_per_batch_measured','separate_fold_ms_per_batch_measured','binding_expansion_ms_per_batch_measured','final_ms_per_batch_measured']:
            if all(metric in b for b in blocks):c[metric]=stat([b[metric] for b in blocks])
        for metric in ['temperature_range_C_measured','sm_clock_range_MHz_measured','memory_clock_range_MHz_measured']:
            c[metric]=[min(b[metric][0] for b in blocks),max(b[metric][1] for b in blocks)]
        share=c['GEMM_plus_epilogue_share_measured'];c['composite_Amdahl_ceiling_inferred']=dict(point=1/(1-share['median_measured']),CI95_inferred=[1/(1-s) for s in share['median_95CI_inferred_from_measured_blocks']],assumption='Entire composite matrix/epilogue stage becomes free; no added conversion/transfer/coordination cost. Time-only thought experiment, not energy or photonic prediction.')
        v['conditions'].append(c)
    output['variants'].append(v)
output['confirmation_complete']=len(output['variants'])==5
target=E/('server-energy-partial.json' if args.partial else 'server-energy-summary.json')
target.write_text(json.dumps(output,indent=2)+'\n')
print(json.dumps(dict(confirmation_complete=output['confirmation_complete'],qualified_variants_measured=len(output['variants']),warm=[dict(name=v['name'],uJ=v['conditions'][1]['board_uJ_per_evaluation_measured']['median_measured'],counter_bias=v['conditions'][1].get('instant_vs_counter_difference_fraction_measured',{}).get('median_measured')) for v in output['variants']])))
