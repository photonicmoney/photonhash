"""Deterministic fault injection; no GPU or NVML needed. Run on the CPU pod."""
import copy, json, math, pathlib, unittest
from telemetry_guard import TelemetryGuard,qualify_samples

def sample(t):
    return dict(type='nvml_sample',monotonic=t,query_end_monotonic=t,
        query_wall_s_measured=.001,temperature_C_measured=60,
        field_instant_status=0,field_instant_valueType=1,power_instant_mW_measured=250000)
def normal():
    return [sample(i/10) for i in range(40)], [dict(condition=c,begin=a,end=b,event_seconds=1.0,correct_evaluations_counted=1000) for c,a,b in [('cold_start',.1,1.3),('warm',1.4,2.6)]]
def qualify(s,w,**kw):
    return qualify_samples(s,w,process_ok=kw.get('process_ok',True),cold_ok=kw.get('cold_ok',True),conformance_ok=kw.get('conformance_ok',True),required_event_seconds=1.0)
class Tests(unittest.TestCase):
    def test_normal(self):
        s,w=normal();self.assertTrue(qualify(s,w)['qualified'])
    def test_recovered_long_query_latches_before_refresh(self):
        g=TelemetryGuard(0);self.assertTrue(g.observe(0,.1,sample(.1)))
        self.assertFalse(g.observe(.2,9.47,sample(9.47)))
        self.assertEqual(g.last,.1);self.assertFalse(g.observe(9.5,9.51,sample(9.51)))
        self.assertFalse(g.healthy(9.52))
    def test_monitor_latch_survives_late_healthy_sample(self):
        g=TelemetryGuard(0);self.assertFalse(g.healthy(2.01))
        self.assertFalse(g.observe(2.02,2.03,sample(2.03)))
    def test_exact_boundary_and_monotonic(self):
        g=TelemetryGuard(0);self.assertTrue(g.observe(0,2,sample(2)))
        self.assertTrue(g.healthy(4));self.assertFalse(g.healthy(4.0001))
    def test_retrospective_rejects_recovered_gap(self):
        s,w=normal()
        for r in s[20:]:r['monotonic']+=9.37;r['query_end_monotonic']+=9.37
        self.assertFalse(qualify(s,w)['qualified'])
    def test_bad_samples(self):
        changes=[('temperature_C_measured',80),('field_instant_status',1),('field_instant_valueType',0),('power_instant_mW_measured',-1),('power_instant_mW_measured',math.nan),('query_wall_s_measured',9.37),('query_wall_s_measured',-1),('query_end_monotonic',math.nan),('query_end_monotonic',.1),('type','sampler_abort')]
        for k,v in changes:
            with self.subTest(k=k,v=v):
                s,w=normal();s[10][k]=v;self.assertFalse(qualify(s,w)['qualified'])
    def test_bad_windows(self):
        changes=[('begin',-1),('end',100),('end',.05),('event_seconds',0),('event_seconds',math.nan),('event_seconds',2),('correct_evaluations_counted',0),('condition','other')]
        for k,v in changes:
            with self.subTest(k=k,v=v):
                s,w=normal();w[0][k]=v;self.assertFalse(qualify(s,w)['qualified'])
    def test_incomplete(self):
        s,w=normal()
        for k in ['process_ok','cold_ok','conformance_ok']:self.assertFalse(qualify(s,w,**{k:False})['qualified'])
        self.assertFalse(qualify(s[:1],w)['qualified']);self.assertFalse(qualify(s,w[:1])['qualified'])
    def test_overlap(self):
        s,w=normal();w[1]['begin']=1.2;self.assertFalse(qualify(s,w)['qualified'])
    def test_online_invalid_samples_latch(self):
        for k,v in [('temperature_C_measured',math.nan),('temperature_C_measured',80),('field_instant_status',1),('power_instant_mW_measured',-1)]:
            with self.subTest(k=k,v=v):
                g=TelemetryGuard(0);s=sample(.1);s[k]=v
                self.assertFalse(g.observe(0,.1,s));self.assertFalse(g.observe(.1,.2,sample(.2)))
        g=TelemetryGuard(0);self.assertTrue(g.observe(0,.1,sample(.1)))
        self.assertFalse(g.observe(.05,.09,sample(.09)))
if __name__=='__main__':
    if not pathlib.Path('/workspace/lf3-followup').is_dir():raise SystemExit('Remote workspace required')
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(Tests)
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    pathlib.Path('/workspace/lf3-followup/evidence/telemetry-fault-tests.json').write_text(json.dumps({'tests_measured':result.testsRun,'failures_measured':len(result.failures),'errors_measured':len(result.errors),'passed':result.wasSuccessful(),'scope':'deterministic injected telemetry; not a sensor calibration'},indent=2))
    raise SystemExit(0 if result.wasSuccessful() else 1)
