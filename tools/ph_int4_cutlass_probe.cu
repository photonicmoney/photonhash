/*
 * Standalone exact signed-INT4 GEMM probe for PhotonHash.
 *
 * This is research tooling. It uses NVIDIA CUTLASS headers supplied separately
 * through the compiler include path and does not alter GPU configuration.
 */

#include <cuda_runtime.h>

#include "cutlass/cutlass.h"
#include "cutlass/gemm/device/gemm.h"

#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <vector>

using Element = cutlass::int4b_t;
using Output = int32_t;
using LayoutA = cutlass::layout::RowMajor;
using LayoutB = cutlass::layout::ColumnMajor;
using LayoutC = cutlass::layout::RowMajor;

using Int4Gemm = cutlass::gemm::device::Gemm<
    Element, LayoutA,
    Element, LayoutB,
    Output, LayoutC,
    int32_t,
    cutlass::arch::OpClassTensorOp,
    cutlass::arch::Sm80,
    cutlass::gemm::GemmShape<128, 256, 256>,
    cutlass::gemm::GemmShape<64, 64, 256>,
    cutlass::gemm::GemmShape<16, 8, 64>,
    cutlass::epilogue::thread::LinearCombinationClamp<
        Output, 128 / cutlass::sizeof_bits<Output>::value,
        int32_t, int32_t>,
    cutlass::gemm::threadblock::GemmIdentityThreadblockSwizzle<>,
    2>;

static void check_cuda(cudaError_t rc, const char *what)
{
    if (rc != cudaSuccess) {
        std::fprintf(stderr, "%s: %s\n", what, cudaGetErrorString(rc));
        std::exit(1);
    }
}

static void check_cutlass(cutlass::Status rc, const char *what)
{
    if (rc != cutlass::Status::kSuccess) {
        std::fprintf(stderr, "%s: CUTLASS status %d; CUDA: %s\n",
                     what, (int)rc, cudaGetErrorString(cudaGetLastError()));
        std::exit(1);
    }
}

static int8_t a_value(uint32_t row, uint32_t k)
{
    return (int8_t)((int)((row * 13u + k * 7u + 3u) & 15u) - 8);
}

static int8_t b_value(uint32_t k, uint32_t col)
{
    return (int8_t)((int)((k * 5u + col * 11u + 1u) & 15u) - 8);
}

static void set_packed(std::vector<uint8_t> &data, size_t i, int8_t value)
{
    uint8_t nibble = (uint8_t)value & 0x0fu;
    if ((i & 1u) == 0)
        data[i / 2u] = (uint8_t)((data[i / 2u] & 0xf0u) | nibble);
    else
        data[i / 2u] = (uint8_t)((data[i / 2u] & 0x0fu) | (nibble << 4));
}

