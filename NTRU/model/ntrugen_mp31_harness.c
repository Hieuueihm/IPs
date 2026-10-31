/*
 * Dump NTRUGen's 31-bit-prime NTT (ng_mp31.c, pinned reference) for model/ntrugen_mp31.py.
 * Built with -DNTRUGEN_AVX2=0. Output: little-endian uint32 stream, per prime:
 *   p, p0i, g, ig;
 *   MONT_PAIRS × (a, b, mp_montymul(a, b));
 *   for logn = 1..10: gm[n], igm[n], a[n], mp_NTT(a)[n], b[n], mp_iNTT(b)[n].
 */
#include <stdio.h>
#include <stdlib.h>
#include "ng_inner.h"

#define NUM_PRIMES 323
#define MONT_PAIRS 67

static uint64_t rng_state = 0x9E3779B97F4A7C15u;

static uint32_t rnd(void)
{
	rng_state ^= rng_state << 13;
	rng_state ^= rng_state >> 7;
	rng_state ^= rng_state << 17;
	return (uint32_t)(rng_state >> 16);
}

static void put(FILE *f, const uint32_t *v, size_t n)
{
	fwrite(v, sizeof(uint32_t), n, f);
}

int main(int argc, char **argv)
{
	static uint32_t gm[1024], igm[1024], a[1024], b[1024];
	FILE *f = fopen(argv[1], "wb");
	if (argc < 2 || f == NULL) {
		return 1;
	}
	for (int i = 0; i < NUM_PRIMES; i++) {
		uint32_t p = PRIMES[i].p, p0i = PRIMES[i].p0i;
		uint32_t hdr[4] = { p, p0i, PRIMES[i].g, PRIMES[i].ig };
		put(f, hdr, 4);
		for (int k = 0; k < MONT_PAIRS; k++) {
			/* first pairs are the edge values 0, 1, p - 1 */
			uint32_t e[3] = { 0, 1, p - 1 };
			uint32_t x = k < 9 ? e[k / 3] : rnd() % p;
			uint32_t y = k < 9 ? e[k % 3] : rnd() % p;
			uint32_t t[3] = { x, y, mp_montymul(x, y, p, p0i) };
			put(f, t, 3);
		}
		for (unsigned logn = 1; logn <= 10; logn++) {
			size_t n = (size_t)1 << logn;
			mp_mkgmigm(logn, gm, igm, PRIMES[i].g, PRIMES[i].ig, p, p0i);
			for (size_t j = 0; j < n; j++) {
				a[j] = rnd() % p;
				b[j] = rnd() % p;
			}
			put(f, gm, n);
			put(f, igm, n);
			put(f, a, n);
			mp_NTT(logn, a, gm, p, p0i);
			put(f, a, n);
			put(f, b, n);
			mp_iNTT(logn, b, igm, p, p0i);
			put(f, b, n);
		}
	}
	fclose(f);
	return 0;
}
