#include "network_cache.h"
#include "bank_openssl.h"
#include "photonhash_lf3_c20_cached.h"
#include <stdlib.h>
#include <string.h>
typedef struct {uint8_t parent[32],target[32];int used;} allowed;
typedef struct {ph_lf2_context_t bank;uint8_t parent[32];uint64_t stamp;int used;} slot;
typedef struct {allowed parents[NF_PARENTS];slot slots[NF_BANK_SLOTS];nf_metrics m;uint64_t stamp;} state;
void *nf_new(void) {return calloc(1,sizeof(state));}
void nf_free(void *pointer) {
    state *s=pointer;if(!s)return;
    for(unsigned i=0;i<NF_BANK_SLOTS;i++)ph_lf2_context_free(&s->slots[i].bank);
    free(s);
}
int nf_allow(void *pointer,unsigned index,const uint8_t parent[32],const uint8_t target[32]) {
    state *s=pointer;
    if(!s||!parent||!target||index>=NF_PARENTS||s->m.derivations)return -1;
    uint8_t any=0;for(unsigned j=0;j<32;j++)any|=target[j];if(!any)return -1;
    for(unsigned i=0;i<NF_PARENTS;i++)if(i!=index&&s->parents[i].used&&!memcmp(s->parents[i].parent,parent,32))return -1;
    memcpy(s->parents[index].parent,parent,32);memcpy(s->parents[index].target,target,32);s->parents[index].used=1;return 0;
}
static void update(state *s) {
    uint64_t resident=0,bytes=0;
    for(unsigned i=0;i<NF_BANK_SLOTS;i++) {
        resident+=(s->slots[i].used!=0);
        for(unsigned p=0;p<8;p++)if(s->slots[i].bank.matrices[p].m)bytes+=(uint64_t)4096*4096;
    }
    s->m.resident=resident;s->m.coefficient_bytes=bytes;
    if(resident>s->m.high_water)s->m.high_water=resident;
}
int nf_eval(void *pointer,const uint8_t parent[32],const uint8_t *header,size_t length,
            uint64_t nonce,uint8_t digest[32],uint8_t h[32],uint8_t fold[2048]) {
    state *s=pointer;
    if(!s||!parent||!digest||!h||!fold||length>4096||(length&&!header))return -1;
    const allowed *a=NULL;
    for(unsigned i=0;i<NF_PARENTS;i++)if(s->parents[i].used&&!memcmp(s->parents[i].parent,parent,32)){a=&s->parents[i];break;}
    if(!a)return 2;
    slot *b=NULL;
    for(unsigned i=0;i<NF_BANK_SLOTS;i++)if(s->slots[i].used&&!memcmp(s->slots[i].parent,parent,32)){b=&s->slots[i];break;}
    if(!b) {
        b=&s->slots[0];
        for(unsigned i=0;i<NF_BANK_SLOTS;i++) {
            if(!s->slots[i].used){b=&s->slots[i];break;}
            if(s->slots[i].stamp<b->stamp)b=&s->slots[i];
        }
        /* Critical bound: destroy the entire victim before allocating a bank.
         * Only these two contexts exist; one worker performs one derivation. */
        if(b->used){ph_lf2_context_free(&b->bank);b->used=0;s->m.evictions++;}
        update(s);s->m.derivations++;
        if(lf3_bank_openssl(&b->bank,parent,1)) {s->m.errors++;update(s);return -1;}
        memcpy(b->parent,parent,32);b->used=1;update(s);
    }
    b->stamp=++s->stamp;s->m.verifications++;
    if(ph_lf3_c20_hash_cached(digest,h,fold,&b->bank,header,length,nonce)){s->m.errors++;return -1;}
    return ph_meets_target(digest,a->target)?1:0;
}
void nf_snapshot(void *pointer,nf_metrics *out) {state *s=pointer;if(!s||!out)return;update(s);*out=s->m;}
