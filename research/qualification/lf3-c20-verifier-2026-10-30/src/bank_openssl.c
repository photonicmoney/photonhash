/* Exact OpenSSL SHAKE256 implementation of the frozen LF2/C20 matrix bank. MIT. */
#include "bank_openssl.h"
#include <openssl/evp.h>
#include <stdlib.h>
#include <string.h>
#include <omp.h>

static int shake(uint8_t *out, size_t outlen, const void *in, size_t len) {
    EVP_MD_CTX *s=EVP_MD_CTX_new();
    int ok=s && EVP_DigestInit_ex(s,EVP_shake256(),NULL)==1 &&
        EVP_DigestUpdate(s,in,len)==1 && EVP_DigestFinalXOF(s,out,outlen)==1;
    EVP_MD_CTX_free(s); return ok ? 0 : -1;
}
static int derive(ph_matrix_t *m, const uint8_t parent[32], unsigned pass) {
    static const char pass_tag[]="LASER/PhotonHash/launch-LF2/matrix";
    static const char matrix_tag[]="LASER/PhotonHash/v1/matrix";
    uint8_t pass_parent[32], input[sizeof pass_tag-1+32+4];
    memcpy(pass_parent,parent,32);
    if(pass) {
        memcpy(input,pass_tag,sizeof pass_tag-1);
        memcpy(input+sizeof pass_tag-1,parent,32);
        for(unsigned b=0;b<4;b++) input[sizeof pass_tag-1+32+b]=(uint8_t)(pass>>(8*b));
        if(shake(pass_parent,32,input,sizeof input)) return -1;
    }
    uint8_t seed_input[sizeof matrix_tag-1+32];
    memcpy(seed_input,matrix_tag,sizeof matrix_tag-1);
    memcpy(seed_input+sizeof matrix_tag-1,pass_parent,32);
    if(shake(m->seed,64,seed_input,sizeof seed_input)) return -1;
    const size_t entries=(size_t)4096*4096, packed=entries/2;
    uint8_t *stream=malloc(packed); m->m=malloc(entries);
    if(!stream || !m->m) { free(stream); free(m->m); m->m=NULL; return -1; }
    if(shake(stream,packed,m->seed,64) || shake(m->checksum,32,stream,packed)) {
        free(stream); free(m->m); m->m=NULL; return -1;
    }
    for(size_t i=0;i<packed;i++) {
        m->m[2*i]=(int8_t)((int)(stream[i]&15)-8);
        m->m[2*i+1]=(int8_t)((int)(stream[i]>>4)-8);
    }
    free(stream); m->n=4096; return 0;
}
int lf3_bank_openssl(ph_lf2_context_t *out,const uint8_t parent[32],unsigned workers) {
    if(!out || !parent || workers<1 || workers>8 || out->initialized) return -1;
    for(unsigned p=0;p<8;p++) if(out->matrices[p].m) return -1;
    int failed=0;
    #pragma omp parallel for num_threads(workers) reduction(|:failed) schedule(static)
    for(unsigned p=0;p<8;p++) failed |= derive(&out->matrices[p],parent,p)!=0;
    if(failed) { ph_lf2_context_free(out); return -1; }
    out->initialized=1; return 0;
}
