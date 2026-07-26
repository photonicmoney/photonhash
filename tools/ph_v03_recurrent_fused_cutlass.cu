/*
 * Fused electronic adversary for PhotonHash v0.3 candidate R1.
 *
 * CUTLASS writes the exact low-bit nonlinear next state directly from the
 * INT32 accumulator, avoiding materialized products and a separate boundary
 * kernel. This is research tooling, not consensus code or a miner.
 */

#include "photonhash.h"

#include <cuda_runtime.h>

#include "cutlass/cutlass.h"
#include "cutlass/gemm/device/gemm.h"
#include "cutlass/epilogue/thread/linear_combination_generic.h"

#include <algorithm>
#include <atomic>
#include <chrono>
#include <cinttypes>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <thread>
#include <vector>

#ifdef _WIN32
#include <windows.h>
#endif

static void check_cuda(cudaError_t status, const char *operation)
{
    if (status != cudaSuccess) {
        std::fprintf(stderr, "%s: %s\n", operation, cudaGetErrorString(status));
        std::exit(2);
    }
}

static void check_cutlass(cutlass::Status status, const char *operation)
{
    if (status != cutlass::Status::kSuccess) {
        std::fprintf(stderr, "%s: CUTLASS status %d; CUDA: %s\n",
                     operation, (int)status,
                     cudaGetErrorString(cudaGetLastError()));
        std::exit(2);
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
                counter_energy_j_ =
                    (double)(end_mj - energy_start_mj_) / 1000.0;
            else
                direct_energy_ = false;
        }
        if (samples_ != 0) {
            average_w_ = power_sum_mw_ / (double)samples_ / 1000.0;
            integrated_energy_j_ = average_w_ * wall_seconds;
        }
        if (initialized_)
            shutdown_();
        initialized_ = false;
        FreeLibrary(lib_);
        lib_ = nullptr;
#else
        (void)wall_seconds;
#endif
    }

    bool available() const { return samples_ != 0; }
    bool direct_energy() const { return direct_energy_; }
    double average_w() const { return average_w_; }
    double integrated_energy_j() const { return integrated_energy_j_; }
    double counter_energy_j() const { return counter_energy_j_; }
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
    double integrated_energy_j_ = 0.0;
    double counter_energy_j_ = 0.0;
};

static unsigned log2_exact(uint32_t n)
{
    unsigned result = 0;
    while ((1u << result) < n)
        result++;
    return result;
}

template <typename Fragment>
struct WrapQuantize {
    struct Arguments {
        int32_t offset;
        int32_t shift;

        CUTLASS_HOST_DEVICE
        Arguments(int32_t offset_ = 0, int32_t shift_ = 0)
            : offset(offset_), shift(shift_) {}
    };

    template <typename Params>
    CUTLASS_HOST_DEVICE
    Fragment operator()(Fragment const &input, Params const &args) const
    {
        Fragment output;
        CUTLASS_PRAGMA_UNROLL
        for (int i = 0; i < Fragment::kElements; i++) {
            uint32_t bucket =
                (((uint32_t)(input[i] + args.offset)) >> args.shift) & 15u;
            output[i] = (int32_t)bucket - 8;
        }
        return output;
    }
};

using Element = int8_t;
using Accumulator = int32_t;
using LayoutA = cutlass::layout::RowMajor;
using LayoutB = cutlass::layout::ColumnMajor;
using LayoutOutput = cutlass::layout::ColumnMajor;

using OutputOp = cutlass::epilogue::thread::LinearCombinationGeneric<
    WrapQuantize,
    Element,
    16,
    Accumulator,
    Accumulator,
    cutlass::epilogue::thread::ScaleType::OnlyAlphaScaling>;

using FusedGemm = cutlass::gemm::device::Gemm<
    Element, LayoutA,
    Element, LayoutB,
    Element, LayoutOutput,
    Accumulator,
    cutlass::arch::OpClassTensorOp,
    cutlass::arch::Sm80,
    cutlass::gemm::GemmShape<128, 256, 128>,
    cutlass::gemm::GemmShape<64, 64, 128>,
    cutlass::gemm::GemmShape<16, 8, 32>,
    OutputOp,
    cutlass::gemm::threadblock::GemmIdentityThreadblockSwizzle<>,
    2>;

static typename OutputOp::Params output_params(uint32_t n)
{
    unsigned shift = 8u + (log2_exact(n) - 9u) / 2u;
    int32_t offset = 64 * (int32_t)n;
    typename OutputOp::Params params(1, 0);
    params.offset = offset;
    params.shift = (int32_t)shift;
    return params;
}

