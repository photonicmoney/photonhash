"""Replay instrumented diagnostic observations; no device queries or workloads."""
import argparse,json,math,pathlib
import numpy as np
p=argparse.ArgumentParser();p.add_argument('--records',type=pathlib.Path,required=True);p.add_argument('--output',type=pathlib.Path,required=True);args=p.parse_args()
if args.output.exists():raise SystemExit('Refusing analysis output overwrite')
def stat(values):
 a=np.asarray(values,float);n=len(a);m=float(np.median(a));rng=np.random.default_rng(0xC20)
 starts=rng.integers(0,n,(4000,math.ceil(n/3)));idx=((starts[:,:,None]+np.arange(3))%n).reshape(4000,-1)[:,:n]
 return {'n_measured':n,'median_measured':m,'MAD_measured':float(np.median(abs(a-m))),'min_measured':float(a.min()),'max_measured':float(a.max()),'median_95CI_inferred_from_measured_samples':np.quantile(np.median(a[idx],axis=1),[.025,.975]).tolist(),'CI_scope':'4000 circular moving-block resamples, span 3; conditional on this shared host/run, not physical-machine variability'}
rr=json.loads(args.records.read_text());probe={'scope':'Separate instrumented CTA/warp-0 timing. Mma loop includes operand loads and synchronization; wall-time attribution is inferred, not pure math wall time. Production long-run composite timings are separate.','trials_measured':30,'full_fold_checks_measured':sum(r['full_fold_checks_measured'] for r in rr),'mappings':{}}
for passes in [1,8]:
 a=[r for r in rr if r['passes_per_CTA_inferred_input']==passes];probe['mappings'][str(passes)]={field:stat([r[field] for r in a]) for field in ['instrumented_kernel_ms_measured','warp0_Mma_cycles_median_measured','warp0_CTA_cycles_median_measured','warp0_Mma_fraction_measured','Mma_attributed_kernel_ms_inferred']}
 attributed=probe['mappings'][str(passes)]['Mma_attributed_kernel_ms_inferred']
 for key in list(attributed):
  if key!='n_measured' and key.endswith('_measured'):attributed[key[:-9]+'_inferred_from_measured_cycles']=attributed.pop(key)
paired={p:{r['trial_inferred_input']:r for r in rr if r['passes_per_CTA_inferred_input']==p} for p in [1,8]}
probe['paired_fused_over_control_kernel_ratio_measured']=stat([paired[8][i]['instrumented_kernel_ms_measured']/paired[1][i]['instrumented_kernel_ms_measured'] for i in range(30)])
probe['paired_per_pass_Mma_cycle_ratio_measured']=stat([paired[8][i]['warp0_Mma_cycles_median_measured']/paired[1][i]['warp0_Mma_cycles_median_measured'] for i in range(30)])
args.output.write_text(json.dumps(probe,indent=2))
