CC       ?= cc
CPPFLAGS ?= -Iinclude
CFLAGS   ?= -O2 -std=c11 -Wall -Wextra -Wpedantic -Wshadow -Wconversion
LDFLAGS  ?=
LDLIBS   ?=

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

test: ph_selftest
	./ph_selftest

vectors: ph_vectors
	./ph_vectors photonhash_test_vectors.generated.txt

check-vectors: ph_vectors
	./ph_vectors --check docs/test-vectors.txt

bench: ph_bench
	./ph_bench

sanitize: CFLAGS := -O1 -g -std=c11 -Wall -Wextra -Wpedantic -Wshadow -Wconversion -Werror -fsanitize=address,undefined -fno-omit-frame-pointer
sanitize: LDFLAGS := -fsanitize=address,undefined
sanitize: clean test check-vectors

clean:
	rm -f $(BINS) $(addsuffix .exe,$(BINS)) $(OBJ) photonhash_test_vectors.generated.txt
	rm -rf $(addsuffix .dSYM,$(BINS))

.PHONY: all test vectors check-vectors bench sanitize clean
