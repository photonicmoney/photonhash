/* Lifecycle and bounded-cache tests for v0.4.0-shadow.1. */
#include "photonhash_shadow.h"

#include <stdio.h>
#include <string.h>

static int failures;
#define CHECK(c, n) do { \
    if (c) printf("  ok      %s\n", n); \
    else { printf("  FAILED  %s\n", n); failures++; } \
} while (0)

static void derive_label(
    uint8_t output[PH_DIGEST_LEN], const char *label)
{
    ph_shake256(output, PH_DIGEST_LEN, label, strlen(label));
}

int main(void)
{
    printf("%s cache test\n\n", ph_shadow_version());
    CHECK(strcmp(ph_shadow_version(),
                 "photonhash-lf2 0.4.0-shadow.1") == 0,
          "shadow version is explicit");
    CHECK(ph_shadow_cache_init(NULL, 1u) == -1,
          "null cache is rejected");

    ph_shadow_verifier_cache_t cache;
    CHECK(ph_shadow_cache_init(&cache, 0u) == -1,
          "zero capacity is rejected");
    CHECK(ph_shadow_cache_init(
              &cache, PH_SHADOW_CACHE_MAX_PARENTS + 1u) == -1,
          "excess capacity is rejected");
    CHECK(ph_shadow_cache_init(&cache, 2u) == 0,
          "two-parent cache initializes");

    uint8_t parent_a[PH_DIGEST_LEN], parent_b[PH_DIGEST_LEN];
    uint8_t parent_c[PH_DIGEST_LEN], unknown[PH_DIGEST_LEN];
    derive_label(parent_a, "shadow-parent-a");
    derive_label(parent_b, "shadow-parent-b");
    derive_label(parent_c, "shadow-parent-c");
    derive_label(unknown, "shadow-parent-unknown");

    CHECK(ph_shadow_cache_prepare_known_parent(
              &cache, parent_a) == 1,
          "first known parent is derived");
    CHECK(ph_shadow_cache_prepare_known_parent(
              &cache, parent_a) == 0,
          "known parent cache hit avoids derivation");
    CHECK(ph_shadow_cache_prepare_known_parent(
              &cache, parent_b) == 1,
          "second known parent is derived");
    CHECK(cache.occupied == 2u, "cache is bounded at two parents");
    CHECK(ph_shadow_cache_find(&cache, parent_a) != NULL,
          "first parent is available before eviction");

    ph_lf2_workspace_t workspace;
    CHECK(ph_lf2_workspace_init(&workspace) == 0,
          "workspace initializes");
    uint8_t maximum_target[PH_DIGEST_LEN];
    memset(maximum_target, 0xff, sizeof maximum_target);
    CHECK(ph_shadow_verify_prepared(
              &cache, &workspace, parent_a,
              NULL, 0u, 0u, maximum_target) == 1,
          "prepared parent verifies");
    CHECK(ph_shadow_verify_prepared(
              &cache, &workspace, unknown,
              NULL, 0u, 0u, maximum_target) == -2,
          "unknown parent never triggers derivation");

    CHECK(ph_shadow_cache_prepare_known_parent(
              &cache, parent_c) == 1,
          "third parent replaces one bounded slot");
    CHECK(cache.occupied == 2u, "replacement does not grow memory bound");
    CHECK(ph_shadow_cache_find(&cache, parent_a) == NULL,
          "oldest parent is evicted");
    CHECK(ph_shadow_cache_find(&cache, parent_b) != NULL &&
          ph_shadow_cache_find(&cache, parent_c) != NULL,
          "newest two parents remain");

    CHECK(ph_shadow_verify_prepared(
              NULL, &workspace, parent_c,
              NULL, 0u, 0u, maximum_target) == -2,
          "invalid cache cannot verify");
    CHECK(ph_shadow_verify_prepared(
              &cache, &workspace, parent_c,
              NULL, 1u, 0u, maximum_target) == -1,
          "null non-empty header is rejected cheaply");

    ph_lf2_workspace_free(&workspace);
    ph_shadow_cache_free(&cache);
    CHECK(cache.initialized == 0 && cache.occupied == 0u,
          "cache free clears all state");

    printf("\n%d failure(s)\n", failures);
    return failures == 0 ? 0 : 1;
}
