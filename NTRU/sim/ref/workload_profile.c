/* Count and time every transform kernel that FlexTransform would run, in the pinned
 * FN-DSA reference (R8) with its bundled NTRUGen, per application phase.
 * Kernels are intercepted with GNU ld --wrap (R8 fft.c and NTRUGen) or with renamed
 * definitions in a generated copy of vrfy.c (static q12289 NTT functions, see
 * workload_profile_ntt.inc). Arithmetic is the original C; nothing is replaced.
 * Output: one JSON document on stdout.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include "inner.h"
#include "falcon.h"

enum { PH_KEYGEN, PH_EXPAND, PH_SIGN, PH_VERIFY, PH_COUNT };
static const char *PHASE_NAMES[PH_COUNT] = { "keygen", "expand", "sign", "verify" };

enum {
	K_FFT, K_IFFT, K_CMUL, K_SPLIT, K_MERGE,               /* R8 Q64.64 */
	K_NTT, K_INTT, K_TOMONT, K_MODMUL,                     /* R8 q = 12289 */
	K_NG_FFT, K_NG_IFFT,                                   /* NTRUGen Q32.32 */
	K_P_NTT, K_P_INTT, K_P_MKGM, K_P_MKIGM, K_P_MKGMIGM,   /* NTRUGen 31-bit primes */
	K_COUNT
};
static const char *KIND_NAMES[K_COUNT] = {
	"r8_fft", "r8_ifft", "r8_cmul", "r8_split", "r8_merge",
	"q12289_ntt", "q12289_intt", "q12289_tomont", "q12289_modmul",
	"ng_fft", "ng_ifft",
	"p31_ntt", "p31_intt", "p31_mkgm", "p31_mkigm", "p31_mkgmigm"
};

static int phase = PH_KEYGEN;
static unsigned long long calls[PH_COUNT][K_COUNT][11];
static unsigned long long kernel_ns[PH_COUNT][K_COUNT][11];
static unsigned long long phase_ns[PH_COUNT];
static int depth;                       /* only time the outermost wrapped kernel */

static unsigned long long now_ns(void)
{
	struct timespec ts;
	clock_gettime(CLOCK_MONOTONIC, &ts);
	return (unsigned long long)ts.tv_sec * 1000000000ull + (unsigned long long)ts.tv_nsec;
}

static void close_batch(void);
static void close_window(void);

unsigned long long wp_begin(void)
{
	close_batch();                      /* any other kernel ends a batch of prime NTTs */
	close_window();                     /* and a window of independent per-prime work */
	depth++;
	return now_ns();
}

static unsigned long long wp_begin_table(void)
{
	close_batch();                      /* a new root table ends a same-prime batch only */
	depth++;
	return now_ns();
}

void wp_end(int kind, unsigned logn, unsigned long long t0)
{
	unsigned long long dt = now_ns() - t0;
	depth--;
	calls[phase][kind][logn]++;
	if (depth == 0) {
		kernel_ns[phase][kind][logn] += dt;
	}
}

/*
 * Host <-> core data traffic, in 128-bit lines, per phase. Three accountings:
 *   all:  every kernel input is written to the core and every output read back;
 *   miss: an input is written only if the core does not already hold that buffer with the same
 *         content (a resident copy left by an earlier kernel and not modified by the host since);
 *   lazy: an output is read back only when the host later changes the buffer, when it is evicted,
 *         or at the end of the phase (lower bound: host reads of unchanged data are not visible).
 * Residency: up to CAP_BYTES (three 16 KiB stores), least recently used buffer evicted first.
 */
#define CAP_BYTES (48u * 1024u)
#define MAX_RES 1024
static struct {
	const unsigned char *p;
	size_t n;
	unsigned long long h, lru;
	int dirty, valid;
} res[MAX_RES];
static size_t res_bytes;
static unsigned long long res_tick;
static unsigned long long io_in_all[PH_COUNT], io_out_all[PH_COUNT], io_in_miss[PH_COUNT], io_out_lazy[PH_COUNT];

static unsigned long long fnv(const void *p, size_t n)
{
	const unsigned char *b = p;
	unsigned long long h = 1469598103934665603ull;
	for (size_t i = 0; i < n; i++) {
		h = (h ^ b[i]) * 1099511628211ull;
	}
	return h;
}

static unsigned long long line_count(size_t n)
{
	return (n + 15) / 16;
}

static void res_drop(int i, int read_back)
{
	if (read_back && res[i].dirty) {
		io_out_lazy[phase] += line_count(res[i].n);
	}
	res[i].valid = 0;
	res_bytes -= res[i].n;
}

