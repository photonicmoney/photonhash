/*
 * ph_bench.c — throughput and cost-profile measurement for PhotonHash.
 *
 * Reports single-threaded attempts/sec at a given dimension and measures
 * the share of pipeline time spent in the matrix stage, to check the
 * specification's Section 6 cost table empirically on this machine.
 *
 * Usage: ph_bench [n] [seconds]     (defaults: 1024, 3)
 *
 * Author: Lightman. License: MIT.
 */

#define _POSIX_C_SOURCE 199309L

#include "photonhash.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

static double now_sec(void)
{
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (double)ts.tv_sec + (double)ts.tv_nsec * 1e-9;
}

int main(int argc, char **argv)
{
    uint32_t n = argc > 1 ? (uint32_t)strtoul(argv[1], NULL, 10)
                          : PH_GENESIS_N;
    double seconds = argc > 2 ? strtod(argv[2], NULL) : 3.0;

    printf("%s — bench (n = %u, %.1f s per phase, single thread)\n\n",
           ph_version(), n, seconds);

    uint8_t parent[PH_DIGEST_LEN], header[80];
    ph_shake256(parent, sizeof parent, "bench-parent", 12);
    ph_shake256(header, sizeof header, "bench-header", 12);

    ph_matrix_t M;
    double t0 = now_sec();
    if (ph_matrix_derive(&M, n, parent) != 0) {
        fprintf(stderr, "matrix derivation failed (n=%u)\n", n);
        return 1;
    }
    double t_derive = now_sec() - t0;
    printf("matrix derivation (once per block): %.1f ms  (%zu KiB unpacked)\n",
           t_derive * 1e3, ((size_t)n * n) >> 10);

    /* Phase 1: full pipeline throughput. */
    uint8_t d[32];
    uint64_t nonce = 0, attempts = 0;
    volatile uint8_t sink = 0;
    t0 = now_sec();
    while (now_sec() - t0 < seconds) {
        for (int k = 0; k < 32; k++)
            ph_hash(d, NULL, &M, header, sizeof header, nonce++);
        attempts += 32;
        sink ^= d[0];
    }
    double full_rate = (double)attempts / (now_sec() - t0);
    double full_us = 1e6 / full_rate;

    /* Phase 2: hash-only baseline (vector derivation + final digest with a
     * fixed dummy r), to estimate the non-matvec share of the pipeline. */
    uint8_t h_in[32];
    uint8_t *xs = malloc(n / 2);
    uint8_t *r  = malloc(n / 2);
    if (!xs || !r) {
        fprintf(stderr, "allocation failed\n");
        free(xs); free(r); ph_matrix_free(&M);
        return 1;
    }
    memset(r, 0x5A, n / 2);
    uint64_t hash_iters = 0;
    t0 = now_sec();
    while (now_sec() - t0 < seconds) {
        for (int k = 0; k < 256; k++) {
            /* h_in derivation (tagged) */
            ph_shake256_t c;
            uint8_t nb[8];
            for (int b = 0; b < 8; b++) nb[b] = (uint8_t)(nonce >> (8 * b));
            ph_shake256_init(&c);
            ph_shake256_absorb(&c, "LASER/PhotonHash/v1/vector", 26);
            ph_shake256_absorb(&c, header, sizeof header);
            ph_shake256_absorb(&c, nb, 8);
            ph_shake256_squeeze(&c, h_in, 32);
            /* x expansion */
            ph_shake256(xs, n / 2, h_in, 32);
            /* final digest over dummy r */
            ph_shake256_init(&c);
            ph_shake256_absorb(&c, "LASER/PhotonHash/v1/final", 25);
            ph_shake256_absorb(&c, h_in, 32);
            ph_shake256_absorb(&c, r, n / 2);
            ph_shake256_squeeze(&c, d, 32);
            nonce++;
        }
        hash_iters += 256;
        sink ^= d[0];
    }
    double hash_rate = (double)hash_iters / (now_sec() - t0);
    double hash_us = 1e6 / hash_rate;

    double matvec_us = full_us - hash_us;
    double share = 100.0 * matvec_us / full_us;

    printf("\nfull pipeline:      %10.0f attempts/s   (%.1f us/attempt)\n",
           full_rate, full_us);
    printf("hash stages only:   %10.0f iters/s      (%.2f us/attempt)\n",
           hash_rate, hash_us);
    printf("matrix stage (inferred): %.1f us/attempt\n", matvec_us);
    printf("\nmatrix share of pipeline cost on this CPU: %.1f%%\n", share);
    printf("(spec section 6: >= 90%% is a design target, not a universal\n"
           " property; record CPU/compiler/dimension with every result)\n");

    (void)sink;
    free(xs);
    free(r);
    ph_matrix_free(&M);
    return 0;
}
