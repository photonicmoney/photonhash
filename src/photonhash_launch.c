/* photonhash_launch.c - portable LF2-K8 research oracle. */

#include "photonhash_launch.h"

#include <stdlib.h>
#include <string.h>

static const char TAG_VECTOR[] = "LASER/PhotonHash/v1/vector";
static const char TAG_LF2_MATRIX[] =
    "LASER/PhotonHash/launch-LF2/matrix";
static const char TAG_LF2_FINAL[] =
    "LASER/PhotonHash/launch-LF2/final";

static void store64_le(uint8_t out[PH_NONCE_LEN], uint64_t value)
{
    for (unsigned i = 0; i < PH_NONCE_LEN; i++)
        out[i] = (uint8_t)(value >> (8u * i));
}

static unsigned nibble_at(const uint8_t *stream, uint32_t index)
{
    uint8_t byte = stream[index >> 1];
    return (index & 1u) != 0u ? byte >> 4 : byte & 0x0fu;
}

static int context_valid(const ph_lf2_context_t *context)
{
    if (!context || !context->initialized)
        return 0;
    for (uint32_t pass = 0; pass < PH_LF2_PASSES; pass++)
        if (!context->matrices[pass].m ||
            context->matrices[pass].n != PH_LF2_N)
            return 0;
    return 1;
}

static int workspace_valid(const ph_lf2_workspace_t *workspace)
{
    return workspace && workspace->packed_x && workspace->x &&
           workspace->folded;
}

int ph_lf2_context_init(
    ph_lf2_context_t *context,
    const uint8_t parent_hash[PH_DIGEST_LEN])
{
    if (!context || !parent_hash)
        return -1;
    memset(context, 0, sizeof(*context));
    if (ph_matrix_derive(&context->matrices[0], PH_LF2_N, parent_hash) != 0)
        return -1;

    for (uint32_t pass = 1; pass < PH_LF2_PASSES; pass++) {
        uint8_t pass_parent[PH_DIGEST_LEN];
        uint8_t pass_le[4] = {
            (uint8_t)pass,
            (uint8_t)(pass >> 8),
            (uint8_t)(pass >> 16),
            (uint8_t)(pass >> 24)
        };
        ph_shake256_t shake;
        ph_shake256_init(&shake);
        ph_shake256_absorb(
            &shake, TAG_LF2_MATRIX, sizeof TAG_LF2_MATRIX - 1u);
        ph_shake256_absorb(&shake, parent_hash, PH_DIGEST_LEN);
        ph_shake256_absorb(&shake, pass_le, sizeof pass_le);
        ph_shake256_squeeze(&shake, pass_parent, sizeof pass_parent);
        if (ph_matrix_derive(
                &context->matrices[pass], PH_LF2_N, pass_parent) != 0) {
            ph_lf2_context_free(context);
            return -1;
        }
    }
    context->initialized = 1;
    return 0;
}

void ph_lf2_context_free(ph_lf2_context_t *context)
{
    if (!context)
        return;
    for (uint32_t pass = 0; pass < PH_LF2_PASSES; pass++)
        ph_matrix_free(&context->matrices[pass]);
    memset(context, 0, sizeof(*context));
}

int ph_lf2_workspace_init(ph_lf2_workspace_t *workspace)
{
    if (!workspace)
        return -1;
    memset(workspace, 0, sizeof(*workspace));
    workspace->packed_x = (uint8_t *)malloc(PH_LF2_N / 2u);
    workspace->x = (int8_t *)malloc(PH_LF2_N);
    workspace->folded = (uint8_t *)malloc(PH_LF2_N / 2u);
    if (!workspace_valid(workspace)) {
        ph_lf2_workspace_free(workspace);
        return -1;
    }
    return 0;
}

void ph_lf2_workspace_free(ph_lf2_workspace_t *workspace)
{
    if (!workspace)
        return;
    free(workspace->packed_x);
    free(workspace->x);
    free(workspace->folded);
    memset(workspace, 0, sizeof(*workspace));
}

