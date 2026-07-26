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

all: $(BINS)

$(OBJ): src/photonhash.c include/photonhash.h
	$(CC) $(CPPFLAGS) $(CFLAGS) -c $< -o $@

ph_selftest: tests/ph_selftest.c $(OBJ)
	$(CC) $(CPPFLAGS) $(CFLAGS) $^ -o $@ $(LDFLAGS) $(LDLIBS)

ph_vectors: tests/ph_vectors.c $(OBJ)
	$(CC) $(CPPFLAGS) $(CFLAGS) $^ -o $@ $(LDFLAGS) $(LDLIBS)

ph_bench: tests/ph_bench.c $(OBJ)
	$(CC) $(CPPFLAGS) $(CFLAGS) $^ -o $@ $(LDFLAGS) $(LDLIBS)

ph_cuda_bench: tools/ph_cuda_bench.cu src/photonhash.c include/photonhash.h
	$(NVCC) $(CPPFLAGS) $(CUDA_CFLAGS) tools/ph_cuda_bench.cu src/photonhash.c -o $@ $(CUDA_LDLIBS)

test: ph_selftest
	./ph_selftest

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

clean:
	rm -f $(BINS) $(addsuffix .exe,$(BINS)) ph_cuda_bench ph_cuda_bench.exe $(OBJ) photonhash_test_vectors.generated.txt
	rm -rf $(addsuffix .dSYM,$(BINS))

.PHONY: all test vectors check-vectors bench cuda-bench v03-model-test v03-analysis-test v03-boundary-test v03-test sanitize clean
