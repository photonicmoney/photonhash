/* LF3-K8-C20-experiment.1: unselected research profile, NOT LF2-K8. MIT. */
#ifndef PHOTONHASH_LF3_C20_H
#define PHOTONHASH_LF3_C20_H
#include "photonhash_lf2_stream.h"
#ifdef __cplusplus
extern "C" {
#endif
#define PH_LF3_C20_PROFILE "LF3-K8-C20-experiment.1"
typedef struct {
    ph_lf2_stream_job_t core;
    uint8_t digest[32];
    int finalized;
} ph_lf3_c20_job_t;

/* RFC 8439 section 2.3 block function, exposed for differential testing only. */
int ph_lf3_c20_block(uint8_t out[64], const uint8_t key[32],
    const uint8_t nonce[12], uint32_t counter);

/* New vector/final tags; same parent matrices, n/K/quantizer/full XOR fold.
 * x = signed_nibbles(ChaCha20(key=h, nonce=0^96, counters=1..32)).
 * Same input ownership, header limit, step limits and cancellation as LF2.
 * This cold reference deliberately reuses the LF2 core and discards its
 * transient legacy binding/expansion/final digest. It is NOT a benchmark.
 */
int ph_lf3_c20_init(ph_lf3_c20_job_t *job, const uint8_t parent[32],
    const uint8_t *header, size_t header_len, uint64_t nonce, uint32_t method);
int ph_lf3_c20_step(ph_lf3_c20_job_t *job, uint32_t rows);
int ph_lf3_c20_result(const ph_lf3_c20_job_t *job, uint8_t digest[32]);
void ph_lf3_c20_cancel(ph_lf3_c20_job_t *job);
#ifdef __cplusplus
}
#endif
#endif
