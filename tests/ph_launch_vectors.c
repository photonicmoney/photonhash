/* Deterministic LF2-K8 research-vector generator and checker. */

#include "photonhash_launch.h"

#include <inttypes.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static void print_hex(FILE *output, const uint8_t *value, size_t length)
{
    for (size_t i = 0; i < length; i++)
        fprintf(output, "%02x", value[i]);
    fputc('\n', output);
}

static int emit_vectors(FILE *output)
{
    uint8_t parent[PH_DIGEST_LEN], header[80];
    ph_shake256(parent, sizeof parent, "lf2-verify-parent", 17u);
    ph_shake256(header, sizeof header, "lf2-verify-header", 17u);

    ph_lf2_context_t context;
    ph_lf2_workspace_t workspace;
    if (ph_lf2_context_init(&context, parent) != 0 ||
        ph_lf2_workspace_init(&workspace) != 0)
        return -1;

    fprintf(output, "PhotonHash LF2-K8 research vectors\n");
    fprintf(output, "status=non-consensus\n");
    fprintf(output, "format=1\n");
    fprintf(output, "n=%u\n", PH_LF2_N);
    fprintf(output, "passes=%u\n", PH_LF2_PASSES);
    fprintf(output, "parent=");
    print_hex(output, parent, sizeof parent);
    fprintf(output, "header80=");
    print_hex(output, header, sizeof header);
    for (uint32_t pass = 0; pass < PH_LF2_PASSES; pass++) {
        fprintf(output, "matrix[%u].seed=", pass);
        print_hex(output, context.matrices[pass].seed, PH_SEED_LEN);
        fprintf(output, "matrix[%u].checksum=", pass);
        print_hex(output, context.matrices[pass].checksum, PH_DIGEST_LEN);
    }

    const uint64_t nonces[] = {0u, 4u, 0u, UINT64_MAX};
    const int empty_header[] = {0, 0, 1, 1};
    for (size_t case_index = 0;
         case_index < sizeof nonces / sizeof nonces[0];
         case_index++) {
        uint8_t digest[PH_DIGEST_LEN], h_in[PH_DIGEST_LEN];
        const uint8_t *case_header = empty_header[case_index] ? NULL : header;
        size_t case_header_len = empty_header[case_index] ? 0u : sizeof header;
        if (ph_lf2_hash_with_workspace(
                digest, h_in, &context, &workspace,
                case_header, case_header_len, nonces[case_index]) != 0)
            return -1;
        fprintf(output, "\ncase[%zu].header=%s\n", case_index,
                empty_header[case_index] ? "empty" : "header80");
        fprintf(output, "case[%zu].nonce=%" PRIu64 "\n",
                case_index, nonces[case_index]);
        fprintf(output, "case[%zu].h_in=", case_index);
        print_hex(output, h_in, sizeof h_in);
        fprintf(output, "case[%zu].folded=", case_index);
        print_hex(output, workspace.folded, PH_LF2_N / 2u);
        fprintf(output, "case[%zu].digest=", case_index);
        print_hex(output, digest, sizeof digest);
    }

    ph_lf2_workspace_free(&workspace);
    ph_lf2_context_free(&context);
    return ferror(output) ? -1 : 0;
}

static int files_equal(FILE *left, FILE *right)
{
    for (;;) {
        int a = fgetc(left);
        int b = fgetc(right);
        if (a != b)
            return 0;
        if (a == EOF)
            return 1;
    }
}

int main(int argc, char **argv)
{
    if (argc == 3 && strcmp(argv[1], "--check") == 0) {
        FILE *generated = tmpfile();
        FILE *expected = fopen(argv[2], "rb");
        if (!generated || !expected || emit_vectors(generated) != 0) {
            fprintf(stderr, "unable to generate or open LF2 vectors\n");
            return 1;
        }
        rewind(generated);
        int equal = files_equal(generated, expected);
        fclose(expected);
        fclose(generated);
        if (!equal) {
            fprintf(stderr, "generated LF2 vectors differ from %s\n", argv[2]);
            return 1;
        }
        printf("generated LF2 vectors match %s\n", argv[2]);
        return 0;
    }

    FILE *output = stdout;
    if (argc == 2) {
        output = fopen(argv[1], "wb");
        if (!output) {
            fprintf(stderr, "unable to open %s\n", argv[1]);
            return 1;
        }
    } else if (argc != 1) {
        fprintf(stderr, "usage: %s [output] | --check expected\n", argv[0]);
        return 2;
    }
    int result = emit_vectors(output);
    if (output != stdout)
        fclose(output);
    return result == 0 ? 0 : 1;
}
