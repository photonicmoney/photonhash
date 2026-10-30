/* Experimental standalone verifier research; no consensus integration. MIT. */
#ifndef LF3_BANK_OPENSSL_H
#define LF3_BANK_OPENSSL_H
#include "photonhash_launch.h"
/* Output must be zero-initialized and unused; workers must be 1..8.
 * Includes the same seeds, raw-stream checksums and full coefficients as C. */
int lf3_bank_openssl(ph_lf2_context_t *out, const uint8_t parent[32], unsigned workers);
#endif
