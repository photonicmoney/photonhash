"""Read stored NVML metadata only; no GPU calls. Timestamp ≠ calibration."""
import json,math,pathlib,sys
def check(samples):
    ages=[(s['unix_ns']/1000-s['field_instant_timestamp_us'])/1e6 for s in samples]
    valid=all(math.isfinite(x) and -.001<=x<=2 for x in ages)
    return dict(passed_metadata_bound=valid,samples_measured=len(ages),minimum_field_age_s_measured=min(ages),maximum_field_age_s_measured=max(ages),older_than_2s_count_measured=sum(x>2 for x in ages),future_beyond_1ms_count_measured=sum(x<-.001 for x in ages),bound_s_configured=2,future_clock_tolerance_s_configured=.001,scope='NVML CPU field timestamp versus sample Unix clock, not a calibrated ADC freshness guarantee or sensor-accuracy claim')
if __name__=='__main__':
    p=pathlib.Path(sys.argv[1]);samples=[json.loads(x) for x in p.read_text().splitlines()];result=check(samples);print(json.dumps(result));raise SystemExit(0 if result['passed_metadata_bound'] else 1)
