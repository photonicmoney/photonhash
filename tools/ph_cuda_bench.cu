/*
 * ph_cuda_bench.cu - exact batched CUDA baseline for PhotonHash.
 *
 * This is an adversarial electronic-miner benchmark, not production mining
 * code. It keeps the parent-derived matrix resident on the GPU and measures:
 *   1. on-device SHAKE256 input binding and signed-vector expansion,
 *   2. exact batched INT8 x INT8 -> INT32 GEMM through cuBLAS,
 *   3. on-device requantization, final SHAKE256, and target comparison.
 *
 * Every stage is differentially checked against the portable C oracle before
 * timing. The matrix upload and allocations are reported separately and are
 * excluded from marginal per-nonce throughput.
 */

#include "photonhash.h"

#include <cuda_runtime.h>
#include <cublas_v2.h>

#include <algorithm>
#include <atomic>
#include <chrono>
#include <cinttypes>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <thread>
#include <vector>

#ifdef _WIN32
#include <windows.h>
#endif

#ifndef CUDA_THREADS
#define CUDA_THREADS 128
#endif
#ifndef PH_CUBLAS_ALGO
#define PH_CUBLAS_ALGO CUBLAS_GEMM_DEFAULT_TENSOR_OP
#endif
#ifndef PH_PIPELINE_DEPTH
#define PH_PIPELINE_DEPTH 8
#endif
#if PH_PIPELINE_DEPTH < 1 || PH_PIPELINE_DEPTH > 16
#error PH_PIPELINE_DEPTH must be between 1 and 16
#endif
#define VALIDATION_NONCES 16

enum {
    SHAKE_THREAD = 0,
    SHAKE_WARP = 1,
    SHAKE_DIRECT = 2,
    SHAKE_REGISTER = 3
};

static const char H_TAG_VECTOR[] = "LASER/PhotonHash/v1/vector";
static const char H_TAG_FINAL[]  = "LASER/PhotonHash/v1/final";

__device__ __constant__ char D_TAG_VECTOR[] =
    "LASER/PhotonHash/v1/vector";
__device__ __constant__ char D_TAG_FINAL[] =
    "LASER/PhotonHash/v1/final";

__device__ __constant__ uint64_t D_KECCAK_RC[24] = {
    0x0000000000000001ULL, 0x0000000000008082ULL,
    0x800000000000808aULL, 0x8000000080008000ULL,
    0x000000000000808bULL, 0x0000000080000001ULL,
    0x8000000080008081ULL, 0x8000000000008009ULL,
    0x000000000000008aULL, 0x0000000000000088ULL,
    0x0000000080008009ULL, 0x000000008000000aULL,
    0x000000008000808bULL, 0x800000000000008bULL,
    0x8000000000008089ULL, 0x8000000000008003ULL,
    0x8000000000008002ULL, 0x8000000000000080ULL,
    0x000000000000800aULL, 0x800000008000000aULL,
    0x8000000080008081ULL, 0x8000000000008080ULL,
    0x0000000080000001ULL, 0x8000000080008008ULL
};

/* For each destination lane after rho+pi: source lane and source rotation. */
__device__ __constant__ uint8_t D_PI_SRC[25] = {
     0,  6, 12, 18, 24,  3,  9, 10, 16, 22,
     1,  7, 13, 19, 20,  4,  5, 11, 17, 23,
     2,  8, 14, 15, 21
};
__device__ __constant__ uint8_t D_PI_RHO[25] = {
     0, 44, 43, 21, 14, 28, 20,  3, 45, 61,
     1,  6, 25,  8, 18, 27, 36, 10, 15, 56,
    62, 55, 39, 41,  2
};

typedef struct {
    uint64_t st[25];
    uint8_t buf[136];
    unsigned pos;
    int squeezing;
} d_shake256_t;

__device__ __forceinline__ uint64_t d_rotl64(uint64_t x, unsigned n)
{
    return (x << n) | (x >> (64u - n));
}

__device__ __forceinline__ uint64_t d_rotl64_safe(uint64_t x, unsigned n)
{
    return n == 0 ? x : d_rotl64(x, n);
}

__device__ __forceinline__ void d_store64_le(uint8_t *p, uint64_t v);

/*
 * One warp owns one Keccak state: lanes 0..24 each keep one 64-bit state
 * lane in a register. This avoids the 200-byte per-thread state and local
 * buffer used by the audit-oriented scalar device implementation.
 */
__device__ __forceinline__ uint64_t
d_warp_keccakf1600(uint64_t a, unsigned lane)
{
    const unsigned mask = 0xffffffffu;
    unsigned x = lane < 25u ? lane % 5u : 0u;
    unsigned y = lane < 25u ? lane / 5u : 0u;

    #pragma unroll
    for (unsigned round = 0; round < 24u; round++) {
        uint64_t c =
            __shfl_sync(mask, a, x) ^
            __shfl_sync(mask, a, x + 5u) ^
            __shfl_sync(mask, a, x + 10u) ^
            __shfl_sync(mask, a, x + 15u) ^
            __shfl_sync(mask, a, x + 20u);
        uint64_t c_left =
            __shfl_sync(mask, c, (x + 4u) % 5u);
        uint64_t c_right =
            __shfl_sync(mask, c, (x + 1u) % 5u);
        if (lane < 25u)
            a ^= c_left ^ d_rotl64(c_right, 1u);

        unsigned rot = lane < 25u ? D_PI_RHO[lane] : 0u;
        unsigned src = lane < 25u ? D_PI_SRC[lane] : 0u;
        uint64_t source = __shfl_sync(mask, a, src);
        uint64_t b = d_rotl64_safe(source, rot);
        if (lane >= 25u)
            b = 0;

        uint64_t b1 = __shfl_sync(
            mask, b, y * 5u + (x + 1u) % 5u);
        uint64_t b2 = __shfl_sync(
            mask, b, y * 5u + (x + 2u) % 5u);
        a = lane < 25u ? b ^ ((~b1) & b2) : 0;
        if (lane == 0u)
            a ^= D_KECCAK_RC[round];
    }
    return a;
}

__device__ __forceinline__ uint8_t
d_vector_message_byte(size_t i, const uint8_t *header, size_t header_len,
                      uint64_t nonce)
{
    const size_t tag_len = sizeof H_TAG_VECTOR - 1u;
    if (i < tag_len)
        return (uint8_t)D_TAG_VECTOR[i];
    i -= tag_len;
    if (i < header_len)
        return header[i];
    i -= header_len;
    return (uint8_t)(nonce >> (8u * (unsigned)i));
}

__global__ void derive_vectors_warp_kernel(
    int8_t *x_out, uint8_t *h_out, const uint8_t *header,
    size_t header_len, uint64_t first_nonce, uint32_t n, uint32_t count)
{
    unsigned global_thread = blockIdx.x * blockDim.x + threadIdx.x;
    unsigned lane = threadIdx.x & 31u;
    uint32_t k = global_thread >> 5;
    if (k >= count)
        return;

    const size_t input_len =
        (sizeof H_TAG_VECTOR - 1u) + header_len + PH_NONCE_LEN;
    uint64_t nonce = first_nonce + k;
    uint64_t word = 0;
    if (lane < 17u) {
        #pragma unroll
        for (unsigned j = 0; j < 8u; j++) {
            size_t i = (size_t)lane * 8u + j;
            uint8_t v = i < input_len
                ? d_vector_message_byte(i, header, header_len, nonce) : 0;
            if (i == input_len)
                v ^= 0x1fu;
            if (i == 135u)
                v ^= 0x80u;
            word |= (uint64_t)v << (8u * j);
        }
    }
    uint64_t h_lane = d_warp_keccakf1600(word, lane);
    if (lane < 4u)
        d_store64_le(h_out + (size_t)k * PH_DIGEST_LEN + lane * 8u,
                     h_lane);

    /* SHAKE256(h_in, n/2): absorb one 32-byte padded block. */
    uint64_t state = lane < 4u ? h_lane : 0;
    if (lane == 4u)
        state = 0x1fu;
    if (lane == 16u)
        state = 0x8000000000000000ULL;
    state = d_warp_keccakf1600(state, lane);

    int8_t *x = x_out + (size_t)k * n;
    uint32_t packed_count = n / 2u;
    for (uint32_t block = 0; block * 136u < packed_count; block++) {
        if (lane < 17u) {
            #pragma unroll
            for (unsigned j = 0; j < 8u; j++) {
                uint32_t out_i = block * 136u + lane * 8u + j;
                if (out_i < packed_count) {
                    uint8_t packed = (uint8_t)(state >> (8u * j));
                    x[2u * out_i] =
                        (int8_t)((int)(packed & 0x0fu) - 8);
                    x[2u * out_i + 1u] =
                        (int8_t)((int)(packed >> 4) - 8);
                }
            }
        }
        if ((block + 1u) * 136u < packed_count)
            state = d_warp_keccakf1600(state, lane);
    }
}

