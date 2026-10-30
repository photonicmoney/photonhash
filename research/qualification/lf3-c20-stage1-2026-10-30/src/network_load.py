"""Bounded load against an explicitly authorized isolated test endpoint. MIT.
Client labels are for measurement only and never appear in the wire protocol.
"""
import argparse,collections,json,math,pathlib,socket,statistics,struct,threading,time
def frame(case):
    body=bytes.fromhex(case['parent'])+int(case['nonce']).to_bytes(8,'little')+bytes.fromhex(case['header'])
    return struct.pack('!4sI',b'L3N1',len(body))+body
def recv_exact(sock,size):
    data=bytearray()
    while len(data)<size:
        part=sock.recv(size-len(data))
        if not part:raise EOFError('connection closed')
        data.extend(part)
    return bytes(data)
def connect(host,port,source,timeout=3):
    sock=socket.socket();sock.settimeout(timeout)
    if source:sock.bind((source,0))
    sock.setsockopt(socket.IPPROTO_TCP,socket.TCP_NODELAY,1)
    try:sock.connect((host,port))
    except BaseException:sock.close();raise
    return sock
def main():
    p=argparse.ArgumentParser();p.add_argument('--host',required=True);p.add_argument('--port',type=int,required=True);p.add_argument('--fixtures',type=pathlib.Path,required=True);p.add_argument('--out',type=pathlib.Path,required=True);p.add_argument('--mode',choices=['cold','baseline','junk_only','junk','slow','churn','shared','remote','attack_only','saturated'],required=True);p.add_argument('--seconds',type=int,default=60);p.add_argument('--start-unix',type=float,default=0);p.add_argument('--ack-owned-target',action='store_true',required=True);a=p.parse_args()
    if not 5<=a.seconds<=120:raise SystemExit('Finite test duration required')
    if a.out.exists():raise SystemExit('Refuse evidence overwrite')
    fixture=json.loads(a.fixtures.read_text());parents=fixture['parents'];local=a.host=='127.0.0.1'
    if a.mode not in ['remote'] and not local:raise SystemExit('Only remote mode allows this explicitly configured external target')
    if a.mode in ['shared','slow','churn','junk','junk_only','attack_only','cold'] and not local:raise SystemExit('Controlled loopback source scenarios only')
    stop=threading.Event();lock=threading.Lock();records=[];mismatches=[];threads=[]
    while time.time()<a.start_unix:time.sleep(min(.1,a.start_unix-time.time()))
    begin=time.monotonic();end=begin+a.seconds
    def fail(detail):
        with lock:mismatches.append(detail)
        stop.set();a.out.parent.joinpath('STOP.json').write_text(json.dumps(dict(reason='Network correctness mismatch',detail=detail))+'\n')
    def legitimate(index,source,cold=False):
        case=parents[0 if cold else index%2]['legitimate_case'];request=frame(case);expected=bytes.fromhex(case['digest']);sock=None;counts=collections.Counter();times=[];latencies=[];submission=time.monotonic()
        try:
            while not stop.is_set() and time.monotonic()<end:
                try:
                    counts['wire_attempts']+=1
                    if sock is None:sock=connect(a.host,a.port,source)
                    sock.settimeout(max(.1,20-(time.monotonic()-submission)))
                    # Exercise a split prefix using the same public protocol.
                    sock.sendall(request[:3]);sock.sendall(request[3:]);response=recv_exact(sock,33)
                    if response[0] in [0,1]:
                        if response[0]!=1 or response[1:]!=expected:fail(dict(client=index,status=response[0],reason='canonical digest or strict target status differs'));break
                        now=time.monotonic();times.append(now-begin);latencies.append(now-submission);counts['valid_completed']+=1;submission=now
                        if cold:break
                    elif response[0] in [4,5]:counts['refused']+=1;sock.close();sock=None;stop.wait(.01)
                    else:fail(dict(client=index,status=response[0],reason='valid canonical wire request returned unexpected status'));break
                except (OSError,EOFError):
                    counts['transport_retries']+=1
                    if sock:sock.close();sock=None
                    if time.monotonic()-submission>=20:counts['submission_deadline_misses']+=1;submission=time.monotonic()
                    stop.wait(.01)
        finally:
            if sock:sock.close()
            with lock:records.append(dict(role='legitimate',client=index,counts_measured=dict(counts),completion_offsets_s_measured=times,logical_latency_s_measured=latencies))
    def hostile(index,source,kind):
        sock=None;counts=collections.Counter();number=0;next_send=begin
        try:
            while not stop.is_set() and time.monotonic()<end:
                try:
                    if sock is None:sock=connect(a.host,a.port,source)
                    sock.settimeout(20 if a.mode=='saturated' else 3)
                    if kind=='slow':
                        sock.sendall(b'L');counts['incomplete_connections']+=1
                        stop.wait(3.2);sock.close();sock=None;continue
                    if kind=='junk':
                        if number%3==0:request=struct.pack('!4sI',b'BAD!',0)
                        elif number%3==1:request=struct.pack('!4sI',b'L3N1',0xffffffff)
                        else:request=struct.pack('!4sI',b'L3N1',40)+bytes([0x37])*32+bytes(8)
                    else:
                        case=dict(parents[2+number%2]['legitimate_case']);case['nonce']=str((int(case['nonce'])+number+1)&((1<<64)-1));request=frame(case)
                    sock.sendall(request);response=recv_exact(sock,33);counts['responses']+=1;counts['status_'+str(response[0])]+=1;number+=1
                    if kind=='junk' and response[0] not in [2,3]:fail(dict(reason='malformed/unknown request was not rejected before hashing',status=response[0]));break
                    if kind=='junk' and response[1:]!=bytes(32):fail(dict(reason='pre-hash refusal exposed nonzero digest'));break
                    if kind=='junk':
                        if response[0]==3:sock.close();sock=None
                        next_send+=32/500;stop.wait(max(0,next_send-time.monotonic()))
                except (OSError,EOFError):
                    counts['transport_retries']+=1
                    if sock:sock.close();sock=None
                    stop.wait(.02)
        finally:
            if sock:sock.close()
            with lock:records.append(dict(role='hostile',client=index,kind=kind,counts_measured=dict(counts)))
    legit_count=0 if a.mode in ['junk_only','attack_only'] else (32 if a.mode=='cold' else 4)
    for i in range(legit_count):
        source=None if not local else ('127.80.0.2' if a.mode=='saturated' else (f'127.10.0.{2+i//4}' if a.mode=='cold' else ('127.30.0.2' if a.mode=='shared' and i<2 else f'127.20.0.{2+i}')))
        threads.append(threading.Thread(target=legitimate,args=(i,source,a.mode=='cold'),daemon=True))
    if a.mode in ['junk','junk_only','slow']:
        for i in range(32):threads.append(threading.Thread(target=hostile,args=(i,f'127.40.0.{2+i//4}','slow' if a.mode=='slow' else 'junk'),daemon=True))
    if a.mode in ['churn','attack_only']:
        for i in range(8):threads.append(threading.Thread(target=hostile,args=(i,f'127.50.0.{2+i}','churn'),daemon=True))
    if a.mode=='shared':
        for i in range(2):threads.append(threading.Thread(target=hostile,args=(i,'127.30.0.2','churn'),daemon=True))
    if a.mode=='saturated':
        for i in range(60):threads.append(threading.Thread(target=hostile,args=(i,f'127.90.0.{2+i//4}','churn'),daemon=True))
    for thread in threads:thread.start()
    for thread in threads:thread.join(max(0,end+22-time.monotonic()))
    if any(thread.is_alive() for thread in threads):stop.set();raise SystemExit('Driver did not drain within its finite deadline')
    passed=not mismatches and len([r for r in records if r['role']=='legitimate'])==legit_count
    for r in records:
        if r['role']!='legitimate':continue
        x=sorted(r['logical_latency_s_measured']);r['p99_logical_latency_s_measured']=x[min(len(x)-1,math.ceil(.99*len(x))-1)] if x else None
        if a.mode=='cold':r['liveness_passed']=r['counts_measured'].get('valid_completed',0)==1
        else:
            holes=[t for t in range(1,a.seconds-20) if not any(t<=v<=t+20 for v in r['completion_offsets_s_measured'])]
            r['empty_20s_interior_window_starts_measured']=holes
            r['liveness_passed']=not holes and bool(x) and r['p99_logical_latency_s_measured']<=20 and not r['counts_measured'].get('submission_deadline_misses',0)
        passed=passed and r['liveness_passed']
    result=dict(passed=passed,mode_configured=a.mode,duration_s_configured=a.seconds,elapsed_s_measured=time.monotonic()-begin,legitimate_clients_configured=legit_count,records=sorted(records,key=lambda r:(r['role'],r['client'])),mismatches=mismatches,wire_scope='Same protocol and scheduling for both roles; repeated canonical valid fixtures, no duplicate suppression in this isolated laboratory',liveness_scope='Finite admitted-source/connection load; no unlimited-Sybil, physical-link or shared-NAT newcomer guarantee')
    a.out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(dict(mode=a.mode,passed=passed,legitimate_clients=legit_count,valid_completed=sum(r['counts_measured'].get('valid_completed',0) for r in records))))
    if mismatches:raise SystemExit(40)
    if not passed:raise SystemExit(1)
if __name__=='__main__':main()
