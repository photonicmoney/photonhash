#define _POSIX_C_SOURCE 200809L
#include "admission_lab.h"
#include "photonhash_lf3_c20_cached.h"
#include <inttypes.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <sys/resource.h>
static double now(clockid_t c){struct timespec t;clock_gettime(c,&t);return t.tv_sec+t.tv_nsec/1e9;}
static void require(int ok,const char *reason){if(!ok){fprintf(stderr,"LAB_ASSERTION_FAILURE: %s\n",reason);exit(1);}}
static unsigned occupancy(const admission_lab *l){unsigned n=0;for(unsigned i=0;i<LAB_BANKS;i++)n+=l->slots[i].used!=0;return n;}
static void mismatch(void){FILE *f=fopen("evidence/STOP.json","wx");if(f){fputs("{\"reason\":\"admission digest mismatch\"}\n",f);fclose(f);}puts("{\"type\":\"STOP\",\"reason\":\"admission digest mismatch\"}");exit(40);}
int main(void){
 admission_lab l;lab_init(&l,2);uint8_t p[3][32]={{0},{1},{2}},target[32],d[32],header[80]={0};memset(target,255,32);
 require(lab_allow_parent(&l,LAB_PARENTS,p[0],target)==LAB_MALFORMED,"parent slot bounded");
 for(unsigned i=0;i<3;i++)require(lab_allow_parent(&l,i,p[i],target)==0,"trusted admission");
 ph_lf2_context_t oracle={0};uint8_t expected[32],h[32],fold[2048];
 require(ph_lf2_context_init(&oracle,p[0])==0,"oracle bank");
 require(ph_lf3_c20_hash_cached(expected,h,fold,&oracle,header,80,0)==0,"oracle hash");ph_lf2_context_free(&oracle);
 require(lab_advance(&l,1)==0,"trusted tick");
 double a=now(CLOCK_MONOTONIC);require(lab_verify(&l,0,p[0],header,80,0,d)==LAB_VALID,"first cold valid");double cold=now(CLOCK_MONOTONIC)-a;
 if(memcmp(d,expected,32))mismatch();
 uint64_t before=l.derivations;
 require(lab_verify(&l,1,p[1],header,80,0,d)==LAB_RATE_LIMIT,"global cold quota");require(l.derivations==before,"cold reject no derive");
 a=now(CLOCK_MONOTONIC);require(lab_verify(&l,0,p[0],header,80,0,d)==LAB_VALID,"cached valid");double cached=now(CLOCK_MONOTONIC)-a;
 require(lab_verify(&l,0,p[0],header,80,0,d)==LAB_RATE_LIMIT,"per-peer quota");
 require(lab_verify(&l,1,p[0],header,80,0,d)==LAB_VALID,"peer one");require(lab_verify(&l,2,p[0],header,80,0,d)==LAB_VALID,"peer two");
 require(lab_verify(&l,3,p[0],header,80,0,d)==LAB_RATE_LIMIT,"global quota across peers");
 require(lab_advance(&l,0)==LAB_MALFORMED,"clock rollback rejected");
 require(lab_advance(&l,1)==0,"same tick no refill");require(lab_verify(&l,3,p[0],header,80,0,d)==LAB_RATE_LIMIT,"same tick stays exhausted");
 for(unsigned mode=0;mode<3;mode++){
  const unsigned count=1048576;uint64_t derives=l.derivations,verifies=l.verifications;unsigned slots=occupancy(&l);
  int8_t *m=l.slots[0].bank.matrices[0].m;double wall=now(CLOCK_MONOTONIC),cpu=now(CLOCK_PROCESS_CPUTIME_ID);
  for(unsigned i=0;i<count;i++){
   uint8_t unknown[32]={0xe0};memcpy(unknown+4,&i,sizeof i);int rc;
   if(mode==0)rc=lab_verify(&l,i%LAB_PEERS,unknown,header,80,i,d);
   else if(mode==1)rc=lab_verify(&l,i%LAB_PEERS,p[0],header,4097,i,d);
   else rc=lab_verify(&l,i%LAB_PEERS,p[0],header,80,i,d);
   require(rc==(mode==0?LAB_UNKNOWN_PARENT:mode==1?LAB_MALFORMED:LAB_RATE_LIMIT),"hostile classification");
  }
  require(l.derivations==derives&&l.verifications==verifies&&occupancy(&l)==slots&&l.slots[0].bank.matrices[0].m==m,"reject path preserves cache and work counts");
  printf("{\"type\":\"hostile_batch\",\"mode\":%u,\"requests_measured\":%u,\"wall_s_measured\":%.9f,\"cpu_s_measured\":%.9f,\"derivations_measured\":0,\"hashes_measured\":0,\"occupancy_unchanged\":true}\n",mode,count,now(CLOCK_MONOTONIC)-wall,now(CLOCK_PROCESS_CPUTIME_ID)-cpu);fflush(stdout);
 }
 /* An admitted-parent attacker can still force bounded cold work/churn. */
 for(unsigned i=0;i<10;i++){
  require(lab_advance(&l,2+i)==0,"next trusted tick");uint64_t derives=l.derivations;
  double wall=now(CLOCK_MONOTONIC),cpu=now(CLOCK_PROCESS_CPUTIME_ID);
  require(lab_verify(&l,i%LAB_PEERS,p[(i+1)%3],header,80,i,d)==LAB_VALID,"admitted churn work");
  require(occupancy(&l)<=LAB_BANKS&&l.derivations-derives<=1,"bounded cold work and cache");
  printf("{\"type\":\"admitted_parent_churn\",\"step\":%u,\"wall_s_measured\":%.9f,\"cpu_s_measured\":%.9f,\"cold_derivations_measured\":%" PRIu64 ",\"slots_measured\":%u}\n",i,now(CLOCK_MONOTONIC)-wall,now(CLOCK_PROCESS_CPUTIME_ID)-cpu,l.derivations-derives,occupancy(&l));fflush(stdout);
 }
 uint8_t zero_target[32]={0};require(lab_allow_parent(&l,3,p[0],zero_target)==LAB_MALFORMED,"zero target trusted-policy validation");
 l.busy=1;require(lab_verify(&l,0,p[0],header,80,0,d)==LAB_BUSY,"busy owner rejects reentry");l.busy=0;
 require(lab_verify(&l,LAB_PEERS,p[0],header,80,0,d)==LAB_MALFORMED,"peer slots bounded");
 require(lab_verify(&l,0,p[0],NULL,80,0,d)==LAB_MALFORMED,"null input rejected");
 require(lab_allow_parent(&l,1,p[0],target)==LAB_MALFORMED,"duplicate parent admission rejected");
 uint8_t replacement[32]={3};require(lab_allow_parent(&l,1,replacement,target)==0,"trusted replacement evicts obsolete parent");
 struct rusage usage;getrusage(RUSAGE_SELF,&usage);
 printf("{\"type\":\"complete\",\"unknown_requests_measured\":1048576,\"oversized_requests_measured\":1048576,\"overquota_requests_measured\":1048576,\"first_cold_wall_s_measured\":%.9f,\"cached_wall_s_measured\":%.9f,\"peak_RSS_KiB_measured\":%ld,\"bank_slots_configured\":2,\"bank_coefficient_bytes_bound_configured\":268435456,\"derivations_measured\":%" PRIu64 ",\"verifications_measured\":%" PRIu64 ",\"evictions_measured\":%" PRIu64 "}\n",cold,cached,usage.ru_maxrss,l.derivations,l.verifications,l.evictions);
 lab_free(&l);return 0;
}
