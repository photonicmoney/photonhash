"""Reviewer's noise experiment extended to scale and nonzero parents. Remote.
Noise experiments measure fold validity, not a photonic miner's energy.
"""
import os
os.environ['OPENBLAS_NUM_THREADS']='2'
os.environ['OMP_NUM_THREADS']='2'
import hashlib,importlib.util,json,math,pathlib,time
import numpy as np
import argparse
parser=argparse.ArgumentParser(description='CPU probability experiment; no physical analog energy measurement')
parser.add_argument('--checker',type=pathlib.Path,default=pathlib.Path(__file__).resolve().parents[3]/'independent/py-c20/ph_indep.py')
parser.add_argument('--reviewer-experiment',type=pathlib.Path,default=pathlib.Path(__file__).with_name('reviewer-approx.py'))
parser.add_argument('--output',type=pathlib.Path,required=True)
parser.add_argument('--nonces',type=int,default=1024)
args=parser.parse_args()
if args.nonces<4:raise SystemExit('Use at least four nonces; qualification requires at least 1000')
s=importlib.util.spec_from_file_location('reviewer',args.checker)
ph=importlib.util.module_from_spec(s);s.loader.exec_module(ph)
T=args.nonces;N=4096;PASSES=8;header=b'LF3-C20/nonzero-parent-approximation-qualification.1'
output=args.output
if output.exists():raise SystemExit('Refusing approximation evidence overwrite')
def wilson(k,n):
 z=1.959963984540054;p=k/n;den=1+z*z/n;c=(p+z*z/(2*n))/den;d=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/den
 return [max(0,c-d),min(1,c+d)]
def quant(y):return ((y.astype(np.int64)>>9)&15).astype(np.uint8)
def entropy(a):
 p=np.bincount(a.ravel(),minlength=16).astype(float);p=p[p>0]/a.size
 return float(-(p*np.log2(p)).sum())
def expected_rounded_gaussian_abs(sigma):
 # E|round(N(0,sigma))| = sum_{k>=1} P(|noise| >= k-0.5).
 return sum(math.erfc((k-.5)/(sigma*math.sqrt(2))) for k in range(1,100))
def sigma_for(p):
 wanted=-math.log(p)/64;lo=.0001;hi=2.
 for _ in range(80):
  m=(lo+hi)/2
  if expected_rounded_gaussian_abs(m)>wanted:hi=m
  else:lo=m
 return (lo+hi)/2
tolerance=[{'winning_blocks_lost_fraction_inferred':loss,
 'P_exact_required_inferred':1-loss,'pm1_rate_inferred':-math.log(1-loss)/64,
 'rounded_gaussian_sigma_inferred':sigma_for(1-loss)} for loss in [.1,.5,.9]]
