/* Test-only external bridge; pinned reference checkout is never edited. */
#ifndef R8_PQC_BRIDGE_H
#define R8_PQC_BRIDGE_H
#include <stdint.h>
int pqc_ntt_replay(const char *, uint16_t *, const uint16_t *, unsigned);
void pqc_ntt_emit(const char *, const uint16_t *, const uint16_t *, const uint16_t *, unsigned);
void pqc_export_ntt(void);
#endif
