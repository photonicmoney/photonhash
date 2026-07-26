/*
 * Exact electronic adversary probe for PhotonHash v0.3 candidate R1.
 *
 * This is not a miner and not a consensus implementation. It measures a
 * repeated resident INT8 matrix with an exact low-bit nonlinear boundary.
 * Firmware, clocks, voltage, power limits, fans, drivers, and system settings
 * are not modified.
 */

#include "photonhash.h"

#include <cuda_runtime.h>
#include <cublas_v2.h>

#include <algorithm>
#include <cinttypes>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <vector>

#ifndef CUDA_THREADS
#define CUDA_THREADS 256
#endif

#ifndef PH_CUBLAS_ALGO
#define PH_CUBLAS_ALGO CUBLAS_GEMM_AUTOTUNE
#endif

static void check_cuda(cudaError_t status, const char *operation)
{
    if (status != cudaSuccess) {
        std::fprintf(stderr, "%s: %s\n", operation, cudaGetErrorString(status));
        std::exit(2);
    }
}

static void check_cublas(cublasStatus_t status, const char *operation)
{
    if (status != CUBLAS_STATUS_SUCCESS) {
        std::fprintf(stderr, "%s: cuBLAS status %d\n", operation, (int)status);
        std::exit(2);
    }
}

static unsigned log2_exact(uint32_t n)
{
    unsigned result = 0;
    while ((1u << result) < n)
        result++;
    return result;
}

__host__ __device__ static inline uint32_t round_mask(uint32_t coordinate,
                                                       uint32_t round)
{
    uint32_t value = coordinate * 0x9e3779b9u;
    value ^= (round + 1u) * 0x85ebca6bu;
    value ^= value >> 16;
    value *= 0x7feb352du;
    value ^= value >> 15;
    return value & 15u;
}

__host__ __device__ static inline int8_t boundary_value(int32_t value,
                                                         uint32_t coordinate,
                                                         uint32_t round,
                                                         unsigned shift,
                                                         int32_t offset)
{
    uint32_t bucket =
        (((uint32_t)(value + offset)) >> shift) & 15u;
    bucket ^= round_mask(coordinate, round);
    return (int8_t)((int)bucket - 8);
}

__global__ void boundary_kernel(int8_t *state, const int32_t *product,
                                uint32_t n, uint32_t batch, uint32_t round,
                                unsigned shift, int32_t offset)
{
    size_t index = (size_t)blockIdx.x * blockDim.x + threadIdx.x;
    size_t count = (size_t)n * batch;
    if (index >= count)
        return;
    uint32_t coordinate = (uint32_t)(index % n);
    state[index] =
        boundary_value(product[index], coordinate, round, shift, offset);
}

static void launch_gemm(cublasHandle_t handle, const int8_t *matrix,
                        const int8_t *state, int32_t *product,
                        uint32_t n, uint32_t batch)
{
    const int alpha = 1;
    const int beta = 0;
    /*
     * The reference matrix is row-major. cuBLAS reads it as column-major M^T;
     * CUBLAS_OP_T recovers M. Each nonce state is one contiguous column.
     */
    check_cublas(
        cublasGemmEx(handle, CUBLAS_OP_T, CUBLAS_OP_N,
                     (int)n, (int)batch, (int)n,
                     &alpha,
                     matrix, CUDA_R_8I, (int)n,
                     state, CUDA_R_8I, (int)n,
                     &beta,
                     product, CUDA_R_32I, (int)n,
                     CUBLAS_COMPUTE_32I,
                     (cublasGemmAlgo_t)PH_CUBLAS_ALGO),
        "cublasGemmEx");
}

