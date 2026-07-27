/* Known-answer and API tests for the non-consensus LF2-K8 research oracle. */

#include "photonhash_launch.h"

#include <inttypes.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static int failures = 0;

#define CHECK(condition, name)                                  \
    do {                                                        \
        if (condition)                                          \
            printf("  ok      %s\n", name);                    \
        else {                                                  \
            printf("  FAILED  %s\n", name);                    \
            failures++;                                         \
        }                                                       \
    } while (0)

static void hex_to_bytes(uint8_t *output, const char *hex, size_t length)
{
    for (size_t i = 0; i < length; i++) {
        unsigned value = 0;
        if (sscanf(hex + 2u * i, "%2x", &value) != 1)
            exit(2);
        output[i] = (uint8_t)value;
    }
}

static void increment_le(uint8_t value[PH_DIGEST_LEN])
{
    for (size_t i = 0; i < PH_DIGEST_LEN; i++) {
        value[i]++;
        if (value[i] != 0u)
            return;
    }
}

int main(void)
{
    printf("PhotonHash LF2-K8 research self-test\n\n");
    CHECK(PH_LF2_N == 4096u, "dimension is frozen at 4096");
    CHECK(PH_LF2_PASSES == 8u, "matrix count is frozen at eight");

    uint8_t parent[PH_DIGEST_LEN], header[80];
    ph_shake256(parent, sizeof parent, "lf2-verify-parent", 17u);
    ph_shake256(header, sizeof header, "lf2-verify-header", 17u);

    ph_lf2_context_t context;
    CHECK(ph_lf2_context_init(&context, parent) == 0,
          "derive 128 MiB parent matrix bank");
    CHECK(context.initialized == 1, "context is marked initialized");
    for (uint32_t pass = 0; pass < PH_LF2_PASSES; pass++)
        CHECK(context.matrices[pass].n == PH_LF2_N &&
              context.matrices[pass].m != NULL,
              "matrix pass is initialized");

    ph_lf2_workspace_t workspace;
    CHECK(ph_lf2_workspace_init(&workspace) == 0,
          "allocate reusable workspace");

    uint8_t expected[PH_DIGEST_LEN], digest[PH_DIGEST_LEN];
    hex_to_bytes(
        expected,
        "b27eeaf6a1116b77d1aadb79467b4ca18"
        "d92cf83b3556fbbca0c684de7f8585e",
        PH_DIGEST_LEN);
    CHECK(ph_lf2_hash_with_workspace(
              digest, NULL, &context, &workspace,
              header, sizeof header, 4u) == 0,
          "hash known-answer nonce");
    CHECK(memcmp(digest, expected, PH_DIGEST_LEN) == 0,
          "known-answer digest matches CUDA/scalar oracle");

    uint8_t target[PH_DIGEST_LEN];
    memcpy(target, digest, sizeof target);
    CHECK(ph_lf2_verify_with_workspace(
              &context, &workspace, header, sizeof header, 4u, target) == 0,
          "strict target rejects equality");
    increment_le(target);
    CHECK(ph_lf2_verify_with_workspace(
              &context, &workspace, header, sizeof header, 4u, target) == 1,
          "strict target accepts digest below target");

    uint8_t maximum_a[PH_DIGEST_LEN], maximum_b[PH_DIGEST_LEN];
    CHECK(ph_lf2_hash_with_workspace(
              maximum_a, NULL, &context, &workspace,
              NULL, 0u, UINT64_MAX) == 0,
          "empty header and maximum nonce are accepted");
    CHECK(ph_lf2_hash(
              maximum_b, NULL, &context, NULL, 0u, UINT64_MAX) == 0,
          "one-shot convenience path succeeds");
    CHECK(memcmp(maximum_a, maximum_b, PH_DIGEST_LEN) == 0,
          "workspace and convenience paths agree");
    CHECK(memcmp(maximum_a, digest, PH_DIGEST_LEN) != 0,
          "distinct input changes the digest");

    CHECK(ph_lf2_hash_with_workspace(
              NULL, NULL, &context, &workspace,
              header, sizeof header, 0u) == -1,
          "null digest is rejected");
    CHECK(ph_lf2_hash_with_workspace(
              digest, NULL, &context, &workspace,
              NULL, 1u, 0u) == -1,
          "null non-empty header is rejected");
    CHECK(ph_lf2_context_init(NULL, parent) == -1,
          "null context is rejected");
    CHECK(ph_lf2_workspace_init(NULL) == -1,
          "null workspace is rejected");

    ph_lf2_workspace_free(&workspace);
    ph_lf2_context_free(&context);
    CHECK(context.initialized == 0, "context free clears state");

    printf("\n%d failure(s)\n", failures);
    return failures == 0 ? 0 : 1;
}
