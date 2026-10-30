/* Cooperative, allocation-free cold evaluation of frozen LF2-K8; MIT. */
#include "photonhash_lf2_stream.h"
#include <string.h>

_Static_assert(PH_LF2_N == 4096u && PH_LF2_PASSES == 8u,
    "This evaluator is specific to frozen LF2-K8");
_Static_assert(PH_DIGEST_LEN == 32u && PH_SEED_LEN == 64u,
    "LF2-K8 requires 32-byte digests and 64-byte matrix seeds");

static const char MATRIX_TAG[] = "LASER/PhotonHash/v1/matrix";
static const char VECTOR_TAG[] = "LASER/PhotonHash/v1/vector";
static const char PASS_TAG[] = "LASER/PhotonHash/launch-LF2/matrix";
static const char FINAL_TAG[] = "LASER/PhotonHash/launch-LF2/final";
static const char BANK_TAG[] = "PhotonHash/v0.4.0-shadow.1/test-bank";

static void begin_pass(ph_lf2_stream_job_t *job)
{
    uint8_t parent[PH_DIGEST_LEN], seed[PH_SEED_LEN];
    memcpy(parent, job->parent, sizeof parent);
    if (job->pass != 0u) {
        uint8_t index[4];
        for (unsigned i = 0; i < 4u; i++)
            index[i] = (uint8_t)(job->pass >> (8u * i));
        ph_shake256_t s;
        ph_shake256_init(&s);
        ph_shake256_absorb(&s, PASS_TAG, sizeof PASS_TAG - 1u);
        ph_shake256_absorb(&s, job->parent, PH_DIGEST_LEN);
        ph_shake256_absorb(&s, index, sizeof index);
        ph_shake256_squeeze(&s, parent, sizeof parent);
    }
    ph_shake256_t s;
    ph_shake256_init(&s);
    ph_shake256_absorb(&s, MATRIX_TAG, sizeof MATRIX_TAG - 1u);
    ph_shake256_absorb(&s, parent, sizeof parent);
    ph_shake256_squeeze(&s, seed, sizeof seed);
    ph_shake256_absorb(&job->bank_stream, seed, sizeof seed);
    ph_shake256_init(&job->matrix_stream);
    ph_shake256_absorb(&job->matrix_stream, seed, sizeof seed);
    ph_shake256_init(&job->checksum_stream);
}

int ph_lf2_stream_init(ph_lf2_stream_job_t *job,
    const uint8_t parent[PH_DIGEST_LEN], const uint8_t *header,
    size_t header_len, uint64_t nonce, uint32_t method)
{
    if (!job)
        return PH_LF2_STREAM_ERROR;
    memset(job, 0, sizeof *job);
    if (!parent || (header_len != 0u && !header) ||
        header_len > PH_LF2_STREAM_MAX_HEADER || method > PH_LF2_STREAM_MOD13)
        return PH_LF2_STREAM_ERROR;
    memcpy(job->parent, parent, PH_DIGEST_LEN);
    job->method = method;
    uint8_t nonce_le[8];
    for (unsigned i = 0; i < 8u; i++)
        nonce_le[i] = (uint8_t)(nonce >> (8u * i));
    ph_shake256_t s;
    ph_shake256_init(&s);
    ph_shake256_absorb(&s, VECTOR_TAG, sizeof VECTOR_TAG - 1u);
    ph_shake256_absorb(&s, header, header_len);
    ph_shake256_absorb(&s, nonce_le, sizeof nonce_le);
    ph_shake256_squeeze(&s, job->h, PH_DIGEST_LEN);
    ph_shake256(job->packed_row, sizeof job->packed_row, job->h, PH_DIGEST_LEN);
    for (uint32_t i = 0; i < PH_LF2_N; i++) {
        unsigned nibble = (unsigned)(job->packed_row[i / 2u] >> ((i & 1u) * 4u)) & 15u;
        job->x[i] = (int8_t)((int)nibble - 8);
    }
    ph_shake256_init(&job->bank_stream);
    ph_shake256_absorb(&job->bank_stream, BANK_TAG, sizeof BANK_TAG - 1u);
    ph_shake256_absorb(&job->bank_stream, parent, PH_DIGEST_LEN);
    begin_pass(job);
    job->initialized = 1u;
    return PH_LF2_STREAM_MORE;
}