static void launch_boundary(int8_t *state, const int32_t *product,
                            uint32_t n, uint32_t batch, uint32_t round)
{
    size_t count = (size_t)n * batch;
    unsigned blocks =
        (unsigned)((count + CUDA_THREADS - 1u) / CUDA_THREADS);
    unsigned log2n = log2_exact(n);
    unsigned shift = 8u + (log2n - 9u) / 2u;
    int32_t offset = 64 * (int32_t)n;
    boundary_kernel<<<blocks, CUDA_THREADS>>>(
        state, product, n, batch, round, shift, offset);
    check_cuda(cudaGetLastError(), "boundary_kernel launch");
}

static float elapsed(cudaEvent_t begin, cudaEvent_t end)
{
    float milliseconds = 0.0f;
    check_cuda(cudaEventElapsedTime(&milliseconds, begin, end),
               "cudaEventElapsedTime");
    return milliseconds;
}

static bool validate(const ph_matrix_t *matrix, int8_t *device_state,
                     int32_t *device_product, const std::vector<int8_t> &initial,
                     uint32_t rounds)
{
    uint32_t n = matrix->n;
    std::vector<int8_t> reference(initial.begin(), initial.begin() + n);
    std::vector<int8_t> observed(n);
    std::vector<int32_t> product(n);
    unsigned log2n = log2_exact(n);
    unsigned shift = 8u + (log2n - 9u) / 2u;
    int32_t offset = 64 * (int32_t)n;

    for (uint32_t round = 0; round < rounds; round++) {
        for (uint32_t row = 0; row < n; row++) {
            int32_t sum = 0;
            const int8_t *m = matrix->m + (size_t)row * n;
            for (uint32_t column = 0; column < n; column++)
                sum += (int32_t)m[column] * reference[column];
            product[row] = sum;
        }
        for (uint32_t i = 0; i < n; i++)
            reference[i] =
                boundary_value(product[i], i, round, shift, offset);
    }

    check_cuda(cudaMemcpy(observed.data(), device_state, n,
                          cudaMemcpyDeviceToHost),
               "download validation state");
    if (!std::equal(reference.begin(), reference.end(), observed.begin())) {
        for (uint32_t i = 0; i < n; i++) {
            if (reference[i] != observed[i]) {
                std::fprintf(stderr,
                    "validation mismatch at coordinate %u: expected %d got %d\n",
                    i, (int)reference[i], (int)observed[i]);
                break;
            }
        }
        return false;
    }

    /* Also keep the product allocation observable to sanitizers. */
    int32_t product_probe = 0;
    check_cuda(cudaMemcpy(&product_probe, device_product, sizeof product_probe,
                          cudaMemcpyDeviceToHost),
               "download validation product");
    std::printf("validation:          PASS (rounds=%u, product_probe=%d)\n",
                rounds, product_probe);
    return true;
}

