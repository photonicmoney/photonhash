"""Read-only continuous NVML sampler. No power/clock/driver setters."""
import ctypes as c
import json
from pathlib import Path
import time
import argparse

class Value(c.Union):
    _fields_=[('d',c.c_double),('si',c.c_int),('ui',c.c_uint),
              ('ul',c.c_ulong),('ull',c.c_ulonglong),('sll',c.c_longlong),('us',c.c_ushort)]
class Field(c.Structure):
    _fields_=[('fieldId',c.c_uint),('scopeId',c.c_uint),('timestamp',c.c_longlong),
              ('latencyUsec',c.c_longlong),('valueType',c.c_int),('status',c.c_int),('value',Value)]
class Utilization(c.Structure):
    _fields_=[('gpu',c.c_uint),('memory',c.c_uint)]

class NVML:
    def __init__(self):
        self.lib=c.CDLL('libnvidia-ml.so.1')
        self.lib.nvmlInit_v2.argtypes=[]
        self.lib.nvmlDeviceGetHandleByIndex_v2.argtypes=[c.c_uint,c.POINTER(c.c_void_p)]
        self.lib.nvmlDeviceGetFieldValues.argtypes=[c.c_void_p,c.c_int,c.POINTER(Field)]
        for name in ['nvmlDeviceGetPowerUsage','nvmlDeviceGetPowerManagementLimit']:
            getattr(self.lib,name).argtypes=[c.c_void_p,c.POINTER(c.c_uint)]
        self.lib.nvmlDeviceGetClockInfo.argtypes=[c.c_void_p,c.c_int,c.POINTER(c.c_uint)]
        self.lib.nvmlDeviceGetTemperature.argtypes=[c.c_void_p,c.c_int,c.POINTER(c.c_uint)]
        self.lib.nvmlDeviceGetUtilizationRates.argtypes=[c.c_void_p,c.POINTER(Utilization)]
        self.lib.nvmlDeviceGetTotalEnergyConsumption.argtypes=[c.c_void_p,c.POINTER(c.c_ulonglong)]
        self.lib.nvmlShutdown.argtypes=[]
        self.check(self.lib.nvmlInit_v2())
        self.device=c.c_void_p();self.check(self.lib.nvmlDeviceGetHandleByIndex_v2(0,c.byref(self.device)))
    @staticmethod
    def check(status):
        if status: raise RuntimeError('NVML status '+str(status))
    def uint(self,name,*args):
        value=c.c_uint();self.check(getattr(self.lib,name)(self.device,*args,c.byref(value)));return value.value
    def sample(self):
        start=time.perf_counter()
        fields=(Field*2)();fields[0].fieldId=186;fields[1].fieldId=185
        self.check(self.lib.nvmlDeviceGetFieldValues(self.device,2,fields))
        record={'type':'nvml_sample','monotonic':time.monotonic(),'unix_ns':time.time_ns(),
            'powerUsage_mW_measured_1s_average':self.uint('nvmlDeviceGetPowerUsage'),
            'powerLimit_mW_measured':self.uint('nvmlDeviceGetPowerManagementLimit'),
            'temperature_C_measured':self.uint('nvmlDeviceGetTemperature',0),
            'smClock_MHz_measured':self.uint('nvmlDeviceGetClockInfo',1),
            'memoryClock_MHz_measured':self.uint('nvmlDeviceGetClockInfo',2)}
        for field,name in zip(fields,['instant','average']):
            record['field_'+name+'_status']=field.status
            record['field_'+name+'_valueType']=field.valueType
            if field.status==0:
                record['field_'+name+'_timestamp_us']=field.timestamp
                if field.valueType!=1: raise RuntimeError('unexpected power field value type')
                record['power_'+name+'_mW_measured']=field.value.ui
        utilization=Utilization();self.check(self.lib.nvmlDeviceGetUtilizationRates(self.device,c.byref(utilization)))
        record['gpu_utilization_percent_measured']=utilization.gpu
        energy=c.c_ulonglong();status=self.lib.nvmlDeviceGetTotalEnergyConsumption(self.device,c.byref(energy))
        record['energyCounter_status']=status
        if status==0:record['energyCounter_mJ_measured']=energy.value
        record['query_wall_s_measured']=time.perf_counter()-start
        return record
    def close(self): self.check(self.lib.nvmlShutdown())

def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True)
    p.add_argument('--seconds',type=float,default=2);p.add_argument('--interval',type=float,default=.1)
    p.add_argument('--thermal-stop-file',type=Path)
    args=p.parse_args();nvml=NVML();end=time.monotonic()+args.seconds;count=0;cpu=time.process_time()
    try:
        with args.output.open('x') as out:
            while time.monotonic()<end:
                begin=time.monotonic();record=nvml.sample();out.write(json.dumps(record)+'\n');out.flush();count+=1
                if record['temperature_C_measured']>=80:
                    if args.thermal_stop_file:args.thermal_stop_file.write_text('thermal guard: measured GPU >=80 C\n')
                    raise RuntimeError('thermal guard: measured GPU >=80 C')
                time.sleep(max(0,args.interval-(time.monotonic()-begin)))
    finally:nvml.close()
    print(json.dumps({'samples_measured':count,'sampler_cpu_s_measured':time.process_time()-cpu,
        'purpose':'telemetry capability only; no attempt-energy claim'}))

if __name__=='__main__':main()
