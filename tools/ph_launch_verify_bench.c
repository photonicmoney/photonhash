/*
 * ph_launch_verify_bench.c - cached-verifier cost screen for LF2.
 *
 * This is a research oracle, not a consensus implementation. It evaluates
 * the exact feed-forward LF2 experiment used by ph_cuda_bench.cu:
 * one nonce vector, a parent-derived matrix bank, nibble requantization,
 * XOR folding, and one final SHAKE256 digest.
 */

#include "photonhash.h"

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

static const char TAG_VECTOR[] = "LASER/PhotonHash/v1/vector";
static const char TAG_LF2_MATRIX[] =
    "LASER/PhotonHash/launch-LF2/matrix";
static const char TAG_LF2_FINAL[] =
    "LASER/PhotonHash/launch-LF2/final";

static void store64_le(uint8_t out[8], uint64_t value)
{
    for (unsigned i = 0; i < 8u; i++)
        out[i] = (uint8_t)(value >> (8u * i));
}

static unsigned nibble_at(const uint8_t *stream, uint32_t index)
{
    uint8_t byte = stream[index >> 1];
    return (index & 1u) != 0u ? byte >> 4 : byte & 0x0fu;
}

static unsigned log2_u32(uint32_t value)
{
    unsigned result = 0;
    while ((value >>= 1) != 0u)
        result++;
    return result;
}

static int derive_matrix_bank(ph_matrix_t *matrices, uint32_t n,
                              uint32_t passes,
                              const uint8_t parent[PH_DIGEST_LEN])
{
    if (ph_matrix_derive(&matrices[0], n, parent) != 0)
        return -1;
    for (uint32_t pass = 1; pass < passes; pass++) {
        uint8_t pass_parent[PH_DIGEST_LEN];
        uint8_t pass_le[4] = {
            (uint8_t)pass, (uint8_t)(pass >> 8),
            (uint8_t)(pass >> 16), (uint8_t)(pass >> 24)
        };
        ph_shake256_t c;
        ph_shake256_init(&c);
        ph_shake256_absorb(&c, TAG_LF2_MATRIX,
                           sizeof TAG_LF2_MATRIX - 1u);
        ph_shake256_absorb(&c, parent, PH_DIGEST_LEN);
        ph_shake256_absorb(&c, pass_le, sizeof pass_le);
        ph_shake256_squeeze(&c, pass_parent, sizeof pass_parent);
        if (ph_matrix_derive(&matrices[pass], n, pass_parent) != 0)
            return -1;
    }
    return 0;
}

static void derive_vector(uint8_t h[PH_DIGEST_LEN], int8_t *x,
                          uint8_t *packed, uint32_t n,
                          const uint8_t *header, size_t header_len,
                          uint64_t nonce)
{
    uint8_t nonce_le[PH_NONCE_LEN];
    ph_shake256_t c;
    store64_le(nonce_le, nonce);
    ph_shake256_init(&c);
    ph_shake256_absorb(&c, TAG_VECTOR, sizeof TAG_VECTOR - 1u);
    ph_shake256_absorb(&c, header, header_len);
    ph_shake256_absorb(&c, nonce_le, sizeof nonce_le);
    ph_shake256_squeeze(&c, h, PH_DIGEST_LEN);
    ph_shake256(packed, n / 2u, h, PH_DIGEST_LEN);
    for (uint32_t i = 0; i < n; i++)
        x[i] = (int8_t)((int)nibble_at(packed, i) - 8);
}

static void matrix_bank_fold(uint8_t *folded, const ph_matrix_t *matrices,
                             uint32_t passes, const int8_t *x, uint32_t n)
{
    unsigned shift = 8u + (log2_u32(n) - 9u) / 2u;
    int32_t offset = 64 * (int32_t)n;
    memset(folded, 0, n / 2u);
    for (uint32_t pass = 0; pass < passes; pass++) {
        const int8_t *matrix = matrices[pass].m;
        for (uint32_t row_index = 0; row_index < n; row_index++) {
            const int8_t *row = matrix + (size_t)row_index * n;
            int32_t accumulator = 0;
            for (uint32_t column = 0; column < n; column++)
                accumulator +=
                    (int32_t)row[column] * (int32_t)x[column];
            uint8_t bucket = (uint8_t)(
                ((uint32_t)(accumulator + offset) >> shift) & 0x0fu);
            if ((row_index & 1u) == 0u)
                folded[row_index / 2u] ^= bucket;
            else
                folded[row_index / 2u] ^= (uint8_t)(bucket << 4);
        }
    }
}