static typename FusedGemm::Arguments make_arguments(
    uint32_t n, uint32_t batch, const int8_t *matrix,
    const int8_t *input, int8_t *output)
{
    return typename FusedGemm::Arguments{
        cutlass::gemm::GemmCoord((int)n, (int)batch, (int)n),
        {matrix, LayoutA((int)n)},
        {input, LayoutB((int)n)},
        {output, LayoutOutput((int)n)},
        {output, LayoutOutput((int)n)},
        output_params(n),
        1};
}

static int8_t boundary_value(int32_t value, unsigned shift, int32_t offset)
{
    uint32_t bucket =
        (((uint32_t)(value + offset)) >> shift) & 15u;
    return (int8_t)((int)bucket - 8);
}

static bool validate(const std::vector<ph_matrix_t> &matrices,
                     const std::vector<int8_t> &initial,
                     const int8_t *device_state,
                     uint32_t rounds)
{
    uint32_t n = matrices[0].n;
    std::vector<int8_t> reference(initial.begin(), initial.begin() + n);
    std::vector<int8_t> observed(n);
    std::vector<int32_t> product(n);
    unsigned shift = 8u + (log2_exact(n) - 9u) / 2u;
    int32_t offset = 64 * (int32_t)n;
    for (uint32_t round = 0; round < rounds; round++) {
        const ph_matrix_t &matrix =
            matrices[round % (uint32_t)matrices.size()];
        for (uint32_t row = 0; row < n; row++) {
            int32_t sum = 0;
            const int8_t *m = matrix.m + (size_t)row * n;
            for (uint32_t column = 0; column < n; column++)
                sum += (int32_t)m[column] * reference[column];
            product[row] = sum;
        }
        for (uint32_t i = 0; i < n; i++)
            reference[i] = boundary_value(product[i], shift, offset);
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
    uint8_t digest[PH_DIGEST_LEN];
    ph_shake256(digest, sizeof digest, observed.data(), observed.size());
    std::printf("validation:          PASS (rounds=%u, state_shake256=", rounds);
    for (unsigned i = 0; i < sizeof digest; i++)
        std::printf("%02x", digest[i]);
    std::printf(")\n");
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
    double energy_seconds = argc > 5 ? std::strtod(argv[5], nullptr) : 2.0;
    const char *matrix_mode = argc > 6 ? argv[6] : "same";
    bool distinct_matrices = std::strcmp(matrix_mode, "distinct") == 0;
    if (n < 1024u || n > 16384u || (n & (n - 1u)) != 0 ||
        (n % 128u) != 0 || batch == 0 || (batch % 256u) != 0 ||
        rounds == 0 || rounds > 1024u || repeats == 0 ||
        energy_seconds < 0.0 || energy_seconds > 30.0 ||
        (!distinct_matrices && std::strcmp(matrix_mode, "same") != 0)) {
        std::fprintf(stderr,
            "usage: %s [power-of-two n 1024..16384] "
            "[batch multiple of 256] [rounds 1..1024] [repeats] "
            "[energy seconds 0..30] [same|distinct]\n",
            argv[0]);
        return 1;
    }

    uint8_t parent[PH_DIGEST_LEN];
    char label[80];
    std::snprintf(label, sizeof label, "PhotonHash/v0.3/%s-fused/n=%u",
                  distinct_matrices ? "F1" : "R1", n);
    ph_shake256(parent, sizeof parent, label, std::strlen(label));
    uint32_t matrix_count = distinct_matrices ? rounds : 1u;
    std::vector<ph_matrix_t> matrices(matrix_count);
    for (uint32_t index = 0; index < matrix_count; index++) {
        uint8_t round_parent[PH_DIGEST_LEN];
        if (index == 0) {
            std::memcpy(round_parent, parent, sizeof round_parent);
        } else {
            uint8_t input[PH_DIGEST_LEN + 4];
            std::memcpy(input, parent, PH_DIGEST_LEN);
            for (unsigned byte = 0; byte < 4; byte++)
                input[PH_DIGEST_LEN + byte] =
                    (uint8_t)(index >> (8u * byte));
            ph_shake256(round_parent, sizeof round_parent,
                        input, sizeof input);
        }
        if (ph_matrix_derive(&matrices[index], n, round_parent) != 0) {
            std::fprintf(stderr,
                         "matrix derivation failed for n=%u round=%u\n",
                         n, index);
            return 1;
        }
    }

    size_t matrix_bytes = (size_t)n * n;
    if (matrix_count > SIZE_MAX / matrix_bytes) {
        std::fprintf(stderr, "matrix bank size overflow\n");
        return 1;
    }
    size_t matrix_bank_bytes = matrix_bytes * matrix_count;
    size_t state_bytes = (size_t)n * batch;
    std::vector<int8_t> initial(state_bytes);
    for (size_t i = 0; i < state_bytes; i++) {
        uint32_t value = (uint32_t)i * 0x9e3779b9u + 0x243f6a88u;
        value ^= value >> 16;
        initial[i] = (int8_t)((int)((value >> 28) & 15u) - 8);
    }

    int8_t *d_matrix = nullptr;
    int8_t *d_state_a = nullptr;
    int8_t *d_state_b = nullptr;
    check_cuda(cudaMalloc((void **)&d_matrix, matrix_bank_bytes),
               "cudaMalloc matrix bank");
    check_cuda(cudaMalloc((void **)&d_state_a, state_bytes),
               "cudaMalloc state A");
    check_cuda(cudaMalloc((void **)&d_state_b, state_bytes),
               "cudaMalloc state B");
    for (uint32_t index = 0; index < matrix_count; index++)
        check_cuda(cudaMemcpy(d_matrix + (size_t)index * matrix_bytes,
                              matrices[index].m, matrix_bytes,
                              cudaMemcpyHostToDevice), "upload matrix");
    check_cuda(cudaMemcpy(d_state_a, initial.data(), state_bytes,
                          cudaMemcpyHostToDevice), "upload state A");

    auto args_ab =
        make_arguments(n, batch, d_matrix, d_state_a, d_state_b);
    auto args_ba =
        make_arguments(n, batch, d_matrix, d_state_b, d_state_a);
    size_t workspace_size = std::max(
        FusedGemm::get_workspace_size(args_ab),
        FusedGemm::get_workspace_size(args_ba));
    uint8_t *workspace_ab = nullptr;
    uint8_t *workspace_ba = nullptr;
    if (workspace_size != 0) {
        check_cuda(cudaMalloc((void **)&workspace_ab, workspace_size),
                   "cudaMalloc workspace AB");
        check_cuda(cudaMalloc((void **)&workspace_ba, workspace_size),
                   "cudaMalloc workspace BA");
    }
    FusedGemm gemm_ab;
    FusedGemm gemm_ba;
    check_cutlass(gemm_ab.can_implement(args_ab), "can_implement AB");
    check_cutlass(gemm_ba.can_implement(args_ba), "can_implement BA");
    check_cutlass(gemm_ab.initialize(args_ab, workspace_ab), "initialize AB");
    check_cutlass(gemm_ba.initialize(args_ba, workspace_ba), "initialize BA");
    auto run_round = [&](uint32_t round, const char *operation) {
        size_t matrix_offset =
            (size_t)(distinct_matrices ? round : 0u) * matrix_bytes;
        if (round & 1u) {
            if (distinct_matrices) {
                auto args = make_arguments(
                    n, batch, d_matrix + matrix_offset,
                    d_state_b, d_state_a);
                check_cutlass(gemm_ba.update(args, workspace_ba),
                              "update BA");
            }
            check_cutlass(gemm_ba(), operation);
        } else {
            if (distinct_matrices) {
                auto args = make_arguments(
                    n, batch, d_matrix + matrix_offset,
                    d_state_a, d_state_b);
                check_cutlass(gemm_ab.update(args, workspace_ab),
                              "update AB");
            }
            check_cutlass(gemm_ab(), operation);
        }
    };

    for (unsigned warmup = 0; warmup < 2; warmup++) {
        for (uint32_t round = 0; round < std::min(rounds, 4u); round++)
            run_round(round, "warmup fused GEMM");
    }
    check_cuda(cudaDeviceSynchronize(), "warmup synchronize");

    check_cuda(cudaMemcpy(d_state_a, initial.data(), state_bytes,
                          cudaMemcpyHostToDevice), "reset validation state");
    for (uint32_t round = 0; round < rounds; round++)
        run_round(round, "validation fused GEMM");
    check_cuda(cudaDeviceSynchronize(), "validation synchronize");
    const int8_t *final_state = (rounds & 1u) ? d_state_b : d_state_a;
    if (!validate(matrices, initial, final_state, rounds))
        return 3;

    cudaEvent_t begin, end;
    check_cuda(cudaEventCreate(&begin), "cudaEventCreate begin");
    check_cuda(cudaEventCreate(&end), "cudaEventCreate end");
    double elapsed_ms = 0.0;
    for (uint32_t repeat = 0; repeat < repeats; repeat++) {
        check_cuda(cudaMemcpy(d_state_a, initial.data(), state_bytes,
                              cudaMemcpyHostToDevice), "reset timed state");
        check_cuda(cudaEventRecord(begin), "record begin");
        for (uint32_t round = 0; round < rounds; round++)
            run_round(round, "timed fused GEMM");
        check_cuda(cudaEventRecord(end), "record end");
        check_cuda(cudaEventSynchronize(end), "synchronize end");
        float milliseconds = 0.0f;
        check_cuda(cudaEventElapsedTime(&milliseconds, begin, end),
                   "cudaEventElapsedTime");
        elapsed_ms += milliseconds;
    }
    elapsed_ms /= repeats;
    double fused_us_attempt = elapsed_ms * 1000.0 / batch;
    double fixed_v02_us_attempt = 0.020556 + 0.008304;
    double projected_share =
        fused_us_attempt / (fused_us_attempt + fixed_v02_us_attempt);

    uint32_t energy_loops = 0;
    double energy_wall_seconds = 0.0;
    PowerSampler power;
    if (energy_seconds > 0.0 && elapsed_ms > 0.0) {
        energy_loops = (uint32_t)std::max(
            1.0, std::min(100000.0,
                std::ceil(energy_seconds / (elapsed_ms / 1000.0))));
        bool power_started = power.begin();
        auto energy_start = std::chrono::steady_clock::now();
        for (uint32_t loop = 0; loop < energy_loops; loop++) {
            for (uint32_t round = 0; round < rounds; round++)
                run_round(round, "energy fused GEMM");
        }
        check_cuda(cudaDeviceSynchronize(), "energy synchronize");
        energy_wall_seconds = std::chrono::duration<double>(
            std::chrono::steady_clock::now() - energy_start).count();
        if (power_started)
            power.end(energy_wall_seconds);
    }
    double energy_attempts = (double)batch * energy_loops;
    double integrated_uj_attempt =
        power.available() && energy_attempts > 0.0
            ? power.integrated_energy_j() * 1e6 / energy_attempts : 0.0;
    double counter_uj_attempt =
        power.direct_energy() && energy_attempts > 0.0
            ? power.counter_energy_j() * 1e6 / energy_attempts : 0.0;

    cudaDeviceProp properties = {};
    check_cuda(cudaGetDeviceProperties(&properties, 0),
               "cudaGetDeviceProperties");
    std::printf("device:              %s, cc %d.%d\n",
                properties.name, properties.major, properties.minor);
    std::printf("candidate:           %s fused low-bit sequence\n",
                distinct_matrices ? "F1-D distinct-matrix" : "R1-F recurrent");
    std::printf("profile:             n=%u batch=%u rounds=%u repeats=%u mode=%s\n",
                n, batch, rounds, repeats, matrix_mode);
    std::printf("resident matrices:   %u, %.3f MiB\n",
                matrix_count, matrix_bank_bytes / (1024.0 * 1024.0));
    std::printf("working set:         %.3f MiB (two low-bit states)\n",
                2.0 * state_bytes / (1024.0 * 1024.0));
    std::printf("fused recurrence:    %.6f us/attempt\n", fused_us_attempt);
    std::printf("core throughput:     %.3f M attempts/s\n",
                1.0 / fused_us_attempt);
    std::printf("projected share:     %.3f%% (fused core / core+v0.2 proxy)\n",
                100.0 * projected_share);
    if (power.available()) {
        std::printf("sustained energy:    %.3f s, %u loops, %.1f W, "
                    "%.3f uJ/attempt (%" PRIu64 " samples)\n",
                    energy_wall_seconds, energy_loops, power.average_w(),
                    integrated_uj_attempt, power.samples());
        if (power.direct_energy())
            std::printf("NVML counter:        %.3f uJ/attempt\n",
                        counter_uj_attempt);
    } else {
        std::printf("sustained energy:    unavailable or disabled\n");
    }
    std::printf(
        "RESULT_JSON {\"matrix_mode\":\"%s\",\"matrix_count\":%u,"
        "\"matrix_bank_mib\":%.6f,\"n\":%u,\"batch\":%u,\"rounds\":%u,"
        "\"repeats\":%u,\"fused_us_attempt\":%.9f,"
        "\"projected_accelerable_share\":%.9f,"
        "\"energy_loops\":%u,\"energy_wall_seconds\":%.9f,"
        "\"average_board_w\":%.6f,"
        "\"integrated_uj_attempt\":%.9f,"
        "\"counter_uj_attempt\":%.9f}\n",
        matrix_mode, matrix_count,
        matrix_bank_bytes / (1024.0 * 1024.0),
        n, batch, rounds, repeats, fused_us_attempt, projected_share,
        energy_loops, energy_wall_seconds,
        power.available() ? power.average_w() : 0.0,
        integrated_uj_attempt, counter_uj_attempt);
    std::printf(
        "warning: electronic timing probe only; excludes a physical feedback "
        "loop and does not establish photonic advantage or consensus parameters\n");

    cudaEventDestroy(begin);
    cudaEventDestroy(end);
    cudaFree(workspace_ab);
    cudaFree(workspace_ba);
    cudaFree(d_matrix);
    cudaFree(d_state_a);
    cudaFree(d_state_b);
    for (ph_matrix_t &matrix : matrices)
        ph_matrix_free(&matrix);
    return 0;
}