static uint8_t row_bucket(const ph_lf2_stream_job_t *job)
{
    int32_t exact = 0;
    uint32_t residue = 0;
    for (uint32_t i = 0; i < PH_LF2_N; i++) {
        unsigned nibble = (unsigned)(job->packed_row[i / 2u] >> ((i & 1u) * 4u)) & 15u;
        int32_t product = ((int32_t)nibble - 8) * (int32_t)job->x[i];
        if (job->method == PH_LF2_STREAM_INT32)
            exact += product;
        else
            residue = (residue + (uint32_t)product) & 8191u;
    }
    if (job->method == PH_LF2_STREAM_INT32)
        return (uint8_t)(((uint32_t)(exact + 262144) >> 9) & 15u);
    return (uint8_t)(residue >> 9);
}

int ph_lf2_stream_step(ph_lf2_stream_job_t *job, uint32_t rows)
{
    if (!job || rows == 0u || rows > PH_LF2_STREAM_MAX_ROWS)
        return PH_LF2_STREAM_ERROR;
    if (job->state == PH_LF2_STREAM_CANCELLED)
        return PH_LF2_STREAM_CANCELLED;
    if (job->initialized != 1u || job->pass > PH_LF2_PASSES ||
        job->row >= PH_LF2_N || job->method > PH_LF2_STREAM_MOD13)
        return PH_LF2_STREAM_ERROR;
    if (job->state == PH_LF2_STREAM_DONE)
        return PH_LF2_STREAM_DONE;
    if (job->state != PH_LF2_STREAM_MORE || job->pass >= PH_LF2_PASSES)
        return PH_LF2_STREAM_ERROR;
    for (uint32_t count = 0; count < rows; count++) {
        ph_shake256_squeeze(&job->matrix_stream, job->packed_row, sizeof job->packed_row);
        ph_shake256_absorb(&job->checksum_stream, job->packed_row, sizeof job->packed_row);
        uint8_t q = row_bucket(job);
        job->folded[job->row / 2u] ^= (uint8_t)(q << ((job->row & 1u) * 4u));
        job->row++;
        if (job->row != PH_LF2_N)
            continue;
        uint8_t checksum[PH_DIGEST_LEN];
        ph_shake256_squeeze(&job->checksum_stream, checksum, sizeof checksum);
        ph_shake256_absorb(&job->bank_stream, checksum, sizeof checksum);
        job->row = 0u;
        job->pass++;
        if (job->pass < PH_LF2_PASSES) {
            begin_pass(job);
            continue;
        }
        ph_shake256_squeeze(&job->bank_stream, job->bank, sizeof job->bank);
        ph_shake256_t s;
        ph_shake256_init(&s);
        ph_shake256_absorb(&s, FINAL_TAG, sizeof FINAL_TAG - 1u);
        ph_shake256_absorb(&s, job->h, sizeof job->h);
        ph_shake256_absorb(&s, job->folded, sizeof job->folded);
        ph_shake256_squeeze(&s, job->digest, sizeof job->digest);
        job->state = PH_LF2_STREAM_DONE;
        return PH_LF2_STREAM_DONE;
    }
    return PH_LF2_STREAM_MORE;
}

void ph_lf2_stream_cancel(ph_lf2_stream_job_t *job)
{
    if (job) {
        memset(job, 0, sizeof *job);
        job->state = PH_LF2_STREAM_CANCELLED;
    }
}

int ph_lf2_stream_result(const ph_lf2_stream_job_t *job,
    uint8_t digest[PH_DIGEST_LEN], uint8_t h[PH_DIGEST_LEN],
    uint8_t folded[PH_LF2_N / 2u], uint8_t bank[PH_DIGEST_LEN])
{
    if (!job || !digest || job->initialized != 1u ||
        job->state != PH_LF2_STREAM_DONE || job->pass != PH_LF2_PASSES || job->row != 0u)
        return PH_LF2_STREAM_ERROR;
    memcpy(digest, job->digest, PH_DIGEST_LEN);
    if (h) memcpy(h, job->h, PH_DIGEST_LEN);
    if (folded) memcpy(folded, job->folded, PH_LF2_N / 2u);
    if (bank) memcpy(bank, job->bank, PH_DIGEST_LEN);
    return PH_LF2_STREAM_DONE;
}