__device__ __forceinline__ uint8_t
d_final_message_byte(size_t i, const int32_t *y, const uint8_t *h,
                     unsigned shift, int32_t offset)
{
    const size_t tag_len = sizeof H_TAG_FINAL - 1u;
    if (i < tag_len)
        return (uint8_t)D_TAG_FINAL[i];
    i -= tag_len;
    if (i < PH_DIGEST_LEN)
        return h[i];
    i -= PH_DIGEST_LEN;
    uint32_t yi = (uint32_t)(2u * i);
    uint8_t lo = (uint8_t)(
        (((uint32_t)(y[yi] + offset)) >> shift) & 0x0fu);
    uint8_t hi = (uint8_t)(
        (((uint32_t)(y[yi + 1u] + offset)) >> shift) & 0x0fu);
    return (uint8_t)(lo | (uint8_t)(hi << 4));
}

__global__ void finalize_warp_kernel(
    uint8_t *digest_out, uint8_t *meets_out, const int32_t *y,
    const uint8_t *h_in, const uint8_t *target, uint32_t n, uint32_t count)
{
    const unsigned mask = 0xffffffffu;
    unsigned global_thread = blockIdx.x * blockDim.x + threadIdx.x;
    unsigned lane = threadIdx.x & 31u;
    uint32_t k = global_thread >> 5;
    if (k >= count)
        return;

    unsigned log2n = 0;
    for (uint32_t v = n; (v >>= 1) != 0; )
        log2n++;
    unsigned shift = 8u + (log2n - 9u) / 2u;
    int32_t offset = 64 * (int32_t)n;
    const int32_t *yk = y + (size_t)k * n;
    const uint8_t *hk = h_in + (size_t)k * PH_DIGEST_LEN;
    const size_t message_len =
        (sizeof H_TAG_FINAL - 1u) + PH_DIGEST_LEN + n / 2u;

    uint64_t state = 0;
    uint32_t blocks = (uint32_t)(message_len / 136u) + 1u;
    for (uint32_t block = 0; block < blocks; block++) {
        uint64_t word = 0;
        if (lane < 17u) {
            #pragma unroll
            for (unsigned j = 0; j < 8u; j++) {
                size_t i = (size_t)block * 136u + lane * 8u + j;
                uint8_t v = i < message_len
                    ? d_final_message_byte(i, yk, hk, shift, offset) : 0;
                if (i == message_len)
                    v ^= 0x1fu;
                if (block + 1u == blocks && lane == 16u && j == 7u)
                    v ^= 0x80u;
                word |= (uint64_t)v << (8u * j);
            }
        }
        state ^= word;
        state = d_warp_keccakf1600(state, lane);
    }

    if (lane < 4u)
        d_store64_le(digest_out + (size_t)k * PH_DIGEST_LEN + lane * 8u,
                     state);

    int meets = 0;
    int decided = 0;
    for (int i = PH_DIGEST_LEN - 1; i >= 0; i--) {
        uint64_t source = __shfl_sync(mask, state, (unsigned)i / 8u);
        uint8_t digest_byte =
            (uint8_t)(source >> (8u * ((unsigned)i & 7u)));
        if (!decided && digest_byte != target[i]) {
            meets = digest_byte < target[i];
            decided = 1;
        }
    }
    if (lane == 0u)
        meets_out[k] = (uint8_t)meets;
}

__device__ void d_keccakf1600(uint64_t st[25])
{
    const uint64_t rc[24] = {
        0x0000000000000001ULL, 0x0000000000008082ULL,
        0x800000000000808aULL, 0x8000000080008000ULL,
        0x000000000000808bULL, 0x0000000080000001ULL,
        0x8000000080008081ULL, 0x8000000000008009ULL,
        0x000000000000008aULL, 0x0000000000000088ULL,
        0x0000000080008009ULL, 0x000000008000000aULL,
        0x000000008000808bULL, 0x800000000000008bULL,
        0x8000000000008089ULL, 0x8000000000008003ULL,
        0x8000000000008002ULL, 0x8000000000000080ULL,
        0x000000000000800aULL, 0x800000008000000aULL,
        0x8000000080008081ULL, 0x8000000000008080ULL,
        0x0000000080000001ULL, 0x8000000080008008ULL
    };
    const unsigned rho[24] = {
         1,  3,  6, 10, 15, 21, 28, 36, 45, 55,  2, 14,
        27, 41, 56,  8, 25, 43, 62, 18, 39, 61, 20, 44
    };
    const unsigned pi[24] = {
        10,  7, 11, 17, 18,  3,  5, 16,  8, 21, 24,  4,
        15, 23, 19, 13, 12,  2, 20, 14, 22,  9,  6,  1
    };
    uint64_t bc[5];
    for (unsigned round = 0; round < 24; round++) {
        for (unsigned i = 0; i < 5; i++)
            bc[i] = st[i] ^ st[i + 5] ^ st[i + 10] ^
                    st[i + 15] ^ st[i + 20];
        for (unsigned i = 0; i < 5; i++) {
            uint64_t t = bc[(i + 4u) % 5u] ^
                         d_rotl64(bc[(i + 1u) % 5u], 1);
            for (unsigned j = 0; j < 25; j += 5)
                st[j + i] ^= t;
        }
        uint64_t t = st[1];
        for (unsigned i = 0; i < 24; i++) {
            unsigned j = pi[i];
            uint64_t saved = st[j];
            st[j] = d_rotl64(t, rho[i]);
            t = saved;
        }
        for (unsigned j = 0; j < 25; j += 5) {
            for (unsigned i = 0; i < 5; i++)
                bc[i] = st[j + i];
            for (unsigned i = 0; i < 5; i++)
                st[j + i] = bc[i] ^
                    ((~bc[(i + 1u) % 5u]) & bc[(i + 2u) % 5u]);
        }
        st[0] ^= rc[round];
    }
}

__device__ __forceinline__ uint64_t d_load64_le(const uint8_t *p)
{
    uint64_t v = 0;
    for (unsigned i = 0; i < 8; i++)
        v |= (uint64_t)p[i] << (8u * i);
    return v;
}

__device__ __forceinline__ void d_store64_le(uint8_t *p, uint64_t v)
{
    for (unsigned i = 0; i < 8; i++)
        p[i] = (uint8_t)(v >> (8u * i));
}

__device__ void d_shake_init(d_shake256_t *c)
{
    for (unsigned i = 0; i < 25; i++)
        c->st[i] = 0;
    for (unsigned i = 0; i < 136; i++)
        c->buf[i] = 0;
    c->pos = 0;
    c->squeezing = 0;
}

__device__ void d_shake_absorb_block(d_shake256_t *c)
{
    for (unsigned i = 0; i < 17; i++)
        c->st[i] ^= d_load64_le(c->buf + 8u * i);
    d_keccakf1600(c->st);
}

__device__ void d_shake_absorb(d_shake256_t *c, const uint8_t *data,
                               size_t len)
{
    while (len != 0) {
        size_t take = 136u - c->pos;
        if (take > len)
            take = len;
        for (size_t i = 0; i < take; i++)
            c->buf[c->pos + i] = data[i];
        c->pos += (unsigned)take;
        data += take;
        len -= take;
        if (c->pos == 136u) {
            d_shake_absorb_block(c);
            c->pos = 0;
        }
    }
}

__device__ void d_shake_finalize(d_shake256_t *c)
{
    for (unsigned i = c->pos; i < 136; i++)
        c->buf[i] = 0;
    c->buf[c->pos] = 0x1f;
    c->buf[135] |= 0x80;
    d_shake_absorb_block(c);
    c->pos = 136;
    c->squeezing = 1;
}

__device__ __forceinline__ uint8_t d_shake_byte(d_shake256_t *c)
{
    if (!c->squeezing)
        d_shake_finalize(c);
    if (c->pos == 136u) {
        for (unsigned i = 0; i < 17; i++)
            d_store64_le(c->buf + 8u * i, c->st[i]);
        c->pos = 0;
    }
    uint8_t out = c->buf[c->pos++];
    if (c->pos == 136u)
        d_keccakf1600(c->st);
    return out;
}

/*
 * Fixed-profile SHAKE path: one nonce per thread, but no generic SHAKE
 * byte buffer. PhotonHash's exact message sizes are absorbed directly into
 * Keccak lanes and squeezed directly from the state.
 */
