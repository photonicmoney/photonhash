/*
 * Non-consensus LF2-K8 parent-transition soak. This deliberately does not
 * import or modify Laser consensus code.
 */
#define _POSIX_C_SOURCE 200809L
#include "photonhash_launch.h"
#include <inttypes.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

static double now_seconds(void)
{
#if defined(_WIN32)
    return (double)clock() / (double)CLOCKS_PER_SEC;
#else
    struct timespec ts;
    if (clock_gettime(CLOCK_MONOTONIC, &ts) != 0) return 0.0;
    return (double)ts.tv_sec + (double)ts.tv_nsec / 1e9;
#endif
}

static void parent_for_tip(uint8_t parent[PH_DIGEST_LEN], uint32_t tip)
{
    char label[64];
    int written = snprintf(label, sizeof label,
        "LF2 shadow parent %" PRIu32, tip);
    if (written < 0 || (size_t)written >= sizeof label) abort();
    ph_shake256(parent, PH_DIGEST_LEN,
        (const uint8_t *)label, (size_t)written);
}

static void header_for_tip(uint8_t header[80], uint32_t tip)
{
    memset(header, 0, 80u);
    for (size_t i = 0; i < 80u; i++)
        header[i] = (uint8_t)(tip * 29u + (uint32_t)i * 17u);
}

int main(int argc, char **argv)
{
    uint32_t tips = 12u, attempts = 2u;
    if (argc > 1) tips = (uint32_t)strtoul(argv[1], NULL, 10);
    if (argc > 2) attempts = (uint32_t)strtoul(argv[2], NULL, 10);
    if (tips < 2u || attempts == 0u) {
        fprintf(stderr, "usage: %s [tips>=2] [attempts-per-tip>=1]\n", argv[0]);
        return 2;
    }
    ph_lf2_workspace_t workspace;
    if (ph_lf2_workspace_init(&workspace) != 0) return 1;
    double setup_total = 0.0, setup_max = 0.0, hash_total = 0.0;
    uint64_t hash_count = 0u;
    uint32_t stale_collisions = 0u;
    uint8_t transcript[PH_DIGEST_LEN] = {0};

    for (uint32_t tip = 0; tip < tips; tip++) {
        uint8_t parent[PH_DIGEST_LEN], header[80];
        parent_for_tip(parent, tip);
        header_for_tip(header, tip);
        ph_lf2_context_t context;
        double start = now_seconds();
        if (ph_lf2_context_init(&context, parent) != 0) return 1;
        double elapsed = now_seconds() - start;
        setup_total += elapsed;
        if (elapsed > setup_max) setup_max = elapsed;
        for (uint32_t attempt = 0; attempt < attempts; attempt++) {
            uint8_t digest[PH_DIGEST_LEN];
            start = now_seconds();
            if (ph_lf2_hash_with_workspace(digest, NULL, &context, &workspace,
                    header, sizeof header,
                    ((uint64_t)tip << 32) | attempt) != 0) return 1;
            hash_total += now_seconds() - start;
            hash_count++;
            for (size_t i = 0; i < PH_DIGEST_LEN; i++)
                transcript[i] ^= digest[i];
        }
        if (tip + 1u < tips) {
            uint8_t next_parent[PH_DIGEST_LEN], next_header[80];
            uint8_t old_digest[PH_DIGEST_LEN], new_digest[PH_DIGEST_LEN];
            ph_lf2_context_t next_context;
            parent_for_tip(next_parent, tip + 1u);
            header_for_tip(next_header, tip + 1u);
            if (ph_lf2_context_init(&next_context, next_parent) != 0 ||
                ph_lf2_hash_with_workspace(old_digest, NULL, &context,
                    &workspace, next_header, sizeof next_header, 0u) != 0 ||
                ph_lf2_hash_with_workspace(new_digest, NULL, &next_context,
                    &workspace, next_header, sizeof next_header, 0u) != 0)
                return 1;
            if (memcmp(old_digest, new_digest, PH_DIGEST_LEN) == 0)
                stale_collisions++;
            ph_lf2_context_free(&next_context);
        }
        ph_lf2_context_free(&context);
    }
    printf("LF2-K8 non-consensus shadow soak\n");
    printf("tips: %" PRIu32 "\n", tips);
    printf("attempts per tip: %" PRIu32 "\n", attempts);
    printf("cold setup mean ms: %.3f\n", 1000.0 * setup_total / tips);
    printf("cold setup max ms: %.3f\n", 1000.0 * setup_max);
    printf("cached attempt mean ms: %.3f\n",
        1000.0 * hash_total / (double)hash_count);
    printf("stale-parent digest collisions: %" PRIu32 "\n", stale_collisions);
    printf("transcript: ");
    for (size_t i = 0; i < PH_DIGEST_LEN; i++) printf("%02x", transcript[i]);
    printf("\n");
    ph_lf2_workspace_free(&workspace);
    return stale_collisions == 0u ? 0 : 1;
}
