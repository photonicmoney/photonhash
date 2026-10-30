"""Bounded isolated IPv4/TCP C20 laboratory. MIT. No Laser node integration.
Wire: 'L3N1' + big-endian u32 body size + parent[32] + nonce[8 LE] + header.
Response: one status byte (1 valid, 0 invalid, 2 unknown, 3 malformed, 4 busy,
5 timeout, 6 internal) + digest[32], zero for pre-hash refusals.
The native cache has exactly one owner thread. All scheduling is on this loop.
"""
import argparse,collections,ctypes,json,os,pathlib,queue,resource,selectors,socket,struct,threading,time
MAX_CONN=64;MAX_PEERS=16;PER_PEER=4;FRAME=4144;READ_S=3;QUEUE_S=20;LIFE_S=90
class Metrics(ctypes.Structure):
    _fields_=[(x,ctypes.c_uint64) for x in ['derivations','verifications','evictions','resident','high_water','coefficient_bytes','errors']]
class Backend:
    def __init__(self,library,parents):
        self.lib=ctypes.CDLL(str(library));L=self.lib;P=ctypes.c_void_p
        L.nf_new.restype=P;L.nf_free.argtypes=[P];L.nf_allow.argtypes=[P,ctypes.c_uint,P,P]
        L.nf_eval.argtypes=[P,P,P,ctypes.c_size_t,ctypes.c_uint64,P,P,P];L.nf_snapshot.argtypes=[P,P]
        self.state=L.nf_new()
        if not self.state:raise MemoryError('native cache')
        for i,a in enumerate(parents):
            if L.nf_allow(self.state,i,bytes.fromhex(a['parent']),bytes.fromhex(a['target'])):raise ValueError('startup parent registry')
    def evaluate(self,body):
        parent=body[:32];nonce=int.from_bytes(body[32:40],'little');header=body[40:]
        digest=ctypes.create_string_buffer(32);h=ctypes.create_string_buffer(32);fold=ctypes.create_string_buffer(2048)
        rc=self.lib.nf_eval(self.state,parent,header,len(header),nonce,digest,h,fold)
        m=Metrics();self.lib.nf_snapshot(self.state,ctypes.byref(m));values={n:getattr(m,n) for n,_ in m._fields_}
        if values['resident']>2 or values['high_water']>2 or values['coefficient_bytes']>268435456:raise RuntimeError('cache bound violated')
        return rc,digest.raw,values
    def close(self):self.lib.nf_free(self.state)