__global__ void derive_vectors_direct_kernel(
    int8_t *x_out, uint8_t *h_out, const uint8_t *header,
    size_t header_len, uint64_t first_nonce, uint32_t n, uint32_t count)
{
    uint32_t k = blockIdx.x * blockDim.x + threadIdx.x;
    if (k >= count)
        return;

    uint64_t st[25] = {};
    const size_t input_len =
        (sizeof H_TAG_VECTOR - 1u) + header_len + PH_NONCE_LEN;
    uint64_t nonce = first_nonce + k;
    for (unsigned lane = 0; lane < 17u; lane++) {
        uint64_t word = 0;
        #pragma unroll
        for (unsigned j = 0; j < 8u; j++) {
            size_t i = (size_t)lane * 8u + j;
            uint8_t v = i < input_len
                ? d_vector_message_byte(i, header, header_len, nonce) : 0;
            if (i == input_len)
                v ^= 0x1fu;
            if (i == 135u)
                v ^= 0x80u;
            word |= (uint64_t)v << (8u * j);
        }
        st[lane] = word;
    }
    d_keccakf1600(st);

    uint64_t h_words[4];
    for (unsigned lane = 0; lane < 4u; lane++) {
        h_words[lane] = st[lane];
        d_store64_le(h_out + (size_t)k * PH_DIGEST_LEN + lane * 8u,
                     st[lane]);
    }

    for (unsigned lane = 0; lane < 25u; lane++)
        st[lane] = lane < 4u ? h_words[lane] : 0;
    st[4] = 0x1fu;
    st[16] = 0x8000000000000000ULL;
    d_keccakf1600(st);

    int8_t *x = x_out + (size_t)k * n;
    uint32_t packed_count = n / 2u;
    for (uint32_t block = 0; block * 136u < packed_count; block++) {
        for (unsigned lane = 0; lane < 17u; lane++) {
            uint64_t word = st[lane];
            #pragma unroll
            for (unsigned j = 0; j < 8u; j++) {
                uint32_t out_i = block * 136u + lane * 8u + j;
                if (out_i < packed_count) {
                    uint8_t packed = (uint8_t)(word >> (8u * j));
                    x[2u * out_i] =
                        (int8_t)((int)(packed & 0x0fu) - 8);
                    x[2u * out_i + 1u] =
                        (int8_t)((int)(packed >> 4) - 8);
                }
            }
        }
        if ((block + 1u) * 136u < packed_count)
            d_keccakf1600(st);
    }
}

__global__ void finalize_direct_kernel(
    uint8_t *digest_out, uint8_t *meets_out, const int32_t *y,
    const uint8_t *h_in, const uint8_t *target, uint32_t n, uint32_t count)
{
    uint32_t k = blockIdx.x * blockDim.x + threadIdx.x;
    if (k >= count)
        return;

    unsigned log2n = 0;
    for (uint32_t v = n; (v >>= 1) != 0; )
        log2n++;
    unsigned shift = 8u + (log2n - 9u) / 2u;
    int32_t offset = 64 * (int32_t)n;
    const int32_t *yk = y + (size_t)k * n;
    const uint8_t *hk = h_in + (size_t)k * PH_DIGEST_LEN;
    const size_t message_len =
        (sizeof H_TAG_FINAL - 1u) + PH_DIGEST_LEN + n / 2u;

    uint64_t st[25] = {};
    uint32_t blocks = (uint32_t)(message_len / 136u) + 1u;
    for (uint32_t block = 0; block < blocks; block++) {
        for (unsigned lane = 0; lane < 17u; lane++) {
            uint64_t word = 0;
            #pragma unroll
            for (unsigned j = 0; j < 8u; j++) {
                size_t i = (size_t)block * 136u + lane * 8u + j;
                uint8_t v = i < message_len
                    ? d_final_message_byte(i, yk, hk, shift, offset) : 0;
                if (i == message_len)
                    v ^= 0x1fu;
                if (block + 1u == blocks && lane == 16u && j == 7u)
                    v ^= 0x80u;
                word |= (uint64_t)v << (8u * j);
            }
            st[lane] ^= word;
        }
        d_keccakf1600(st);
    }

    uint8_t *dk = digest_out + (size_t)k * PH_DIGEST_LEN;
    for (unsigned lane = 0; lane < 4u; lane++)
        d_store64_le(dk + lane * 8u, st[lane]);

    int meets = 0;
    for (int i = PH_DIGEST_LEN - 1; i >= 0; i--) {
        uint8_t digest_byte =
            (uint8_t)(st[(unsigned)i / 8u] >>
                      (8u * ((unsigned)i & 7u)));
        if (digest_byte < target[i]) {
            meets = 1;
            break;
        }
        if (digest_byte > target[i])
            break;
    }
    meets_out[k] = (uint8_t)meets;
}

typedef struct {
    uint64_t a0, a1, a2, a3, a4;
    uint64_t a5, a6, a7, a8, a9;
    uint64_t a10, a11, a12, a13, a14;
    uint64_t a15, a16, a17, a18, a19;
    uint64_t a20, a21, a22, a23, a24;
} d_reg_state_t;

__device__ __forceinline__ void d_keccakf_registers(d_reg_state_t &s)
{
    #pragma unroll
    for (unsigned round = 0; round < 24u; round++) {
        uint64_t c0 = s.a0 ^ s.a5 ^ s.a10 ^ s.a15 ^ s.a20;
        uint64_t c1 = s.a1 ^ s.a6 ^ s.a11 ^ s.a16 ^ s.a21;
        uint64_t c2 = s.a2 ^ s.a7 ^ s.a12 ^ s.a17 ^ s.a22;
        uint64_t c3 = s.a3 ^ s.a8 ^ s.a13 ^ s.a18 ^ s.a23;
        uint64_t c4 = s.a4 ^ s.a9 ^ s.a14 ^ s.a19 ^ s.a24;
        uint64_t d0 = c4 ^ d_rotl64(c1, 1u);
        uint64_t d1 = c0 ^ d_rotl64(c2, 1u);
        uint64_t d2 = c1 ^ d_rotl64(c3, 1u);
        uint64_t d3 = c2 ^ d_rotl64(c4, 1u);
        uint64_t d4 = c3 ^ d_rotl64(c0, 1u);
        s.a0 ^= d0; s.a5 ^= d0; s.a10 ^= d0; s.a15 ^= d0; s.a20 ^= d0;
        s.a1 ^= d1; s.a6 ^= d1; s.a11 ^= d1; s.a16 ^= d1; s.a21 ^= d1;
        s.a2 ^= d2; s.a7 ^= d2; s.a12 ^= d2; s.a17 ^= d2; s.a22 ^= d2;
        s.a3 ^= d3; s.a8 ^= d3; s.a13 ^= d3; s.a18 ^= d3; s.a23 ^= d3;
        s.a4 ^= d4; s.a9 ^= d4; s.a14 ^= d4; s.a19 ^= d4; s.a24 ^= d4;

        uint64_t b0 = s.a0;
        uint64_t b1 = d_rotl64(s.a6, 44u);
        uint64_t b2 = d_rotl64(s.a12, 43u);
        uint64_t b3 = d_rotl64(s.a18, 21u);
        uint64_t b4 = d_rotl64(s.a24, 14u);
        uint64_t b5 = d_rotl64(s.a3, 28u);
        uint64_t b6 = d_rotl64(s.a9, 20u);
        uint64_t b7 = d_rotl64(s.a10, 3u);
        uint64_t b8 = d_rotl64(s.a16, 45u);
        uint64_t b9 = d_rotl64(s.a22, 61u);
        uint64_t b10 = d_rotl64(s.a1, 1u);
        uint64_t b11 = d_rotl64(s.a7, 6u);
        uint64_t b12 = d_rotl64(s.a13, 25u);
        uint64_t b13 = d_rotl64(s.a19, 8u);
        uint64_t b14 = d_rotl64(s.a20, 18u);
        uint64_t b15 = d_rotl64(s.a4, 27u);
        uint64_t b16 = d_rotl64(s.a5, 36u);
        uint64_t b17 = d_rotl64(s.a11, 10u);
        uint64_t b18 = d_rotl64(s.a17, 15u);
        uint64_t b19 = d_rotl64(s.a23, 56u);
        uint64_t b20 = d_rotl64(s.a2, 62u);
        uint64_t b21 = d_rotl64(s.a8, 55u);
        uint64_t b22 = d_rotl64(s.a14, 39u);
        uint64_t b23 = d_rotl64(s.a15, 41u);
        uint64_t b24 = d_rotl64(s.a21, 2u);

        s.a0 = b0 ^ ((~b1) & b2);
        s.a1 = b1 ^ ((~b2) & b3);
        s.a2 = b2 ^ ((~b3) & b4);
        s.a3 = b3 ^ ((~b4) & b0);
        s.a4 = b4 ^ ((~b0) & b1);
        s.a5 = b5 ^ ((~b6) & b7);
        s.a6 = b6 ^ ((~b7) & b8);
        s.a7 = b7 ^ ((~b8) & b9);
        s.a8 = b8 ^ ((~b9) & b5);
        s.a9 = b9 ^ ((~b5) & b6);
        s.a10 = b10 ^ ((~b11) & b12);
        s.a11 = b11 ^ ((~b12) & b13);
        s.a12 = b12 ^ ((~b13) & b14);
        s.a13 = b13 ^ ((~b14) & b10);
        s.a14 = b14 ^ ((~b10) & b11);
        s.a15 = b15 ^ ((~b16) & b17);
        s.a16 = b16 ^ ((~b17) & b18);
        s.a17 = b17 ^ ((~b18) & b19);
        s.a18 = b18 ^ ((~b19) & b15);
        s.a19 = b19 ^ ((~b15) & b16);
        s.a20 = b20 ^ ((~b21) & b22);
        s.a21 = b21 ^ ((~b22) & b23);
        s.a22 = b22 ^ ((~b23) & b24);
        s.a23 = b23 ^ ((~b24) & b20);
        s.a24 = b24 ^ ((~b20) & b21);
        s.a0 ^= D_KECCAK_RC[round];
    }
}

