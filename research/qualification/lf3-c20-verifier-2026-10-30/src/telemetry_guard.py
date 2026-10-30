"""Fail-closed telemetry acceptance. No NVML dependency; tested remotely.

The first failure is permanent. An overdue observation cannot refresh its way
back to healthy. Qualification rechecks raw samples independently of heartbeat.
"""
import math
import threading

class TelemetryGuard:
    def __init__(self, started, max_gap=2.0, thermal_limit=80):
        self.last=float(started)
        self.max_gap=float(max_gap)
        self.thermal_limit=thermal_limit
        self.failure=None
        self.lock=threading.Lock()

    def fail(self, reason):
        if self.failure is None:
            self.failure=reason
        return False

    def observe(self, begin, end, sample):
        with self.lock:
            if self.failure is not None: return False
            if not all(math.isfinite(x) for x in [begin,end]) or end<begin:
                return self.fail('invalid query clock')
            if end<=self.last:
                return self.fail('non-monotonic sample clock')
            if end-self.last>self.max_gap:
                return self.fail('sample gap exceeds bound')
            if end-begin>self.max_gap:
                return self.fail('query duration exceeds bound')
            temp=sample.get('temperature_C_measured',math.nan)
            if not math.isfinite(temp) or temp>=self.thermal_limit:
                return self.fail('thermal bound reached')
            if sample.get('field_instant_status')!=0 or sample.get('field_instant_valueType')!=1:
                return self.fail('instantaneous power field invalid')
            if not math.isfinite(sample.get('power_instant_mW_measured',math.nan)) or sample['power_instant_mW_measured']<0:
                return self.fail('invalid measured power')
            self.last=end  # Refresh only after every check succeeds.
            return True

    def healthy(self, now):
        with self.lock:
            if self.failure is not None: return False
            if not math.isfinite(now) or now-self.last>self.max_gap:
                return self.fail('heartbeat overdue')
            return True

def qualify_samples(samples, windows, *, process_ok, cold_ok, conformance_ok,
                    required_event_seconds=600.0,max_gap=2.0):
    """Independent complete-run acceptance; returns evidence, never repairs data."""
    errors=[]
    if not process_ok: errors.append('process incomplete or failed')
    if not cold_ok: errors.append('cold start unqualified')
    if not conformance_ok: errors.append('conformance unqualified')
    if len(samples)<2: errors.append('insufficient telemetry')
    times=[]
    for s in samples:
        t=s.get('query_end_monotonic',s.get('monotonic',math.nan))
        if not math.isfinite(t): errors.append('invalid timestamp'); continue
        times.append(t)
        duration=s.get('query_wall_s_measured',math.nan)
        if not math.isfinite(duration) or duration<0 or duration>max_gap: errors.append('invalid query duration')
        temp=s.get('temperature_C_measured',math.nan)
        if not math.isfinite(temp) or temp>=80: errors.append('thermal bound invalid')
        if s.get('field_instant_status')!=0 or s.get('field_instant_valueType')!=1: errors.append('instantaneous power field invalid')
        power=s.get('power_instant_mW_measured',math.nan)
        if not math.isfinite(power) or power<0: errors.append('invalid power')
        if s.get('type')!='nvml_sample': errors.append('sampler failure record')
    gaps=[b-a for a,b in zip(times,times[1:])]
    if any(g<=0 or g>max_gap for g in gaps): errors.append('timestamp gap invalid')
    previous_end=None
    for w in windows:
        a,b=w.get('begin',math.nan),w.get('end',math.nan)
        if not all(math.isfinite(x) for x in [a,b]) or not a<b: errors.append('invalid window'); continue
        if not times or not times[0]<=a<b<=times[-1]: errors.append('window outside telemetry')
        if previous_end is not None and a<previous_end: errors.append('overlapping windows')
        previous_end=b
        if w.get('correct_evaluations_counted',0)<=0: errors.append('invalid denominator')
        ev=w.get('event_seconds',math.nan)
        if not math.isfinite(ev) or ev<=0 or ev>b-a+0.001: errors.append('invalid event duration')
    totals={c:sum(w.get('event_seconds',0) for w in windows if w.get('condition')==c) for c in ['cold_start','warm']}
    if any(t<required_event_seconds for t in totals.values()): errors.append('insufficient fixed condition windows')
    if any(w.get('condition') not in totals for w in windows): errors.append('unknown condition')
    return {'qualified':not errors,'reasons':sorted(set(errors)),
            'max_sampling_gap_s_measured':max(gaps,default=None),
            'samples_measured':len(samples),'event_seconds_measured':totals,
            'guard_s_configured':max_gap,'sensor_accuracy':'OPEN: statistical acceptance does not calibrate NVML'}