int main(int argc, char **argv)
{
    uint32_t m = argc > 1 ? (uint32_t)std::strtoul(argv[1], nullptr, 10)
                          : 32768u;
    uint32_t iterations =
        argc > 2 ? (uint32_t)std::strtoul(argv[2], nullptr, 10) : 100u;
    const uint32_t n = 1024u;
    const uint32_t kdim = 1024u;
    if (m == 0 || iterations == 0 || (m % 128u) != 0) {
        std::fprintf(stderr, "usage: %s [M multiple of 128] [iterations]\n",
                     argv[0]);
        return 2;
    }

    std::vector<uint8_t> h_a((size_t)m * kdim / 2u, 0);
    std::vector<uint8_t> h_b((size_t)kdim * n / 2u, 0);
    for (uint32_t row = 0; row < m; row++)
        for (uint32_t kk = 0; kk < kdim; kk++)
            set_packed(h_a, (size_t)row * kdim + kk, a_value(row, kk));
    for (uint32_t col = 0; col < n; col++)
        for (uint32_t kk = 0; kk < kdim; kk++)
            set_packed(h_b, (size_t)col * kdim + kk, b_value(kk, col));

    uint8_t *d_a = nullptr, *d_b = nullptr;
    int32_t *d_c = nullptr;
    check_cuda(cudaMalloc((void **)&d_a, h_a.size()), "cudaMalloc A");
    check_cuda(cudaMalloc((void **)&d_b, h_b.size()), "cudaMalloc B");
    check_cuda(cudaMalloc((void **)&d_c, (size_t)m * n * sizeof(int32_t)),
               "cudaMalloc C");
    check_cuda(cudaMemcpy(d_a, h_a.data(), h_a.size(), cudaMemcpyHostToDevice),
               "copy A");
    check_cuda(cudaMemcpy(d_b, h_b.data(), h_b.size(), cudaMemcpyHostToDevice),
               "copy B");

    typename Int4Gemm::Arguments args{
        cutlass::gemm::GemmCoord((int)m, (int)n, (int)kdim),
        {reinterpret_cast<Element *>(d_a), LayoutA((int)kdim)},
        {reinterpret_cast<Element *>(d_b), LayoutB((int)kdim)},
        {d_c, LayoutC((int)n)},
        {d_c, LayoutC((int)n)},
        {1, 0},
        1};

    size_t workspace_size = Int4Gemm::get_workspace_size(args);
    uint8_t *workspace = nullptr;
    if (workspace_size != 0)
        check_cuda(cudaMalloc((void **)&workspace, workspace_size),
                   "cudaMalloc workspace");

    Int4Gemm gemm;
    check_cutlass(gemm.can_implement(args), "can_implement");
    check_cutlass(gemm.initialize(args, workspace), "initialize");
    for (unsigned warmup = 0; warmup < 3u; warmup++)
        check_cutlass(gemm(), "warmup");
    check_cuda(cudaDeviceSynchronize(), "warmup synchronize");

    std::vector<int32_t> got((size_t)8u * n);
    check_cuda(cudaMemcpy(got.data(), d_c, got.size() * sizeof(int32_t),
                          cudaMemcpyDeviceToHost), "copy validation");
    for (uint32_t row = 0; row < 8u; row++) {
        for (uint32_t col = 0; col < n; col++) {
            int32_t expected = 0;
            for (uint32_t kk = 0; kk < kdim; kk++)
                expected += (int32_t)a_value(row, kk) *
                            (int32_t)b_value(kk, col);
            if (got[(size_t)row * n + col] != expected) {
                std::fprintf(stderr,
                             "mismatch row=%u col=%u got=%d expected=%d\n",
                             row, col, got[(size_t)row * n + col], expected);
                return 1;
            }
        }
    }
    std::printf("validation: 8 x 1024 outputs exact\n");

    cudaEvent_t start, end;
    check_cuda(cudaEventCreate(&start), "event start");
    check_cuda(cudaEventCreate(&end), "event end");
    check_cuda(cudaEventRecord(start), "record start");
    for (uint32_t iter = 0; iter < iterations; iter++)
        check_cutlass(gemm(), "timed GEMM");
    check_cuda(cudaEventRecord(end), "record end");
    check_cuda(cudaEventSynchronize(end), "sync end");
    float elapsed_ms = 0;
    check_cuda(cudaEventElapsedTime(&elapsed_ms, start, end), "elapsed");
    double attempts = (double)m * iterations;
    double macs = attempts * n * kdim;
    std::printf("shape: M=%u N=%u K=%u iterations=%u\n",
                m, n, kdim, iterations);
    std::printf("exact INT4 GEMM: %.6f us/attempt, %.3f TMAC/s\n",
                elapsed_ms * 1000.0 / attempts,
                macs / (elapsed_ms / 1000.0) / 1e12);

    cudaEventDestroy(start);
    cudaEventDestroy(end);
    cudaFree(workspace);
    cudaFree(d_a);
    cudaFree(d_b);
    cudaFree(d_c);
    return 0;
}