__device__ __forceinline__ uint64_t d_vector_input_word(
    unsigned lane, const uint8_t *header, size_t header_len, uint64_t nonce)
{
    const size_t input_len =
        (sizeof H_TAG_VECTOR - 1u) + header_len + PH_NONCE_LEN;
    uint64_t word = 0;
    #pragma unroll
    for (unsigned j = 0; j < 8u; j++) {
        size_t i = (size_t)lane * 8u + j;
        uint8_t v = i < input_len
            ? d_vector_message_byte(i, header, header_len, nonce) : 0;
        if (i == input_len)
            v ^= 0x1fu;
        if (i == 135u)
            v ^= 0x80u;
        word |= (uint64_t)v << (8u * j);
    }
    return word;
}

__device__ __forceinline__ void d_decode_packed_word(
    uint64_t word, int8_t *x, uint32_t base, uint32_t packed_count)
{
    #pragma unroll
    for (unsigned j = 0; j < 8u; j++) {
        uint32_t out_i = base + j;
        if (out_i < packed_count) {
            uint8_t packed = (uint8_t)(word >> (8u * j));
            x[2u * out_i] = (int8_t)((int)(packed & 0x0fu) - 8);
            x[2u * out_i + 1u] =
                (int8_t)((int)(packed >> 4) - 8);
        }
    }
}

__device__ __forceinline__ uint64_t d_final_input_word(
    unsigned block, unsigned lane, const int32_t *y, const uint8_t *h,
    unsigned shift, int32_t offset, size_t message_len)
{
    uint64_t word = 0;
    #pragma unroll
    for (unsigned j = 0; j < 8u; j++) {
        size_t i = (size_t)block * 136u + lane * 8u + j;
        uint8_t v = i < message_len
            ? d_final_message_byte(i, y, h, shift, offset) : 0;
        if (i == message_len)
            v ^= 0x1fu;
        if (block == message_len / 136u && lane == 16u && j == 7u)
            v ^= 0x80u;
        word |= (uint64_t)v << (8u * j);
    }
    return word;
}

#define PH_DECODE_REG_BLOCK(base_) do { \
    d_decode_packed_word(s.a0, x, (base_) +   0u, packed_count); \
    d_decode_packed_word(s.a1, x, (base_) +   8u, packed_count); \
    d_decode_packed_word(s.a2, x, (base_) +  16u, packed_count); \
    d_decode_packed_word(s.a3, x, (base_) +  24u, packed_count); \
    d_decode_packed_word(s.a4, x, (base_) +  32u, packed_count); \
    d_decode_packed_word(s.a5, x, (base_) +  40u, packed_count); \
    d_decode_packed_word(s.a6, x, (base_) +  48u, packed_count); \
    d_decode_packed_word(s.a7, x, (base_) +  56u, packed_count); \
    d_decode_packed_word(s.a8, x, (base_) +  64u, packed_count); \
    d_decode_packed_word(s.a9, x, (base_) +  72u, packed_count); \
    d_decode_packed_word(s.a10, x, (base_) +  80u, packed_count); \
    d_decode_packed_word(s.a11, x, (base_) +  88u, packed_count); \
    d_decode_packed_word(s.a12, x, (base_) +  96u, packed_count); \
    d_decode_packed_word(s.a13, x, (base_) + 104u, packed_count); \
    d_decode_packed_word(s.a14, x, (base_) + 112u, packed_count); \
    d_decode_packed_word(s.a15, x, (base_) + 120u, packed_count); \
    d_decode_packed_word(s.a16, x, (base_) + 128u, packed_count); \
} while (0)

#define PH_ABSORB_REG_BLOCK(block_) do { \
    s.a0 ^= d_final_input_word((block_), 0u, yk, hk, shift, offset, message_len); \
    s.a1 ^= d_final_input_word((block_), 1u, yk, hk, shift, offset, message_len); \
    s.a2 ^= d_final_input_word((block_), 2u, yk, hk, shift, offset, message_len); \
    s.a3 ^= d_final_input_word((block_), 3u, yk, hk, shift, offset, message_len); \
    s.a4 ^= d_final_input_word((block_), 4u, yk, hk, shift, offset, message_len); \
    s.a5 ^= d_final_input_word((block_), 5u, yk, hk, shift, offset, message_len); \
    s.a6 ^= d_final_input_word((block_), 6u, yk, hk, shift, offset, message_len); \
    s.a7 ^= d_final_input_word((block_), 7u, yk, hk, shift, offset, message_len); \
    s.a8 ^= d_final_input_word((block_), 8u, yk, hk, shift, offset, message_len); \
    s.a9 ^= d_final_input_word((block_), 9u, yk, hk, shift, offset, message_len); \
    s.a10 ^= d_final_input_word((block_), 10u, yk, hk, shift, offset, message_len); \
    s.a11 ^= d_final_input_word((block_), 11u, yk, hk, shift, offset, message_len); \
    s.a12 ^= d_final_input_word((block_), 12u, yk, hk, shift, offset, message_len); \
    s.a13 ^= d_final_input_word((block_), 13u, yk, hk, shift, offset, message_len); \
    s.a14 ^= d_final_input_word((block_), 14u, yk, hk, shift, offset, message_len); \
    s.a15 ^= d_final_input_word((block_), 15u, yk, hk, shift, offset, message_len); \
    s.a16 ^= d_final_input_word((block_), 16u, yk, hk, shift, offset, message_len); \
    d_keccakf_registers(s); \
} while (0)

__global__ void derive_vectors_register_kernel(
    int8_t *x_out, uint8_t *h_out, const uint8_t *header,
    size_t header_len, uint64_t first_nonce, uint32_t n, uint32_t count)
{
    uint32_t k = blockIdx.x * blockDim.x + threadIdx.x;
    if (k >= count)
        return;
    uint64_t nonce = first_nonce + k;
    d_reg_state_t s = {
        d_vector_input_word(0u, header, header_len, nonce),
        d_vector_input_word(1u, header, header_len, nonce),
        d_vector_input_word(2u, header, header_len, nonce),
        d_vector_input_word(3u, header, header_len, nonce),
        d_vector_input_word(4u, header, header_len, nonce),
        d_vector_input_word(5u, header, header_len, nonce),
        d_vector_input_word(6u, header, header_len, nonce),
        d_vector_input_word(7u, header, header_len, nonce),
        d_vector_input_word(8u, header, header_len, nonce),
        d_vector_input_word(9u, header, header_len, nonce),
        d_vector_input_word(10u, header, header_len, nonce),
        d_vector_input_word(11u, header, header_len, nonce),
        d_vector_input_word(12u, header, header_len, nonce),
        d_vector_input_word(13u, header, header_len, nonce),
        d_vector_input_word(14u, header, header_len, nonce),
        d_vector_input_word(15u, header, header_len, nonce),
        d_vector_input_word(16u, header, header_len, nonce),
        0, 0, 0, 0, 0, 0, 0, 0
    };
    d_keccakf_registers(s);

    uint64_t h0 = s.a0, h1 = s.a1, h2 = s.a2, h3 = s.a3;
    uint8_t *hout = h_out + (size_t)k * PH_DIGEST_LEN;
    d_store64_le(hout, h0);
    d_store64_le(hout + 8u, h1);
    d_store64_le(hout + 16u, h2);
    d_store64_le(hout + 24u, h3);

    s = {h0, h1, h2, h3, 0x1fu, 0, 0, 0, 0, 0,
         0, 0, 0, 0, 0, 0, 0x8000000000000000ULL, 0, 0, 0,
         0, 0, 0, 0, 0};
    d_keccakf_registers(s);

    int8_t *x = x_out + (size_t)k * n;
    uint32_t packed_count = n / 2u;
    PH_DECODE_REG_BLOCK(0u);
    d_keccakf_registers(s);
    PH_DECODE_REG_BLOCK(136u);
    d_keccakf_registers(s);
    PH_DECODE_REG_BLOCK(272u);
    d_keccakf_registers(s);
    PH_DECODE_REG_BLOCK(408u);
}

