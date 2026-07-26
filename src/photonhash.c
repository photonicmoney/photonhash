/*
 * photonhash.c — PhotonHash reference implementation
 *
 * Self-contained: includes a portable Keccak-f[1600] / SHAKE256.
 * Exact integer arithmetic throughout; no floating point anywhere.
 *
 * Spec: "PhotonHash: Technical Specification" v0.2
 * Author: Lightman
 * License: MIT
 */

#include "photonhash.h"

#include <stdlib.h>
#include <string.h>

#define PH_VERSION_STR "photonhash-ref 0.2.3-falsified"

/* Domain-separation tags (spec 5.1, 5.2, 5.4). ASCII, no trailing NUL. */
static const char TAG_MATRIX[] = "LASER/PhotonHash/v1/matrix";
static const char TAG_VECTOR[] = "LASER/PhotonHash/v1/vector";
static const char TAG_FINAL[]  = "LASER/PhotonHash/v1/final";

/* ================================================================== */
/* Keccak-f[1600]                                                      */
/* ================================================================== */

#define ROTL64(x, n) (((x) << (n)) | ((x) >> (64 - (n))))

static const uint64_t KC_RC[24] = {
    0x0000000000000001ULL, 0x0000000000008082ULL, 0x800000000000808aULL,
    0x8000000080008000ULL, 0x000000000000808bULL, 0x0000000080000001ULL,
    0x8000000080008081ULL, 0x8000000000008009ULL, 0x000000000000008aULL,
    0x0000000000000088ULL, 0x0000000080008009ULL, 0x000000008000000aULL,
    0x000000008000808bULL, 0x800000000000008bULL, 0x8000000000008089ULL,
    0x8000000000008003ULL, 0x8000000000008002ULL, 0x8000000000000080ULL,
    0x000000000000800aULL, 0x800000008000000aULL, 0x8000000080008081ULL,
    0x8000000000008080ULL, 0x0000000080000001ULL, 0x8000000080008008ULL
};

static const int KC_RHO[24] = {
     1,  3,  6, 10, 15, 21, 28, 36, 45, 55,  2, 14,
    27, 41, 56,  8, 25, 43, 62, 18, 39, 61, 20, 44
};

static const int KC_PI[24] = {
    10,  7, 11, 17, 18,  3,  5, 16,  8, 21, 24,  4,
    15, 23, 19, 13, 12,  2, 20, 14, 22,  9,  6,  1
};

static void keccakf1600(uint64_t st[25])
{
    uint64_t bc[5], t;
    for (int round = 0; round < 24; round++) {
        /* Theta */
        for (int i = 0; i < 5; i++)
            bc[i] = st[i] ^ st[i + 5] ^ st[i + 10] ^ st[i + 15] ^ st[i + 20];
        for (int i = 0; i < 5; i++) {
            t = bc[(i + 4) % 5] ^ ROTL64(bc[(i + 1) % 5], 1);
            for (int j = 0; j < 25; j += 5)
                st[j + i] ^= t;
        }
        /* Rho and Pi */
        t = st[1];
        for (int i = 0; i < 24; i++) {
            int j = KC_PI[i];
            bc[0] = st[j];
            st[j] = ROTL64(t, KC_RHO[i]);
            t = bc[0];
        }
        /* Chi */
        for (int j = 0; j < 25; j += 5) {
            for (int i = 0; i < 5; i++)
                bc[i] = st[j + i];
            for (int i = 0; i < 5; i++)
                st[j + i] = bc[i] ^ ((~bc[(i + 1) % 5]) & bc[(i + 2) % 5]);
        }
        /* Iota */
        st[0] ^= KC_RC[round];
    }
}

/* Portable little-endian lane load/store (independent of host order). */
static uint64_t load64_le(const uint8_t *p)
{
    return  (uint64_t)p[0]        | ((uint64_t)p[1] << 8)  |
           ((uint64_t)p[2] << 16) | ((uint64_t)p[3] << 24) |
           ((uint64_t)p[4] << 32) | ((uint64_t)p[5] << 40) |
           ((uint64_t)p[6] << 48) | ((uint64_t)p[7] << 56);
}

