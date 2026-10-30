"""Strict full-fold vector adapter for the unmodified external checker."""
import argparse
import importlib.util
import json
from pathlib import Path
import sys
import time

def main():
    p=argparse.ArgumentParser();p.add_argument('vectors',type=Path)
    p.add_argument('--dependency-path',type=Path)
    a=p.parse_args()
    if not __debug__:raise RuntimeError('run without -O; reviewer assertions must stay enabled')
    if a.dependency_path:sys.path.insert(0,str(a.dependency_path.resolve()))
    module_path=Path(__file__).with_name('ph_indep.py')
    spec=importlib.util.spec_from_file_location('reviewer_ph_indep',module_path)
    reviewer=importlib.util.module_from_spec(spec);spec.loader.exec_module(reviewer)
    fields={}
    for line in a.vectors.read_text().splitlines():
        if '=' in line:
            key,value=line.split('=',1)
            if key in fields:raise ValueError('duplicate field '+key)
            fields[key]=value
    if (fields.get('profile'),fields.get('n'),fields.get('passes'))!=('LF3-K8-C20-experiment.1','4096','8'):
        raise ValueError('wrong experiment vector profile')
    count=int(fields['cases'])
    if count<64:raise ValueError('fewer than required 64 cases')
    parent_previous=None;mats=None;derive=0.;evaluate=0.
    for case in range(count):
        prefix=f'case[{case}].'
        parent=bytes.fromhex(fields[prefix+'parent'])
        if len(parent)!=32:raise ValueError('parent length')
        if parent!=parent_previous:
            mats=None
            print(json.dumps({'type':'python_bank_begin','case':case}),flush=True)
            start=time.perf_counter();mats,_=reviewer.bank(parent);derive+=time.perf_counter()-start
            parent_previous=parent
        header=bytes.fromhex(fields[prefix+'header']);nonce=int(fields[prefix+'nonce'])
        start=time.perf_counter()
        h,_,fold,digest,_=reviewer.evaluate('C20',mats,header,nonce)
        evaluate+=time.perf_counter()-start
        for field,actual in [('h',h),('fold',fold),('digest',digest)]:
            if actual!=bytes.fromhex(fields[prefix+field]):
                print(json.dumps({'type':'STOP','reason':'implementation_mismatch','implementation':'Python','case':case,'field':field}),flush=True)
                return 40
        if case%8==7:print(json.dumps({'type':'python_vector_progress','cases_measured':case+1}),flush=True)
    print(json.dumps({'type':'complete','implementation':'Python-independent','cases_measured':count,
        'full_fold_checked':True,'passed':True,'derive_wall_s_measured_capped':derive,
        'evaluate_wall_s_measured_capped':evaluate}),flush=True)
    return 0

if __name__=='__main__':sys.exit(main())
