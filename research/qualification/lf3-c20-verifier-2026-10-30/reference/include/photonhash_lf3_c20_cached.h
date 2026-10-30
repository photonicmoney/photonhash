/* Local experiment verifier with an explicitly supplied, already-derived bank.
 * No cache admission, target policy or consensus integration is implied. MIT. */
#ifndef PHOTONHASH_LF3_C20_CACHED_H
#define PHOTONHASH_LF3_C20_CACHED_H
#include "photonhash_launch.h"
#ifdef __cplusplus
extern "C" {
#endif
int ph_lf3_c20_hash_cached(uint8_t digest[32], uint8_t h[32],
    uint8_t fold[2048], const ph_lf2_context_t *bank,
    const uint8_t *header, size_t length, uint64_t nonce);
#ifdef __cplusplus
}
#endif
#endif
