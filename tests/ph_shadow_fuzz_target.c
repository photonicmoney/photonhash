/*
 * LLVM libFuzzer entry point for the frozen LF2-K8 attempt surface.
 *
 * Build only for fuzzing; the matrix bank is fixed so fuzz iterations exercise
 * arbitrary header bytes, nonce serialization, target comparison, and the
 * complete exact attempt pipeline without paying cold setup every iteration.
 */
#include "photonhash_shadow.h"

#include <stddef.h>
#include <stdint.h>
#include <string.h>

int LLVMFuzzerTestOneInput(const uint8_t *data, size_t size)
{
    static ph_lf2_context_t context;
    static ph_lf2_workspace_t workspace;
    static int ready;
    if (!ready) {
        uint8_t parent[PH_DIGEST_LEN];
        ph_shake256(parent, sizeof parent,
                    "v0.4-shadow-libfuzzer", 22u);
        if (ph_lf2_context_init(&context, parent) != 0 ||
            ph_lf2_workspace_init(&workspace) != 0)
            return 0;
        ready = 1;
    }
    if (!data || size < PH_NONCE_LEN || size > 4096u)
        return 0;

    uint64_t nonce = 0u;
    for (unsigned index = 0; index < PH_NONCE_LEN; index++)
        nonce |= (uint64_t)data[index] << (8u * index);
    const uint8_t *header = data + PH_NONCE_LEN;
    size_t header_len = size - PH_NONCE_LEN;

    uint8_t digest[PH_DIGEST_LEN];
    if (ph_lf2_hash_with_workspace(
            digest, NULL, &context, &workspace,
            header, header_len, nonce) == 0) {
        (void)ph_lf2_verify_with_workspace(
            &context, &workspace, header, header_len,
            nonce, digest);
    }
    return 0;
}
