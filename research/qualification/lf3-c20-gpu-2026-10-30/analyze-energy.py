"""RAW STATISTICS ONLY. Legacy completion flag is not qualification; see post-review-qualification.json. No GPU calls; no local execution."""
import argparse,json,math,pathlib
import numpy as np
prefix='remote-energy-confirmation-paced50-retry2'
p=argparse.ArgumentParser();p.add_argument('--partial',action='store_true');p.add_argument('--evidence',type=pathlib.Path,required=True);p.add_argument('--output',type=pathlib.Path,required=True);args=p.parse_args();root=args.evidence
if args.output.exists():raise SystemExit('Refusing analysis output overwrite')
def rows(path):
 result=[]
 for line in path.read_text().splitlines():
  try:result.append(json.loads(line))
  except ValueError:pass
 return result
def summarize(values,seed=0xC200):
 a=np.array(values,float);n=len(a);m=float(np.median(a));rng=np.random.default_rng(seed)
 # Circular moving-block bootstrap, three adjacent ~20-event-second blocks.
 starts=rng.integers(0,n,size=(4000,math.ceil(n/3)))
 indices=((starts[:,:,None]+np.arange(3))%n).reshape(4000,-1)[:,:n]
 boot=np.median(a[indices],axis=1)
 return {'n_blocks_measured':n,'median_measured':m,'MAD_measured':float(np.median(np.abs(a-m))),'min_measured':float(a.min()),'max_measured':float(a.max()),'median_95CI_inferred_from_measured_blocks':np.quantile(boot,[.025,.975]).tolist(),'bootstrap':'4000 circular moving-block resamples; span 3; conditional on this run; excludes sensor bias'}
