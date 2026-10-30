/* Unselected LF3-K8-C20-experiment.1 cold reference; no consensus use. MIT. */
#include "photonhash_lf3_c20.h"
#include <string.h>

static const char VECTOR_TAG[] = "LASER/PhotonHash/LF3-K8-C20-experiment.1/vector";
static const char FINAL_TAG[] = "LASER/PhotonHash/LF3-K8-C20-experiment.1/final";

static uint32_t load32(const uint8_t *p)
{
    return (uint32_t)p[0] | ((uint32_t)p[1] << 8) |
        ((uint32_t)p[2] << 16) | ((uint32_t)p[3] << 24);
}
static uint32_t rot(uint32_t x, unsigned n) { return (x << n) | (x >> (32u - n)); }
static void quarter(uint32_t *s, unsigned a, unsigned b, unsigned c, unsigned d)
{
    s[a] += s[b]; s[d] = rot(s[d] ^ s[a], 16);
    s[c] += s[d]; s[b] = rot(s[b] ^ s[c], 12);
    s[a] += s[b]; s[d] = rot(s[d] ^ s[a], 8);
    s[c] += s[d]; s[b] = rot(s[b] ^ s[c], 7);
}
int ph_lf3_c20_block(uint8_t out[64], const uint8_t key[32],
    const uint8_t nonce[12], uint32_t counter)
{
    if (!out || !key || !nonce) return -1;
    uint32_t initial[16] = {0x61707865u, 0x3320646eu, 0x79622d32u, 0x6b206574u};
    for (unsigned i = 0; i < 8u; i++) initial[4u + i] = load32(key + 4u * i);
    initial[12] = counter;
    for (unsigned i = 0; i < 3u; i++) initial[13u + i] = load32(nonce + 4u * i);
    uint32_t s[16]; memcpy(s, initial, sizeof s);
    for (unsigned round = 0; round < 10u; round++) {
        quarter(s, 0, 4, 8, 12); quarter(s, 1, 5, 9, 13);
        quarter(s, 2, 6, 10, 14); quarter(s, 3, 7, 11, 15);
        quarter(s, 0, 5, 10, 15); quarter(s, 1, 6, 11, 12);
        quarter(s, 2, 7, 8, 13); quarter(s, 3, 4, 9, 14);
    }
    for (unsigned i = 0; i < 16u; i++) {
        uint32_t word = s[i] + initial[i];
        for (unsigned b = 0; b < 4u; b++) out[4u * i + b] = (uint8_t)(word >> (8u * b));
    }
    return 0;
}

int ph_lf3_c20_init(ph_lf3_c20_job_t *job, const uint8_t parent[32],
    const uint8_t *header, size_t header_len, uint64_t nonce, uint32_t method)
{
    if (!job) return -1;
    memset(job, 0, sizeof *job);
    if (ph_lf2_stream_init(&job->core, parent, header, header_len, nonce, method) != 0)
        return -1;
    uint8_t nonce_le[8];
    for (unsigned i = 0; i < 8u; i++) nonce_le[i] = (uint8_t)(nonce >> (8u * i));
    ph_shake256_t s;
    ph_shake256_init(&s);
    ph_shake256_absorb(&s, VECTOR_TAG, sizeof VECTOR_TAG - 1u);
    ph_shake256_absorb(&s, header, header_len);
    ph_shake256_absorb(&s, nonce_le, sizeof nonce_le);
    ph_shake256_squeeze(&s, job->core.h, 32);
    uint8_t zero_nonce[12] = {0}, block[64];
    for (uint32_t counter = 1; counter <= 32u; counter++) {
        (void)ph_lf3_c20_block(block, job->core.h, zero_nonce, counter);
        for (unsigned i = 0; i < 64u; i++) {
            size_t base = (size_t)(counter - 1u) * 128u + 2u * i;
            job->core.x[base] = (int8_t)((int)(block[i] & 15u) - 8);
            job->core.x[base + 1u] = (int8_t)((int)(block[i] >> 4) - 8);
        }
    }
    return 0;
}

int ph_lf3_c20_step(ph_lf3_c20_job_t *job, uint32_t rows)
{
    if (!job) return -1;
    int result = ph_lf2_stream_step(&job->core, rows);
    if (result == 1 && !job->finalized) {
        ph_shake256_t s;
        ph_shake256_init(&s);
        ph_shake256_absorb(&s, FINAL_TAG, sizeof FINAL_TAG - 1u);
        ph_shake256_absorb(&s, job->core.h, 32);
        ph_shake256_absorb(&s, job->core.folded, sizeof job->core.folded);
        ph_shake256_squeeze(&s, job->digest, 32);
        job->finalized = 1;
    }
    return result;
}
int ph_lf3_c20_result(const ph_lf3_c20_job_t *job, uint8_t digest[32])
{
    if (!job || !digest || job->finalized != 1 || job->core.state != 1) return -1;
    memcpy(digest, job->digest, 32);
    return 1;
}
void ph_lf3_c20_cancel(ph_lf3_c20_job_t *job)
{
    if (job) { memset(job, 0, sizeof *job); ph_lf2_stream_cancel(&job->core); }
}