static int res_find(const void *p, size_t n)
{
	for (int i = 0; i < MAX_RES; i++) {
		if (res[i].valid && res[i].p == p && res[i].n == n) {
			return i;
		}
	}
	return -1;
}

static void res_evict_lru(void)
{
	int old = -1;
	for (int i = 0; i < MAX_RES; i++) {
		if (res[i].valid && (old < 0 || res[i].lru < res[old].lru)) {
			old = i;
		}
	}
	if (old >= 0) {
		res_drop(old, 1);
	}
}

static int res_insert(const void *p, size_t n)
{
	while (res_bytes > 0 && res_bytes + n > CAP_BYTES) {
		res_evict_lru();
	}
	for (;;) {
		for (int i = 0; i < MAX_RES; i++) {
			if (!res[i].valid) {
				res[i].p = p;
				res[i].n = n;
				res[i].valid = 1;
				res[i].dirty = 0;
				res_bytes += n;
				return i;
			}
		}
		res_evict_lru();             /* too many small buffers: also bounded like a real buffer table */
	}
}

void wp_in(const void *p, size_t n)
{
	unsigned long long h = fnv(p, n);
	int i = res_find(p, n);
	io_in_all[phase] += line_count(n);
	if (i >= 0 && res[i].h == h) {
		res[i].lru = res_tick++;
		return;
	}
	if (i >= 0) {
		res_drop(i, 1);             /* the host changed it, so it had read the core's result */
	}
	io_in_miss[phase] += line_count(n);
	i = res_insert(p, n);
	res[i].h = h;
	res[i].lru = res_tick++;
}

void wp_out(const void *p, size_t n)
{
	const unsigned char *b = p;
	io_out_all[phase] += line_count(n);
	for (int k = 0; k < MAX_RES; k++) {
		if (res[k].valid && !(res[k].p == b && res[k].n == n)
			&& res[k].p < b + n && b < res[k].p + res[k].n) {
			res_drop(k, 0);         /* overwritten inside the core: never needed by the host */
		}
	}
	int i = res_find(p, n);
	if (i < 0) {
		i = res_insert(p, n);
	}
	res[i].h = fnv(p, n);
	res[i].dirty = 1;
	res[i].lru = res_tick++;
}

static void res_end_phase(void)
{
	for (int i = 0; i < MAX_RES; i++) {
		if (res[i].valid && res[i].dirty) {
			io_out_lazy[phase] += line_count(res[i].n);
			res[i].dirty = 0;        /* results handed to the application */
		}
	}
}

#define WRAP_IO(sym, kind, params, args, logn_expr, active, pre, post) \
	void __real_##sym params; \
	void __wrap_##sym params { \
		unsigned long long t0 = wp_begin(); \
		if (active) { pre; } \
		__real_##sym args; \
		if (active) { post; } \
		wp_end(kind, logn_expr, t0); \
	}

#define FPR_N(logn) (((size_t)1 << (logn)) * sizeof(fpr))
WRAP_IO(falcon_inner_FFT, K_FFT, (fpr *f, unsigned logn), (f, logn), logn, logn > 1,
	wp_in(f, FPR_N(logn)), wp_out(f, FPR_N(logn)))
WRAP_IO(falcon_inner_iFFT, K_IFFT, (fpr *f, unsigned logn), (f, logn), logn, logn > 1,
	wp_in(f, FPR_N(logn)), wp_out(f, FPR_N(logn)))
WRAP_IO(falcon_inner_poly_mul_fft, K_CMUL, (fpr *a, const fpr *b, unsigned logn), (a, b, logn), logn, 1,
	(wp_in(a, FPR_N(logn)), wp_in(b, FPR_N(logn))), wp_out(a, FPR_N(logn)))
WRAP_IO(falcon_inner_poly_split_fft, K_SPLIT, (fpr *f0, fpr *f1, const fpr *f, unsigned logn),
	(f0, f1, f, logn), logn, 1,
	wp_in(f, FPR_N(logn)), (wp_out(f0, FPR_N(logn) / 2), wp_out(f1, FPR_N(logn) / 2)))
WRAP_IO(falcon_inner_poly_merge_fft, K_MERGE, (fpr *f, const fpr *f0, const fpr *f1, unsigned logn),
	(f, f0, f1, logn), logn, 1,
	(wp_in(f0, FPR_N(logn) / 2), wp_in(f1, FPR_N(logn) / 2)), wp_out(f, FPR_N(logn)))