def main():
    p=argparse.ArgumentParser();p.add_argument('--library',type=pathlib.Path,required=True);p.add_argument('--fixtures',type=pathlib.Path,required=True);p.add_argument('--evidence',type=pathlib.Path,required=True);p.add_argument('--port',type=int,default=19090);p.add_argument('--seconds',type=int,default=90);a=p.parse_args()
    if not 10<=a.seconds<=900:raise SystemExit('Bounded runtime required')
    parents=json.loads(a.fixtures.read_text())['parents']
    if not 1<=len(parents)<=MAX_PEERS:raise SystemExit('Bounded trusted registry required')
    known={bytes.fromhex(x['parent']) for x in parents}
    if len(known)!=len(parents) or any(len(x)!=32 for x in known):raise SystemExit('Invalid trusted registry')
    a.evidence.mkdir(exist_ok=False,parents=True)
    resource.setrlimit(resource.RLIMIT_AS,(768*1024*1024,768*1024*1024))
    resource.setrlimit(resource.RLIMIT_NOFILE,(160,160))
    resource.setrlimit(resource.RLIMIT_CORE,(0,0))
    sel=selectors.DefaultSelector();listener=socket.socket();listener.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1);listener.bind(('0.0.0.0',a.port));listener.listen(64);listener.setblocking(False);sel.register(listener,selectors.EVENT_READ,'listen')
    wake_r,wake_w=socket.socketpair();wake_r.setblocking(False);sel.register(wake_r,selectors.EVENT_READ,'wake')
    jobs=queue.Queue(maxsize=1);results=queue.Queue(maxsize=1);ready=threading.Event();startup=[]
    def worker():
        backend=None
        try:
            backend=Backend(a.library,parents);startup.append(None)
        except Exception as error:startup.append(type(error).__name__)
        finally:ready.set()
        if backend is None:return
        try:
            while True:
                job=jobs.get()
                if job is None:break
                ident,body=job
                try:answer=backend.evaluate(body)
                except Exception as error:answer=(-1,bytes(32),{'worker_error':type(error).__name__})
                results.put((ident,answer));wake_w.send(b'x')
        finally:backend.close()
    thread=threading.Thread(target=worker,daemon=True);thread.start()
    if not ready.wait(15) or startup!=[None]:raise SystemExit('Native worker startup failed')
    conns={};peers={};rr=collections.deque();next_id=0;inflight=None;native={};start=time.monotonic();last_report=start
    counts=collections.Counter();high=collections.Counter();socket_buffers=set();fatal=None
    def report(kind):
        record=dict(type=kind,elapsed_s_measured=time.monotonic()-start,counts_measured=dict(counts),native_measured=native,connections_measured=len(conns),sources_measured=len(peers),pending_measured=sum(len(x['pending']) for x in peers.values()),inflight_measured=int(inflight is not None),high_water_measured=dict(high),rss_peak_KiB_measured=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
        print(json.dumps(record),flush=True)
        return record
    def peer_cleanup(key):
        peer=peers.get(key)
        if peer and not peer['connections'] and not (inflight and inflight[1]==key):
            if peer['in_rr']:
                try:rr.remove(key)
                except ValueError:pass
            del peers[key]
    def close(c):
        if c['id'] not in conns:return
        try:sel.unregister(c['socket'])
        except KeyError:pass
        c['socket'].close();del conns[c['id']]
        peer=peers[c['peer']];peer['connections'].discard(c['id'])
        try:peer['pending'].remove(c['id'])
        except ValueError:pass
        peer_cleanup(c['peer'])
    def watch(c,events):
        try:sel.modify(c['socket'],events,c)
        except KeyError:sel.register(c['socket'],events,c)
    def respond(c,status,digest=bytes(32),terminate=False):
        c.update(state='write',tx=bytes([status])+digest,sent=0,deadline=time.monotonic()+READ_S,terminate=terminate);watch(c,selectors.EVENT_WRITE)
    def schedule():
        nonlocal inflight
        if inflight is not None:return
        while rr:
            key=rr.popleft();peer=peers[key];peer['in_rr']=False
            if not peer['pending']:continue
            ident=peer['pending'].popleft();c=conns[ident]
            if peer['pending']:rr.append(key);peer['in_rr']=True
            c['state']='working';inflight=(ident,key,time.monotonic())
            jobs.put_nowait((ident,bytes(c['rx'][8:c['need']])));counts['scheduled']+=1;return
    config=dict(type='design',wire='L3N1/u32BE length/parent32/nonceLE64/header0..4096; response status+digest32',maximum_connections_configured=MAX_CONN,maximum_sources_configured=MAX_PEERS,maximum_connections_per_source_configured=PER_PEER,frame_buffer_bytes_per_connection_configured=FRAME,maximum_pending_configured=MAX_CONN,native_cache_slots_configured=2,coefficient_bound_bytes_configured=268435456,virtual_address_limit_bytes_configured=768*1024*1024,read_deadline_s_configured=READ_S,queue_deadline_s_configured=QUEUE_S,connection_lifetime_s_configured=LIFE_S,service_runtime_s_configured=a.seconds,policy='Identical unprivileged source/connection round robin; socket source address only; no client role or forwarded address',fairness_scope='Bounded admitted sources and connections, eventual finite native execution and functioning network/OS; no unlimited-Sybil, link saturation or shared-NAT newcomer guarantee')
    print(json.dumps(config),flush=True);(a.evidence/'ready.json').write_text(json.dumps(dict(ready=True,pid=os.getpid(),port=a.port))+'\n')
    try:
        while time.monotonic()-start<a.seconds and not (a.evidence/'STOP.json').exists():
            now=time.monotonic()
            for key,event in sel.select(.02):
                if key.data=='listen':
                    for _ in range(16):
                        try:sock,address=listener.accept()
                        except BlockingIOError:break
                        source=address[0];counts['accepted_TCP']+=1
                        if len(conns)>=MAX_CONN or (source not in peers and len(peers)>=MAX_PEERS) or (source in peers and len(peers[source]['connections'])>=PER_PEER):sock.close();counts['connection_refused']+=1;continue
                        sock.setblocking(False);sock.setsockopt(socket.SOL_SOCKET,socket.SO_RCVBUF,8192);sock.setsockopt(socket.SOL_SOCKET,socket.SO_SNDBUF,8192);sock.setsockopt(socket.IPPROTO_TCP,socket.TCP_NODELAY,1)
                        socket_buffers.add((sock.getsockopt(socket.SOL_SOCKET,socket.SO_RCVBUF),sock.getsockopt(socket.SOL_SOCKET,socket.SO_SNDBUF)))
                        if source not in peers:peers[source]=dict(connections=set(),pending=collections.deque(),in_rr=False)
                        next_id+=1;c=dict(id=next_id,socket=sock,peer=source,rx=bytearray(FRAME),have=0,need=8,state='read',deadline=now+READ_S,born=now)
                        conns[next_id]=c;peers[source]['connections'].add(next_id);watch(c,selectors.EVENT_READ)
                elif key.data=='wake':
                    try:wake_r.recv(8)
                    except BlockingIOError:pass
                    ident,(rc,digest,snapshot)=results.get_nowait();old=inflight;inflight=None;native=snapshot
                    if rc<0:fatal='native internal failure';break
                    counts['completed_native']+=1;counts['valid' if rc==1 else 'invalid']+=1
                    if ident in conns:respond(conns[ident],rc,digest)
                    peer_cleanup(old[1])
                else:
                    c=key.data
                    try:
                        if c['state']=='read':
                            n=c['socket'].recv_into(memoryview(c['rx'])[c['have']:c['need']])
                            if not n:close(c);continue
                            counts['bytes_received']+=n;c['have']+=n
                            if c['have']==8 and c['need']==8:
                                size=struct.unpack_from('!I',c['rx'],4)[0]
                                if c['rx'][:4]!=b'L3N1' or not 40<=size<=4136:counts['malformed']+=1;respond(c,3,terminate=True);continue
                                c['need']=8+size
                            if c['have']==c['need']:
                                if bytes(c['rx'][8:40]) not in known:counts['unknown_parent']+=1;respond(c,2);continue
                                c.update(state='queued',deadline=now+QUEUE_S);sel.unregister(c['socket']);peer=peers[c['peer']];peer['pending'].append(c['id'])
                                if not peer['in_rr']:rr.append(c['peer']);peer['in_rr']=True
                        elif c['state']=='write':
                            c['sent']+=c['socket'].send(c['tx'][c['sent']:])
                            if c['sent']==33:
                                if c['terminate']:close(c)
                                else:c.update(state='read',have=0,need=8,deadline=now+READ_S,tx=b'');watch(c,selectors.EVENT_READ)
                    except (BrokenPipeError,ConnectionResetError,OSError):close(c)
            if fatal:break
            for c in list(conns.values()):
                if (c['state']!='working' and now>c['deadline']) or now-c['born']>LIFE_S:counts['deadline_close']+=1;close(c)
            schedule()
            high['connections']=max(high['connections'],len(conns));high['sources']=max(high['sources'],len(peers));high['pending']=max(high['pending'],sum(len(x['pending']) for x in peers.values()))
            if now-last_report>=1:report('sample');last_report=now
    finally:
        for c in list(conns.values()):close(c)
        listener.close();sel.close()
        if inflight is None:jobs.put_nowait(None);thread.join(5)
        summary=report('complete');summary.update(fatal=fatal,socket_buffers_bytes_measured=sorted(socket_buffers),stopped_by_controller=(a.evidence/'STOP.json').exists());(a.evidence/'server-summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    if fatal:raise SystemExit(20)
if __name__=='__main__':main()
