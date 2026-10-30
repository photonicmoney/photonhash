/* Isolated allocation-failure test; never linked into the server. MIT. */
#include "network_cache.h"
#include "photonhash_lf3_c20_cached.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
void *__real_malloc(size_t);
static int fail_at=-1,seen=0;
void *__wrap_malloc(size_t n) {
    if(n>=(size_t)8*1024*1024 && fail_at>=0 && seen++==fail_at)return NULL;
    return __real_malloc(n);
}
static int stop(const char *reason) {fprintf(stderr,"{\"type\":\"STOP\",\"reason\":\"%s\"}\n",reason);return 40;}
int main(void) {
    void *s=nf_new();if(!s)return 2;
    uint8_t parents[3][32]={{0},{1},{2}},target[32],d[32],h[32],f[2048],ed[32],eh[32],ef[2048];memset(target,255,32);
    for(unsigned i=0;i<3;i++)if(nf_allow(s,i,parents[i],target))return 2;
    ph_lf2_context_t reference={0};
    if(ph_lf2_context_init(&reference,parents[0])||ph_lf3_c20_hash_cached(ed,eh,ef,&reference,NULL,0,0))return 2;
    for(int failure=0;failure<16;failure++) {
        if(nf_eval(s,parents[0],NULL,0,0,d,h,f)!=1)return 2;
        if(memcmp(d,ed,32)||memcmp(h,eh,32)||memcmp(f,ef,2048))return stop("fault-test warm trace mismatch");
        if(nf_eval(s,parents[1],NULL,0,0,d,h,f)!=1)return 2;
        seen=0;fail_at=failure;
        int rc=nf_eval(s,parents[2],NULL,0,0,d,h,f);fail_at=-1;
        nf_metrics m;nf_snapshot(s,&m);
        if(rc!=-1||m.resident!=1||m.coefficient_bytes!=134217728||m.high_water>2)return 3;
        if(nf_eval(s,parents[2],NULL,0,0,d,h,f)!=1||nf_eval(s,parents[0],NULL,0,0,d,h,f)!=1)return 2;
        if(memcmp(d,ed,32)||memcmp(h,eh,32)||memcmp(f,ef,2048))return stop("fault-test recovery trace mismatch");
        printf("{\"type\":\"allocation_failure_recovered\",\"large_allocation_index_configured\":%d,\"resident_after_failure_measured\":1}\n",failure);
    }
    ph_lf2_context_free(&reference);nf_free(s);puts("{\"type\":\"complete\",\"injected_allocation_failures_measured\":16,\"passed\":true}");return 0;
}