WRAP_IO(ntrugen_vect_FFT, K_NG_FFT, (unsigned logn, void *f), (logn, f), logn, logn > 1,
	wp_in(f, ((size_t)8) << logn), wp_out(f, ((size_t)8) << logn))
WRAP_IO(ntrugen_vect_iFFT, K_NG_IFFT, (unsigned logn, void *f), (logn, f), logn, logn > 1,
	wp_in(f, ((size_t)8) << logn), wp_out(f, ((size_t)8) << logn))
/*
 * Batching of 31-bit-prime NTT calls (spec 2.0: several polynomials in one command).
 * A call joins the open batch when it immediately follows the batch's last call (no other
 * counted kernel in between), with the same direction, logn, prime and root table, on a
 * disjoint array, and the batch is below the spec limit: N < 64: jobs * N <= 32 and
 * jobs <= 8; N >= 64: jobs <= 2. Call sites of joined calls are recorded so that their
 * independence can be checked in the source.
 */
#define MAX_JOBS 8
static unsigned long long batches[PH_COUNT][2][11][MAX_JOBS + 1];
static struct {
	int open, kind;
	unsigned logn, size;
	uint32_t p;
	const uint32_t *table;
	const uint32_t *arrays[MAX_JOBS];
	void *first_site;
} cur;
static struct { void *a, *b; unsigned long long n; } site_pairs[256];
static int site_pair_count;

/*
 * Upper bound for batching ACROSS primes (each tile has its own modulus register): inside a
 * window of prime NTT work with no other kernel kind in between, calls of the same direction
 * and logn are grouped into commands of up to xlimit(logn) polynomials, possibly with different
 * primes. This assumes the loops over primes can be split (RNS lanes are independent); it is an
 * estimate, not a property checked on the code.
 */
#define MAX_XJOBS 16
static unsigned long long window_calls[2][11];
static unsigned long long xbatches[PH_COUNT][2][11][MAX_XJOBS + 1];

static unsigned xlimit(unsigned logn)
{
	unsigned n = 1u << logn;
	if (n >= 64) {
		return 1;                       /* N >= 64 shares every tile: one prime per command */
	}
	return (64 / n < MAX_JOBS) ? 64 / n : MAX_JOBS;     /* 16 tiles x 4 coefficients, jobs <= 8 */
}

static void close_window(void)
{
	for (int dir = 0; dir < 2; dir++) {
		for (unsigned l = 1; l <= 10; l++) {
			unsigned long long c = window_calls[dir][l];
			unsigned b = xlimit(l);
			if (c) {
				xbatches[phase][dir][l][b] += c / b;
				if (c % b) {
					xbatches[phase][dir][l][c % b]++;
				}
				window_calls[dir][l] = 0;
			}
		}
	}
}

static unsigned batch_limit(unsigned logn)
{
	unsigned n = 1u << logn;
	if (n >= 64) {
		return 2;
	}
	return (32 / n < MAX_JOBS) ? 32 / n : MAX_JOBS;
}

static void close_batch(void)
{
	if (cur.open) {
		batches[phase][cur.kind][cur.logn][cur.size]++;
		cur.open = 0;
	}
}

static void note_site_pair(void *a, void *b)
{
	for (int i = 0; i < site_pair_count; i++) {
		if (site_pairs[i].a == a && site_pairs[i].b == b) {
			site_pairs[i].n++;
			return;
		}
	}
	if (site_pair_count < 256) {
		site_pairs[site_pair_count].a = a;
		site_pairs[site_pair_count].b = b;
		site_pairs[site_pair_count].n = 1;
		site_pair_count++;
	}
}

static void batch_call(int dir, unsigned logn, const uint32_t *a, const uint32_t *table, uint32_t p, void *site)
{
	size_t n = (size_t)1 << logn;
	if (logn > 0) {
		window_calls[dir][logn]++;
	}
	int join = cur.open && cur.kind == dir && cur.logn == logn && cur.p == p && cur.table == table
		&& cur.size < batch_limit(logn);
	for (unsigned i = 0; join && i < cur.size; i++) {
		if (a < cur.arrays[i] + n && cur.arrays[i] < a + n) {
			join = 0;
		}
	}
	if (join) {
		cur.arrays[cur.size++] = a;
		note_site_pair(cur.first_site, site);
		return;
	}
	close_batch();
	cur.open = 1;
	cur.kind = dir;
	cur.logn = logn;
	cur.size = 1;
	cur.p = p;
	cur.table = table;
	cur.arrays[0] = a;
	cur.first_site = site;
}