__global__ void finalize_register_kernel(
    uint8_t *digest_out, uint8_t *meets_out, const int32_t *y,
    const uint8_t *h_in, const uint8_t *target, uint32_t n, uint32_t count)
{
    uint32_t k = blockIdx.x * blockDim.x + threadIdx.x;
    if (k >= count)
        return;
    unsigned log2n = 0;
    for (uint32_t v = n; (v >>= 1) != 0; )
        log2n++;
    unsigned shift = 8u + (log2n - 9u) / 2u;
    int32_t offset = 64 * (int32_t)n;
    const int32_t *yk = y + (size_t)k * n;
    const uint8_t *hk = h_in + (size_t)k * PH_DIGEST_LEN;
    const size_t message_len =
        (sizeof H_TAG_FINAL - 1u) + PH_DIGEST_LEN + n / 2u;
    d_reg_state_t s = {};
    PH_ABSORB_REG_BLOCK(0u);
    PH_ABSORB_REG_BLOCK(1u);
    PH_ABSORB_REG_BLOCK(2u);
    PH_ABSORB_REG_BLOCK(3u);
    PH_ABSORB_REG_BLOCK(4u);

    uint8_t *dk = digest_out + (size_t)k * PH_DIGEST_LEN;
    d_store64_le(dk, s.a0);
    d_store64_le(dk + 8u, s.a1);
    d_store64_le(dk + 16u, s.a2);
    d_store64_le(dk + 24u, s.a3);
    int meets = 0;
    for (int i = PH_DIGEST_LEN - 1; i >= 0; i--) {
        if (dk[i] < target[i]) {
            meets = 1;
            break;
        }
        if (dk[i] > target[i])
            break;
    }
    meets_out[k] = (uint8_t)meets;
}

#undef PH_DECODE_REG_BLOCK
#undef PH_ABSORB_REG_BLOCK

__global__ void derive_vectors_kernel(int8_t *x_out, uint8_t *h_out,
                                      const uint8_t *header,
                                      size_t header_len,
                                      uint64_t first_nonce,
                                      uint32_t n, uint32_t count)
{
    uint32_t k = blockIdx.x * blockDim.x + threadIdx.x;
    if (k >= count)
        return;

    uint8_t nonce_le[PH_NONCE_LEN];
    uint8_t h[PH_DIGEST_LEN];
    uint64_t nonce = first_nonce + k;
    for (unsigned i = 0; i < PH_NONCE_LEN; i++)
        nonce_le[i] = (uint8_t)(nonce >> (8u * i));

    d_shake256_t c;
    d_shake_init(&c);
    d_shake_absorb(&c, (const uint8_t *)D_TAG_VECTOR,
                   sizeof H_TAG_VECTOR - 1u);
    d_shake_absorb(&c, header, header_len);
    d_shake_absorb(&c, nonce_le, sizeof nonce_le);
    for (unsigned i = 0; i < PH_DIGEST_LEN; i++) {
        h[i] = d_shake_byte(&c);
        h_out[(size_t)k * PH_DIGEST_LEN + i] = h[i];
    }

    d_shake_init(&c);
    d_shake_absorb(&c, h, sizeof h);
    int8_t *x = x_out + (size_t)k * n;
    for (uint32_t i = 0; i < n; i += 2) {
        uint8_t packed = d_shake_byte(&c);
        x[i] = (int8_t)((int)(packed & 0x0f) - 8);
        x[i + 1] = (int8_t)((int)(packed >> 4) - 8);
    }
}

__global__ void finalize_kernel(uint8_t *digest_out, uint8_t *meets_out,
                                const int32_t *y, const uint8_t *h_in,
                                const uint8_t *target, uint32_t n,
                                uint32_t count)
{
    uint32_t k = blockIdx.x * blockDim.x + threadIdx.x;
    if (k >= count)
        return;

    unsigned log2n = 0;
    for (uint32_t v = n; (v >>= 1) != 0; )
        log2n++;
    unsigned shift = 8u + (log2n - 9u) / 2u;
    int32_t offset = 64 * (int32_t)n;
    const int32_t *yk = y + (size_t)k * n;
    const uint8_t *hk = h_in + (size_t)k * PH_DIGEST_LEN;

    d_shake256_t c;
    d_shake_init(&c);
    d_shake_absorb(&c, (const uint8_t *)D_TAG_FINAL,
                   sizeof H_TAG_FINAL - 1u);
    d_shake_absorb(&c, hk, PH_DIGEST_LEN);
    for (uint32_t i = 0; i < n; i += 2) {
        uint8_t lo = (uint8_t)(
            (((uint32_t)(yk[i] + offset)) >> shift) & 0x0fu);
        uint8_t hi = (uint8_t)(
            (((uint32_t)(yk[i + 1] + offset)) >> shift) & 0x0fu);
        uint8_t packed = (uint8_t)(lo | (uint8_t)(hi << 4));
        d_shake_absorb(&c, &packed, 1);
    }

    uint8_t *dk = digest_out + (size_t)k * PH_DIGEST_LEN;
    for (unsigned i = 0; i < PH_DIGEST_LEN; i++)
        dk[i] = d_shake_byte(&c);

    int meets = 0;
    for (int i = PH_DIGEST_LEN - 1; i >= 0; i--) {
        if (dk[i] < target[i]) {
            meets = 1;
            break;
        }
        if (dk[i] > target[i])
            break;
    }
    meets_out[k] = (uint8_t)meets;
}

static void check_cuda(cudaError_t rc, const char *what)
{
    if (rc != cudaSuccess) {
        std::fprintf(stderr, "%s: %s\n", what, cudaGetErrorString(rc));
        std::exit(1);
    }
}

static void check_cublas(cublasStatus_t rc, const char *what)
{
    if (rc != CUBLAS_STATUS_SUCCESS) {
        std::fprintf(stderr, "%s: cuBLAS status %d\n", what, (int)rc);
        std::exit(1);
    }
}

class PowerSampler {
public:
    bool begin()
    {
#ifdef _WIN32
        lib_ = LoadLibraryA("nvml.dll");
        if (!lib_)
            return false;
        init_ = (init_fn)GetProcAddress(lib_, "nvmlInit_v2");
        shutdown_ = (shutdown_fn)GetProcAddress(lib_, "nvmlShutdown");
        get_handle_ = (get_handle_fn)GetProcAddress(
            lib_, "nvmlDeviceGetHandleByIndex_v2");
        get_power_ = (get_power_fn)GetProcAddress(
            lib_, "nvmlDeviceGetPowerUsage");
        get_energy_ = (get_energy_fn)GetProcAddress(
            lib_, "nvmlDeviceGetTotalEnergyConsumption");
        if (!init_ || !shutdown_ || !get_handle_ || !get_power_) {
            FreeLibrary(lib_);
            lib_ = nullptr;
            return false;
        }
        if (init_() != 0) {
            FreeLibrary(lib_);
            lib_ = nullptr;
            return false;
        }
        initialized_ = true;
        if (get_handle_(0, &device_) != 0) {
            shutdown_();
            initialized_ = false;
            FreeLibrary(lib_);
            lib_ = nullptr;
            return false;
        }
        if (get_energy_ && get_energy_(device_, &energy_start_mj_) == 0)
            direct_energy_ = true;
        running_.store(true);
        worker_ = std::thread([this]() {
            while (running_.load()) {
                unsigned power_mw = 0;
                if (get_power_(device_, &power_mw) == 0) {
                    power_sum_mw_ += power_mw;
                    samples_++;
                }
                std::this_thread::sleep_for(std::chrono::milliseconds(10));
            }
        });
        return true;
#else
        return false;
#endif
    }

    void end(double wall_seconds)
    {
#ifdef _WIN32
        if (!lib_)
            return;
        running_.store(false);
        if (worker_.joinable())
            worker_.join();
        if (direct_energy_) {
            unsigned long long end_mj = 0;
            if (get_energy_(device_, &end_mj) == 0 &&
                end_mj > energy_start_mj_)
                energy_j_ = (double)(end_mj - energy_start_mj_) / 1000.0;
            else
                direct_energy_ = false;
        }
        if (samples_ != 0) {
            average_w_ = power_sum_mw_ / (double)samples_ / 1000.0;
            integrated_energy_j_ = average_w_ * wall_seconds;
        }
        if (initialized_) {
            shutdown_();
            initialized_ = false;
        }
        FreeLibrary(lib_);
        lib_ = nullptr;
#else
        (void)wall_seconds;
#endif
    }

    bool available() const { return samples_ != 0; }
    bool direct_energy() const { return direct_energy_; }
    double average_w() const { return average_w_; }
    double counter_energy_j() const { return energy_j_; }
    double integrated_energy_j() const { return integrated_energy_j_; }
    uint64_t samples() const { return samples_; }

private:
#ifdef _WIN32
    typedef struct nvmlDevice_st *device_t;
    typedef int (__cdecl *init_fn)(void);
    typedef int (__cdecl *shutdown_fn)(void);
    typedef int (__cdecl *get_handle_fn)(unsigned, device_t *);
    typedef int (__cdecl *get_power_fn)(device_t, unsigned *);
    typedef int (__cdecl *get_energy_fn)(device_t, unsigned long long *);
    HMODULE lib_ = nullptr;
    init_fn init_ = nullptr;
    shutdown_fn shutdown_ = nullptr;
    get_handle_fn get_handle_ = nullptr;
    get_power_fn get_power_ = nullptr;
    get_energy_fn get_energy_ = nullptr;
    device_t device_ = nullptr;
    bool initialized_ = false;
    std::atomic<bool> running_{false};
    std::thread worker_;
    unsigned long long energy_start_mj_ = 0;
#endif
    bool direct_energy_ = false;
    double power_sum_mw_ = 0.0;
    uint64_t samples_ = 0;
    double average_w_ = 0.0;
    double energy_j_ = 0.0;
    double integrated_energy_j_ = 0.0;
};

