/* Allocation-free, cooperative LF2-K8 cold verifier. Research only; MIT.
 * This is a different execution strategy for the frozen hash, not a new hash.
 * Every job owns its inputs/state. Never share a mutable job across threads.
 */
#ifndef PHOTONHASH_LF2_STREAM_H
#define PHOTONHASH_LF2_STREAM_H

#include "photonhash_launch.h"

#ifdef __cplusplus
extern "C" {
#endif

#define PH_LF2_STREAM_MAX_HEADER 4096u
#define PH_LF2_STREAM_MAX_ROWS 16u
#define PH_LF2_STREAM_MORE 0
#define PH_LF2_STREAM_DONE 1
#define PH_LF2_STREAM_ERROR (-1)
#define PH_LF2_STREAM_CANCELLED (-2)

/* Both methods reproduce LF2-K8 exactly. MOD13 is an electronic adversary:
 * the output needs bits 9..12 of the sum, so reduction modulo 8192 suffices.
 * No claim of hardware speedup follows from using fewer accumulator bits.
 */
#define PH_LF2_STREAM_INT32 0u
#define PH_LF2_STREAM_MOD13 1u

typedef struct {
    ph_shake256_t matrix_stream, checksum_stream, bank_stream;
    uint8_t parent[PH_DIGEST_LEN], h[PH_DIGEST_LEN];
    uint8_t digest[PH_DIGEST_LEN], bank[PH_DIGEST_LEN];
    uint8_t folded[PH_LF2_N / 2u], packed_row[PH_LF2_N / 2u];
    int8_t x[PH_LF2_N];
    uint32_t pass, row, method;
    int state;
    unsigned initialized;
} ph_lf2_stream_job_t;

/* Init binds/copies all inputs, performs only bounded header/vector hashing,
 * and allocates nothing. A 4096-byte header cap belongs to this shadow API,
 * not to the unrestricted LF2 mathematical function. Output buffers and input
 * buffers must not overlap the job. Zeroed/uninitialized jobs cannot step.
 */
int ph_lf2_stream_init(ph_lf2_stream_job_t *job,
    const uint8_t parent[PH_DIGEST_LEN], const uint8_t *header,
    size_t header_len, uint64_t nonce, uint32_t method);

/* Each call computes at most 1..16 complete 4096-term rows, including the
 * corresponding SHAKE matrix bytes and audit checksum. The caller schedules
 * yields and enforces parent admission, queue/rate limits and wall deadlines.
 * Invalid budgets return ERROR without changing the job. DONE is idempotent.
 */
int ph_lf2_stream_step(ph_lf2_stream_job_t *job, uint32_t rows);

/* Wipes state; cancellation is terminal until reinitialized. */
void ph_lf2_stream_cancel(ph_lf2_stream_job_t *job);

/* Returns DONE only after complete evaluation; otherwise ERROR, without
 * modifying any output. digest is required; other outputs may be NULL.
 * The bank commitment is the existing compact-vector audit artifact only.
 */
int ph_lf2_stream_result(const ph_lf2_stream_job_t *job,
    uint8_t digest[PH_DIGEST_LEN], uint8_t h[PH_DIGEST_LEN],
    uint8_t folded[PH_LF2_N / 2u], uint8_t bank[PH_DIGEST_LEN]);

#ifdef __cplusplus
}
#endif
#endif
