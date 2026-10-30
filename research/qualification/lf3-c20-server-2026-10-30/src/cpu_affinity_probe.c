#define _GNU_SOURCE
#include <omp.h>
#include <sched.h>
#include <stdio.h>
int main(void) {
    int failed=0;
    for(unsigned i=0;i<4;i++) {
        unsigned requested=(unsigned[]){1,2,4,8}[i];
        #pragma omp parallel num_threads(requested) reduction(|:failed)
        {
            unsigned actual=(unsigned)omp_get_num_threads();
            failed |= actual!=requested;
            #pragma omp critical
            printf("{\"type\":\"affinity_probe\",\"workers_configured\":%u,\"workers_measured\":%u,\"thread_measured\":%u,\"CPU_measured\":%d}\n",requested,actual,(unsigned)omp_get_thread_num(),sched_getcpu());
        }
    }
    puts("{\"type\":\"probe_complete\"}");return failed?3:0;
}
