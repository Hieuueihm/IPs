/*
 * Dump NTRUGen's Q32.32 FFT (ng_fxp.c, pinned reference) for scripts/build_spec2_kernel_assets.py.
 * Built with -DNTRUGEN_AVX2=0. Reads "logn count" pairs is not needed: the case list is fixed here.
 * Output: little-endian uint64 stream; for each case: logn, kind (0 = FFT, 1 = iFFT), input[n], output[n].
 */
#include <stdio.h>
#include <stdlib.h>
#include "ng_inner.h"

static uint64_t rng_state = 0x243F6A8885A308D3u;

static uint64_t rnd(void)
{
	rng_state ^= rng_state << 13;
	rng_state ^= rng_state >> 7;
	rng_state ^= rng_state << 17;
	return rng_state;
}

int main(int argc, char **argv)
{
	static uint64_t a[1024], b[1024];
	FILE *f = fopen(argv[1], "wb");
	if (argc < 2 || f == NULL) {
		return 1;
	}
	for (uint64_t logn = 1; logn <= 10; logn++) {
		size_t n = (size_t)1 << logn;
		for (uint64_t kind = 0; kind < 2; kind++) {
			/* style 0: |x| < 2^40 (values the keygen sees); style 1: full 64-bit words */
			for (int style = 0; style < 2; style++) {
				for (size_t j = 0; j < n; j++) {
					uint64_t v = rnd();
					a[j] = style ? v : (uint64_t)((int64_t)v >> 24);
					b[j] = a[j];
				}
				if (kind == 0) {
					vect_FFT((unsigned)logn, (fxr *)b);
				} else {
					vect_iFFT((unsigned)logn, (fxr *)b);
				}
				fwrite(&logn, 8, 1, f);
				fwrite(&kind, 8, 1, f);
				fwrite(a, 8, n, f);
				fwrite(b, 8, n, f);
			}
		}
	}
	fclose(f);
	return 0;
}