int main(int argc, char **argv)
{
    uint32_t n = argc > 1 ? (uint32_t)std::strtoul(argv[1], nullptr, 10)
                          : 1024u;
    uint32_t batch = argc > 2 ? (uint32_t)std::strtoul(argv[2], nullptr, 10)
                              : 32768u;
    uint32_t rounds = argc > 3 ? (uint32_t)std::strtoul(argv[3], nullptr, 10)
                               : 64u;
    uint32_t repeats = argc > 4 ? (uint32_t)std::strtoul(argv[4], nullptr, 10)
                                : 5u;
    if (n < 1024u || n > 16384u || (n & (n - 1u)) != 0 ||
        batch == 0 || batch > (1u << 20) ||
        rounds == 0 || rounds > 1024u || repeats == 0) {
        std::fprintf(stderr,
            "usage: %s [power-of-two n 1024..16384] [batch] [rounds 1..1024] [repeats]\n",
            argv[0]);
        return 1;
    }

    uint8_t parent[PH_DIGEST_LEN];
    char label[80];
    std::snprintf(label, sizeof label, "PhotonHash/v0.3/R1/n=%u", n);
    ph_shake256(parent, sizeof parent, label, std::strlen(label));
    ph_matrix_t matrix = {};
    if (ph_matrix_derive(&matrix, n, parent) != 0) {
        std::fprintf(stderr, "matrix derivation failed for n=%u\n", n);
        return 1;
    }

    size_t matrix_bytes = (size_t)n * n;
    size_t state_bytes = (size_t)n * batch;
    size_t product_bytes = state_bytes * sizeof(int32_t);
    std::vector<int8_t> initial(state_bytes);
    for (size_t i = 0; i < state_bytes; i++) {
        uint32_t value = (uint32_t)i * 0x9e3779b9u + 0x243f6a88u;
        value ^= value >> 16;
        initial[i] = (int8_t)((int)((value >> 28) & 15u) - 8);
    }

    int8_t *d_matrix = nullptr;
    int8_t *d_state = nullptr;
    int32_t *d_product = nullptr;
    check_cuda(cudaMalloc((void **)&d_matrix, matrix_bytes), "cudaMalloc matrix");
    check_cuda(cudaMalloc((void **)&d_state, state_bytes), "cudaMalloc state");
    check_cuda(cudaMalloc((void **)&d_product, product_bytes),
               "cudaMalloc product");
    check_cuda(cudaMemcpy(d_matrix, matrix.m, matrix_bytes,
                          cudaMemcpyHostToDevice), "upload matrix");
    check_cuda(cudaMemcpy(d_state, initial.data(), state_bytes,
                          cudaMemcpyHostToDevice), "upload state");

    cublasHandle_t handle = nullptr;
    check_cublas(cublasCreate(&handle), "cublasCreate");
    for (unsigned warmup = 0; warmup < 2; warmup++) {
        for (uint32_t round = 0; round < std::min(rounds, 4u); round++) {
            launch_gemm(handle, d_matrix, d_state, d_product, n, batch);
            launch_boundary(d_state, d_product, n, batch, round);
        }
    }
    check_cuda(cudaDeviceSynchronize(), "warmup synchronize");

    check_cuda(cudaMemcpy(d_state, initial.data(), state_bytes,
                          cudaMemcpyHostToDevice), "reset validation state");
    for (uint32_t round = 0; round < rounds; round++) {
        launch_gemm(handle, d_matrix, d_state, d_product, n, batch);
        launch_boundary(d_state, d_product, n, batch, round);
    }
    check_cuda(cudaDeviceSynchronize(), "validation synchronize");
    if (!validate(&matrix, d_state, d_product, initial, rounds))
        return 3;

    cudaEvent_t begin, after_gemm, after_boundary, end;
    check_cuda(cudaEventCreate(&begin), "cudaEventCreate begin");
    check_cuda(cudaEventCreate(&after_gemm), "cudaEventCreate after_gemm");
    check_cuda(cudaEventCreate(&after_boundary), "cudaEventCreate after_boundary");
    check_cuda(cudaEventCreate(&end), "cudaEventCreate end");

    double gemm_ms = 0.0;
    double boundary_ms = 0.0;
    double recurrent_ms = 0.0;
    for (uint32_t repeat = 0; repeat < repeats; repeat++) {
        check_cuda(cudaEventRecord(begin), "record gemm begin");
        for (uint32_t round = 0; round < rounds; round++)
            launch_gemm(handle, d_matrix, d_state, d_product, n, batch);
        check_cuda(cudaEventRecord(after_gemm), "record gemm end");
        check_cuda(cudaEventSynchronize(after_gemm), "sync gemm end");
        gemm_ms += elapsed(begin, after_gemm);

        check_cuda(cudaEventRecord(begin), "record boundary begin");
        for (uint32_t round = 0; round < rounds; round++)
            launch_boundary(d_state, d_product, n, batch, round);
        check_cuda(cudaEventRecord(after_boundary), "record boundary end");
        check_cuda(cudaEventSynchronize(after_boundary), "sync boundary end");
        boundary_ms += elapsed(begin, after_boundary);

        check_cuda(cudaMemcpy(d_state, initial.data(), state_bytes,
                              cudaMemcpyHostToDevice), "reset timed state");
        check_cuda(cudaEventRecord(begin), "record recurrent begin");
        for (uint32_t round = 0; round < rounds; round++) {
            launch_gemm(handle, d_matrix, d_state, d_product, n, batch);
            launch_boundary(d_state, d_product, n, batch, round);
        }
        check_cuda(cudaEventRecord(end), "record recurrent end");
        check_cuda(cudaEventSynchronize(end), "sync recurrent end");
        recurrent_ms += elapsed(begin, end);
    }
    gemm_ms /= repeats;
    boundary_ms /= repeats;
    recurrent_ms /= repeats;

    double attempts = (double)batch;
    double gemm_us_attempt = gemm_ms * 1000.0 / attempts;
    double boundary_us_attempt = boundary_ms * 1000.0 / attempts;
    double recurrent_us_attempt = recurrent_ms * 1000.0 / attempts;
    double fixed_v02_us_attempt = 0.020556 + 0.008304;
    double projected_total = recurrent_us_attempt + fixed_v02_us_attempt;
    double recurrent_gemm_share =
        gemm_us_attempt / (gemm_us_attempt + boundary_us_attempt);
    double projected_matrix_share = gemm_us_attempt / projected_total;

    cudaDeviceProp properties = {};
    check_cuda(cudaGetDeviceProperties(&properties, 0),
               "cudaGetDeviceProperties");
    std::printf("device:              %s, cc %d.%d\n",
                properties.name, properties.major, properties.minor);
    std::printf("candidate:           R1 recurrent same-matrix probe\n");
    std::printf("profile:             n=%u batch=%u rounds=%u repeats=%u\n",
                n, batch, rounds, repeats);
    std::printf("resident matrix:     %.3f MiB\n",
                matrix_bytes / (1024.0 * 1024.0));
    std::printf("working set:         %.3f MiB\n",
                (state_bytes + product_bytes) / (1024.0 * 1024.0));
    std::printf("GEMM-only:           %.6f us/attempt\n", gemm_us_attempt);
    std::printf("boundary-only:       %.6f us/attempt\n", boundary_us_attempt);
    std::printf("alternating core:    %.6f us/attempt\n", recurrent_us_attempt);
    std::printf("core GEMM share:     %.3f%%\n", 100.0 * recurrent_gemm_share);
    std::printf("v0.2 fixed proxy:    %.6f us/attempt (screening only)\n",
                fixed_v02_us_attempt);
    std::printf("projected share:     %.3f%% (GEMM / recurrent+v0.2 proxy)\n",
                100.0 * projected_matrix_share);
    std::printf("core throughput:     %.3f M attempts/s\n",
                1.0 / recurrent_us_attempt);
    std::printf(
        "RESULT_JSON {\"n\":%u,\"batch\":%u,\"rounds\":%u,"
        "\"repeats\":%u,\"gemm_us_attempt\":%.9f,"
        "\"boundary_us_attempt\":%.9f,\"recurrent_us_attempt\":%.9f,"
        "\"core_gemm_share\":%.9f,\"projected_matrix_share\":%.9f}\n",
        n, batch, rounds, repeats, gemm_us_attempt, boundary_us_attempt,
        recurrent_us_attempt, recurrent_gemm_share, projected_matrix_share);
    std::printf(
        "warning: timing probe only; excludes a physical feedback loop and "
        "does not establish photonic advantage or consensus parameters\n");

    cudaEventDestroy(begin);
    cudaEventDestroy(after_gemm);
    cudaEventDestroy(after_boundary);
    cudaEventDestroy(end);
    cublasDestroy(handle);
    cudaFree(d_matrix);
    cudaFree(d_state);
    cudaFree(d_product);
    ph_matrix_free(&matrix);
    return 0;
}
