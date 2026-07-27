CC       ?= cc
NVCC     ?= nvcc
CPPFLAGS ?= -Iinclude
CFLAGS   ?= -O2 -std=c11 -Wall -Wextra -Wpedantic -Wshadow -Wconversion
CUDA_CFLAGS ?= -O3 -std=c++17
LDFLAGS  ?=
LDLIBS   ?=
CUDA_LDLIBS ?= -lcublas
PYTHON   ?= python3

OBJ = photonhash.o
BINS = ph_selftest ph_vectors ph_bench
SHADOW_BINS = ph_launch_selftest ph_launch_vectors ph_shadow_cache_test \
	ph_shadow_vectors ph_shadow_fuzz_smoke ph_lf2_shadow_soak

all: $(BINS)

$(OBJ): src/photonhash.c include/photonhash.h
	$(CC) $(CPPFLAGS) $(CFLAGS) -c $< -o $@

ph_selftest: tests/ph_selftest.c $(OBJ)
	$(CC) $(CPPFLAGS) $(CFLAGS) $^ -o $@ $(LDFLAGS) $(LDLIBS)

ph_vectors: tests/ph_vectors.c $(OBJ)
	$(CC) $(CPPFLAGS) $(CFLAGS) $^ -o $@ $(LDFLAGS) $(LDLIBS)

ph_bench: tests/ph_bench.c $(OBJ)
	$(CC) $(CPPFLAGS) $(CFLAGS) $^ -o $@ $(LDFLAGS) $(LDLIBS)

ph_launch_selftest: tests/ph_launch_selftest.c src/photonhash_launch.c \
		include/photonhash_launch.h $(OBJ)
	$(CC) $(CPPFLAGS) $(CFLAGS) tests/ph_launch_selftest.c \
		src/photonhash_launch.c $(OBJ) -o $@ $(LDFLAGS) $(LDLIBS)

ph_launch_vectors: tests/ph_launch_vectors.c src/photonhash_launch.c \
		include/photonhash_launch.h $(OBJ)
	$(CC) $(CPPFLAGS) $(CFLAGS) tests/ph_launch_vectors.c \
		src/photonhash_launch.c $(OBJ) -o $@ $(LDFLAGS) $(LDLIBS)

ph_lf2_shadow_soak: tools/ph_lf2_shadow_soak.c src/photonhash_launch.c \
		include/photonhash_launch.h $(OBJ)
	$(CC) $(CPPFLAGS) $(CFLAGS) tools/ph_lf2_shadow_soak.c \
		src/photonhash_launch.c $(OBJ) -o $@ $(LDFLAGS) $(LDLIBS)

ph_shadow_cache_test: tests/ph_shadow_cache_test.c src/photonhash_shadow.c \
		src/photonhash_launch.c include/photonhash_shadow.h \
		include/photonhash_launch.h $(OBJ)
	$(CC) $(CPPFLAGS) $(CFLAGS) tests/ph_shadow_cache_test.c \
		src/photonhash_shadow.c src/photonhash_launch.c $(OBJ) \
		-o $@ $(LDFLAGS) $(LDLIBS)

ph_shadow_vectors: tests/ph_shadow_vectors.c src/photonhash_shadow.c \
		src/photonhash_launch.c include/photonhash_shadow.h \
		include/photonhash_launch.h $(OBJ)
	$(CC) $(CPPFLAGS) $(CFLAGS) tests/ph_shadow_vectors.c \
		src/photonhash_shadow.c src/photonhash_launch.c $(OBJ) \
		-o $@ $(LDFLAGS) $(LDLIBS)

ph_shadow_fuzz_smoke: tests/ph_shadow_fuzz_smoke.c \
		src/photonhash_shadow.c src/photonhash_launch.c \
		include/photonhash_shadow.h include/photonhash_launch.h $(OBJ)
	$(CC) $(CPPFLAGS) $(CFLAGS) tests/ph_shadow_fuzz_smoke.c \
		src/photonhash_shadow.c src/photonhash_launch.c $(OBJ) \
		-o $@ $(LDFLAGS) $(LDLIBS)

ph_cuda_bench: tools/ph_cuda_bench.cu src/photonhash.c include/photonhash.h
	$(NVCC) $(CPPFLAGS) $(CUDA_CFLAGS) tools/ph_cuda_bench.cu src/photonhash.c -o $@ $(CUDA_LDLIBS)

