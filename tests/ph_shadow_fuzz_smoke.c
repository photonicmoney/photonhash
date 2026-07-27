/* Deterministic API and differential smoke-fuzzing for the shadow profile. */
#include "photonhash_shadow.h"

#include <inttypes.h>
#include <stdio.h>
#include <string.h>

static uint64_t rng_state = UINT64_C(0x7d0c5a4b1938e2f1);

static uint64_t next_u64(void)
{
    uint64_t value = rng_state;
    value ^= value << 13;
    value ^= value >> 7;
    value ^= value << 17;
    rng_state = value;
    return value;
}

static void increment_le(uint8_t value[PH_DIGEST_LEN])
{
    for (size_t index = 0; index < PH_DIGEST_LEN; index++) {
        value[index]++;
        if (value[index] != 0u)
            break;
    }
}

int main(void)
{
    uint8_t parent[PH_DIGEST_LEN];
    ph_shake256(parent, sizeof parent,
                "v0.4-shadow-fuzz-parent", 23u);
    ph_lf2_context_t context;
    ph_lf2_workspace_t workspace;
    if (ph_lf2_context_init(&context, parent) != 0 ||
        ph_lf2_workspace_init(&workspace) != 0)
        return 1;

    uint8_t header[513];
    unsigned failures = 0u;
    const unsigned cases = 128u;
    for (unsigned case_index = 0; case_index < cases; case_index++) {
        size_t header_len = (size_t)(next_u64() % sizeof header);
        for (size_t index = 0; index < header_len; index++)
            header[index] = (uint8_t)next_u64();
        uint64_t nonce = next_u64();
        uint8_t digest_a[PH_DIGEST_LEN], digest_b[PH_DIGEST_LEN];
        uint8_t h_a[PH_DIGEST_LEN], h_b[PH_DIGEST_LEN];
        if (ph_lf2_hash_with_workspace(
                digest_a, h_a, &context, &workspace,
                header, header_len, nonce) != 0 ||
            ph_lf2_hash(
                digest_b, h_b, &context,
                header, header_len, nonce) != 0 ||
            memcmp(digest_a, digest_b, sizeof digest_a) != 0 ||
            memcmp(h_a, h_b, sizeof h_a) != 0)
            failures++;

        uint8_t target[PH_DIGEST_LEN];
        memcpy(target, digest_a, sizeof target);
        if (ph_lf2_verify_with_workspace(
                &context, &workspace, header, header_len,
                nonce, target) != 0)
            failures++;
        increment_le(target);
        if (memcmp(target, digest_a, sizeof target) != 0 &&
            ph_lf2_verify_with_workspace(
                &context, &workspace, header, header_len,
                nonce, target) != 1)
            failures++;
    }

    if (ph_lf2_hash_with_workspace(
            NULL, NULL, &context, &workspace,
            header, sizeof header, 0u) != -1 ||
        ph_lf2_hash_with_workspace(
            header, NULL, &context, &workspace,
            NULL, 1u, 0u) != -1)
        failures++;

    ph_lf2_workspace_free(&workspace);
    ph_lf2_context_free(&context);
    printf("%s deterministic fuzz smoke: %u cases, %u failures\n",
           ph_shadow_version(), cases, failures);
    return failures == 0u ? 0 : 1;
}
