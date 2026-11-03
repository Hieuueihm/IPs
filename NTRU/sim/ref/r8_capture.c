/* External capture harness for unmodified pinned R8 scalar fixed-point kernels.
 * Build fft.c with symbol renames only; wrappers below observe calls without
 * changing any arithmetic or the reference source files.
 */
#include <inttypes.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "inner.h"
#include "falcon.h"

#if !FALCON_FXP || FALCON_AVX2
#error This harness requires the pinned scalar fixed-point configuration.
#endif

void r8_original_FFT(fpr *, unsigned);
void r8_original_iFFT(fpr *, unsigned);
void r8_original_poly_mul_fft(fpr *, const fpr *, unsigned);
void r8_original_poly_split_fft(fpr *, fpr *, const fpr *, unsigned);
void r8_original_poly_merge_fft(fpr *, const fpr *, const fpr *, unsigned);

static const char *origin = "synthetic";
static unsigned long long sequence;
static unsigned case_id;

static void *checked_alloc(size_t n)
{
    void *p = calloc(1, n);
    if (!p) { fprintf(stderr, "allocation failed\n"); exit(2); }
    return p;
}

static void dump_array(const fpr *a, size_t n)
{
    putchar('[');
    for (size_t i = 0; i < n; i++) {
        if (i) putchar(',');
        printf("\"%016" PRIx64 "%016" PRIx64 "\"",
            (uint64_t)(a[i].v >> 64), (uint64_t)a[i].v);
    }
    putchar(']');
}

static fpr *snapshot(const fpr *a, size_t n)
{
    fpr *p = checked_alloc(n * sizeof *p);
    memcpy(p, a, n * sizeof *p);
    return p;
}

static void emit(const char *op, unsigned logn, const fpr *a, size_t na,
                 const fpr *b, size_t nb, const fpr *y, const fpr *z)
{
    size_t n = (size_t)1 << logn;
    printf("{\"type\":\"kernel\",\"id\":%llu,\"case\":%u,\"origin\":\"%s\","
           "\"op\":\"%s\",\"logn\":%u,\"a\":", sequence++, case_id, origin, op, logn);
    dump_array(a, na);
    if (b) { printf(",\"b\":"); dump_array(b, nb); }
    printf(",\"out\":"); dump_array(y, z ? n/2 : n);
    if (z) { printf(",\"out1\":"); dump_array(z, n/2); }
    puts("}");
}

void Zf(FFT)(fpr *a, unsigned logn)
{
    size_t n = (size_t)1 << logn;
    fpr *before = snapshot(a, n);
    r8_original_FFT(a, logn);
    emit("FFT", logn, before, n, NULL, 0, a, NULL);
    free(before);
}

void Zf(iFFT)(fpr *a, unsigned logn)
{
    size_t n = (size_t)1 << logn;
    fpr *before = snapshot(a, n);
    r8_original_iFFT(a, logn);
    emit("IFFT", logn, before, n, NULL, 0, a, NULL);
    free(before);
}

void Zf(poly_mul_fft)(fpr *a, const fpr *b, unsigned logn)
{
    size_t n = (size_t)1 << logn;
    fpr *before = snapshot(a, n), *other = snapshot(b, n);
    r8_original_poly_mul_fft(a, b, logn);
    emit("CMUL", logn, before, n, other, n, a, NULL);
    free(before); free(other);
}

void Zf(poly_split_fft)(fpr *f0, fpr *f1, const fpr *a, unsigned logn)
{
    size_t n = (size_t)1 << logn;
    fpr *before = snapshot(a, n);
    r8_original_poly_split_fft(f0, f1, a, logn);
    emit("SPLIT", logn, before, n, NULL, 0, f0, f1);
    free(before);
}

void Zf(poly_merge_fft)(fpr *f, const fpr *f0, const fpr *f1, unsigned logn)
{
    size_t hn = (size_t)1 << (logn-1);
    fpr *a = snapshot(f0, hn), *b = snapshot(f1, hn);
    r8_original_poly_merge_fft(f, f0, f1, logn);
    emit("MERGE", logn, a, hn, b, hn, f, NULL);
    free(a); free(b);
}

static fpr read_word(void)
{
    char s[40], *end;
    fpr a;
    if (scanf("%39s", s) != 1 || strlen(s) != 32) exit(3);
    uint64_t low = strtoull(s+16, &end, 16);
    if (*end) exit(3);
    s[16] = 0;
    uint64_t high = strtoull(s, &end, 16);
    if (*end) exit(3);
    a.v = ((uint128_t)high << 64) | low;
    return a;
}