test: ph_selftest
	./ph_selftest

launch-test: ph_launch_selftest
	./ph_launch_selftest

launch-vectors: ph_launch_vectors
	./ph_launch_vectors docs/launch-profile-lf2-vectors.txt

check-launch-vectors: ph_launch_vectors
	./ph_launch_vectors --check docs/launch-profile-lf2-vectors.txt

check-shadow-vectors: ph_shadow_vectors
	./ph_shadow_vectors --check docs/v0.4-shadow-vectors.txt

shadow-cache-test: ph_shadow_cache_test
	./ph_shadow_cache_test

shadow-fuzz-smoke: ph_shadow_fuzz_smoke
	./ph_shadow_fuzz_smoke

shadow-protocol-test:
	$(PYTHON) -m unittest tests.test_shadow_protocol -v

shadow-rust-test:
	cargo test --release --locked --manifest-path independent/rust-lf2/Cargo.toml

ph_shadow_fuzzer: tests/ph_shadow_fuzz_target.c src/photonhash_shadow.c \
		src/photonhash_launch.c include/photonhash_shadow.h \
		include/photonhash_launch.h src/photonhash.c include/photonhash.h
	$(CC) $(CPPFLAGS) -O1 -g -std=c11 -Wall -Wextra -Wpedantic \
		-Wshadow -Wconversion -Werror \
		-fsanitize=fuzzer,address,undefined -fno-omit-frame-pointer \
		tests/ph_shadow_fuzz_target.c src/photonhash_shadow.c \
		src/photonhash_launch.c src/photonhash.c -o $@

shadow-test: launch-test check-launch-vectors check-shadow-vectors \
		shadow-cache-test shadow-fuzz-smoke shadow-protocol-test

shadow-ci: all test check-vectors shadow-test shadow-rust-test

vectors: ph_vectors
	./ph_vectors photonhash_test_vectors.generated.txt

check-vectors: ph_vectors
	./ph_vectors --check docs/test-vectors.txt

bench: ph_bench
	./ph_bench

cuda-bench: ph_cuda_bench
	./ph_cuda_bench

v03-model-test:
	$(PYTHON) -m unittest tests.test_v03_model -v

v03-analysis-test:
	$(PYTHON) -m unittest tests.test_v03_recurrence -v

v03-boundary-test:
	$(PYTHON) -m unittest tests.test_v03_boundary_sim -v

v03-test: v03-model-test v03-analysis-test v03-boundary-test

sanitize: CFLAGS := -O1 -g -std=c11 -Wall -Wextra -Wpedantic -Wshadow -Wconversion -Werror -fsanitize=address,undefined -fno-omit-frame-pointer
sanitize: LDFLAGS := -fsanitize=address,undefined
sanitize: clean all test check-vectors

sanitize-shadow: CFLAGS := -O1 -g -std=c11 -Wall -Wextra -Wpedantic -Wshadow -Wconversion -Werror -fsanitize=address,undefined -fno-omit-frame-pointer
sanitize-shadow: LDFLAGS := -fsanitize=address,undefined
sanitize-shadow: clean ph_launch_selftest ph_launch_vectors \
		ph_shadow_cache_test ph_shadow_vectors ph_shadow_fuzz_smoke
	./ph_launch_selftest
	./ph_launch_vectors --check docs/launch-profile-lf2-vectors.txt
	./ph_shadow_cache_test
	./ph_shadow_vectors --check docs/v0.4-shadow-vectors.txt
	./ph_shadow_fuzz_smoke

clean:
	rm -f $(BINS) $(addsuffix .exe,$(BINS)) $(SHADOW_BINS) \
		$(addsuffix .exe,$(SHADOW_BINS)) ph_cuda_bench ph_cuda_bench.exe \
		ph_shadow_fuzzer ph_shadow_fuzzer.exe \
		$(OBJ) photonhash_test_vectors.generated.txt
	rm -rf $(addsuffix .dSYM,$(BINS))

.PHONY: all test launch-test launch-vectors check-launch-vectors \
	check-shadow-vectors shadow-cache-test shadow-fuzz-smoke \
	shadow-protocol-test shadow-rust-test shadow-test shadow-ci \
	ph_shadow_fuzzer \
	vectors check-vectors bench cuda-bench v03-model-test \
	v03-analysis-test v03-boundary-test v03-test sanitize \
	sanitize-shadow clean
