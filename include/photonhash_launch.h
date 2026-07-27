/*
 * photonhash_launch.h - non-consensus LF2-K8 research API.
 *
 * This API is intentionally separate from frozen PhotonHash v0.2. It is a
 * review target for the launch-profile program, not Laser consensus code.
 */

#ifndef PHOTONHASH_LAUNCH_H
#define PHOTONHASH_LAUNCH_H

#include "photonhash.h"

#ifdef __cplusplus
extern "C" {
#endif

#define PH_LF2_N       4096u
#define PH_LF2_PASSES     8u

typedef struct {
    ph_matrix_t matrices[PH_LF2_PASSES];
    int initialized;
} ph_lf2_context_t;

typedef struct {
    uint8_t *packed_x;
    int8_t *x;
    uint8_t *folded;
} ph_lf2_workspace_t;

/* Derives and caches the 128 MiB parent matrix bank. */
int ph_lf2_context_init(
    ph_lf2_context_t *context,
    const uint8_t parent_hash[PH_DIGEST_LEN]);
void ph_lf2_context_free(ph_lf2_context_t *context);

/* A workspace is reusable by one caller/thread across nonce attempts. */
int ph_lf2_workspace_init(ph_lf2_workspace_t *workspace);
void ph_lf2_workspace_free(ph_lf2_workspace_t *workspace);

int ph_lf2_hash_with_workspace(
    uint8_t digest[PH_DIGEST_LEN],
    uint8_t h_in[PH_DIGEST_LEN],
    const ph_lf2_context_t *context,
    ph_lf2_workspace_t *workspace,
    const uint8_t *header, size_t header_len,
    uint64_t nonce);

/* Convenience wrapper that allocates scratch for one call. */
int ph_lf2_hash(
    uint8_t digest[PH_DIGEST_LEN],
    uint8_t h_in[PH_DIGEST_LEN],
    const ph_lf2_context_t *context,
    const uint8_t *header, size_t header_len,
    uint64_t nonce);

int ph_lf2_verify_with_workspace(
    const ph_lf2_context_t *context,
    ph_lf2_workspace_t *workspace,
    const uint8_t *header, size_t header_len,
    uint64_t nonce,
    const uint8_t target[PH_DIGEST_LEN]);

#ifdef __cplusplus
}
#endif

#endif
