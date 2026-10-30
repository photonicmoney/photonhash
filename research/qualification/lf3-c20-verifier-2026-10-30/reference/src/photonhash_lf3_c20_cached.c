/* Exact cached experiment reference. No activation or integration policy. MIT. */
#include "photonhash_lf3_c20_cached.h"
#include "photonhash_lf3_c20.h"
#include <string.h>

int ph_lf3_c20_hash_cached(uint8_t digest[32], uint8_t h[32],
    uint8_t fold[2048], const ph_lf2_context_t *bank,
    const uint8_t *header, size_t length, uint64_t nonce)
{
    static const char final_tag[]="LASER/PhotonHash/LF3-K8-C20-experiment.1/final";
    if (!digest || !h || !fold || !bank || !bank->initialized ||
        (length && !header)) return -1;
    /* The expander is parent-independent. Avoid regenerating the bank. */
    const uint8_t unused_parent[32]={0};
    ph_lf3_c20_job_t expansion;
    if (ph_lf3_c20_init(&expansion,unused_parent,header,length,nonce,0)!=0) return -1;
    memset(fold,0,2048);
    memcpy(h,expansion.core.h,32);
    for (unsigned pass=0;pass<8u;++pass) {
        if (!bank->matrices[pass].m) return -1;
        for (unsigned row=0;row<4096u;++row) {
            const int8_t *m=bank->matrices[pass].m+(size_t)row*4096u;
            int32_t sum=0;
            for (unsigned col=0;col<4096u;++col)
                sum+=(int32_t)m[col]*(int32_t)expansion.core.x[col];
            uint8_t q=(uint8_t)(((uint32_t)sum>>9)&15u);
            fold[row/2u]^=(uint8_t)(q<<(4u*(row&1u)));
        }
    }
    ph_shake256_t state;
    ph_shake256_init(&state);
    ph_shake256_absorb(&state,final_tag,sizeof final_tag-1u);
    ph_shake256_absorb(&state,h,32);
    ph_shake256_absorb(&state,fold,2048);
    ph_shake256_squeeze(&state,digest,32);
    return 0;
}
