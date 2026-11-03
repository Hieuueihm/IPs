# R8 C → FlexTransform golden model: differential check

- Pinned commit: `ad1e5bf7714d53230ad457364db8a46a1b459c94`.
- C kernel calls: **3842**; mismatches: **0**.
- Output Q64.64 words checked per model: **171464** (both leaf 16 and 32).
- C source remained pristine; compiler commands and SHA-256 recorded in the vector manifest.

| Origin / kernel / N | Captured calls |
|---|---:|
| expand_privkey/FFT/N1024 | 4 |
| expand_privkey/FFT/N512 | 4 |
| expand_privkey/SPLIT/N1024 | 1 |
| expand_privkey/SPLIT/N128 | 12 |
| expand_privkey/SPLIT/N16 | 96 |
| expand_privkey/SPLIT/N2 | 768 |
| expand_privkey/SPLIT/N256 | 6 |
| expand_privkey/SPLIT/N32 | 48 |
| expand_privkey/SPLIT/N4 | 384 |
| expand_privkey/SPLIT/N512 | 3 |
| expand_privkey/SPLIT/N64 | 24 |
| expand_privkey/SPLIT/N8 | 192 |
| sign_tree/CMUL/N1024 | 7 |
| sign_tree/CMUL/N128 | 12 |
| sign_tree/CMUL/N16 | 96 |
| sign_tree/CMUL/N256 | 6 |
| sign_tree/CMUL/N32 | 48 |
| sign_tree/CMUL/N512 | 9 |
| sign_tree/CMUL/N64 | 24 |
| sign_tree/CMUL/N8 | 192 |
| sign_tree/FFT/N1024 | 3 |
| sign_tree/FFT/N512 | 3 |
| sign_tree/IFFT/N1024 | 4 |
| sign_tree/IFFT/N512 | 4 |
| sign_tree/MERGE/N1024 | 2 |
| sign_tree/MERGE/N128 | 24 |
| sign_tree/MERGE/N16 | 192 |
| sign_tree/MERGE/N256 | 12 |
| sign_tree/MERGE/N32 | 96 |
| sign_tree/MERGE/N512 | 6 |
| sign_tree/MERGE/N64 | 48 |
| sign_tree/MERGE/N8 | 384 |
| sign_tree/SPLIT/N1024 | 2 |
| sign_tree/SPLIT/N128 | 24 |
| sign_tree/SPLIT/N16 | 192 |
| sign_tree/SPLIT/N256 | 12 |
| sign_tree/SPLIT/N32 | 96 |
| sign_tree/SPLIT/N512 | 6 |
| sign_tree/SPLIT/N64 | 48 |
| sign_tree/SPLIT/N8 | 384 |
| synthetic/CMUL/N1024 | 7 |
| synthetic/CMUL/N128 | 7 |
| synthetic/CMUL/N16 | 7 |
| synthetic/CMUL/N2 | 7 |
| synthetic/CMUL/N256 | 7 |
| synthetic/CMUL/N32 | 7 |
| synthetic/CMUL/N4 | 7 |
| synthetic/CMUL/N512 | 7 |
| synthetic/CMUL/N64 | 7 |
| synthetic/CMUL/N8 | 7 |
| synthetic/FFT/N1 | 7 |
| synthetic/FFT/N1024 | 7 |
| synthetic/FFT/N128 | 7 |
| synthetic/FFT/N16 | 7 |
| synthetic/FFT/N2 | 7 |
| synthetic/FFT/N256 | 7 |
| synthetic/FFT/N32 | 7 |
| synthetic/FFT/N4 | 7 |
| synthetic/FFT/N512 | 7 |
| synthetic/FFT/N64 | 7 |
| synthetic/FFT/N8 | 7 |
| synthetic/IFFT/N1 | 7 |
| synthetic/IFFT/N1024 | 7 |
| synthetic/IFFT/N128 | 7 |
| synthetic/IFFT/N16 | 7 |
| synthetic/IFFT/N2 | 7 |
| synthetic/IFFT/N256 | 7 |
| synthetic/IFFT/N32 | 7 |
| synthetic/IFFT/N4 | 7 |
| synthetic/IFFT/N512 | 7 |
| synthetic/IFFT/N64 | 7 |
| synthetic/IFFT/N8 | 7 |
| synthetic/MERGE/N1024 | 7 |
| synthetic/MERGE/N128 | 7 |
| synthetic/MERGE/N16 | 7 |
| synthetic/MERGE/N2 | 7 |
| synthetic/MERGE/N256 | 7 |
| synthetic/MERGE/N32 | 7 |
| synthetic/MERGE/N4 | 7 |
| synthetic/MERGE/N512 | 7 |
| synthetic/MERGE/N64 | 7 |
| synthetic/MERGE/N8 | 7 |
| synthetic/SPLIT/N1024 | 7 |
| synthetic/SPLIT/N128 | 7 |
| synthetic/SPLIT/N16 | 7 |
| synthetic/SPLIT/N2 | 7 |
| synthetic/SPLIT/N256 | 7 |
| synthetic/SPLIT/N32 | 7 |
| synthetic/SPLIT/N4 | 7 |
| synthetic/SPLIT/N512 | 7 |
| synthetic/SPLIT/N64 | 7 |
| synthetic/SPLIT/N8 | 7 |

Workload status:
- N=512: keygen/expand/sign_tree/verify all returned 0; signature 654 bytes.
- N=1024: keygen/expand/sign_tree/verify all returned 0; signature 1273 bytes.

Limits:
- No RTL/cycle/backpressure/PPA check.
- No hardware kernel substituted in signing.
- Q64.64 only; FFT32/64 not validated against R8.
- R8 keygen uses NTRUGen, whose Q32.32 FFT is outside this capture.

Negative controls (both detected):
- 4M_instead_of_3M: {'case': 31, 'op': 'CMUL', 'logn': 1}
- forward_root_in_IFFT: {'case': 55, 'op': 'IFFT', 'logn': 2}