def record(log,d):log.write(json.dumps(d)+'\n');log.flush();print(json.dumps({k:v for k,v in d.items() if k not in ['histogram_measured']}),flush=True)
with output.open('x') as log:
 record(log,{'type':'approximation_design','nonces_per_parent_inferred_input':T,'parents_inferred_input':2,'qualification_sample_count_eligible':T>=1000,
  'header_hex_inferred_input':header.hex(),'nonce_range_inferred_input':[0,T-1],
  'stop_rule':'Stop/report demonstrated work-avoiding energy/correct-fold advantage; representation gains are hardware economics. Conformance failures invalidate results and block freeze.',
  'reviewer_original_sha256_measured':hashlib.sha256(args.reviewer_experiment.read_bytes()).hexdigest(),
  'model_inferred':'P approximately exp(-sum E|integer error|/512); independent small phase-unbiased errors, with XOR cancellation neglected; not a security bound.',
  'energy_scope':'Probability experiment only. No analog/noisy miner energy measured. Normalized energy=1 is an optimistic model for injecting errors after the same exact work, excluding injection overhead. Physical noisy-hardware criterion remains conditional on actual energy.',
  'tolerance_inferred':tolerance})
 for parent_index in range(2):
  parent=hashlib.shake_256(b'LF3-C20/approximation-nonzero-parent.1'+bytes([parent_index])).digest(32)
  rng=np.random.default_rng(0xC2030000+parent_index);start=time.monotonic()
  mats,_=ph.bank(parent)
  X=np.empty((N,T),np.float32)
  for n in range(T):_,x=ph.vector('C20',header,n);X[:,n]=x
  Y=np.empty((T,PASSES,N),np.int32)
  for j,M in enumerate(mats):
   result=M@X
   if not np.isfinite(result).all() or not np.equal(result,np.rint(result)).all():
    raise RuntimeError('Conformance failure: exact CPU float32 integer partial sums not integral')
   Y[:,j,:]=result.T.astype(np.int32)
  Q=quant(Y);F=np.bitwise_xor.reduce(Q,axis=1)
  for n in [0,1,T-1]:
   _,_,fold,_,qs=ph.evaluate('C20',mats,header,n,keep=True)
   packed=(F[n,0::2]|(F[n,1::2]<<4)).tobytes()
   if packed!=fold or not np.array_equal(Q[n],np.stack(qs)):
    raise RuntimeError('Conformance failure: batched exact sums differ from original reviewer evaluator')
  record(log,{'type':'approximation_parent','parent_index_inferred_input':parent_index,'parent_hex_inferred_input':parent.hex(),
   'nonces_measured':T,'skipped_cases_measured':0,'per_pass_entropy_bits_measured':[entropy(Q[:,j,:]) for j in range(PASSES)],
   'fold_entropy_bits_measured':entropy(F),'sum_mean_measured':float(Y.mean()),'sum_sd_measured':float(Y.std()),
   'residue512_histogram_measured':np.bincount((Y&511).ravel(),minlength=512).tolist(),
   'exact_y_SHA256_measured':hashlib.sha256(Y.tobytes()).hexdigest(),'exact_generation_wall_s_measured':time.monotonic()-start})
  def assess(name,make,energy_model,applicable=True,extra=None):
   ok=0;abs_error=0.;models=[]
   for n in range(T):
    yp=make(n,Y[n]);qp=quant(yp);fp=np.bitwise_xor.reduce(qp,axis=0)
    ok+=int(np.array_equal(fp,F[n]))
    e=float(np.abs(yp.astype(np.float64)-Y[n]).sum());abs_error+=e
    if applicable:models.append(math.exp(-e/512))
   p=ok/T;ci=wilson(ok,T)
   ratio=energy_model.get('normalized_energy_ratio_inferred')
   decision='OPEN: physical energy unmeasured' if ratio is None else 'ahead under stated model' if ratio<p else 'not ahead under stated model'
   record(log,{'type':'approximation_result','parent_index_inferred_input':parent_index,'error_model':name,
    'nonces_measured':T,'skipped_cases_measured':0,'exact_folds_measured':ok,'P_exact_fold_measured':p,
    'P_exact_fold_95CI_inferred_from_measured':ci,'mean_sum_absolute_error_measured':abs_error/T,
    'P_exp_of_mean_L1_inferred':math.exp(-abs_error/T/512) if applicable else None,
    'P_mean_exp_of_L1_inferred':float(np.mean(models)) if applicable else None,
    'model_applicability_inferred':applicable,'energy_model_inferred':energy_model,
    'break_even_energy_ratio_inferred':p,
    'criterion_result_under_energy_model_inferred':decision,
    'physical_noisy_hardware_criterion':'OPEN until energy of a real method is measured or justified',
    **(extra or {})})
   if name.startswith('drop_nonzero_products') and ratio is not None and ratio<p:
    finding={'type':'STOP','reason':'modeled_work_avoiding_advantage_requires_immediate_review','error_model':name,'P_measured':p,'energy_ratio_inferred':ratio,'energy_assumptions':energy_model}
    record(log,finding)
    raise SystemExit(40)
  exact_injection={'normalized_energy_ratio_inferred':1.,'basis':'same exact computation plus error injection; overhead excluded, so optimistic for this harness','criterion_inferred':'does not beat exact evaluation because P<=1'}
  for f in sorted(set([.001,.005,.01,.02,.05]+[d['pm1_rate_inferred'] for d in tolerance])):
   def pm(n,y,f=f):return y+np.where(rng.random(y.shape)<f,rng.choice(np.array([-1,1],np.int32),size=y.shape),0)
   assess('pm1_rate_'+format(f,'.12g'),pm,exact_injection)
  for sigma in sorted(set([.25,.5,1.,2.]+[d['rounded_gaussian_sigma_inferred'] for d in tolerance])):
   assess('gaussian_nearest_integer_sigma_'+format(sigma,'.12g'),lambda n,y,ss=sigma:y+np.rint(rng.normal(0,ss,y.shape)).astype(np.int32),exact_injection)
  # Quantizer without half-integer decision calibration is intentionally
  # separate: integer sums can sit exactly at the raw analog threshold.
  for sigma in [.01,.25]:
   assess('gaussian_raw_floor_threshold_sigma_'+str(sigma),lambda n,y,ss=sigma:np.floor(y+rng.normal(0,ss,y.shape)),exact_injection,False,
    {'photonic_calibration_note':'No nearest-integer recovery; raw threshold at 512k. Do not substitute the rounded-noise tolerance.'})
  for bits in [1,4,8,9,10]:
   assess('truncate_final_sum_low_bits_'+str(bits),lambda n,y,b=bits:(y>>b)<<b,exact_injection,False,
    {'classification':'post-exact transformation; bits<=9 preserve every quantized nibble, not a work-saving algorithm'})
  # Work-skipping attacks: remove nonzero products of small magnitude. The
  # matrix work count is measured; the energy model assumes perfect pruning,
  # zero scheduling overhead and ALL energy proportional to retained MACs.
  # This is deliberately favorable to the attacker, not measured GPU energy.
  Bs={a:((X==a).astype(np.float32)-(X==-a).astype(np.float32)) for a in [1,2,3,4]}
  for threshold in [1,2,4]:
   error=np.zeros_like(Y);removed=0
   for j,M in enumerate(mats):
    ey=np.zeros((N,T),np.float32)
    for a in range(1,threshold+1):
     select=(np.abs(M)<=threshold//a)
     ey+=a*((M*select)@Bs[a])
     # Count nonzero skipped terms; zero terms carry no approximation error.
     rows=np.count_nonzero(select & (M!=0),axis=0).astype(np.uint64)
     cols=np.count_nonzero((X==a)|(X==-a),axis=1).astype(np.uint64)
     removed+=int(rows@cols)
    error[:,j,:]=ey.T.astype(np.int32)
   saving=removed/(T*PASSES*N*N)
   assess('drop_nonzero_products_abs_le_'+str(threshold),lambda n,y,e=error:y-e[n],
     {'normalized_energy_ratio_inferred':1-saving,'basis':'optimistic ALL-energy-proportional-to-nonzero-MAC count, no pruning overhead; excludes any baseline zero skipping','nonzero_products_removed_measured':removed,'fraction_MACs_removed_measured':saving},True)
  # Reduced precision after every 64-term exact chunk, not merely final cast.
  # FP16 and saturating accumulator variants keep every scalar product.
  approximations={k:np.zeros_like(Y) for k in ['fp16_round_each_64_terms','signed12_saturate_each_64_terms','signed13_saturate_each_64_terms']}
  for j,M in enumerate(mats):
   af=np.zeros((N,T),np.float32);a12=np.zeros((N,T),np.float32);a13=np.zeros((N,T),np.float32)
   for col in range(0,N,64):
    partial=M[:,col:col+64]@X[col:col+64]
    af=(af+partial).astype(np.float16).astype(np.float32)
    a12=np.clip(a12+partial,-2048,2047);a13=np.clip(a13+partial,-4096,4095)
   for key,a in [('fp16_round_each_64_terms',af),('signed12_saturate_each_64_terms',a12),('signed13_saturate_each_64_terms',a13)]:approximations[key][:,j,:]=a.T.astype(np.int32)
  for name,a in approximations.items():
   assess(name,lambda n,y,a=a:a[n],{'normalized_energy_ratio_inferred':None,'basis':'all products retained; no mapped circuit or GPU implementation power measured; cannot infer joules from bit width'},True)
  for bits in [12,13,16,20]:
   assess('exact_signed_wrap_accumulator_'+str(bits),lambda n,y,b=bits:((y+(1<<(b-1)))&((1<<b)-1))-(1<<(b-1)),
    {'normalized_energy_ratio_inferred':None,'basis':'exact arithmetic representation for bits>=13; hardware-economics category, no silicon energy measured'},False,
    {'classification':'exact representation, not approximation or shortcut' if bits>=13 else 'insufficient accumulator residue width'})
  del mats,X,Y,Q,F
 record(log,{'type':'complete','parents_measured':2,'nonces_per_parent_measured':T,'skipped_cases_measured':0,'energy_shortcut_demonstrated':False,
   'conclusion':'No measured energy advantage established by synthetic noise probabilities. Photonic break-even energy must be < P_exact_fold times exact energy; approximate device qualification remains OPEN.'})
