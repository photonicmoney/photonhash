/*
 * ph_bench.c - direct stage-level benchmark for PhotonHash.
 *
 * Measures the scalar reference stages over a batch of distinct nonces with
 * all scratch buffers allocated once. The benchmark intentionally does not
 * infer matvec cost by subtracting a dissimilar hash-only loop.
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

#define BENCH_BATCH 32u

static const char TAG_VECTOR[] = "LASER/PhotonHash/v1/vector";
static const char TAG_FINAL[]  = "LASER/PhotonHash/v1/final";

typedef struct {
    uint8_t *h_in;
    uint8_t *xs;
    int8_t  *x;
    int32_t *y;
    uint8_t *r;
    uint8_t *d;
} bench_buffers_t;

static double now_sec(void)
{
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (double)ts.tv_sec + (double)ts.tv_nsec * 1e-9;
}

static void store64_le(uint8_t out[8], uint64_t v)
{
    for (unsigned i = 0; i < 8; i++)
        out[i] = (uint8_t)(v >> (8u * i));
}

static unsigned nibble_at(const uint8_t *stream, size_t k)
{
    uint8_t b = stream[k >> 1];
    return (k & 1u) != 0u ? (unsigned)(b >> 4) : (unsigned)(b & 0x0Fu);
}

static unsigned log2_u32(uint32_t v)
{
    unsigned r = 0;
    while ((v >>= 1) != 0u)
        r++;
    return r;
}

static int buffers_alloc(bench_buffers_t *b, uint32_t n)
{
    const size_t batch = BENCH_BATCH;
    b->h_in = (uint8_t *)malloc(batch * PH_DIGEST_LEN);
    b->xs = (uint8_t *)malloc(batch * (size_t)n / 2u);
    b->x = (int8_t *)malloc(batch * (size_t)n);
    b->y = (int32_t *)malloc(batch * (size_t)n * sizeof(*b->y));
    b->r = (uint8_t *)malloc(batch * (size_t)n / 2u);
    b->d = (uint8_t *)malloc(batch * PH_DIGEST_LEN);
    return b->h_in && b->xs && b->x && b->y && b->r && b->d ? 0 : -1;
}

static void buffers_free(bench_buffers_t *b)
{
    free(b->h_in);
    free(b->xs);
    free(b->x);
    free(b->y);
    free(b->r);
    free(b->d);
    memset(b, 0, sizeof *b);
}

static void stage_h_in(bench_buffers_t *b, const uint8_t *header,
                       size_t header_len, uint64_t first_nonce)
{
    for (uint32_t k = 0; k < BENCH_BATCH; k++) {
        uint8_t nonce_le[PH_NONCE_LEN];
        ph_shake256_t c;
        store64_le(nonce_le, first_nonce + k);
        ph_shake256_init(&c);
        ph_shake256_absorb(&c, TAG_VECTOR, sizeof TAG_VECTOR - 1u);
        ph_shake256_absorb(&c, header, header_len);
        ph_shake256_absorb(&c, nonce_le, sizeof nonce_le);
        ph_shake256_squeeze(&c, b->h_in + (size_t)k * PH_DIGEST_LEN,
                            PH_DIGEST_LEN);
    }
}

static void stage_x_expand(bench_buffers_t *b, uint32_t n)
{
    for (uint32_t k = 0; k < BENCH_BATCH; k++)
        ph_shake256(b->xs + (size_t)k * n / 2u, n / 2u,
                    b->h_in + (size_t)k * PH_DIGEST_LEN, PH_DIGEST_LEN);
}

static void stage_x_decode(bench_buffers_t *b, uint32_t n)
{
    for (uint32_t k = 0; k < BENCH_BATCH; k++) {
        const uint8_t *xs = b->xs + (size_t)k * n / 2u;
        int8_t *x = b->x + (size_t)k * n;
        for (uint32_t i = 0; i < n; i++)
            x[i] = (int8_t)((int)nibble_at(xs, i) - 8);
    }
}

static void stage_matvec(bench_buffers_t *b, const ph_matrix_t *M)
{
    const uint32_t n = M->n;
    for (uint32_t k = 0; k < BENCH_BATCH; k++) {
        const int8_t *x = b->x + (size_t)k * n;
        int32_t *y = b->y + (size_t)k * n;
        for (uint32_t i = 0; i < n; i++) {
            const int8_t *row = M->m + (size_t)i * n;
            int32_t acc = 0;
            for (uint32_t j = 0; j < n; j++)
                acc += (int32_t)row[j] * (int32_t)x[j];
            y[i] = acc;
        }
    }
}

static void stage_requantize(bench_buffers_t *b, uint32_t n)
{
    const unsigned shift = 8u + (log2_u32(n) - 9u) / 2u;
    const int32_t offset = 64 * (int32_t)n;
    for (uint32_t k = 0; k < BENCH_BATCH; k++) {
        const int32_t *y = b->y + (size_t)k * n;
        uint8_t *r = b->r + (size_t)k * n / 2u;
        for (uint32_t i = 0; i < n; i++) {
            uint32_t u = (uint32_t)(y[i] + offset);
            uint8_t bucket = (uint8_t)((u >> shift) & 0x0Fu);
            if ((i & 1u) != 0u)
                r[i >> 1] |= (uint8_t)(bucket << 4);
            else
                r[i >> 1] = bucket;
        }
    }
}

static void stage_final(bench_buffers_t *b, uint32_t n)
{
    for (uint32_t k = 0; k < BENCH_BATCH; k++) {
        ph_shake256_t c;
        ph_shake256_init(&c);
        ph_shake256_absorb(&c, TAG_FINAL, sizeof TAG_FINAL - 1u);
        ph_shake256_absorb(&c, b->h_in + (size_t)k * PH_DIGEST_LEN,
                           PH_DIGEST_LEN);
        ph_shake256_absorb(&c, b->r + (size_t)k * n / 2u, n / 2u);
        ph_shake256_squeeze(&c, b->d + (size_t)k * PH_DIGEST_LEN,
                            PH_DIGEST_LEN);
    }
}

static void print_stage(const char *name, double elapsed, uint64_t attempts,
                        double total)
{
    double us = elapsed * 1e6 / (double)attempts;
    double share = total > 0.0 ? 100.0 * elapsed / total : 0.0;
    printf("%-22s %9.3f us/attempt  %6.2f%%\n", name, us, share);
}

int main(int argc, char **argv)
{
    uint32_t n = argc > 1 ? (uint32_t)strtoul(argv[1], NULL, 10)
                          : PH_GENESIS_N;
    double seconds = argc > 2 ? strtod(argv[2], NULL) : 3.0;

    printf("%s - direct stage bench (n = %u, %.1f s, batch = %u)\n\n",
           ph_version(), n, seconds, BENCH_BATCH);

    uint8_t parent[PH_DIGEST_LEN], header[80];
    ph_shake256(parent, sizeof parent, "bench-parent", 12);
    ph_shake256(header, sizeof header, "bench-header", 12);

    ph_matrix_t M = {0};
    double t0 = now_sec();
    if (ph_matrix_derive(&M, n, parent) != 0) {
        fprintf(stderr, "matrix derivation failed (n=%u)\n", n);
        return 1;
    }
    double t_derive = now_sec() - t0;
    printf("matrix derivation (once per parent): %.1f ms  (%zu KiB unpacked)\n",
           t_derive * 1e3, ((size_t)n * n) >> 10);

    bench_buffers_t b = {0};
    if (buffers_alloc(&b, n) != 0) {
        fprintf(stderr, "scratch allocation failed\n");
        buffers_free(&b);
        ph_matrix_free(&M);
        return 1;
    }

    /* The independently staged benchmark must agree with the library oracle. */
    stage_h_in(&b, header, sizeof header, 0);
    stage_x_expand(&b, n);
    stage_x_decode(&b, n);
    stage_matvec(&b, &M);
    stage_requantize(&b, n);
    stage_final(&b, n);
    uint8_t expected[PH_DIGEST_LEN];
    for (uint32_t k = 0; k < BENCH_BATCH; k++) {
        if (ph_hash(expected, NULL, &M, header, sizeof header, k) != 0 ||
            memcmp(expected, b.d + (size_t)k * PH_DIGEST_LEN,
                   PH_DIGEST_LEN) != 0) {
            fprintf(stderr, "staged benchmark disagrees with ph_hash "
                    "at batch index %u\n", k);
            buffers_free(&b);
            ph_matrix_free(&M);
            return 1;
        }
    }

    double t_h_in = 0.0, t_expand = 0.0, t_decode = 0.0;
    double t_matvec = 0.0, t_requant = 0.0, t_final = 0.0;
    uint64_t attempts = 0, nonce = BENCH_BATCH;
    volatile uint8_t sink = 0;
    const double wall_start = now_sec();
    while (now_sec() - wall_start < seconds) {
        double a = now_sec();
        stage_h_in(&b, header, sizeof header, nonce);
        double c = now_sec();
        stage_x_expand(&b, n);
        double d = now_sec();
        stage_x_decode(&b, n);
        double e = now_sec();
        stage_matvec(&b, &M);
        double f = now_sec();
        stage_requantize(&b, n);
        double g = now_sec();
        stage_final(&b, n);
        double h = now_sec();

        t_h_in += c - a;
        t_expand += d - c;
        t_decode += e - d;
        t_matvec += f - e;
        t_requant += g - f;
        t_final += h - g;
        attempts += BENCH_BATCH;
        nonce += BENCH_BATCH;
        sink ^= b.d[(BENCH_BATCH - 1u) * PH_DIGEST_LEN];
    }

    const double total = t_h_in + t_expand + t_decode + t_matvec +
                         t_requant + t_final;
    printf("\nDirect stage timings (scratch allocation excluded):\n");
    print_stage("h_in SHAKE256", t_h_in, attempts, total);
    print_stage("x expansion SHAKE256", t_expand, attempts, total);
    print_stage("nibble decode", t_decode, attempts, total);
    print_stage("exact scalar matvec", t_matvec, attempts, total);
    print_stage("requantize + pack", t_requant, attempts, total);
    print_stage("final SHAKE256", t_final, attempts, total);

    const double rate = (double)attempts / total;
    const double macs = (double)attempts * (double)n * (double)n;
    const double matrix_bytes = (double)attempts * (double)n * (double)n;
    printf("\nstaged pipeline:       %.0f attempts/s  (%.3f us/attempt)\n",
           rate, 1e6 / rate);
    printf("scalar matvec:         %.3f GMAC/s\n", macs / t_matvec / 1e9);
    printf("matrix-read bandwidth: %.2f GiB/s effective (cache-inclusive)\n",
           matrix_bytes / t_matvec / (1024.0 * 1024.0 * 1024.0));
    printf("\nThis is an audit-oriented scalar baseline, not a GPU, SIMD, or\n"
           "photonic competitiveness result. Record CPU, compiler, flags,\n"
           "dimension, and batch size with every measurement.\n");

    (void)sink;
    buffers_free(&b);
    ph_matrix_free(&M);
    return 0;
}
