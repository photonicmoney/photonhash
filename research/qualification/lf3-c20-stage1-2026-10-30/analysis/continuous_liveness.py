"""Check continuous-window coverage directly from raw client completion times. MIT."""
import json,pathlib,sys
root=pathlib.Path(sys.argv[1]);result={}
for path in sorted((root/'evidence').glob('network-*/clients.json')):
    data=json.loads(path.read_text());seconds=data['duration_s_configured']
    if seconds<21 or data['mode_configured'] in ['cold','junk_only','attack_only']:continue
    clients=[]
    for r in data['records']:
        if r['role']!='legitimate':continue
        x=r['completion_offsets_s_measured']
        if x!=sorted(x):raise SystemExit('Non-monotonic completions')
        interior=[v for v in x if 1<=v<=seconds-1]
        edges=[1,*interior,seconds-1];gap=max(b-a for a,b in zip(edges,edges[1:]))
        clients.append(dict(client=r['client'],maximum_interior_gap_s_measured=gap,continuous_interior_20s_coverage_measured=bool(interior) and gap<=20))
    result[path.parent.name]=dict(all_legitimate_clients_covered_measured=bool(clients) and all(r['continuous_interior_20s_coverage_measured'] for r in clients),clients=clients)
summary=dict(method='Filter completion offsets to [1,duration-1], add endpoints 1 and duration-1, require every consecutive gap <=20 s. This covers every real-valued 20 s window with start in [1,duration-21], not only the driver integer-grid smoke check.',scenarios=result)
(root/'evidence/continuous-liveness.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary))
expected_failure='network-cross-001'
if any(not r['all_legitimate_clients_covered_measured'] for name,r in result.items() if name!=expected_failure):raise SystemExit(1)
