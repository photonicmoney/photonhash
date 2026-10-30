#include "admission_lab.h"
#include "photonhash_lf3_c20_cached.h"
#include <string.h>

void lab_init(admission_lab *l,unsigned workers) {
    memset(l,0,sizeof *l);l->workers=workers;
}
void lab_free(admission_lab *l) {
    for(unsigned i=0;i<LAB_BANKS;i++) ph_lf2_context_free(&l->slots[i].bank);
    memset(l,0,sizeof *l);
}
int lab_allow_parent(admission_lab *l,unsigned slot,const uint8_t p[32],const uint8_t t[32]) {
    if(!l||!p||!t||slot>=LAB_PARENTS||l->busy) return LAB_MALFORMED;
    uint8_t any=0;for(unsigned j=0;j<32;j++) any|=t[j];if(!any)return LAB_MALFORMED;
    for(unsigned i=0;i<LAB_PARENTS;i++) if(i!=slot&&l->parents[i].used&&!memcmp(l->parents[i].hash,p,32)) return LAB_MALFORMED;
    if(l->parents[slot].used && memcmp(l->parents[slot].hash,p,32)) {
        for(unsigned i=0;i<LAB_BANKS;i++) if(l->slots[i].used && !memcmp(l->slots[i].parent,l->parents[slot].hash,32)) {
            ph_lf2_context_free(&l->slots[i].bank);l->slots[i].used=0;
        }
    }
    memcpy(l->parents[slot].hash,p,32);memcpy(l->parents[slot].target,t,32);l->parents[slot].used=1;
    return 0;
}
int lab_advance(admission_lab *l,uint64_t now) {
    if(!l||l->busy||now<l->epoch)return LAB_MALFORMED;
    if(now>l->epoch) {
        memset(l->peer_used,0,sizeof l->peer_used);l->global_used=0;l->cold_used=0;l->epoch=now;
    }
    return 0;
}
int lab_verify(admission_lab *l,unsigned peer,const uint8_t parent[32],const uint8_t *header,size_t length,uint64_t nonce,uint8_t digest[32]) {
    if(!l||!parent||!digest||peer>=LAB_PEERS||length>4096||(length&&!header))return LAB_MALFORMED;
    if(l->busy)return LAB_BUSY;
    const lab_parent *admitted=NULL;
    for(unsigned i=0;i<LAB_PARENTS;i++) if(l->parents[i].used&&!memcmp(l->parents[i].hash,parent,32)) {admitted=&l->parents[i];break;}
    if(!admitted) {l->unknown_rejects++;return LAB_UNKNOWN_PARENT;}
    if(l->global_used>=4||l->peer_used[peer]>=2) {l->rate_rejects++;return LAB_RATE_LIMIT;}
    lab_slot *bank=NULL;
    for(unsigned i=0;i<LAB_BANKS;i++) if(l->slots[i].used&&!memcmp(l->slots[i].parent,parent,32)){bank=&l->slots[i];break;}
    if(!bank&&l->cold_used>=1){l->rate_rejects++;return LAB_RATE_LIMIT;}
    /* Reserve quotas before any allocation or work, including failed work. */
    l->global_used++;l->peer_used[peer]++;l->busy=1;
    if(!bank) {
        l->cold_used++;
        bank=&l->slots[0];
        for(unsigned i=0;i<LAB_BANKS;i++) {
            if(!l->slots[i].used){bank=&l->slots[i];break;}
            if(l->slots[i].stamp<bank->stamp)bank=&l->slots[i];
        }
        if(bank->used){ph_lf2_context_free(&bank->bank);bank->used=0;l->evictions++;}
        l->derivations++;
        if(lf3_bank_openssl(&bank->bank,parent,l->workers)){l->busy=0;return LAB_ERROR;}
        memcpy(bank->parent,parent,32);bank->used=1;
    }
    bank->stamp=++l->stamp;
    uint8_t h[32],fold[2048];l->verifications++;
    int rc=ph_lf3_c20_hash_cached(digest,h,fold,&bank->bank,header,length,nonce);
    l->busy=0;
    if(rc)return LAB_ERROR;
    return ph_meets_target(digest,admitted->target) ? LAB_VALID : LAB_INVALID;
}