static void synthetic(void)
{
    char op[20];
    unsigned logn;
    while (scanf("%19s %u %u", op, &logn, &case_id) == 3) {
        if (logn > 10 || (!logn && strcmp(op, "FFT") && strcmp(op, "IFFT"))) exit(3);
        size_t n = (size_t)1 << logn;
        fpr *a = checked_alloc(n*sizeof *a), *b = checked_alloc(n*sizeof *b);
        fpr *y = checked_alloc(n*sizeof *y);
        for (size_t i=0; i<n; i++) a[i]=read_word();
        if (!strcmp(op, "CMUL")) for (size_t i=0; i<n; i++) b[i]=read_word();
        if (!strcmp(op, "FFT")) Zf(FFT)(a, logn);
        else if (!strcmp(op, "IFFT")) Zf(iFFT)(a, logn);
        else if (!strcmp(op, "CMUL")) Zf(poly_mul_fft)(a, b, logn);
        else if (!strcmp(op, "SPLIT")) Zf(poly_split_fft)(y, y+n/2, a, logn);
        else if (!strcmp(op, "MERGE")) Zf(poly_merge_fft)(y, a, a+n/2, logn);
        else exit(3);
        free(a); free(b); free(y);
    }
}

static void workload(unsigned logn)
{
    if (logn != 9 && logn != 10) exit(3);
    unsigned char seed[48];
    for (unsigned i=0; i<sizeof seed; i++) seed[i]=(unsigned char)(i+17*logn);
    const char message[] = "FlexTransform deterministic R8 capture 2026-10-25";
    shake256_context rng;
    shake256_init_prng_from_seed(&rng, seed, sizeof seed);
    size_t sklen=FALCON_PRIVKEY_SIZE(logn), pklen=FALCON_PUBKEY_SIZE(logn);
    size_t eklen=FALCON_EXPANDEDKEY_SIZE(logn);
    size_t siglen=FALCON_SIG_COMPRESSED_MAXSIZE(logn);
    size_t tmplen=FALCON_TMPSIZE_KEYGEN(logn);
    if (tmplen < FALCON_TMPSIZE_EXPANDPRIV(logn)) tmplen=FALCON_TMPSIZE_EXPANDPRIV(logn);
    if (tmplen < FALCON_TMPSIZE_SIGNTREE(logn)) tmplen=FALCON_TMPSIZE_SIGNTREE(logn);
    if (tmplen < FALCON_TMPSIZE_VERIFY(logn)) tmplen=FALCON_TMPSIZE_VERIFY(logn);
    void *sk=checked_alloc(sklen), *pk=checked_alloc(pklen), *ek=checked_alloc(eklen);
    void *sig=checked_alloc(siglen), *tmp=checked_alloc(tmplen);
    origin="keygen";
    int kg=falcon_keygen_make(&rng, logn, sk, sklen, pk, pklen, tmp, tmplen);
    fprintf(stderr,"keygen N=%u status=%d\n",1u<<logn,kg); fflush(stderr);
    if (kg) exit(4);
    origin="expand_privkey";
    int ex=falcon_expand_privkey(ek, eklen, sk, sklen, tmp, tmplen);
    fprintf(stderr,"expand N=%u status=%d\n",1u<<logn,ex); fflush(stderr);
    if (ex) exit(4);
    origin="sign_tree";
    int si=falcon_sign_tree(&rng,sig,&siglen,FALCON_SIG_COMPRESSED,ek,
                           message,sizeof message-1,tmp,tmplen);
    fprintf(stderr,"sign N=%u status=%d\n",1u<<logn,si); fflush(stderr);
    if (si) exit(4);
    origin="verify";
    int ve=falcon_verify(sig,siglen,FALCON_SIG_COMPRESSED,pk,pklen,
                         message,sizeof message-1,tmp,tmplen);
    printf("{\"type\":\"workload\",\"logn\":%u,\"keygen\":%d,\"expand\":%d,"
           "\"sign\":%d,\"verify\":%d,\"signature_bytes\":%zu}\n",logn,kg,ex,si,ve,siglen);
    if (ve) exit(4);
    free(sk); free(pk); free(ek); free(sig); free(tmp);
}

int main(int argc, char **argv)
{
    /* Export exact reference constants; no host floating-point regeneration. */
    printf("{\"type\":\"rom\",\"words\":");
    dump_array(fpr_gm_tab, 2048); puts("}");
    if (argc==3 && !strcmp(argv[1],"--workload")) workload((unsigned)atoi(argv[2]));
    else if (argc==1) synthetic();
    else return 3;
    return ferror(stdout) ? 5 : 0;
}