static void launch_vectors(int8_t *d_x, uint8_t *d_h,
                           const uint8_t *d_header, size_t header_len,
                           uint64_t first_nonce, uint32_t n, uint32_t batch,
                           int shake_mode, cudaStream_t stream = 0)
{
    unsigned work_items = shake_mode == SHAKE_WARP ? batch * 32u : batch;
    unsigned blocks = (work_items + CUDA_THREADS - 1u) / CUDA_THREADS;
    if (shake_mode == SHAKE_WARP) {
        derive_vectors_warp_kernel<<<blocks, CUDA_THREADS, 0, stream>>>(
            d_x, d_h, d_header, header_len, first_nonce, n, batch);
    } else if (shake_mode == SHAKE_REGISTER) {
        derive_vectors_register_kernel<<<blocks, CUDA_THREADS, 0, stream>>>(
            d_x, d_h, d_header, header_len, first_nonce, n, batch);
    } else if (shake_mode == SHAKE_DIRECT) {
        derive_vectors_direct_kernel<<<blocks, CUDA_THREADS, 0, stream>>>(
            d_x, d_h, d_header, header_len, first_nonce, n, batch);
    } else {
        derive_vectors_kernel<<<blocks, CUDA_THREADS, 0, stream>>>(
            d_x, d_h, d_header, header_len, first_nonce, n, batch);
    }
    check_cuda(cudaGetLastError(), "derive_vectors_kernel launch");
}

static void launch_gemm(cublasHandle_t handle, const int8_t *d_m,
                        const int8_t *d_x, int32_t *d_y,
                        uint32_t n, uint32_t batch)
{
    const int alpha = 1;
    const int beta = 0;
    /*
     * M is row-major in the reference. cuBLAS reads column-major, so the
     * resident bytes represent M^T and CUBLAS_OP_T recovers M. Each nonce
     * vector is one contiguous column of X; Y uses the same layout.
     */
    check_cublas(cublasGemmEx(
        handle, CUBLAS_OP_T, CUBLAS_OP_N,
        (int)n, (int)batch, (int)n,
        &alpha,
        d_m, CUDA_R_8I, (int)n,
        d_x, CUDA_R_8I, (int)n,
        &beta,
        d_y, CUDA_R_32I, (int)n,
        CUBLAS_COMPUTE_32I, (cublasGemmAlgo_t)PH_CUBLAS_ALGO),
        "exact INT8 GEMM");
}

static void launch_final(uint8_t *d_digest, uint8_t *d_meets,
                         const int32_t *d_y, const uint8_t *d_h,
                         const uint8_t *d_target,
                         uint32_t n, uint32_t batch, int shake_mode,
                         cudaStream_t stream = 0)
{
    unsigned work_items = shake_mode == SHAKE_WARP ? batch * 32u : batch;
    unsigned blocks = (work_items + CUDA_THREADS - 1u) / CUDA_THREADS;
    if (shake_mode == SHAKE_WARP) {
        finalize_warp_kernel<<<blocks, CUDA_THREADS, 0, stream>>>(
            d_digest, d_meets, d_y, d_h, d_target, n, batch);
    } else if (shake_mode == SHAKE_REGISTER) {
        finalize_register_kernel<<<blocks, CUDA_THREADS, 0, stream>>>(
            d_digest, d_meets, d_y, d_h, d_target, n, batch);
    } else if (shake_mode == SHAKE_DIRECT) {
        finalize_direct_kernel<<<blocks, CUDA_THREADS, 0, stream>>>(
            d_digest, d_meets, d_y, d_h, d_target, n, batch);
    } else {
        finalize_kernel<<<blocks, CUDA_THREADS, 0, stream>>>(
            d_digest, d_meets, d_y, d_h, d_target, n, batch);
    }
    check_cuda(cudaGetLastError(), "finalize_kernel launch");
}

static int validate_pipeline(const ph_matrix_t *matrix,
                             const uint8_t *header, size_t header_len,
                             const uint8_t target[PH_DIGEST_LEN],
                             const int8_t *d_x, const int32_t *d_y,
                             const uint8_t *d_h, const uint8_t *d_digest,
                             const uint8_t *d_meets, uint32_t batch,
                             uint64_t first_nonce)
{
    uint32_t count = std::min(batch, (uint32_t)VALIDATION_NONCES);
    uint32_t n = matrix->n;
    std::vector<int8_t> got_x((size_t)count * n);
    std::vector<int32_t> got_y((size_t)count * n);
    std::vector<uint8_t> got_h((size_t)count * PH_DIGEST_LEN);
    std::vector<uint8_t> got_d((size_t)count * PH_DIGEST_LEN);
    std::vector<uint8_t> got_meets(count);
    check_cuda(cudaMemcpy(got_x.data(), d_x, got_x.size() * sizeof(int8_t),
                          cudaMemcpyDeviceToHost), "copy validation x");
    check_cuda(cudaMemcpy(got_y.data(), d_y, got_y.size() * sizeof(int32_t),
                          cudaMemcpyDeviceToHost), "copy validation y");
    check_cuda(cudaMemcpy(got_h.data(), d_h, got_h.size(),
                          cudaMemcpyDeviceToHost), "copy validation h");
    check_cuda(cudaMemcpy(got_d.data(), d_digest, got_d.size(),
                          cudaMemcpyDeviceToHost), "copy validation digest");
    check_cuda(cudaMemcpy(got_meets.data(), d_meets, got_meets.size(),
                          cudaMemcpyDeviceToHost), "copy validation target");

    std::vector<int8_t> ref_x(n);
    std::vector<int32_t> ref_y(n);
    std::vector<uint8_t> ref_r(n / 2u);
    uint8_t ref_h[PH_DIGEST_LEN], ref_d[PH_DIGEST_LEN];
    for (uint32_t k = 0; k < count; k++) {
        if (ph_hash_trace(ref_d, ref_h, ref_x.data(), ref_y.data(),
                          ref_r.data(), matrix, header, header_len,
                          first_nonce + k) != 0) {
            std::fprintf(stderr, "C oracle failed at nonce %llu\n",
                         (unsigned long long)(first_nonce + k));
            return 0;
        }
        if (std::memcmp(ref_h, got_h.data() + (size_t)k * PH_DIGEST_LEN,
                        PH_DIGEST_LEN) != 0) {
            std::fprintf(stderr, "GPU h_in mismatch at nonce %u\n", k);
            return 0;
        }
        if (std::memcmp(ref_x.data(), got_x.data() + (size_t)k * n, n) != 0) {
            std::fprintf(stderr, "GPU x mismatch at nonce %u\n", k);
            return 0;
        }
        if (std::memcmp(ref_y.data(), got_y.data() + (size_t)k * n,
                        (size_t)n * sizeof(int32_t)) != 0) {
            std::fprintf(stderr, "GPU y mismatch at nonce %u\n", k);
            return 0;
        }
        if (std::memcmp(ref_d, got_d.data() + (size_t)k * PH_DIGEST_LEN,
                        PH_DIGEST_LEN) != 0) {
            std::fprintf(stderr, "GPU digest mismatch at nonce %u\n", k);
            return 0;
        }
        if ((uint8_t)ph_meets_target(ref_d, target) != got_meets[k]) {
            std::fprintf(stderr, "GPU target mismatch at nonce %u\n", k);
            return 0;
        }
    }
    std::printf("validation:          %u/%u nonces match h_in, x, y, d, target\n",
                count, count);
    return 1;
}