void __real_ntrugen_mp_NTT(unsigned logn, uint32_t *a, const uint32_t *gm, uint32_t p, uint32_t p0i);
void __wrap_ntrugen_mp_NTT(unsigned logn, uint32_t *a, const uint32_t *gm, uint32_t p, uint32_t p0i)
{
	batch_call(0, logn, a, gm, p, __builtin_return_address(0));
	unsigned long long t0 = now_ns();
	depth++;
	if (logn > 0) {
		wp_in(a, (size_t)4 << logn);
	}
	__real_ntrugen_mp_NTT(logn, a, gm, p, p0i);
	if (logn > 0) {
		wp_out(a, (size_t)4 << logn);
	}
	depth--;
	calls[phase][K_P_NTT][logn]++;
	if (depth == 0) {
		kernel_ns[phase][K_P_NTT][logn] += now_ns() - t0;
	}
}

void __real_ntrugen_mp_iNTT(unsigned logn, uint32_t *a, const uint32_t *igm, uint32_t p, uint32_t p0i);
void __wrap_ntrugen_mp_iNTT(unsigned logn, uint32_t *a, const uint32_t *igm, uint32_t p, uint32_t p0i)
{
	batch_call(1, logn, a, igm, p, __builtin_return_address(0));
	unsigned long long t0 = now_ns();
	depth++;
	if (logn > 0) {
		wp_in(a, (size_t)4 << logn);
	}
	__real_ntrugen_mp_iNTT(logn, a, igm, p, p0i);
	if (logn > 0) {
		wp_out(a, (size_t)4 << logn);
	}
	depth--;
	calls[phase][K_P_INTT][logn]++;
	if (depth == 0) {
		kernel_ns[phase][K_P_INTT][logn] += now_ns() - t0;
	}
}
#define WRAP_TABLE(sym, kind, params, args, logn_expr) \
	void __real_##sym params; \
	void __wrap_##sym params { \
		unsigned long long t0 = wp_begin_table(); \
		__real_##sym args; \
		wp_end(kind, logn_expr, t0); \
	}

WRAP_TABLE(ntrugen_mp_mkgm, K_P_MKGM, (unsigned logn, uint32_t *gm, uint32_t g, uint32_t p, uint32_t p0i),
	(logn, gm, g, p, p0i), logn)
WRAP_TABLE(ntrugen_mp_mkigm, K_P_MKIGM, (unsigned logn, uint32_t *igm, uint32_t ig, uint32_t p, uint32_t p0i),
	(logn, igm, ig, p, p0i), logn)
WRAP_TABLE(ntrugen_mp_mkgmigm, K_P_MKGMIGM,
	(unsigned logn, uint32_t *gm, uint32_t *igm, uint32_t g, uint32_t ig, uint32_t p, uint32_t p0i),
	(logn, gm, igm, g, ig, p, p0i), logn)

static void *alloc_bytes(size_t n)
{
	void *p = calloc(1, n);
	if (p == NULL) {
		fprintf(stderr, "allocation failed\n");
		exit(2);
	}
	return p;
}

static void fail(const char *what)
{
	fprintf(stderr, "workload_profile: %s\n", what);
	exit(4);
}

static void run_phase(int ph, int rc, unsigned long long t0, const char *what, int expect_ok)
{
	phase_ns[ph] += now_ns() - t0;
	close_batch();
	close_window();
	res_end_phase();
	if ((rc == 0) != expect_ok) {
		fail(what);
	}
}