int ph_lf2_hash_with_workspace(
    uint8_t digest[PH_DIGEST_LEN],
    uint8_t h_in_out[PH_DIGEST_LEN],
    const ph_lf2_context_t *context,
    ph_lf2_workspace_t *workspace,
    const uint8_t *header, size_t header_len,
    uint64_t nonce)
{
    if (!digest || !context_valid(context) || !workspace_valid(workspace) ||
        (header_len != 0u && !header))
        return -1;

    uint8_t h_in[PH_DIGEST_LEN];
    uint8_t nonce_le[PH_NONCE_LEN];
    store64_le(nonce_le, nonce);
    ph_shake256_t shake;
    ph_shake256_init(&shake);
    ph_shake256_absorb(&shake, TAG_VECTOR, sizeof TAG_VECTOR - 1u);
    ph_shake256_absorb(&shake, header, header_len);
    ph_shake256_absorb(&shake, nonce_le, sizeof nonce_le);
    ph_shake256_squeeze(&shake, h_in, sizeof h_in);

    ph_shake256(
        workspace->packed_x, PH_LF2_N / 2u, h_in, sizeof h_in);
    for (uint32_t index = 0; index < PH_LF2_N; index++)
        workspace->x[index] = (int8_t)(
            (int)nibble_at(workspace->packed_x, index) - 8);

    memset(workspace->folded, 0, PH_LF2_N / 2u);
    /* n=4096: shift = 8 + floor((log2(n)-9)/2) = 9. */
    const unsigned shift = 9u;
    const int32_t offset = 64 * (int32_t)PH_LF2_N;
    for (uint32_t pass = 0; pass < PH_LF2_PASSES; pass++) {
        const int8_t *matrix = context->matrices[pass].m;
        for (uint32_t row_index = 0; row_index < PH_LF2_N; row_index++) {
            const int8_t *row =
                matrix + (size_t)row_index * PH_LF2_N;
            int32_t accumulator = 0;
            for (uint32_t column = 0; column < PH_LF2_N; column++)
                accumulator +=
                    (int32_t)row[column] * (int32_t)workspace->x[column];
            uint8_t bucket = (uint8_t)(
                ((uint32_t)(accumulator + offset) >> shift) & 0x0fu);
            if ((row_index & 1u) == 0u)
                workspace->folded[row_index / 2u] ^= bucket;
            else
                workspace->folded[row_index / 2u] ^=
                    (uint8_t)(bucket << 4);
        }
    }

    ph_shake256_init(&shake);
    ph_shake256_absorb(
        &shake, TAG_LF2_FINAL, sizeof TAG_LF2_FINAL - 1u);
    ph_shake256_absorb(&shake, h_in, sizeof h_in);
    ph_shake256_absorb(&shake, workspace->folded, PH_LF2_N / 2u);
    ph_shake256_squeeze(&shake, digest, PH_DIGEST_LEN);
    if (h_in_out)
        memcpy(h_in_out, h_in, sizeof h_in);
    return 0;
}

int ph_lf2_hash(
    uint8_t digest[PH_DIGEST_LEN],
    uint8_t h_in[PH_DIGEST_LEN],
    const ph_lf2_context_t *context,
    const uint8_t *header, size_t header_len,
    uint64_t nonce)
{
    ph_lf2_workspace_t workspace;
    if (ph_lf2_workspace_init(&workspace) != 0)
        return -1;
    int result = ph_lf2_hash_with_workspace(
        digest, h_in, context, &workspace, header, header_len, nonce);
    ph_lf2_workspace_free(&workspace);
    return result;
}

int ph_lf2_verify_with_workspace(
    const ph_lf2_context_t *context,
    ph_lf2_workspace_t *workspace,
    const uint8_t *header, size_t header_len,
    uint64_t nonce,
    const uint8_t target[PH_DIGEST_LEN])
{
    uint8_t digest[PH_DIGEST_LEN];
    if (!target || ph_lf2_hash_with_workspace(
            digest, NULL, context, workspace,
            header, header_len, nonce) != 0)
        return -1;
    return ph_meets_target(digest, target);
}
