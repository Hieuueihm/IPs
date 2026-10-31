/* Appended to a generated copy of vrfy.c by scripts/profile_fn_dsa_workload.py.
 * The four q = 12289 kernel definitions were renamed to wp_original_*; these
 * wrappers keep the original names, call the original code and count the call
 * and its host data traffic.
 */
unsigned long long wp_begin(void);
void wp_end(int kind, unsigned logn, unsigned long long t0);
void wp_in(const void *p, size_t n);
void wp_out(const void *p, size_t n);

static void mq_NTT(uint16_t *a, unsigned logn)
{
	unsigned long long t0 = wp_begin();
	wp_in(a, (size_t)2 << logn);
	wp_original_mq_NTT(a, logn);
	wp_out(a, (size_t)2 << logn);
	wp_end(5, logn, t0);
}

static void mq_iNTT(uint16_t *a, unsigned logn)
{
	unsigned long long t0 = wp_begin();
	wp_in(a, (size_t)2 << logn);
	wp_original_mq_iNTT(a, logn);
	wp_out(a, (size_t)2 << logn);
	wp_end(6, logn, t0);
}

static void mq_poly_tomonty(uint16_t *a, unsigned logn)
{
	unsigned long long t0 = wp_begin();
	wp_in(a, (size_t)2 << logn);
	wp_original_mq_poly_tomonty(a, logn);
	wp_out(a, (size_t)2 << logn);
	wp_end(7, logn, t0);
}

static void mq_poly_montymul_ntt(uint16_t *a, const uint16_t *b, unsigned logn)
{
	unsigned long long t0 = wp_begin();
	wp_in(a, (size_t)2 << logn);
	wp_in(b, (size_t)2 << logn);
	wp_original_mq_poly_montymul_ntt(a, b, logn);
	wp_out(a, (size_t)2 << logn);
	wp_end(8, logn, t0);
}
