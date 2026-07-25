/*
 * ph_vectors.c — deterministic test-vector generator for Appendix A of the
 * PhotonHash technical specification.
 *
 * Emits five end-to-end vectors at n = 1024. All inputs are themselves
 * derived from fixed ASCII labels via SHAKE256, so the entire appendix is
 * reproducible from this source file alone.
 *
 * Author: Lightman. License: MIT.
 */

#include "photonhash.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static void print_hex(FILE *f, const char *label, const uint8_t *b, size_t n)
{
    fprintf(f, "%-14s", label);
    for (size_t i = 0; i < n; i++)
        fprintf(f, "%02x", b[i]);
    fprintf(f, "\n");
}

static int stream_matches_file(FILE *generated, const char *path)
{
    FILE *golden = fopen(path, "rb");
    if (!golden) {
        perror(path);
        return 0;
    }
    rewind(generated);
    int equal = 1;
    for (;;) {
        int a = fgetc(generated);
        int b = fgetc(golden);
        if (a != b) { equal = 0; break; }
        if (a == EOF) break;
    }
    if (ferror(generated) || ferror(golden))
        equal = 0;
    fclose(golden);
    return equal;
}

int main(int argc, char **argv)
{
    const uint32_t n = PH_GENESIS_N;
    FILE *f = stdout;
    const char *check_path = NULL;
    if (argc == 3 && strcmp(argv[1], "--check") == 0) {
        check_path = argv[2];
        f = tmpfile();
        if (!f) { perror("tmpfile"); return 1; }
    } else if (argc == 2) {
        f = fopen(argv[1], "w");
        if (!f) { perror("fopen"); return 1; }
    } else if (argc > 1) {
        fprintf(stderr, "usage: %s [output-file | --check golden-file]\n", argv[0]);
        return 2;
    }

    fprintf(f, "PhotonHash test vectors — Appendix A (draft)\n");
    fprintf(f, "generator: %s\n", ph_version());
    fprintf(f, "parameters: n = %u, entries 4-bit signed [-8,7], "
               "shift = 8 (spec v0.2 era 0), header = 80 bytes, "
               "nonce = 8-byte LE\n", n);
    fprintf(f, "domain tags: LASER/PhotonHash/v1/{matrix,vector,final}\n");
    fprintf(f, "convention: nibble k = byte[k>>1], even k low nibble, "
               "odd k high nibble\n\n");

    static const uint64_t nonces[5] = {
        0x0000000000000000ULL,
        0x0000000000000001ULL,
        0x00000000DEADBEEFULL,
        0x0123456789ABCDEFULL,
        0xFFFFFFFFFFFFFFFFULL
    };

    int8_t  *x = malloc(n);
    int32_t *y = malloc(n * sizeof(int32_t));
    uint8_t *r = malloc(n / 2);
    if (!x || !y || !r) {
        fprintf(stderr, "allocation failed\n");
        free(x); free(y); free(r);
        if (f != stdout) fclose(f);
        return 1;
    }

    for (int v = 0; v < 5; v++) {
        char label[64];

        /* parent hash and header are derived from fixed labels */
        uint8_t parent[PH_DIGEST_LEN];
        snprintf(label, sizeof label, "LASER/PhotonHash/testvec/parent/%d", v);
        ph_shake256(parent, sizeof parent, label, strlen(label));

        uint8_t header[80];
        snprintf(label, sizeof label, "LASER/PhotonHash/testvec/header/%d", v);
        ph_shake256(header, sizeof header, label, strlen(label));

        ph_matrix_t M;
        if (ph_matrix_derive(&M, n, parent) != 0) {
            fprintf(stderr, "matrix derivation failed\n");
            free(x); free(y); free(r);
            if (f != stdout) fclose(f);
            return 1;
        }

        uint8_t d[PH_DIGEST_LEN], h_in[PH_DIGEST_LEN];
        if (ph_hash_trace(d, h_in, x, y, r, &M, header, sizeof header,
                          nonces[v]) != 0) {
            fprintf(stderr, "hash evaluation failed\n");
            ph_matrix_free(&M);
            free(x); free(y); free(r);
            if (f != stdout) fclose(f);
            return 1;
        }

        /* digests over full x / y / r for compact verification */
        uint8_t xsum[32], ysum[32], rsum[32];
        ph_shake256(xsum, 32, x, n);
        uint8_t *yle = malloc((size_t)n * 4); /* y serialized LE for hashing */
        if (!yle) {
            fprintf(stderr, "allocation failed\n");
            ph_matrix_free(&M);
            free(x); free(y); free(r);
            if (f != stdout) fclose(f);
            return 1;
        }
        for (uint32_t i = 0; i < n; i++)
            for (uint32_t k = 0; k < 4; k++)
                yle[4 * i + k] = (uint8_t)((uint32_t)y[i] >> (8 * k));
        ph_shake256(ysum, 32, yle, (size_t)n * 4);
        free(yle);
        ph_shake256(rsum, 32, r, n / 2);

        int32_t ymin = y[0], ymax = y[0];
        for (uint32_t i = 1; i < n; i++) {
            if (y[i] < ymin) ymin = y[i];
            if (y[i] > ymax) ymax = y[i];
        }

        fprintf(f, "vector %d\n", v);
        fprintf(f, "  nonce         %016llx\n",
                (unsigned long long)nonces[v]);
        print_hex(f, "  parent", parent, PH_DIGEST_LEN);
        print_hex(f, "  header[0:16]", header, 16);
        print_hex(f, "  seed_M[0:16]", M.seed, 16);
        print_hex(f, "  M.checksum", M.checksum, PH_DIGEST_LEN);
        print_hex(f, "  h_in", h_in, PH_DIGEST_LEN);
        fprintf(f, "  x[0:8]        ");
        for (int i = 0; i < 8; i++) fprintf(f, "%s%d", i == 0 ? "" : " ", x[i]);
        fprintf(f, "\n");
        print_hex(f, "  shake256(x)", xsum, 32);
        fprintf(f, "  y[0:8]        ");
        for (int i = 0; i < 8; i++) fprintf(f, "%s%d", i == 0 ? "" : " ", y[i]);
        fprintf(f, "\n");
        fprintf(f, "  y range       [%d, %d]\n", ymin, ymax);
        print_hex(f, "  shake256(y)", ysum, 32);
        print_hex(f, "  r[0:16]", r, 16);
        print_hex(f, "  shake256(r)", rsum, 32);
        print_hex(f, "  d", d, PH_DIGEST_LEN);
        if (v != 4)
            fprintf(f, "\n");

        ph_matrix_free(&M);
    }

    free(x); free(y); free(r);
    int rc = 0;
    if (check_path) {
        if (fflush(f) != 0 || !stream_matches_file(f, check_path)) {
            fprintf(stderr, "generated vectors differ from %s\n", check_path);
            rc = 1;
        } else {
            printf("generated vectors match %s\n", check_path);
        }
    }
    if (f != stdout)
        fclose(f);
    return rc;
}
