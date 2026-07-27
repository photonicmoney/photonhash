/*
 * PhotonHash v0.4.0-shadow.1 - non-consensus LF2-K8 shadownet support.
 *
 * This wrapper adds bounded verifier lifecycle management around the frozen
 * LF2-K8 construction. It does not modify Laser consensus.
 */
#ifndef PHOTONHASH_SHADOW_H
#define PHOTONHASH_SHADOW_H

#include "photonhash_launch.h"

#ifdef __cplusplus
extern "C" {
#endif

#define PH_SHADOW_VERSION "0.4.0-shadow.1"
#define PH_SHADOW_CACHE_MAX_PARENTS 2u

typedef struct {
    uint8_t parent_hash[PH_DIGEST_LEN];
    ph_lf2_context_t context;
    uint64_t generation;
    int occupied;
} ph_shadow_cache_slot_t;

typedef struct {
    ph_shadow_cache_slot_t slots[PH_SHADOW_CACHE_MAX_PARENTS];
    uint32_t capacity;
    uint32_t occupied;
    uint64_t generation;
    int initialized;
} ph_shadow_verifier_cache_t;

/* Returns the shadow-candidate release identity. */
const char *ph_shadow_version(void);

/*
 * Initializes an empty bounded cache. Capacity must be one or two.
 * A populated two-parent cache owns approximately 256 MiB and replacement
 * evicts before deriving so it never intentionally allocates a third bank.
 */
int ph_shadow_cache_init(
    ph_shadow_verifier_cache_t *cache, uint32_t capacity);
void ph_shadow_cache_free(ph_shadow_verifier_cache_t *cache);

/*
 * Prepares a matrix bank only for a parent already admitted by the caller.
 * Returns 0 for a cache hit, 1 for a newly derived bank, and -1 on error.
 *
 * Replacement evicts the oldest slot before allocation; an allocation failure
 * therefore leaves that slot empty. This deliberately does not derive from
 * untrusted arbitrary parent hashes
 * inside verification. Callers must perform cheap chain/header admission
 * first, then serialize cache mutation.
 */
int ph_shadow_cache_prepare_known_parent(
    ph_shadow_verifier_cache_t *cache,
    const uint8_t parent_hash[PH_DIGEST_LEN]);

/*
 * Returns a borrowed immutable context, or NULL if the parent is not ready.
 * The pointer remains valid only until cache mutation or free. Concurrent
 * hashing is safe with one workspace per thread while mutation is excluded.
 */
const ph_lf2_context_t *ph_shadow_cache_find(
    const ph_shadow_verifier_cache_t *cache,
    const uint8_t parent_hash[PH_DIGEST_LEN]);

/*
 * Verifies against a prepared parent. Returns 1 for a valid target, 0 for a
 * computed non-solution, -1 for invalid arguments, and -2 for a cache miss.
 */
int ph_shadow_verify_prepared(
    const ph_shadow_verifier_cache_t *cache,
    ph_lf2_workspace_t *workspace,
    const uint8_t parent_hash[PH_DIGEST_LEN],
    const uint8_t *header, size_t header_len,
    uint64_t nonce,
    const uint8_t target[PH_DIGEST_LEN]);

#ifdef __cplusplus
}
#endif

#endif