output={'scope':'Nominal 50% GPU-event duty; gross GPU board energy includes per-window idle inside each block, excludes bank setup and validation outside blocks. Not sustained unpaced or PSU/CPU energy.','sensor':'10-Hz continuous NVML instantaneous power trapezoids; continuously sampled energy counter is a cross-check. Driver-reported sensor accuracy is not established by a statistical CI.','confirmation_complete':False,'variants':[]}
for choice in range(5):
 name=f'{prefix}-{choice}-001';log=root/(name+'.log');samples=root/(name+'-nvml.jsonl');receipt=root/(name+'.receipt.json')
 if not log.exists() or not samples.exists():
  if args.partial:continue
  raise RuntimeError('Missing variant '+name)
 passed=receipt.exists() and json.loads(receipt.read_text())['passed_process']
 if not args.partial and not passed:raise RuntimeError('Incomplete or failed '+name)
 data=rows(log);ss=[r for r in rows(samples) if r.get('type')=='nvml_sample']
 if not all(r.get('field_instant_status')==0 and r.get('field_instant_valueType')==1 for r in ss):raise RuntimeError('Invalid instantaneous telemetry')
 ts=np.array([r['monotonic'] for r in ss]);power=np.array([r['power_instant_mW_measured']/1000 for r in ss]);average=np.array([r['power_average_mW_measured']/1000 for r in ss]);counter=np.array([r['energyCounter_mJ_measured']/1000 for r in ss])
 if np.any(np.diff(ts)<=0):raise RuntimeError('Non-monotonic telemetry')
 def energy(a,b):
  if not ts[0]<=a<b<=ts[-1]:raise RuntimeError('Block outside telemetry')
  inside=ts[(ts>a)&(ts<b)];xx=np.r_[a,inside,b]
  return float(np.trapezoid(np.interp(xx,ts,power),xx)),float(np.interp(b,ts,counter)-np.interp(a,ts,counter)),float(np.trapezoid(np.interp(xx,ts,average),xx))
 starts={(r['condition'],r['block']):r for r in data if r.get('type')=='energy_block_begin'}
 ends=[r for r in data if r.get('type')=='energy_block_end'];windows=[r for r in data if r.get('type')=='event_window']
 variant={'name':next(r['name'] for r in data if r.get('type')=='confirmation_design'),'passed_process':passed,'sample_count_measured':len(ss),'max_sampling_gap_s_measured':float(np.diff(ts).max()),'power_limit_W_measured':sorted(set(r['powerLimit_mW_measured']/1000 for r in ss)),'conditions':[]}
 for condition in ['cold_start','warm']:
  blocks=[]
  for end in [r for r in ends if r['condition']==condition]:
   key=(condition,end['block']);begin=starts[key];a=begin['host_monotonic_measured'];b=end['host_monotonic_measured'];J,counterJ,averageJ=energy(a,b);count=end['correct_evaluations_counted'];ww=[r for r in windows if (r['condition'],r['block'])==key];st=np.array([r['last_graph_stage_ms_measured'] for r in ww]);selected=[s for s in ss if a<=s['monotonic']<=b]
   blocks.append({'block_input':end['block'],'event_seconds_measured':end['event_ms_measured']/1000,'wall_seconds_measured':b-a,'evaluations_counted_measured':count,'board_J_integrated_from_measured':J,'counter_J_continuously_sampled_measured':counterJ,'counter_difference_fraction_measured':(J-counterJ)/counterJ,'board_uJ_per_evaluation_measured':J/count*1e6,'counter_uJ_per_evaluation_measured':counterJ/count*1e6,'event_evaluations_s_measured':count/(end['event_ms_measured']/1000),'paced_elapsed_evaluations_s_measured':count/(b-a),'GEMM_plus_epilogue_share_measured':float(np.median(st[:,1]/st[:,4])),'GEMM_plus_epilogue_ms_per_batch_measured':float(np.median(st[:,1])),'separate_fold_ms_per_batch_measured':float(np.median(st[:,2])),'binding_expansion_ms_per_batch_measured':float(np.median(st[:,0])),'final_ms_per_batch_measured':float(np.median(st[:,3])),'temperature_min_C_measured':min(s['temperature_C_measured'] for s in selected),'temperature_max_C_measured':max(s['temperature_C_measured'] for s in selected),'sm_clock_min_MHz_measured':min(s['smClock_MHz_measured'] for s in selected),'sm_clock_max_MHz_measured':max(s['smClock_MHz_measured'] for s in selected),'memory_clock_min_MHz_measured':min(s['memoryClock_MHz_measured'] for s in selected),'memory_clock_max_MHz_measured':max(s['memoryClock_MHz_measured'] for s in selected)})
   blocks[-1]['average_power_uJ_per_evaluation_measured']=averageJ/count*1e6
   blocks[-1]['average_vs_counter_difference_fraction_measured']=(averageJ-counterJ)/counterJ
  if not blocks:continue
  complete=[r for r in data if r.get('type')=='condition_complete' and r['condition']==condition]
  if not args.partial and (not complete or sum(r['event_seconds_measured'] for r in blocks)<600):raise RuntimeError('Insufficient event windows')
  entry={'condition':condition,'complete':bool(complete),'event_seconds_measured':sum(r['event_seconds_measured'] for r in blocks),'wall_seconds_measured':sum(r['wall_seconds_measured'] for r in blocks),'evaluations_counted_measured':sum(r['evaluations_counted_measured'] for r in blocks),'temperature_range_C_measured':[min(r['temperature_min_C_measured'] for r in blocks),max(r['temperature_max_C_measured'] for r in blocks)],'sm_clock_range_MHz_measured':[min(r['sm_clock_min_MHz_measured'] for r in blocks),max(r['sm_clock_max_MHz_measured'] for r in blocks)],'memory_clock_range_MHz_measured':[min(r['memory_clock_min_MHz_measured'] for r in blocks),max(r['memory_clock_max_MHz_measured'] for r in blocks)],'blocks_measured':blocks}
  for metric in ['board_uJ_per_evaluation_measured','counter_uJ_per_evaluation_measured','average_power_uJ_per_evaluation_measured','counter_difference_fraction_measured','average_vs_counter_difference_fraction_measured','event_evaluations_s_measured','paced_elapsed_evaluations_s_measured','GEMM_plus_epilogue_share_measured','GEMM_plus_epilogue_ms_per_batch_measured','separate_fold_ms_per_batch_measured','binding_expansion_ms_per_batch_measured','final_ms_per_batch_measured']:
   entry[metric]=summarize([r[metric] for r in blocks])
  share=entry['GEMM_plus_epilogue_share_measured'];entry['composite_Amdahl_ceiling_inferred']={'point':1/(1-share['median_measured']),'95CI_inferred_from_measured_share':[1/(1-x) for x in share['median_95CI_inferred_from_measured_blocks']],'assumption':'Entire composite stage becomes free, no added conversion, transfer or coordination cost; time only, not energy.'}
  variant['conditions'].append(entry)
 variant['cold_start_qualified_measured']=json.loads((root/(name+'-cooldown.json')).read_text())['cold_start_qualified'];output['variants'].append(variant)
if args.partial:
 quality=[{'name':v['name'],'sampling_gap_max_s_measured':v['max_sampling_gap_s_measured'],'conditions':[{'condition':c['condition'],'completed_blocks_measured':len(c['blocks_measured']),'counter_discrepancy_fraction_measured_summary':c['counter_difference_fraction_measured'],'average_power_vs_counter_discrepancy_fraction_measured_summary':c['average_vs_counter_difference_fraction_measured'],'temperature_range_C_measured':c['temperature_range_C_measured']} for c in v['conditions']]} for v in output['variants']]
 args.output.write_text(json.dumps(quality,indent=2));print(json.dumps(quality,indent=2))
else:
 output['confirmation_complete']=True
 args.output.write_text(json.dumps(output,indent=2));print(json.dumps({'passed':True,'variants_measured':len(output['variants'])}))
