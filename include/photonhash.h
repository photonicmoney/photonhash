/*
 * photonhash.h — PhotonHash reference implementation (public API)
 *
 * Implements the PhotonHash proof-of-work function of the Laser blockchain,
 * per "PhotonHash: Technical Specification" v0.2.
 *
 * This is the digital reference: exact integer arithmetic, deterministic
 * across platforms. Where prose in the specification is ambiguous, the
 * behavior of this implementation is a review oracle. Neither the prose nor
 * implementation is normative while this release remains experimental.
 *
 * Author: Lightman
 * License: MIT
 */

#ifndef PHOTONHASH_H
#define PHOTONHASH_H

#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/* ------------------------------------------------------------------ */
/* Constants                                                           */
/* ------------------------------------------------------------------ */

#define PH_DIGEST_LEN   32   /* all digests are 32-byte SHAKE256 outputs   */
#define PH_SEED_LEN     64   /* matrix seed length (spec 5.1)              */
#define PH_NONCE_LEN     8   /* nonce serialized as 8-byte little-endian   */

/* Genesis matrix dimension (spec 3, provisional). */
#define PH_GENESIS_N  1024u

/* ------------------------------------------------------------------ */
/* SHAKE256 (exposed for tests and tooling)                            */
/* ------------------------------------------------------------------ */

typedef struct {
    uint64_t st[25];
    uint8_t  buf[136];          /* rate for SHAKE256 = 136 bytes */
    size_t   pos;
    int      squeezing;
} ph_shake256_t;

void ph_shake256_init(ph_shake256_t *c);
void ph_shake256_absorb(ph_shake256_t *c, const void *data, size_t len);
void ph_shake256_squeeze(ph_shake256_t *c, void *out, size_t len);
/* One-shot convenience. */
void ph_shake256(void *out, size_t outlen, const void *in, size_t inlen);

/* ------------------------------------------------------------------ */
/* Matrix (per block template — spec 5.1)                              */
/* ------------------------------------------------------------------ */

typedef struct {
    uint32_t n;                       /* dimension                       */
    int8_t  *m;                       /* n*n entries, row-major, [-8,7]  */
    uint8_t  seed[PH_SEED_LEN];       /* seed_M, retained for audit      */
    uint8_t  checksum[PH_DIGEST_LEN]; /* SHAKE256 of the raw nibble stream */
} ph_matrix_t;

/*
 * Derive M from the previous block's hash. Allocates M->m (n*n bytes).
 * Returns 0 on success, -1 on allocation failure, invalid arguments, or n
 * (n must be a power of two mapping to a defined era:
 * 1024 <= n <= 1<<20, per spec section 8). Dimensions whose matrix size
 * cannot be represented by size_t on the host are rejected.
 */
int  ph_matrix_derive(ph_matrix_t *M, uint32_t n,
                      const uint8_t prev_block_hash[PH_DIGEST_LEN]);
void ph_matrix_free(ph_matrix_t *M);

/* The active v0.2 experimental profile fixes n at PH_GENESIS_N. */
uint32_t ph_dim_for_height(uint64_t height);

/* ------------------------------------------------------------------ */
/* Pipeline (spec 5.2–5.4)                                             */
/* ------------------------------------------------------------------ */

/*
 * Full PhotonHash evaluation for one attempt.
 *
 *   header      — block header WITHOUT the nonce field
 *   nonce       — serialized internally as 8-byte little-endian
 *   d_out       — final digest (spec 5.4)
 *   h_in_out    — binding digest (spec 5.2); may be NULL if not wanted
 *
 * Scratch buffers are managed internally; the function is thread-safe
 * with respect to a shared, immutable ph_matrix_t.
 * Returns 0 on success, -1 on allocation failure or invalid arguments.
 */
int ph_hash(uint8_t d_out[PH_DIGEST_LEN],
            uint8_t h_in_out[PH_DIGEST_LEN],
            const ph_matrix_t *M,
            const uint8_t *header, size_t header_len,
            uint64_t nonce);

/*
 * Expanded evaluation for tooling and vector generation: also writes the
 * derived vector x (n entries), exact product y (n entries), and packed
 * requantized output r (n/2 bytes). Buffers must be caller-allocated with
 * those sizes, any of them may be NULL to skip.
 */
int ph_hash_trace(uint8_t d_out[PH_DIGEST_LEN],
                  uint8_t h_in_out[PH_DIGEST_LEN],
                  int8_t *x_out, int32_t *y_out, uint8_t *r_out,
                  const ph_matrix_t *M,
                  const uint8_t *header, size_t header_len,
                  uint64_t nonce);

/*
 * target comparison: little_endian_uint256(d) < little_endian_uint256(t)
 * Returns 1 if d beats the target, 0 otherwise. Not constant-time
 * (targets and digests are public).
 */
int ph_meets_target(const uint8_t d[PH_DIGEST_LEN],
                    const uint8_t target[PH_DIGEST_LEN]);

/*
 * Verify with a caller-owned matrix already derived for the claimed parent.
 * This is the normal path for miners, nodes validating sibling candidates,
 * and DoS measurements that must not charge matrix setup to every attempt.
 * Returns 1 valid, 0 invalid, -1 on error.
 */
int ph_verify_with_matrix(const ph_matrix_t *M,
                          const uint8_t *header, size_t header_len,
                          uint64_t nonce,
                          const uint8_t target[PH_DIGEST_LEN]);

/*
 * Full verification of a claimed solution: derives M for prev_block_hash
 * at the dimension implied by height, evaluates the pipeline, checks the
 * target. Returns 1 valid, 0 invalid, -1 on error.
 * A verifier at a fixed tip should derive M once and call
 * ph_verify_with_matrix; this helper is for one-shot use.
 */
int ph_verify(const uint8_t prev_block_hash[PH_DIGEST_LEN],
              uint64_t height,
              const uint8_t *header, size_t header_len,
              uint64_t nonce,
              const uint8_t target[PH_DIGEST_LEN]);

/* Library version string. */
const char *ph_version(void);

#ifdef __cplusplus
}
#endif

#endif /* PHOTONHASH_H */
