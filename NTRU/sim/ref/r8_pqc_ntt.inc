/* Included after vrfy.c in a generated, mechanically instrumented TU.
 * Only four function definition names are renamed; all original callers use
 * these wrappers. Capture executes original C; replay consumes only the file.
 */
static void mq_NTT(uint16_t *a, unsigned logn)
{
    uint16_t before[1024];
    if (pqc_ntt_replay("NTT", a, NULL, logn)) return;
    memcpy(before, a, ((size_t)1 << logn)*sizeof *a);
    pqc_original_mq_NTT(a, logn);
    pqc_ntt_emit("NTT", before, NULL, a, logn);
}
static void mq_iNTT(uint16_t *a, unsigned logn)
{
    uint16_t before[1024];
    if (pqc_ntt_replay("INTT", a, NULL, logn)) return;
    memcpy(before, a, ((size_t)1 << logn)*sizeof *a);
    pqc_original_mq_iNTT(a, logn);
    pqc_ntt_emit("INTT", before, NULL, a, logn);
}
static void mq_poly_tomonty(uint16_t *a, unsigned logn)
{
    uint16_t before[1024];
    if (pqc_ntt_replay("TOMONT", a, NULL, logn)) return;
    memcpy(before, a, ((size_t)1 << logn)*sizeof *a);
    pqc_original_mq_poly_tomonty(a, logn);
    pqc_ntt_emit("TOMONT", before, NULL, a, logn);
}
static void mq_poly_montymul_ntt(uint16_t *a, const uint16_t *b, unsigned logn)
{
    uint16_t before[1024];
    if (pqc_ntt_replay("MODMUL", a, b, logn)) return;
    memcpy(before, a, ((size_t)1 << logn)*sizeof *a);
    pqc_original_mq_poly_montymul_ntt(a, b, logn);
    pqc_ntt_emit("MODMUL", before, b, a, logn);
}
void pqc_export_ntt(void)
{
    printf("{\"type\":\"ntt_rom\",\"forward\":[");
    for (unsigned i=0;i<1024;i++)printf("%s%u",i?",":"",GMb[i]);
    printf("],\"inverse\":[");
    for (unsigned i=0;i<1024;i++)printf("%s%u",i?",":"",iGMb[i]);
    puts("]}");
}
