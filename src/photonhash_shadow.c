/* Bounded non-consensus verifier lifecycle for v0.4.0-shadow.1. */
#include "photonhash_shadow.h"

#include <string.h>

const char *ph_shadow_version(void)
{
    return "photonhash-lf2 0.4.0-shadow.1";
}

static int cache_valid(const ph_shadow_verifier_cache_t *cache)
{
    return cache && cache->initialized &&
           cache->capacity >= 1u &&
           cache->capacity <= PH_SHADOW_CACHE_MAX_PARENTS &&
           cache->occupied <= cache->capacity;
}

int ph_shadow_cache_init(
    ph_shadow_verifier_cache_t *cache, uint32_t capacity)
{
    if (!cache || capacity == 0u ||
        capacity > PH_SHADOW_CACHE_MAX_PARENTS)
        return -1;
    memset(cache, 0, sizeof(*cache));
    cache->capacity = capacity;
    cache->initialized = 1;
    return 0;
}

void ph_shadow_cache_free(ph_shadow_verifier_cache_t *cache)
{
    if (!cache)
        return;
    for (uint32_t index = 0;
         index < PH_SHADOW_CACHE_MAX_PARENTS; index++) {
        if (cache->slots[index].occupied)
            ph_lf2_context_free(&cache->slots[index].context);
    }
    memset(cache, 0, sizeof(*cache));
}

const ph_lf2_context_t *ph_shadow_cache_find(
    const ph_shadow_verifier_cache_t *cache,
    const uint8_t parent_hash[PH_DIGEST_LEN])
{
    if (!cache_valid(cache) || !parent_hash)
        return NULL;
    for (uint32_t index = 0; index < cache->capacity; index++) {
        const ph_shadow_cache_slot_t *slot = &cache->slots[index];
        if (slot->occupied &&
            memcmp(slot->parent_hash, parent_hash, PH_DIGEST_LEN) == 0)
            return &slot->context;
    }
    return NULL;
}

int ph_shadow_cache_prepare_known_parent(
    ph_shadow_verifier_cache_t *cache,
    const uint8_t parent_hash[PH_DIGEST_LEN])
{
    if (!cache_valid(cache) || !parent_hash)
        return -1;
    if (ph_shadow_cache_find(cache, parent_hash))
        return 0;

    uint32_t selected = cache->capacity;
    uint64_t oldest = UINT64_MAX;
    for (uint32_t index = 0; index < cache->capacity; index++) {
        ph_shadow_cache_slot_t *slot = &cache->slots[index];
        if (!slot->occupied) {
            selected = index;
            break;
        }
        if (slot->generation < oldest) {
            oldest = slot->generation;
            selected = index;
        }
    }
    if (selected >= cache->capacity)
        return -1;

    ph_shadow_cache_slot_t *slot = &cache->slots[selected];
    if (slot->occupied) {
        ph_lf2_context_free(&slot->context);
        cache->occupied--;
    }
    memset(slot, 0, sizeof(*slot));
    /*
     * Derive only after eviction. This keeps the strict two-bank allocation
     * ceiling during replacement instead of temporarily owning a third bank.
     * On allocation failure the selected slot intentionally remains empty.
     */
    if (ph_lf2_context_init(&slot->context, parent_hash) != 0)
        return -1;
    memcpy(slot->parent_hash, parent_hash, PH_DIGEST_LEN);
    cache->generation++;
    slot->generation = cache->generation;
    slot->occupied = 1;
    cache->occupied++;
    return 1;
}

int ph_shadow_verify_prepared(
    const ph_shadow_verifier_cache_t *cache,
    ph_lf2_workspace_t *workspace,
    const uint8_t parent_hash[PH_DIGEST_LEN],
    const uint8_t *header, size_t header_len,
    uint64_t nonce,
    const uint8_t target[PH_DIGEST_LEN])
{
    if (!workspace || !parent_hash || !target ||
        (header_len != 0u && !header))
        return -1;
    const ph_lf2_context_t *context =
        ph_shadow_cache_find(cache, parent_hash);
    if (!context)
        return -2;
    return ph_lf2_verify_with_workspace(
        context, workspace, header, header_len, nonce, target);
}
