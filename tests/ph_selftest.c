/*
 * ph_selftest.c — known-answer tests and invariants for PhotonHash.
 * Exit code 0 = all tests pass.
 *
 * Author: Lightman. License: MIT.
 */

#include "photonhash.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static int failures = 0;

#define CHECK(cond, name)                                     \
    do {                                                      \
        if (cond) {                                           \
            printf("  ok      %s\n", name);                   \
        } else {                                              \
            printf("  FAILED  %s\n", name);                   \
            failures++;                                       \
        }                                                     \
    } while (0)

static void hex_to_bytes(uint8_t *out, const char *hex, size_t n)
{
    for (size_t i = 0; i < n; i++) {
        unsigned v = 0;
        if (sscanf(hex + 2 * i, "%2x", &v) != 1) {
            fprintf(stderr, "invalid embedded test vector\n");
            exit(2);
        }
        out[i] = (uint8_t)v;
    }
}

int main(void)
{
    printf("%s — self test\n\n", ph_version());

    /* ------------------------------------------------------------ */
    printf("SHAKE256 known-answer tests\n");

    /* NIST KAT: SHAKE256(""), first 32 bytes. */
    {
        uint8_t expect[32], got[32];
        hex_to_bytes(expect,
            "46b9dd2b0ba88d13233b3feb743eeb24"
            "3fcd52ea62b81b82b50c27646ed5762f", 32);
        ph_shake256(got, 32, "", 0);
        CHECK(memcmp(got, expect, 32) == 0, "SHAKE256(empty), 32 bytes");
    }

    /* Incremental absorb == one-shot. */
    {
        const char msg[] = "The quick brown fox jumps over the lazy dog";
        uint8_t a[64], b[64];
        ph_shake256(a, 64, msg, sizeof msg - 1);

        ph_shake256_t c;
        ph_shake256_init(&c);
        for (size_t i = 0; i < sizeof msg - 1; i++)
            ph_shake256_absorb(&c, msg + i, 1);
        ph_shake256_squeeze(&c, b, 64);
        CHECK(memcmp(a, b, 64) == 0, "byte-at-a-time absorb equals one-shot");
    }

    /* Chunked squeeze == one-shot (crosses a rate boundary: 300 bytes). */
    {
        uint8_t a[300], b[300];
        ph_shake256(a, 300, "laser", 5);
        ph_shake256_t c;
        ph_shake256_init(&c);
        ph_shake256_absorb(&c, "laser", 5);
        for (size_t off = 0; off < 300; off += 7) {
            size_t take = 300 - off < 7 ? 300 - off : 7;
            ph_shake256_squeeze(&c, b + off, take);
        }
        CHECK(memcmp(a, b, 300) == 0, "chunked squeeze equals one-shot");
    }

    /* ------------------------------------------------------------ */
    printf("\nPhotonHash pipeline invariants (n = %u)\n", PH_GENESIS_N);

    uint8_t parent[PH_DIGEST_LEN];
    ph_shake256(parent, sizeof parent, "selftest-parent", 15);

    ph_matrix_t M;
    if (ph_matrix_derive(&M, PH_GENESIS_N, parent) != 0) {
        printf("  FAILED  matrix derivation (allocation)\n");
        return 1;
    }

    /* Matrix entries within [-8, 7]. */
    {
        int in_range = 1;
        for (size_t k = 0; k < (size_t)M.n * M.n; k++)
            if (M.m[k] < -8 || M.m[k] > 7) { in_range = 0; break; }
        CHECK(in_range, "matrix entries in [-8, 7]");
    }

    /* Determinism: same parent => same checksum; different parent differs. */
    {
        ph_matrix_t M2 = {0}, M3 = {0};
        uint8_t parent2[PH_DIGEST_LEN];
        ph_shake256(parent2, sizeof parent2, "selftest-parent-2", 17);
        int rc2 = ph_matrix_derive(&M2, PH_GENESIS_N, parent);
        int rc3 = ph_matrix_derive(&M3, PH_GENESIS_N, parent2);
        if (rc2 != 0 || rc3 != 0) {
            fprintf(stderr, "matrix derivation failed in determinism test\n");
            ph_matrix_free(&M2);
            ph_matrix_free(&M3);
            ph_matrix_free(&M);
            return 1;
        }
        CHECK(memcmp(M.checksum, M2.checksum, PH_DIGEST_LEN) == 0,
              "matrix derivation is deterministic");
        CHECK(memcmp(M.checksum, M3.checksum, PH_DIGEST_LEN) != 0,
              "matrix depends on parent hash");
        ph_matrix_free(&M2);
        ph_matrix_free(&M3);
    }

    uint8_t header[80];
    ph_shake256(header, sizeof header, "selftest-header", 15);

    /* Pipeline determinism and nonce sensitivity. */
    {
        uint8_t d1[32], d2[32], d3[32], h1[32];
        ph_hash(d1, h1, &M, header, sizeof header, 42);
        ph_hash(d2, NULL, &M, header, sizeof header, 42);
        ph_hash(d3, NULL, &M, header, sizeof header, 43);
        CHECK(memcmp(d1, d2, 32) == 0, "pipeline is deterministic");
        CHECK(memcmp(d1, d3, 32) != 0, "digest depends on nonce");
    }

    /* Trace consistency: recomputing y from traced x and M matches. */
    {
        int8_t  *x = malloc(M.n);
        int32_t *y = malloc(M.n * sizeof(int32_t));
        uint8_t *r = malloc(M.n / 2);
        uint8_t d[32], h[32];
        if (!x || !y || !r ||
            ph_hash_trace(d, h, x, y, r, &M, header, sizeof header, 42) != 0) {
            fprintf(stderr, "trace allocation/evaluation failed\n");
            free(x); free(y); free(r); ph_matrix_free(&M);
            return 1;
        }

        int ok = 1;
        int32_t ymin = y[0], ymax = y[0];
        for (uint32_t i = 0; i < M.n && ok; i++) {
            const int8_t *row = M.m + (size_t)i * M.n;
            int32_t acc = 0;
            for (uint32_t j = 0; j < M.n; j++)
                acc += (int32_t)row[j] * (int32_t)x[j];
            if (acc != y[i])
                ok = 0;
            if (y[i] < ymin) ymin = y[i];
            if (y[i] > ymax) ymax = y[i];
        }
        CHECK(ok, "traced y equals independent recomputation");
        CHECK(ymin >= -64 * (int32_t)M.n && ymax <= 64 * (int32_t)M.n,
              "y within [-64n, 64n]");
        printf("          (observed y range: [%d, %d])\n", ymin, ymax);
        free(x); free(y); free(r);
    }

    /* v0.2 regression: requantization must use the full nibble range.
     * Under v0.1 parameters, r collapsed to {0x0, 0xF}; under v0.2's
     * distribution-tuned shift, all 16 values should appear and no value
     * should exceed ~25% of components. */
    {
        int8_t  *x = malloc(M.n);
        int32_t *y = malloc(M.n * sizeof(int32_t));
        uint8_t *r = malloc(M.n / 2);
        uint8_t d[32], h[32];
        if (!x || !y || !r ||
            ph_hash_trace(d, h, x, y, r, &M, header, sizeof header, 1234) != 0) {
            fprintf(stderr, "requantization allocation/evaluation failed\n");
            free(x); free(y); free(r); ph_matrix_free(&M);
            return 1;
        }
        unsigned hist[16] = {0};
        for (uint32_t i = 0; i < M.n; i++) {
            uint8_t nib = (i & 1) ? (uint8_t)(r[i >> 1] >> 4)
                                  : (uint8_t)(r[i >> 1] & 0x0F);
            hist[nib]++;
        }
        int distinct = 0;
        unsigned maxc = 0;
        for (int i = 0; i < 16; i++) {
            if (hist[i]) distinct++;
            if (hist[i] > maxc) maxc = hist[i];
        }
        CHECK(distinct == 16, "requantized output uses all 16 nibble values");
        CHECK(maxc < M.n / 4, "no nibble value dominates (v0.2 spread)");
        printf("          (max nibble frequency: %.1f%%)\n",
               100.0 * (double)maxc / (double)M.n);
        free(x); free(y); free(r);
    }

    /* Target semantics. */
    {
        uint8_t d[32], lo[32], hi[32];
        ph_hash(d, NULL, &M, header, sizeof header, 7);
        memcpy(lo, d, 32);
        memcpy(hi, d, 32);
        /* hi = d + 1, lo = d (equal must not pass) */
        for (int i = 0; i < 32; i++) { if (++hi[i]) break; }
        CHECK(ph_meets_target(d, hi) == 1, "d < d+1 meets target");
        CHECK(ph_meets_target(d, lo) == 0, "d == target does not meet target");
        CHECK(ph_meets_target(hi, lo) == 0, "d+1 > d does not meet target");
    }

    /* One-shot verify agrees with manual pipeline. */
    {
        uint8_t d[32];
        uint8_t target_all_ff[32];
        memset(target_all_ff, 0xFF, 32);
        ph_hash(d, NULL, &M, header, sizeof header, 7);
        int v = ph_verify(parent, 0, header, sizeof header, 7, target_all_ff);
        CHECK(v == 1, "ph_verify accepts under max target");
        uint8_t target_zero[32] = {0};
        v = ph_verify(parent, 0, header, sizeof header, 7, target_zero);
        CHECK(v == 0, "ph_verify rejects under zero target");
    }

    /* Input validation: dimensions below genesis and invalid arguments are
     * rejected before allocation or hashing. */
    {
        ph_matrix_t Mbad;
        CHECK(ph_matrix_derive(&Mbad, 64, parent) == -1,
              "n = 64 is rejected (no defined era)");
        CHECK(ph_matrix_derive(&Mbad, 512, parent) == -1,
              "n = 512 is rejected (no defined era)");
        CHECK(ph_matrix_derive(&Mbad, 1000, parent) == -1,
              "non-power-of-two n is rejected");
        CHECK(ph_matrix_derive(NULL, PH_GENESIS_N, parent) == -1,
              "null matrix output is rejected");
        CHECK(ph_matrix_derive(&Mbad, PH_GENESIS_N, NULL) == -1,
              "null parent hash is rejected");
        CHECK(ph_hash(NULL, NULL, &M, header, sizeof header, 0) == -1,
              "null digest output is rejected");
        CHECK(ph_hash(header, NULL, NULL, header, sizeof header, 0) == -1,
              "null matrix input is rejected");
        CHECK(ph_hash(header, NULL, &M, NULL, sizeof header, 0) == -1,
              "null non-empty header is rejected");
        CHECK(ph_meets_target(NULL, header) == 0,
              "null digest cannot meet target");
        CHECK(ph_verify(NULL, 0, header, sizeof header, 0, header) == -1,
              "null verification parent is rejected");
    }

    /* Active v0.2 experimental-profile dimension freeze. */
    {
        CHECK(ph_dim_for_height(0) == PH_GENESIS_N,
              "genesis dimension is frozen at 1024");
        CHECK(ph_dim_for_height(6307199u) == PH_GENESIS_N,
              "pre-era boundary remains at the genesis dimension");
        CHECK(ph_dim_for_height(6307200u) == PH_GENESIS_N,
              "former era boundary does not activate a dimension change");
        CHECK(ph_dim_for_height(UINT64_MAX) == PH_GENESIS_N,
              "all future heights remain at the genesis dimension");
    }

    ph_matrix_free(&M);

    printf("\n%s\n", failures == 0 ? "ALL TESTS PASSED" : "TESTS FAILED");
    return failures == 0 ? 0 : 1;
}
