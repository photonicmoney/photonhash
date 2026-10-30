/* Standalone serialized admission research. Not a network/consensus API. MIT. */
#ifndef LF3_ADMISSION_LAB_H
#define LF3_ADMISSION_LAB_H
#include "bank_openssl.h"
#define LAB_PARENTS 16u
#define LAB_PEERS 16u
#define LAB_BANKS 2u
enum { LAB_VALID=1,LAB_INVALID=0,LAB_MALFORMED=-1,LAB_UNKNOWN_PARENT=-2,
       LAB_RATE_LIMIT=-3,LAB_ERROR=-4,LAB_BUSY=-5 };
typedef struct { uint8_t hash[32],target[32]; int used; } lab_parent;
typedef struct { ph_lf2_context_t bank;uint8_t parent[32];uint64_t stamp;int used; } lab_slot;
typedef struct {
    lab_parent parents[LAB_PARENTS];lab_slot slots[LAB_BANKS];
    unsigned peer_used[LAB_PEERS],global_used,cold_used;uint64_t epoch,stamp;
    uint64_t derivations,verifications,evictions,unknown_rejects,rate_rejects;
    unsigned workers;int busy;
} admission_lab;
void lab_init(admission_lab *lab,unsigned workers);
void lab_free(admission_lab *lab);
/* Trusted harness operations ONLY. A network caller must not expose these. */
int lab_allow_parent(admission_lab *lab,unsigned slot,const uint8_t parent[32],const uint8_t target[32]);
int lab_advance(admission_lab *lab,uint64_t monotonic_second);
/* Called by a single owner thread; peer slot is allocated by trusted adapter.
 * Quotas: four hashes/second globally, two/peer, one cold bank globally.
 * Request carries no target, parent-admission command, time or cache policy. */
int lab_verify(admission_lab *lab,unsigned peer,const uint8_t parent[32],
               const uint8_t *header,size_t length,uint64_t nonce,uint8_t digest[32]);
#endif
