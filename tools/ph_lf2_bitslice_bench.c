/*
 * Exact bit-sliced LF2-K8 adversary.
 *
 * Decomposes signed four-bit values into two's-complement bitplanes and
 * replaces each dot product with 16 weighted AND-popcount reductions. This
 * probes a materially different CPU/FPGA/ASIC evaluation strategy.
 */

#include "photonhash_launch.h"

#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#ifdef _WIN32
#include <windows.h>
static double now_sec(void)
{
    LARGE_INTEGER counter, frequency;
    QueryPerformanceFrequency(&frequency);
    QueryPerformanceCounter(&counter);
    return (double)counter.QuadPart / (double)frequency.QuadPart;
}
#else
#include <time.h>
static double now_sec(void)
{
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (double)ts.tv_sec + (double)ts.tv_nsec * 1e-9;
}
#endif

#define WORD_BITS 64u
#define WORDS_PER_ROW (PH_LF2_N / WORD_BITS)
#define PLANE_WORDS \
    ((size_t)PH_LF2_PASSES * 4u * PH_LF2_N * WORDS_PER_ROW)

static const char TAG_VECTOR[] = "LASER/PhotonHash/v1/vector";
static const char TAG_FINAL[] = "LASER/PhotonHash/launch-LF2/final";

static unsigned popcount64(uint64_t value)
{
#if defined(_MSC_VER)
    return (unsigned)__popcnt64(value);
#else
    return (unsigned)__builtin_popcountll(value);
#endif
}

static void store64_le(uint8_t output[8], uint64_t value)
{
    for (unsigned index = 0; index < 8u; index++)
        output[index] = (uint8_t)(value >> (8u * index));
}

static int8_t nibble_value(const uint8_t *packed, uint32_t index)
{
    uint8_t byte = packed[index / 2u];
    uint8_t nibble = (index & 1u) == 0u ? byte & 15u : byte >> 4;
    return (int8_t)((int)nibble - 8);
}

static size_t plane_offset(uint32_t pass, unsigned bit, uint32_t row)
{
    return (((size_t)pass * 4u + bit) * PH_LF2_N + row) * WORDS_PER_ROW;
}

static int pack_matrix_planes(
    uint64_t *planes, const ph_lf2_context_t *context)
{
    memset(planes, 0, PLANE_WORDS * sizeof(*planes));
    for (uint32_t pass = 0; pass < PH_LF2_PASSES; pass++) {
        const int8_t *matrix = context->matrices[pass].m;
        for (uint32_t row = 0; row < PH_LF2_N; row++) {
            for (uint32_t column = 0; column < PH_LF2_N; column++) {
                unsigned encoded =
                    (unsigned)((uint8_t)matrix[(size_t)row * PH_LF2_N + column]) &
                    15u;
                uint64_t mask = UINT64_C(1) << (column & 63u);
                size_t word = column / WORD_BITS;
                for (unsigned bit = 0; bit < 4u; bit++)
                    if ((encoded & (1u << bit)) != 0u)
                        planes[plane_offset(pass, bit, row) + word] |= mask;
            }
        }
    }
    return 0;
}

static void derive_x(
    uint8_t h[PH_DIGEST_LEN], int8_t x[PH_LF2_N],
    const uint8_t *header, size_t header_len, uint64_t nonce)
{
    uint8_t nonce_le[8];
    uint8_t packed[PH_LF2_N / 2u];
    store64_le(nonce_le, nonce);
    ph_shake256_t shake;
    ph_shake256_init(&shake);
    ph_shake256_absorb(&shake, TAG_VECTOR, sizeof TAG_VECTOR - 1u);
    ph_shake256_absorb(&shake, header, header_len);
    ph_shake256_absorb(&shake, nonce_le, sizeof nonce_le);
    ph_shake256_squeeze(&shake, h, PH_DIGEST_LEN);
    ph_shake256(packed, sizeof packed, h, PH_DIGEST_LEN);
    for (uint32_t index = 0; index < PH_LF2_N; index++)
        x[index] = nibble_value(packed, index);
}

static void pack_x_planes(uint64_t planes[4][WORDS_PER_ROW], const int8_t *x)
{
    memset(planes, 0, 4u * WORDS_PER_ROW * sizeof(uint64_t));
    for (uint32_t column = 0; column < PH_LF2_N; column++) {
        unsigned encoded = (unsigned)((uint8_t)x[column]) & 15u;
        uint64_t mask = UINT64_C(1) << (column & 63u);
        for (unsigned bit = 0; bit < 4u; bit++)
            if ((encoded & (1u << bit)) != 0u)
                planes[bit][column / WORD_BITS] |= mask;
    }
}

static int32_t bitslice_dot(
    const uint64_t *matrix_planes, uint32_t pass, uint32_t row,
    const uint64_t *x_planes)
{
    static const int weights[4] = {1, 2, 4, -8};
    int32_t result = 0;
    for (unsigned matrix_bit = 0; matrix_bit < 4u; matrix_bit++) {
        const uint64_t *matrix =
            matrix_planes + plane_offset(pass, matrix_bit, row);
        for (unsigned vector_bit = 0; vector_bit < 4u; vector_bit++) {
            uint32_t count = 0;
            for (size_t word = 0; word < WORDS_PER_ROW; word++)
                count += popcount64(
                    matrix[word] &
                    x_planes[(size_t)vector_bit * WORDS_PER_ROW + word]);
            result += weights[matrix_bit] * weights[vector_bit] *
                      (int32_t)count;
        }
    }
    return result;
}