static void store64_le(uint8_t *p, uint64_t v)
{
    for (int i = 0; i < 8; i++)
        p[i] = (uint8_t)(v >> (8 * i));
}

/* ================================================================== */
/* SHAKE256 sponge (rate 136, capacity 512)                            */
/* ================================================================== */

#define SHAKE256_RATE 136

void ph_shake256_init(ph_shake256_t *c)
{
    memset(c, 0, sizeof *c);
}

static void shake_absorb_block(ph_shake256_t *c)
{
    for (int i = 0; i < SHAKE256_RATE / 8; i++)
        c->st[i] ^= load64_le(c->buf + 8 * i);
    keccakf1600(c->st);
}

void ph_shake256_absorb(ph_shake256_t *c, const void *data, size_t len)
{
    const uint8_t *p = (const uint8_t *)data;
    /* absorbing after squeezing began is a caller bug; make it inert */
    if (c->squeezing)
        return;
    while (len > 0) {
        size_t take = SHAKE256_RATE - c->pos;
        if (take > len)
            take = len;
        memcpy(c->buf + c->pos, p, take);
        c->pos += take;
        p += take;
        len -= take;
        if (c->pos == SHAKE256_RATE) {
            shake_absorb_block(c);
            c->pos = 0;
        }
    }
}

static void shake_finalize(ph_shake256_t *c)
{
    /* SHAKE domain padding 0x1F ... 0x80 within the rate block. */
    memset(c->buf + c->pos, 0, SHAKE256_RATE - c->pos);
    c->buf[c->pos] = 0x1F;
    c->buf[SHAKE256_RATE - 1] |= 0x80;
    shake_absorb_block(c);
    c->pos = SHAKE256_RATE; /* force a fresh squeeze of the state below */
    c->squeezing = 1;
}

void ph_shake256_squeeze(ph_shake256_t *c, void *out, size_t len)
{
    uint8_t *p = (uint8_t *)out;
    if (!c->squeezing)
        shake_finalize(c);
    while (len > 0) {
        if (c->pos == SHAKE256_RATE) {
            for (int i = 0; i < SHAKE256_RATE / 8; i++)
                store64_le(c->buf + 8 * i, c->st[i]);
            c->pos = 0;
        }
        size_t take = SHAKE256_RATE - c->pos;
        if (take > len)
            take = len;
        memcpy(p, c->buf + c->pos, take);
        c->pos += take;
        p += take;
        len -= take;
        if (c->pos == SHAKE256_RATE)
            keccakf1600(c->st);
    }
}

void ph_shake256(void *out, size_t outlen, const void *in, size_t inlen)
{
    ph_shake256_t c;
    ph_shake256_init(&c);
    ph_shake256_absorb(&c, in, inlen);
    ph_shake256_squeeze(&c, out, outlen);
}

/* ================================================================== */
/* Helpers                                                             */
/* ================================================================== */

/* Nibble convention (spec 5.1/5.2): index k reads byte k>>1;
 * even k -> low nibble, odd k -> high nibble. */
static inline unsigned nibble_at(const uint8_t *stream, size_t k)
{
    uint8_t b = stream[k >> 1];
    return (k & 1) ? (b >> 4) : (b & 0x0F);
}

static inline int is_pow2(uint32_t v) { return v && !(v & (v - 1)); }

static int valid_dim_for_host(uint32_t n)
{
    return is_pow2(n) && n >= PH_GENESIS_N && n <= (1u << 20) &&
           (size_t)n <= SIZE_MAX / (size_t)n;
}

static unsigned log2_u32(uint32_t v)
{
    unsigned r = 0;
    while (v >>= 1)
        r++;
    return r;
}

/* ================================================================== */
/* Matrix derivation (spec 5.1)                                        */
/* ================================================================== */

