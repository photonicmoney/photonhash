#define _POSIX_C_SOURCE 200809L
#include "bank_openssl.h"
#include "photonhash_lf3_c20_cached.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
static double seconds(clockid_t clock) {
    struct timespec t;clock_gettime(clock,&t);return t.tv_sec+t.tv_nsec/1e9;
}
static void stop(unsigned variant,unsigned step) {
    FILE *f=fopen("evidence/STOP.json","wx");if(f) {fprintf(f,"{\"reason\":\"CPU benchmark correctness mismatch\",\"variant\":%u,\"step\":%u}\n",variant,step);fclose(f);}
    puts("{\"type\":\"STOP\",\"reason\":\"CPU benchmark correctness mismatch\"}");exit(40);
}
static int derive(ph_lf2_context_t *b,const uint8_t p[32],unsigned variant) {
    return variant==0 ? ph_lf2_context_init(b,p) : lf3_bank_openssl(b,p,variant);
}
int main(void) {
    uint8_t expected_parent[31][32],expected_fold[31][2048];
    const uint8_t header[80]={0x43,0x32,0x30};
    for(unsigned vi=0;vi<5;vi++) {
        unsigned variant=(unsigned[]){0,1,2,4,8}[vi];
        uint8_t parent[32]={1};
        for(unsigned i=0;i<31;i++) {
            ph_lf2_context_t bank={0};uint8_t d[32],h[32],fold[2048];
            double begin=seconds(CLOCK_MONOTONIC),cpu=seconds(CLOCK_PROCESS_CPUTIME_ID);
            if(derive(&bank,parent,variant)) return 3;
            double bank_end=seconds(CLOCK_MONOTONIC),bank_cpu=seconds(CLOCK_PROCESS_CPUTIME_ID);
            if(ph_lf3_c20_hash_cached(d,h,fold,&bank,header,80,i)) return 3;
            double end=seconds(CLOCK_MONOTONIC),end_cpu=seconds(CLOCK_PROCESS_CPUTIME_ID);
            if(variant==0) {memcpy(expected_parent[i],d,32);memcpy(expected_fold[i],fold,2048);}
            else if(memcmp(expected_parent[i],d,32)||memcmp(expected_fold[i],fold,2048)) stop(variant,i);
            printf("{\"type\":\"serial_parent_step\",\"variant\":%u,\"step\":%u,\"bank_wall_s_measured\":%.9f,\"bank_cpu_s_measured\":%.9f,\"cold_wall_s_measured\":%.9f,\"cold_cpu_s_measured\":%.9f,\"cached_wall_s_measured\":%.9f}\n",variant,i,bank_end-begin,bank_cpu-cpu,end-begin,end_cpu-cpu,end-bank_end);fflush(stdout);
            memcpy(parent,d,32);ph_lf2_context_free(&bank);
        }
        ph_lf2_context_t bank={0}; if(derive(&bank,parent,variant)) return 3;
        for(unsigned i=0;i<64;i++) {
            uint8_t d[32],h[32],fold[2048];double begin=seconds(CLOCK_MONOTONIC),cpu=seconds(CLOCK_PROCESS_CPUTIME_ID);
            if(ph_lf3_c20_hash_cached(d,h,fold,&bank,header,80,i)) return 3;
            printf("{\"type\":\"cached_verify\",\"variant\":%u,\"sample\":%u,\"wall_s_measured\":%.9f,\"cpu_s_measured\":%.9f}\n",variant,i,seconds(CLOCK_MONOTONIC)-begin,seconds(CLOCK_PROCESS_CPUTIME_ID)-cpu);
        }
        ph_lf2_context_free(&bank);
    }
    puts("{\"type\":\"complete\",\"serial_steps_per_variant_measured\":31,\"cached_samples_per_variant_measured\":64,\"full_fold_cross_variant_steps_measured\":124}");
    return 0;
}