static void bitslice_hash(
    uint8_t digest[PH_DIGEST_LEN], uint8_t folded[PH_LF2_N / 2u],
    const uint64_t *matrix_planes,
    const uint8_t *header, size_t header_len, uint64_t nonce)
{
    uint8_t h[PH_DIGEST_LEN];
    int8_t x[PH_LF2_N];
    uint64_t x_planes[4][WORDS_PER_ROW];
    derive_x(h, x, header, header_len, nonce);
    pack_x_planes(x_planes, x);
    memset(folded, 0, PH_LF2_N / 2u);
    for (uint32_t pass = 0; pass < PH_LF2_PASSES; pass++) {
        for (uint32_t row = 0; row < PH_LF2_N; row++) {
            int32_t dot = bitslice_dot(
                matrix_planes, pass, row, &x_planes[0][0]);
            uint8_t bucket = (uint8_t)(
                ((uint32_t)(dot + 64 * (int32_t)PH_LF2_N) >> 9) & 15u);
            folded[row / 2u] ^=
                (row & 1u) == 0u ? bucket : (uint8_t)(bucket << 4);
        }
    }
    ph_shake256_t shake;
    ph_shake256_init(&shake);
    ph_shake256_absorb(&shake, TAG_FINAL, sizeof TAG_FINAL - 1u);
    ph_shake256_absorb(&shake, h, sizeof h);
    ph_shake256_absorb(&shake, folded, PH_LF2_N / 2u);
    ph_shake256_squeeze(&shake, digest, PH_DIGEST_LEN);
}

int main(int argc, char **argv)
{
    uint32_t attempts = argc > 1 ? (uint32_t)strtoul(argv[1], NULL, 10) : 3u;
    if (attempts == 0u) {
        fprintf(stderr, "usage: %s [attempts > 0]\n", argv[0]);
        return 2;
    }
    uint8_t parent[PH_DIGEST_LEN], header[80];
    ph_shake256(parent, sizeof parent, "lf2-verify-parent", 17u);
    ph_shake256(header, sizeof header, "lf2-verify-header", 17u);
    ph_lf2_context_t context;
    ph_lf2_workspace_t workspace;
    if (ph_lf2_context_init(&context, parent) != 0 ||
        ph_lf2_workspace_init(&workspace) != 0)
        return 1;

    uint64_t *matrix_planes =
        (uint64_t *)malloc(PLANE_WORDS * sizeof(*matrix_planes));
    if (!matrix_planes)
        return 1;
    double pack_started = now_sec();
    pack_matrix_planes(matrix_planes, &context);
    double pack_seconds = now_sec() - pack_started;

    uint8_t reference[PH_DIGEST_LEN], candidate[PH_DIGEST_LEN];
    uint8_t folded[PH_LF2_N / 2u];
    if (ph_lf2_hash_with_workspace(
            reference, NULL, &context, &workspace,
            header, sizeof header, 0u) != 0)
        return 1;
    bitslice_hash(candidate, folded, matrix_planes, header, sizeof header, 0u);
    if (memcmp(reference, candidate, sizeof reference) != 0 ||
        memcmp(workspace.folded, folded, sizeof folded) != 0) {
        fprintf(stderr, "bit-sliced result differs from portable oracle\n");
        return 1;
    }

    double scalar_started = now_sec();
    for (uint32_t nonce = 0; nonce < attempts; nonce++)
        ph_lf2_hash_with_workspace(
            reference, NULL, &context, &workspace,
            header, sizeof header, nonce);
    double scalar_seconds = now_sec() - scalar_started;

    double bitslice_started = now_sec();
    for (uint32_t nonce = 0; nonce < attempts; nonce++)
        bitslice_hash(candidate, folded, matrix_planes,
                      header, sizeof header, nonce);
    double bitslice_seconds = now_sec() - bitslice_started;

    printf("LF2-K8 exact bit-sliced adversary\n");
    printf("validation:           folded state and digest match\n");
    printf("packed matrix bank:   %.1f MiB\n",
           PLANE_WORDS * sizeof(*matrix_planes) / (1024.0 * 1024.0));
    printf("one-time bit packing: %.3f s\n", pack_seconds);
    printf("portable int8:        %.3f ms/attempt\n",
           scalar_seconds * 1e3 / attempts);
    printf("bit-sliced popcount:  %.3f ms/attempt\n",
           bitslice_seconds * 1e3 / attempts);
    printf("relative speed:       %.3fx\n",
           scalar_seconds / bitslice_seconds);
    printf("popcount reductions:  %zu per attempt\n",
           (size_t)PH_LF2_PASSES * PH_LF2_N * 16u * WORDS_PER_ROW);

    free(matrix_planes);
    ph_lf2_workspace_free(&workspace);
    ph_lf2_context_free(&context);
    return 0;
}
