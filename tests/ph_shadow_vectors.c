/* Compact multi-parent vectors for PhotonHash v0.4.0-shadow.1. */
#include "photonhash_shadow.h"

#include <inttypes.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static const char BANK_TEST_TAG[] =
    "PhotonHash/v0.4.0-shadow.1/test-bank";

static void print_hex(FILE *output, const uint8_t *value, size_t length)
{
    for (size_t index = 0; index < length; index++)
        fprintf(output, "%02x", value[index]);
    fputc('\n', output);
}

static void fill_parent(uint8_t parent[PH_DIGEST_LEN], unsigned index)
{
    if (index == 0u)
        memset(parent, 0, PH_DIGEST_LEN);
    else if (index == 1u)
        memset(parent, 0xff, PH_DIGEST_LEN);
    else if (index == 2u)
        for (size_t i = 0; i < PH_DIGEST_LEN; i++)
            parent[i] = (uint8_t)i;
    else
        ph_shake256(parent, PH_DIGEST_LEN,
                    "v0.4-shadow-parent-3", 20u);
}

static const char *fill_header(
    uint8_t header[4096], size_t *length, unsigned index)
{
    if (index == 0u) {
        *length = 0u;
        return "empty";
    }
    if (index == 1u) {
        header[0] = 0u;
        *length = 1u;
        return "zero";
    }
    if (index == 2u) {
        *length = 80u;
        for (size_t i = 0; i < *length; i++)
            header[i] = (uint8_t)i;
        return "incrementing";
    }
    *length = 4096u;
    for (size_t i = 0; i < *length; i++)
        header[i] = (uint8_t)(i * 131u + 17u);
    return "affine131+17";
}

static void bank_commitment(
    uint8_t output[PH_DIGEST_LEN],
    const uint8_t parent[PH_DIGEST_LEN],
    const ph_lf2_context_t *context)
{
    ph_shake256_t shake;
    ph_shake256_init(&shake);
    ph_shake256_absorb(
        &shake, BANK_TEST_TAG, sizeof BANK_TEST_TAG - 1u);
    ph_shake256_absorb(&shake, parent, PH_DIGEST_LEN);
    for (uint32_t pass = 0; pass < PH_LF2_PASSES; pass++) {
        ph_shake256_absorb(
            &shake, context->matrices[pass].seed, PH_SEED_LEN);
        ph_shake256_absorb(
            &shake, context->matrices[pass].checksum, PH_DIGEST_LEN);
    }
    ph_shake256_squeeze(&shake, output, PH_DIGEST_LEN);
}

static int emit(FILE *output)
{
    const uint64_t nonces[4] = {
        0u, UINT64_MAX, UINT64_C(0x0123456789abcdef), 1u
    };
    fprintf(output, "PhotonHash v0.4.0-shadow.1 compact vectors\n");
    fprintf(output, "status=non-consensus-shadownet-candidate\n");
    fprintf(output, "format=1\n");
    fprintf(output, "profile=LF2-K8\n");
    fprintf(output, "n=%u\n", PH_LF2_N);
    fprintf(output, "passes=%u\n", PH_LF2_PASSES);
    fprintf(output, "cases=4\n");

    ph_lf2_workspace_t workspace;
    if (ph_lf2_workspace_init(&workspace) != 0)
        return -1;
    for (unsigned index = 0; index < 4u; index++) {
        uint8_t parent[PH_DIGEST_LEN], header[4096];
        uint8_t bank[PH_DIGEST_LEN], h[PH_DIGEST_LEN];
        uint8_t fold_digest[PH_DIGEST_LEN], digest[PH_DIGEST_LEN];
        size_t header_len;
        fill_parent(parent, index);
        const char *header_kind =
            fill_header(header, &header_len, index);
        ph_lf2_context_t context;
        if (ph_lf2_context_init(&context, parent) != 0) {
            ph_lf2_workspace_free(&workspace);
            return -1;
        }
        bank_commitment(bank, parent, &context);
        if (ph_lf2_hash_with_workspace(
                digest, h, &context, &workspace,
                header_len ? header : NULL, header_len,
                nonces[index]) != 0) {
            ph_lf2_context_free(&context);
            ph_lf2_workspace_free(&workspace);
            return -1;
        }
        ph_shake256(
            fold_digest, PH_DIGEST_LEN,
            workspace.folded, PH_LF2_N / 2u);

        fprintf(output, "\ncase[%u].parent=", index);
        print_hex(output, parent, PH_DIGEST_LEN);
        fprintf(output, "case[%u].header=%s\n", index, header_kind);
        fprintf(output, "case[%u].header_len=%zu\n", index, header_len);
        fprintf(output, "case[%u].nonce=%" PRIu64 "\n",
                index, nonces[index]);
        fprintf(output, "case[%u].bank_commitment=", index);
        print_hex(output, bank, PH_DIGEST_LEN);
        fprintf(output, "case[%u].h_in=", index);
        print_hex(output, h, PH_DIGEST_LEN);
        fprintf(output, "case[%u].fold_digest=", index);
        print_hex(output, fold_digest, PH_DIGEST_LEN);
        fprintf(output, "case[%u].digest=", index);
        print_hex(output, digest, PH_DIGEST_LEN);
        ph_lf2_context_free(&context);
    }
    ph_lf2_workspace_free(&workspace);
    return ferror(output) ? -1 : 0;
}

static int files_equal(FILE *left, FILE *right)
{
    for (;;) {
        int a = fgetc(left), b = fgetc(right);
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
        if (!generated || !expected || emit(generated) != 0)
            return 1;
        rewind(generated);
        int equal = files_equal(generated, expected);
        fclose(expected);
        fclose(generated);
        if (!equal)
            fprintf(stderr, "shadow vectors differ from %s\n", argv[2]);
        else
            printf("shadow vectors match %s\n", argv[2]);
        return equal ? 0 : 1;
    }
    FILE *output = stdout;
    if (argc == 2) {
        output = fopen(argv[1], "wb");
        if (!output)
            return 1;
    } else if (argc != 1) {
        return 2;
    }
    int result = emit(output);
    if (output != stdout)
        fclose(output);
    return result == 0 ? 0 : 1;
}