int ph_matrix_derive(ph_matrix_t *M, uint32_t n,
                     const uint8_t prev_block_hash[PH_DIGEST_LEN])
{
    if (!M || !prev_block_hash || !valid_dim_for_host(n))
        return -1;

    const size_t entries = (size_t)n * (size_t)n;
    const size_t stream_len = entries / 2;
    uint8_t *stream = (uint8_t *)malloc(stream_len);
    int8_t  *m      = (int8_t *)malloc(entries);
    if (!stream || !m) {
        free(stream);
        free(m);
        return -1;
    }

    /* seed_M = SHAKE256(tag || prev_hash, 64) */
    ph_shake256_t c;
    ph_shake256_init(&c);
    ph_shake256_absorb(&c, TAG_MATRIX, sizeof TAG_MATRIX - 1);
    ph_shake256_absorb(&c, prev_block_hash, PH_DIGEST_LEN);
    ph_shake256_squeeze(&c, M->seed, PH_SEED_LEN);

    /* stream = SHAKE256(seed_M, n*n/2), entries = nibble - 8 */
    ph_shake256(stream, stream_len, M->seed, PH_SEED_LEN);
    for (size_t k = 0; k < entries; k++)
        m[k] = (int8_t)((int)nibble_at(stream, k) - 8);

    /* audit checksum over the raw nibble stream */
    ph_shake256(M->checksum, PH_DIGEST_LEN, stream, stream_len);

    free(stream);
    M->n = n;
    M->m = m;
    return 0;
}

void ph_matrix_free(ph_matrix_t *M)
{
    if (M && M->m) {
        free(M->m);
        M->m = NULL;
        M->n = 0;
    }
}

uint32_t ph_dim_for_height(uint64_t height)
{
    /* The active v0.2 experimental profile fixes proof cost at genesis n.
     * Dynamic eras require separate work-discontinuity analysis, vectors,
     * review, and an explicit future activation boundary. */
    (void)height;
    return PH_GENESIS_N;
}

/* ================================================================== */
/* Pipeline (spec 5.2 – 5.4)                                           */
/* ================================================================== */

static void derive_h_in(uint8_t h_in[PH_DIGEST_LEN],
                        const uint8_t *header, size_t header_len,
                        uint64_t nonce)
{
    uint8_t nonce_le[PH_NONCE_LEN];
    store64_le(nonce_le, nonce);

    ph_shake256_t c;
    ph_shake256_init(&c);
    ph_shake256_absorb(&c, TAG_VECTOR, sizeof TAG_VECTOR - 1);
    ph_shake256_absorb(&c, header, header_len);
    ph_shake256_absorb(&c, nonce_le, PH_NONCE_LEN);
    ph_shake256_squeeze(&c, h_in, PH_DIGEST_LEN);
}

