/* Isolated C20 network laboratory backend. MIT. No Laser integration. */
#ifndef STAGE1_NETWORK_CACHE_H
#define STAGE1_NETWORK_CACHE_H
#include <stddef.h>
#include <stdint.h>
#define NF_BANK_SLOTS 2u
#define NF_PARENTS 16u
typedef struct { uint64_t derivations,verifications,evictions,resident,high_water,coefficient_bytes,errors; } nf_metrics;
void *nf_new(void);
void nf_free(void *state);
/* Trusted startup only. The network protocol never exposes this operation. */
int nf_allow(void *state,unsigned index,const uint8_t parent[32],const uint8_t target[32]);
/* A SINGLE native worker owns state. No simultaneous calls, including metrics.
 * Returns 1 valid, 0 invalid, 2 unknown parent, -1 internal/malformed. */
int nf_eval(void *state,const uint8_t parent[32],const uint8_t *header,size_t length,
            uint64_t nonce,uint8_t digest[32],uint8_t h[32],uint8_t fold[2048]);
void nf_snapshot(void *state,nf_metrics *out);
#endif