int main(int argc, char **argv)
{
    uint32_t batch = argc > 1 ? (uint32_t)std::strtoul(argv[1], nullptr, 10)
                              : 4096u;
    uint32_t iterations =
        argc > 2 ? (uint32_t)std::strtoul(argv[2], nullptr, 10) : 50u;
    int shake_mode = SHAKE_REGISTER;
    if (argc > 3 && std::strcmp(argv[3], "thread") == 0)
        shake_mode = SHAKE_THREAD;
    else if (argc > 3 && std::strcmp(argv[3], "warp") == 0)
        shake_mode = SHAKE_WARP;
    else if (argc > 3 && std::strcmp(argv[3], "direct") == 0)
        shake_mode = SHAKE_DIRECT;
    else if (argc > 3 && std::strcmp(argv[3], "register") == 0)
        shake_mode = SHAKE_REGISTER;
    uint32_t dataset =
        argc > 4 ? (uint32_t)std::strtoul(argv[4], nullptr, 10) : 0u;
    if (batch == 0 || iterations == 0 || batch > (1u << 20)) {
        std::fprintf(stderr, "usage: %s [batch 1..1048576] [iterations > 0]\n",
                     argv[0]);
        return 2;
    }
    if (argc > 3 && std::strcmp(argv[3], "register") != 0 &&
        std::strcmp(argv[3], "direct") != 0 &&
        std::strcmp(argv[3], "warp") != 0 &&
        std::strcmp(argv[3], "thread") != 0) {
        std::fprintf(stderr,
                     "kernel must be register, direct, warp, or thread\n");
        return 2;
    }

    cudaDeviceProp props;
    check_cuda(cudaGetDeviceProperties(&props, 0), "cudaGetDeviceProperties");
    check_cuda(cudaSetDevice(0), "cudaSetDevice");

    uint8_t parent[PH_DIGEST_LEN], header[80], target[PH_DIGEST_LEN];
    char label[64];
    std::snprintf(label, sizeof label, "cuda-bench-parent-%u", dataset);
    ph_shake256(parent, sizeof parent, label, std::strlen(label));
    std::snprintf(label, sizeof label, "cuda-bench-header-%u", dataset);
    ph_shake256(header, sizeof header, label, std::strlen(label));
    std::snprintf(label, sizeof label, "cuda-bench-target-%u", dataset);
    ph_shake256(target, sizeof target, label, std::strlen(label));

    ph_matrix_t matrix = {};
    if (ph_matrix_derive(&matrix, PH_GENESIS_N, parent) != 0) {
        std::fprintf(stderr, "matrix derivation failed\n");
        return 1;
    }
    uint32_t n = matrix.n;
    size_t matrix_bytes = (size_t)n * n;
    size_t x_bytes = (size_t)batch * n;
    size_t y_bytes = (size_t)batch * n * sizeof(int32_t);
    size_t h_bytes = (size_t)batch * PH_DIGEST_LEN;
    size_t d_bytes = (size_t)batch * PH_DIGEST_LEN;

    int8_t *d_m = nullptr, *d_x = nullptr;
    int32_t *d_y = nullptr;
    uint8_t *d_h = nullptr, *d_digest = nullptr;
    uint8_t *d_meets = nullptr, *d_header = nullptr, *d_target = nullptr;
    check_cuda(cudaMalloc((void **)&d_m, matrix_bytes), "cudaMalloc M");
    check_cuda(cudaMalloc((void **)&d_x, x_bytes), "cudaMalloc X");
    check_cuda(cudaMalloc((void **)&d_y, y_bytes), "cudaMalloc Y");
    check_cuda(cudaMalloc((void **)&d_h, h_bytes), "cudaMalloc h_in");
    check_cuda(cudaMalloc((void **)&d_digest, d_bytes), "cudaMalloc digest");
    check_cuda(cudaMalloc((void **)&d_meets, batch), "cudaMalloc meets");
    check_cuda(cudaMalloc((void **)&d_header, sizeof header), "cudaMalloc header");
    check_cuda(cudaMalloc((void **)&d_target, sizeof target), "cudaMalloc target");

    auto upload_start = std::chrono::steady_clock::now();
    check_cuda(cudaMemcpy(d_m, matrix.m, matrix_bytes, cudaMemcpyHostToDevice),
               "upload M");
    check_cuda(cudaMemcpy(d_header, header, sizeof header,
                          cudaMemcpyHostToDevice), "upload header");
    check_cuda(cudaMemcpy(d_target, target, sizeof target,
                          cudaMemcpyHostToDevice), "upload target");
    check_cuda(cudaDeviceSynchronize(), "matrix upload synchronize");
    double upload_ms = std::chrono::duration<double, std::milli>(
        std::chrono::steady_clock::now() - upload_start).count();

    cublasHandle_t handle;
    check_cublas(cublasCreate(&handle), "cublasCreate");

    for (unsigned warmup = 0; warmup < 3; warmup++) {
        launch_vectors(d_x, d_h, d_header, sizeof header,
                       (uint64_t)warmup * batch, n, batch, shake_mode);
        launch_gemm(handle, d_m, d_x, d_y, n, batch);
        launch_final(d_digest, d_meets, d_y, d_h, d_target, n, batch,
                     shake_mode);
    }
    check_cuda(cudaDeviceSynchronize(), "warmup synchronize");

    launch_vectors(d_x, d_h, d_header, sizeof header, 0, n, batch,
                   shake_mode);
    launch_gemm(handle, d_m, d_x, d_y, n, batch);
    launch_final(d_digest, d_meets, d_y, d_h, d_target, n, batch,
                 shake_mode);
    check_cuda(cudaDeviceSynchronize(), "validation synchronize");
    if (!validate_pipeline(&matrix, header, sizeof header, target,
                           d_x, d_y, d_h, d_digest, d_meets, batch, 0))
        return 1;

    cudaEvent_t e0, e1, e2, e3;
    check_cuda(cudaEventCreate(&e0), "cudaEventCreate e0");
    check_cuda(cudaEventCreate(&e1), "cudaEventCreate e1");
    check_cuda(cudaEventCreate(&e2), "cudaEventCreate e2");
    check_cuda(cudaEventCreate(&e3), "cudaEventCreate e3");

    float vector_ms = 0.0f, gemm_ms = 0.0f, final_ms = 0.0f;
    uint64_t first_nonce = batch;
    PowerSampler power;
    bool power_started = power.begin();
    auto wall_start = std::chrono::steady_clock::now();
    for (uint32_t iter = 0; iter < iterations; iter++) {
        float ms = 0.0f;
        check_cuda(cudaEventRecord(e0), "record e0");
        launch_vectors(d_x, d_h, d_header, sizeof header,
                       first_nonce, n, batch, shake_mode);
        check_cuda(cudaEventRecord(e1), "record e1");
        launch_gemm(handle, d_m, d_x, d_y, n, batch);
        check_cuda(cudaEventRecord(e2), "record e2");
        launch_final(d_digest, d_meets, d_y, d_h, d_target, n, batch,
                     shake_mode);
        check_cuda(cudaEventRecord(e3), "record e3");
        check_cuda(cudaEventSynchronize(e3), "synchronize e3");
        check_cuda(cudaEventElapsedTime(&ms, e0, e1), "elapsed vectors");
        vector_ms += ms;
        check_cuda(cudaEventElapsedTime(&ms, e1, e2), "elapsed GEMM");
        gemm_ms += ms;
        check_cuda(cudaEventElapsedTime(&ms, e2, e3), "elapsed final");
        final_ms += ms;
        first_nonce += batch;
    }
    double wall_s = std::chrono::duration<double>(
        std::chrono::steady_clock::now() - wall_start).count();
    if (power_started)
        power.end(wall_s);

    /*
     * Three independent nonce buffers/streams expose cross-batch overlap.
     * Each stream preserves vector -> GEMM -> final ordering, while distinct
     * streams may overlap digital kernels with another batch's GEMM.
     */
    static const unsigned pipeline_depth = PH_PIPELINE_DEPTH;
    std::vector<int8_t *> pipeline_x(pipeline_depth, nullptr);
    std::vector<int32_t *> pipeline_y(pipeline_depth, nullptr);
    std::vector<uint8_t *> pipeline_h(pipeline_depth, nullptr);
    std::vector<uint8_t *> pipeline_digest(pipeline_depth, nullptr);
    std::vector<uint8_t *> pipeline_meets(pipeline_depth, nullptr);
    std::vector<cudaStream_t> pipeline_stream(pipeline_depth, nullptr);
    std::vector<cublasHandle_t> pipeline_handle(pipeline_depth, nullptr);
    pipeline_x[0] = d_x;
    pipeline_y[0] = d_y;
    pipeline_h[0] = d_h;
    pipeline_digest[0] = d_digest;
    pipeline_meets[0] = d_meets;
    pipeline_handle[0] = handle;
    for (unsigned slot = 0; slot < pipeline_depth; slot++) {
        check_cuda(cudaStreamCreateWithFlags(
                       &pipeline_stream[slot], cudaStreamNonBlocking),
                   "create pipeline stream");
        if (slot != 0u)
            check_cublas(cublasCreate(&pipeline_handle[slot]),
                         "create pipeline cuBLAS handle");
        check_cublas(cublasSetStream(
                         pipeline_handle[slot], pipeline_stream[slot]),
                     "set pipeline cuBLAS stream");
        if (slot != 0u) {
            check_cuda(cudaMalloc((void **)&pipeline_x[slot], x_bytes),
                       "cudaMalloc pipeline X");
            check_cuda(cudaMalloc((void **)&pipeline_y[slot], y_bytes),
                       "cudaMalloc pipeline Y");
            check_cuda(cudaMalloc((void **)&pipeline_h[slot], h_bytes),
                       "cudaMalloc pipeline h");
            check_cuda(cudaMalloc((void **)&pipeline_digest[slot], d_bytes),
                       "cudaMalloc pipeline digest");
            check_cuda(cudaMalloc((void **)&pipeline_meets[slot], batch),
                       "cudaMalloc pipeline meets");
        }
    }
    uint64_t pipeline_first =
        (uint64_t)batch * ((uint64_t)iterations + 1u);
    for (unsigned slot = 0; slot < pipeline_depth; slot++) {
        launch_vectors(pipeline_x[slot], pipeline_h[slot], d_header,
                       sizeof header, pipeline_first + (uint64_t)slot * batch,
                       n, batch, shake_mode, pipeline_stream[slot]);
        launch_gemm(pipeline_handle[slot], d_m, pipeline_x[slot],
                    pipeline_y[slot], n, batch);
        launch_final(pipeline_digest[slot], pipeline_meets[slot],
                     pipeline_y[slot], pipeline_h[slot], d_target, n, batch,
                     shake_mode, pipeline_stream[slot]);
    }
    for (unsigned slot = 0; slot < pipeline_depth; slot++)
        check_cuda(cudaStreamSynchronize(pipeline_stream[slot]),
                   "pipeline warmup synchronize");

    for (unsigned slot = 0; slot < pipeline_depth; slot++) {
        if (!validate_pipeline(
                &matrix, header, sizeof header, target,
                pipeline_x[slot], pipeline_y[slot], pipeline_h[slot],
                pipeline_digest[slot], pipeline_meets[slot], batch,
                pipeline_first + (uint64_t)slot * batch))
            return 1;
    }

    std::this_thread::sleep_for(std::chrono::milliseconds(1000));
    PowerSampler pipeline_power;
    bool pipeline_power_started = pipeline_power.begin();
    auto pipeline_start = std::chrono::steady_clock::now();
    pipeline_first += (uint64_t)pipeline_depth * batch;
    for (uint32_t iter = 0; iter < iterations; iter++) {
        unsigned slot = iter % pipeline_depth;
        if (iter >= pipeline_depth)
            check_cuda(cudaStreamSynchronize(pipeline_stream[slot]),
                       "pipeline slot synchronize");
        launch_vectors(pipeline_x[slot], pipeline_h[slot], d_header,
                       sizeof header, pipeline_first, n, batch, shake_mode,
                       pipeline_stream[slot]);
        launch_gemm(pipeline_handle[slot], d_m, pipeline_x[slot],
                    pipeline_y[slot], n, batch);
        launch_final(pipeline_digest[slot], pipeline_meets[slot],
                     pipeline_y[slot], pipeline_h[slot], d_target, n, batch,
                     shake_mode, pipeline_stream[slot]);
        pipeline_first += batch;
    }
    for (unsigned slot = 0; slot < pipeline_depth; slot++)
        check_cuda(cudaStreamSynchronize(pipeline_stream[slot]),
                   "pipeline final synchronize");
    double pipeline_wall_s = std::chrono::duration<double>(
        std::chrono::steady_clock::now() - pipeline_start).count();
    if (pipeline_power_started)
        pipeline_power.end(pipeline_wall_s);

    double attempts = (double)batch * iterations;
    double device_ms = (double)vector_ms + gemm_ms + final_ms;
    double device_s = device_ms / 1000.0;
    double macs = attempts * (double)n * n;
    std::printf("\n%s\n", ph_version());
    std::printf("device:              %s (cc %d.%d, %zu MiB global)\n",
                props.name, props.major, props.minor,
                (size_t)props.totalGlobalMem >> 20);
    std::printf("profile:             n=%u batch=%u iterations=%u dataset=%u\n",
                n, batch, iterations, dataset);
    const char *shake_name = shake_mode == SHAKE_REGISTER ?
        "register-per-state" : (shake_mode == SHAKE_DIRECT ? "direct-lane" :
        (shake_mode == SHAKE_WARP ? "warp-per-state" : "thread-per-state"));
    std::printf("SHAKE kernel:        %s\n", shake_name);
    const char *gemm_name = PH_CUBLAS_ALGO == CUBLAS_GEMM_AUTOTUNE ?
        "cublas-autotune" : "cublas-default-tensor-op";
    std::printf("GEMM algorithm:      %s\n", gemm_name);
    int runtime_version = 0, driver_version = 0;
    check_cuda(cudaRuntimeGetVersion(&runtime_version), "CUDA runtime version");
    check_cuda(cudaDriverGetVersion(&driver_version), "CUDA driver version");
    std::printf("CUDA build/runtime:  nvcc %d.%d, runtime %d, driver %d\n",
                __CUDACC_VER_MAJOR__, __CUDACC_VER_MINOR__,
                runtime_version, driver_version);
    std::printf("resident matrix:     %.3f MiB, upload %.3f ms (excluded)\n",
                matrix_bytes / (1024.0 * 1024.0), upload_ms);
    std::printf("scratch/output:      %.3f MiB\n",
                (x_bytes + y_bytes + h_bytes + d_bytes + batch) /
                (1024.0 * 1024.0));
    std::printf("\nGPU stage timings:\n");
    std::printf("vector SHAKE+decode: %9.3f us/attempt  %6.2f%%\n",
                vector_ms * 1000.0 / attempts,
                100.0 * vector_ms / device_ms);
    std::printf("exact INT8 GEMM:     %9.3f us/attempt  %6.2f%%\n",
                gemm_ms * 1000.0 / attempts,
                100.0 * gemm_ms / device_ms);
    std::printf("requant+final SHAKE: %9.3f us/attempt  %6.2f%%\n",
                final_ms * 1000.0 / attempts,
                100.0 * final_ms / device_ms);
    std::printf("\nend-to-end device:   %.0f attempts/s (%.3f us/attempt)\n",
                attempts / device_s, device_ms * 1000.0 / attempts);
    std::printf("exact GEMM rate:     %.3f TMAC/s\n",
                macs / ((double)gemm_ms / 1000.0) / 1e12);
    std::printf("host-observed rate:  %.0f attempts/s (event sync included)\n",
                attempts / wall_s);
    if (power.available()) {
        std::printf("average board power: %.1f W (%" PRIu64 " NVML samples)\n",
                    power.average_w(), power.samples());
        std::printf("integrated energy:   %.3f J, %.3f uJ/attempt\n",
                    power.integrated_energy_j(),
                    power.integrated_energy_j() * 1e6 / attempts);
        if (power.direct_energy())
            std::printf("NVML counter energy: %.3f J, %.3f uJ/attempt\n",
                        power.counter_energy_j(),
                        power.counter_energy_j() * 1e6 / attempts);
    } else {
        std::printf("energy:              unavailable from NVML\n");
    }
    std::printf("%u-stream pipeline:   %.0f attempts/s (host-observed)\n",
                pipeline_depth, attempts / pipeline_wall_s);
    if (pipeline_power.available()) {
        std::printf("pipeline integrated: %.3f J, %.3f uJ/attempt, %.1f W\n",
                    pipeline_power.integrated_energy_j(),
                    pipeline_power.integrated_energy_j() * 1e6 / attempts,
                    pipeline_power.average_w());
        if (pipeline_power.direct_energy())
            std::printf("pipeline counter:    %.3f J, %.3f uJ/attempt\n",
                        pipeline_power.counter_energy_j(),
                        pipeline_power.counter_energy_j() * 1e6 / attempts);
    }
    double average_w = power.available() ? power.average_w() : 0.0;
    double integrated_uj = power.available() ?
        power.integrated_energy_j() * 1e6 / attempts : 0.0;
    double counter_uj = power.direct_energy() ?
        power.counter_energy_j() * 1e6 / attempts : 0.0;
    std::printf(
        "RESULT_CSV,%u,%u,%u,%s,%s,%u,%.9f,%.9f,%.9f,%.3f,%.3f,"
        "%.6f,%.3f,%.6f,%.6f,%.3f,%.3f,%.6f,%.6f\n",
        dataset, batch, iterations, shake_name, gemm_name, pipeline_depth,
        vector_ms * 1000.0 / attempts,
        gemm_ms * 1000.0 / attempts,
        final_ms * 1000.0 / attempts,
        attempts / device_s, attempts / wall_s,
        100.0 * gemm_ms / device_ms, average_w, integrated_uj, counter_uj,
        attempts / pipeline_wall_s,
        pipeline_power.available() ? pipeline_power.average_w() : 0.0,
        pipeline_power.available() ?
            pipeline_power.integrated_energy_j() * 1e6 / attempts : 0.0,
        pipeline_power.direct_energy() ?
            pipeline_power.counter_energy_j() * 1e6 / attempts : 0.0);
    std::printf("\nNo PCIe input streaming is charged per nonce; header, target, and\n"
                "matrix are resident. Integrated energy is sampled board power\n"
                "times wall time; the independent NVML counter is also shown.\n"
                "Both exclude allocation, validation, upload, and the settle gap.\n");

    cudaEventDestroy(e0);
    cudaEventDestroy(e1);
    cudaEventDestroy(e2);
    cudaEventDestroy(e3);
    for (unsigned slot = 0; slot < pipeline_depth; slot++) {
        cudaStreamDestroy(pipeline_stream[slot]);
        if (slot != 0u) {
            cublasDestroy(pipeline_handle[slot]);
            cudaFree(pipeline_x[slot]);
            cudaFree(pipeline_y[slot]);
            cudaFree(pipeline_h[slot]);
            cudaFree(pipeline_digest[slot]);
            cudaFree(pipeline_meets[slot]);
        }
    }
    cublasDestroy(handle);
    cudaFree(d_m);
    cudaFree(d_x);
    cudaFree(d_y);
    cudaFree(d_h);
    cudaFree(d_digest);
    cudaFree(d_meets);
    cudaFree(d_header);
    cudaFree(d_target);
    ph_matrix_free(&matrix);
    return 0;
}