static int pipeline(uint8_t d_out[PH_DIGEST_LEN],
                    uint8_t h_in_out[PH_DIGEST_LEN],
                    int8_t *x_trace, int32_t *y_trace, uint8_t *r_trace,
                    const ph_matrix_t *M,
                    const uint8_t *header, size_t header_len,
                    uint64_t nonce)
{
    if (!d_out || !M || !M->m || !valid_dim_for_host(M->n) ||
        (header_len != 0 && !header))
        return -1;

    const uint32_t n = M->n;
    /* v0.2 spec 5.3: shift_e = 8 + floor((era+1)/2), keyed here on n:
     * era = log2(n) - 10, so shift = 8 + floor((log2(n) - 9) / 2). */
    const unsigned shift = 8 + (log2_u32(n) - 9) / 2;
    const int32_t  offset = 64 * (int32_t)n; /* maps y into [0, 128n] */

    uint8_t h_in[PH_DIGEST_LEN];
    derive_h_in(h_in, header, header_len, nonce);

    /* x from SHAKE256(h_in, n/2) */
    uint8_t *xs = (uint8_t *)malloc(n / 2);
    int8_t  *x  = (int8_t *)malloc(n);
    uint8_t *r  = (uint8_t *)malloc(n / 2);
    if (!xs || !x || !r) {
        free(xs); free(x); free(r);
        return -1;
    }
    ph_shake256(xs, n / 2, h_in, PH_DIGEST_LEN);
    for (uint32_t i = 0; i < n; i++)
        x[i] = (int8_t)((int)nibble_at(xs, i) - 8);

    /* y = Mx exact; requantize into packed nibbles (spec 5.3) */
    for (uint32_t i = 0; i < n; i++) {
        const int8_t *row = M->m + (size_t)i * n;
        int32_t acc = 0;
        for (uint32_t j = 0; j < n; j++)
            acc += (int32_t)row[j] * (int32_t)x[j];
        if (y_trace)
            y_trace[i] = acc;
        uint32_t u = (uint32_t)(acc + offset);
        uint8_t bucket = (uint8_t)((u >> shift) & 0x0F);
        if (i & 1)
            r[i >> 1] |= (uint8_t)(bucket << 4);
        else
            r[i >> 1] = bucket;
    }

    /* d = SHAKE256(tag || h_in || r, 32) (spec 5.4) */
    ph_shake256_t c;
    ph_shake256_init(&c);
    ph_shake256_absorb(&c, TAG_FINAL, sizeof TAG_FINAL - 1);
    ph_shake256_absorb(&c, h_in, PH_DIGEST_LEN);
    ph_shake256_absorb(&c, r, n / 2);
    ph_shake256_squeeze(&c, d_out, PH_DIGEST_LEN);

    if (h_in_out)
        memcpy(h_in_out, h_in, PH_DIGEST_LEN);
    if (x_trace)
        memcpy(x_trace, x, n);
    if (r_trace)
        memcpy(r_trace, r, n / 2);

    free(xs); free(x); free(r);
    return 0;
}

int ph_hash(uint8_t d_out[PH_DIGEST_LEN],
            uint8_t h_in_out[PH_DIGEST_LEN],
            const ph_matrix_t *M,
            const uint8_t *header, size_t header_len,
            uint64_t nonce)
{
    return pipeline(d_out, h_in_out, NULL, NULL, NULL,
                    M, header, header_len, nonce);
}

int ph_hash_trace(uint8_t d_out[PH_DIGEST_LEN],
                  uint8_t h_in_out[PH_DIGEST_LEN],
                  int8_t *x_out, int32_t *y_out, uint8_t *r_out,
                  const ph_matrix_t *M,
                  const uint8_t *header, size_t header_len,
                  uint64_t nonce)
{
    return pipeline(d_out, h_in_out, x_out, y_out, r_out,
                    M, header, header_len, nonce);
}

int ph_meets_target(const uint8_t d[PH_DIGEST_LEN],
                    const uint8_t target[PH_DIGEST_LEN])
{
    if (!d || !target)
        return 0;

    /* little-endian 256-bit compare: most significant byte is index 31 */
    for (int i = PH_DIGEST_LEN - 1; i >= 0; i--) {
        if (d[i] < target[i]) return 1;
        if (d[i] > target[i]) return 0;
    }
    return 0; /* equal does not beat the target */
}

int ph_verify_with_matrix(const ph_matrix_t *M,
                          const uint8_t *header, size_t header_len,
                          uint64_t nonce,
                          const uint8_t target[PH_DIGEST_LEN])
{
    if (!M || !target || (header_len != 0 && !header))
        return -1;

    uint8_t d[PH_DIGEST_LEN];
    if (ph_hash(d, NULL, M, header, header_len, nonce) != 0)
        return -1;
    return ph_meets_target(d, target);
}

int ph_verify(const uint8_t prev_block_hash[PH_DIGEST_LEN],
              uint64_t height,
              const uint8_t *header, size_t header_len,
              uint64_t nonce,
              const uint8_t target[PH_DIGEST_LEN])
{
    if (!prev_block_hash || !target || (header_len != 0 && !header))
        return -1;

    ph_matrix_t M;
    if (ph_matrix_derive(&M, ph_dim_for_height(height), prev_block_hash) != 0)
        return -1;
    int rc = ph_verify_with_matrix(&M, header, header_len, nonce, target);
    ph_matrix_free(&M);
    return rc;
}

const char *ph_version(void)
{
    return PH_VERSION_STR;
}