static void finalize(uint8_t digest[PH_DIGEST_LEN],
                     const uint8_t h[PH_DIGEST_LEN],
                     const uint8_t *folded, uint32_t n)
{
    ph_shake256_t c;
    ph_shake256_init(&c);
    ph_shake256_absorb(&c, TAG_LF2_FINAL, sizeof TAG_LF2_FINAL - 1u);
    ph_shake256_absorb(&c, h, PH_DIGEST_LEN);
    ph_shake256_absorb(&c, folded, n / 2u);
    ph_shake256_squeeze(&c, digest, PH_DIGEST_LEN);
}

int main(int argc, char **argv)
{
    uint32_t n = argc > 1 ? (uint32_t)strtoul(argv[1], NULL, 10) : 4096u;
    uint32_t passes = argc > 2 ?
        (uint32_t)strtoul(argv[2], NULL, 10) : 16u;
    uint32_t attempts = argc > 3 ?
        (uint32_t)strtoul(argv[3], NULL, 10) : 3u;
    if (n < 1024u || (n & (n - 1u)) != 0u ||
        passes == 0u || passes > 32u || attempts == 0u) {
        fprintf(stderr, "usage: %s [power-of-two n] [passes 1..32] "
                        "[attempts > 0]\n", argv[0]);
        return 2;
    }

    uint8_t parent[PH_DIGEST_LEN], header[80];
    ph_shake256(parent, sizeof parent, "lf2-verify-parent", 17u);
    ph_shake256(header, sizeof header, "lf2-verify-header", 17u);

    ph_matrix_t *matrices =
        (ph_matrix_t *)calloc(passes, sizeof(*matrices));
    if (!matrices)
        return 1;
    double start = now_sec();
    if (derive_matrix_bank(matrices, n, passes, parent) != 0) {
        fprintf(stderr, "LF2 matrix-bank derivation failed\n");
        return 1;
    }
    double derive_seconds = now_sec() - start;

    uint8_t *packed = (uint8_t *)malloc(n / 2u);
    uint8_t *folded = (uint8_t *)malloc(n / 2u);
    int8_t *x = (int8_t *)malloc(n);
    if (!packed || !folded || !x) {
        fprintf(stderr, "scratch allocation failed\n");
        return 1;
    }

    double vector_seconds = 0.0;
    double matrix_seconds = 0.0;
    double final_seconds = 0.0;
    uint8_t digest[PH_DIGEST_LEN], h[PH_DIGEST_LEN];
    volatile uint8_t sink = 0;
    for (uint32_t attempt = 0; attempt < attempts; attempt++) {
        double a = now_sec();
        derive_vector(h, x, packed, n, header, sizeof header, attempt);
        double b = now_sec();
        matrix_bank_fold(folded, matrices, passes, x, n);
        double c = now_sec();
        finalize(digest, h, folded, n);
        double d = now_sec();
        vector_seconds += b - a;
        matrix_seconds += c - b;
        final_seconds += d - c;
        sink ^= digest[0];
    }

    double total_seconds =
        vector_seconds + matrix_seconds + final_seconds;
    printf("LF2 cached-verifier cost screen\n");
    printf("profile:              n=%u passes=%u attempts=%u\n",
           n, passes, attempts);
    printf("matrix bank:          %.1f MiB\n",
           (double)n * n * passes / (1024.0 * 1024.0));
    printf("cold parent setup:    %.3f s\n", derive_seconds);
    printf("vector expansion:     %.3f ms/attempt\n",
           vector_seconds * 1e3 / attempts);
    printf("matrix + fold:        %.3f ms/attempt  (%.2f%%)\n",
           matrix_seconds * 1e3 / attempts,
           100.0 * matrix_seconds / total_seconds);
    printf("final SHAKE256:       %.3f ms/attempt\n",
           final_seconds * 1e3 / attempts);
    printf("cached verification:  %.3f ms/attempt\n",
           total_seconds * 1e3 / attempts);
    printf("digest nonce %u:      ", attempts - 1u);
    for (unsigned i = 0; i < PH_DIGEST_LEN; i++)
        printf("%02x", digest[i]);
    printf("\n");

    (void)sink;
    free(x);
    free(folded);
    free(packed);
    for (uint32_t pass = 0; pass < passes; pass++)
        ph_matrix_free(&matrices[pass]);
    free(matrices);
    return 0;
}