int main(int argc, char **argv)
{
	if (argc != 4) {
		return 3;
	}
	unsigned logn = (unsigned)atoi(argv[1]);
	unsigned keys = (unsigned)atoi(argv[2]);
	unsigned sigs = (unsigned)atoi(argv[3]);
	size_t sklen = FALCON_PRIVKEY_SIZE(logn), pklen = FALCON_PUBKEY_SIZE(logn);
	size_t eklen = FALCON_EXPANDEDKEY_SIZE(logn), cap = FALCON_SIG_COMPRESSED_MAXSIZE(logn);
	size_t tmplen = FALCON_TMPSIZE_KEYGEN(logn);
	if (tmplen < FALCON_TMPSIZE_EXPANDPRIV(logn)) tmplen = FALCON_TMPSIZE_EXPANDPRIV(logn);
	if (tmplen < FALCON_TMPSIZE_SIGNTREE(logn)) tmplen = FALCON_TMPSIZE_SIGNTREE(logn);
	if (tmplen < FALCON_TMPSIZE_VERIFY(logn)) tmplen = FALCON_TMPSIZE_VERIFY(logn);
	void *sk = alloc_bytes(sklen), *pk = alloc_bytes(pklen), *ek = alloc_bytes(eklen), *tmp = alloc_bytes(tmplen);
	unsigned char *sig = alloc_bytes(cap);

	for (unsigned k = 0; k < keys; k++) {
		unsigned char seed[48];
		for (unsigned i = 0; i < sizeof seed; i++) {
			seed[i] = (unsigned char)(i + 17 * logn + 101 * k);
		}
		shake256_context rng;
		shake256_init_prng_from_seed(&rng, seed, sizeof seed);
		unsigned long long t0;

		phase = PH_KEYGEN;
		t0 = now_ns();
		run_phase(PH_KEYGEN, falcon_keygen_make(&rng, logn, sk, sklen, pk, pklen, tmp, tmplen), t0, "keygen", 1);
		phase = PH_EXPAND;
		t0 = now_ns();
		run_phase(PH_EXPAND, falcon_expand_privkey(ek, eklen, sk, sklen, tmp, tmplen), t0, "expand", 1);
		for (unsigned s = 0; s < sigs; s++) {
			char msg[96];
			int ml = snprintf(msg, sizeof msg, "FlexTransform workload profile key=%u msg=%u", k, s);
			size_t siglen = cap;
			phase = PH_SIGN;
			t0 = now_ns();
			run_phase(PH_SIGN, falcon_sign_tree(&rng, sig, &siglen, FALCON_SIG_COMPRESSED, ek, msg, (size_t)ml,
				tmp, tmplen), t0, "sign", 1);
			phase = PH_VERIFY;
			t0 = now_ns();
			run_phase(PH_VERIFY, falcon_verify(sig, siglen, FALCON_SIG_COMPRESSED, pk, pklen, msg, (size_t)ml,
				tmp, tmplen), t0, "verify", 1);
		}
	}

	printf("{\"logn\":%u,\"keys\":%u,\"sigs_per_key\":%u,\"phases\":{", logn, keys, sigs);
	for (int ph = 0; ph < PH_COUNT; ph++) {
		printf("%s\"%s\":{\"ns\":%llu,\"io_lines\":{\"in_all\":%llu,\"out_all\":%llu,\"in_miss\":%llu,"
			"\"out_lazy\":%llu},\"kernels\":[", ph ? "," : "", PHASE_NAMES[ph], phase_ns[ph],
			io_in_all[ph], io_out_all[ph], io_in_miss[ph], io_out_lazy[ph]);
		int first = 1;
		for (int kd = 0; kd < K_COUNT; kd++) {
			for (unsigned l = 0; l <= 10; l++) {
				if (calls[ph][kd][l]) {
					printf("%s{\"kind\":\"%s\",\"logn\":%u,\"calls\":%llu,\"ns\":%llu}", first ? "" : ",",
						KIND_NAMES[kd], l, calls[ph][kd][l], kernel_ns[ph][kd][l]);
					first = 0;
				}
			}
		}
		printf("],\"p31_batches\":[");
		first = 1;
		for (int dir = 0; dir < 2; dir++) {
			for (unsigned l = 0; l <= 10; l++) {
				for (unsigned s = 1; s <= MAX_JOBS; s++) {
					if (batches[ph][dir][l][s]) {
						printf("%s{\"dir\":%d,\"logn\":%u,\"jobs\":%u,\"count\":%llu}", first ? "" : ",",
							dir, l, s, batches[ph][dir][l][s]);
						first = 0;
					}
				}
			}
		}
		printf("],\"p31_cross_prime_batches\":[");
		first = 1;
		for (int dir = 0; dir < 2; dir++) {
			for (unsigned l = 1; l <= 10; l++) {
				for (unsigned s = 1; s <= MAX_XJOBS; s++) {
					if (xbatches[ph][dir][l][s]) {
						printf("%s{\"dir\":%d,\"logn\":%u,\"jobs\":%u,\"count\":%llu}", first ? "" : ",",
							dir, l, s, xbatches[ph][dir][l][s]);
						first = 0;
					}
				}
			}
		}
		printf("]}");
	}
	printf("},\"site_pairs\":[");
	for (int i = 0; i < site_pair_count; i++) {
		printf("%s{\"first\":\"%p\",\"joined\":\"%p\",\"count\":%llu}", i ? "," : "",
			site_pairs[i].a, site_pairs[i].b, site_pairs[i].n);
	}
	printf("]}\n");
	free(sk); free(pk); free(ek); free(tmp); free(sig);
	return 0;
}
