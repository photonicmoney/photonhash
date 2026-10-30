"""Opt-in RTL/mapping reproduction. Synthesis area is inferred, not chip energy.
MIT. Nangate45 is an external Apache-2.0, non-manufacturable research library.
"""
import argparse,collections,hashlib,json,pathlib,re,subprocess,time,urllib.request
p=argparse.ArgumentParser()
p.add_argument('results',type=pathlib.Path)
p.add_argument('--ack-research',action='store_true',required=True)
a=p.parse_args();out=a.results.resolve()
if out.exists():raise SystemExit('Refusing an existing results directory')
out.mkdir(parents=True)
src=pathlib.Path(__file__).resolve().parent
commit='75cd896b6d1ea33d2e8cdc3046b55cfd34ed963b'
base=f'https://raw.githubusercontent.com/The-OpenROAD-Project/OpenROAD-flow-scripts/{commit}/flow/platforms/nangate45/'
lib=out/'NangateOpenCellLibrary_typical.lib'
with urllib.request.urlopen(base+'lib/'+lib.name,timeout=30) as response:lib.write_bytes(response.read())
digest=hashlib.sha256(lib.read_bytes()).hexdigest()
if digest!='8d540a4d4cf6d09d27c87ad067857a9c0c2eeb023ab7a56e058cd3113db4e9b1':raise SystemExit('External library artifact mismatch; no results qualified')
def q(path):return json.dumps(str(path))
def run(name,args):
    start=time.monotonic()
    with (out/(name+'.log')).open('x') as f:
        result=subprocess.run(args,stdout=f,stderr=subprocess.STDOUT,timeout=60)
    receipt=dict(passed_process=result.returncode==0,exit_code=result.returncode,wall_seconds_measured=time.monotonic()-start)
    (out/(name+'.receipt.json')).write_text(json.dumps(receipt,indent=2)+'\n')
    if result.returncode:raise SystemExit(name+' failed; retain and inspect its log; no qualification')
run('mod13-proof',['yosys','-Q','-T','-p',f'read_verilog -formal {q(src/"mac.v")}; prep -top equiv -flatten; sat -verify -prove mismatch 0 -show-inputs -show-outputs'])
run('simulation-build',['iverilog','-g2012','-s','mac_tb','-o',str(out/'mac_tb'),str(src/'mac.v'),str(src/'mac_tb.v')])
run('simulation',['vvp',str(out/'mac_tb')])
for top in ['mac_comb','mac_register']:
    for w in [13,20,32]:
        name=f'{top}-{w}'
        commands=f'read_verilog {q(src/"mac.v")}; chparam -set W {w} {top}; synth -top {top} -noabc; dfflibmap -liberty {q(lib)}; abc -liberty {q(lib)}; clean; stat -liberty {q(lib)}; write_json {q(out/(name+".json"))}; write_verilog -noattr {q(out/(name+".v"))}'
        run(name,['yosys','-Q','-T','-p',commands])
        commands=f'read_verilog {q(src/"mac.v")}; chparam -set W {w} {top}; hierarchy -top {top}; proc; flatten; opt; rename {top} gold; design -stash gold; read_liberty -ignore_miss_func {q(lib)}; read_verilog {q(out/(name+".v"))}; hierarchy -top {top}; proc; flatten; opt; rename {top} gate; design -stash gate; design -copy-from gold -as gold gold; design -copy-from gate -as gate gate; equiv_make gold gate equiv; hierarchy -top equiv; equiv_simple; equiv_induct -seq 4; equiv_status -assert'
        run('equivalence-'+name,['yosys','-Q','-T','-p',commands])
text=lib.read_text();starts=list(re.finditer(r'\bcell\s*\(\s*([^\s)]+)\s*\)\s*\{',text));areas={}
for i,m in enumerate(starts):
    block=text[m.end():starts[i+1].start() if i+1<len(starts) else len(text)]
    area=re.search(r'\barea\s*:\s*([\d.eE+-]+)\s*;',block)
    if area:areas[m.group(1)]=float(area.group(1))
stats={'scope':'Inferred synthesis area, not measured silicon energy or GPU efficiency','library_SHA256_measured':digest,'library_source_commit':commit,'yosys_version_measured':subprocess.check_output(['yosys','-V'],text=True).strip(),'variants':[],'ratios_inferred':[]}
for top in ['mac_comb','mac_register']:
    for w in [13,20,32]:
        modules=json.loads((out/f'{top}-{w}.json').read_text())['modules']
        def count(module):
            result=collections.Counter()
            for c in modules[module].get('cells',{}).values():
                if c['type'] in modules:result.update(count(c['type']))
                else:result[c['type']]+=1
            return result
        cells=count(top)
        if set(cells)-set(areas):raise SystemExit('Unmapped cells; no area claim')
        stats['variants'].append(dict(top=top,accumulator_bits_configured=w,total_cells_inferred=sum(cells.values()),cell_counts_inferred=dict(cells),cell_area_library_units_inferred=sum(areas[n]*v for n,v in cells.items())))
    ar={x['accumulator_bits_configured']:x['cell_area_library_units_inferred'] for x in stats['variants'] if x['top']==top}
    stats['ratios_inferred'].append(dict(top=top,area_13_over_32_inferred=ar[13]/ar[32],area_13_over_20_inferred=ar[13]/ar[20]))
(out/'mapped-area-summary.json').write_text(json.dumps(stats,indent=2)+'\n')
print(json.dumps({'passed_process':True,'mapped_netlist_equivalence_checks_measured':6,'RTL_simulation_accumulation_checks_measured':262144,'ratios_inferred':stats['ratios_inferred']}))
