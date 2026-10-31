"""Check the spec 2.0 kernel assets against the pseudo-code of 01_so_hoc_kernel.md and independent oracles.

  FFT 64 bit NTRUGen:  the spec pseudo-code (Python, wrap-64 arithmetic, GM_TAB from the .mem asset)
                       must reproduce every C output in kernel/fft_ntrugen.jsonl
  NTT q = 8380417:     every NTT output equals direct evaluation a(psi^(2*brv8(j)+1)) at position j;
                       NTT(INTT(x)) = x; TOMONT and MODMUL by definition
  NTT prime 31 bit:    the spec pseudo-code (halving at every layer, no final factor) reproduces every
                       C output in kernel/ntt_prime31.jsonl
  plus SHA-256 of every file listed in kernel/manifest.json

Run: python scripts/check_spec2_kernel_assets.py
"""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "spec" / "FlexTransform" / "2.0" / "assets"
M64 = (1 << 64) - 1
R32 = 1 << 32


def s64(x):
    x &= M64
    return x - (1 << 64) if x >> 63 else x


# --- FFT 64 bit NTRUGen, as written in 01 ---------------------------------------------------------

def fmul(x, y):
    return (s64(x) * s64(y)) >> 32 & M64              # floor(x*y / 2^32), wrap 64


def fhalf(v):
    return (s64(v + 1) >> 1) & M64                     # wrap(v + 1) then arithmetic shift


def cmul3(sr, si, yr, yi):
    z0, z1 = fmul(sr, yr), fmul(si, yi)
    z2 = fmul((sr + si) & M64, (yr + yi) & M64)
    return (z0 - z1) & M64, (z2 - z0 - z1) & M64


def fft_ntrugen(a, logn, gm):
    a, hn = list(a), 1 << (logn - 1)
    t = hn
    for lm in range(1, logn):
        m, ht = 1 << lm, t >> 1
        for i in range(m >> 1):
            sr, si = gm[m + i]
            for j in range(i * t, i * t + ht):
                yr, yi = cmul3(sr, si, a[j + ht], a[j + ht + hn])
                xr, xi = a[j], a[j + hn]
                a[j], a[j + hn] = (xr + yr) & M64, (xi + yi) & M64
                a[j + ht], a[j + ht + hn] = (xr - yr) & M64, (xi - yi) & M64
        t = ht
    return a


def ifft_ntrugen(a, logn, gm):
    a, hn = list(a), 1 << (logn - 1)
    ht = 1
    for lm in range(logn - 1, 0, -1):
        m, t = 1 << lm, ht << 1
        for i in range(m >> 1):
            sr, si = gm[m + i][0], (-gm[m + i][1]) & M64                 # conjugate root
            for j in range(i * t, i * t + ht):
                xr, xi, yr, yi = a[j], a[j + hn], a[j + ht], a[j + ht + hn]
                a[j], a[j + hn] = fhalf(xr + yr), fhalf(xi + yi)
                a[j + ht], a[j + ht + hn] = cmul3(sr, si, fhalf(xr - yr), fhalf(xi - yi))
        ht = t
    return a


# --- NTT ----------------------------------------------------------------------------------------

def mont(a, b, q):
    return a * b * pow(R32, -1, q) % q


def ntt_fwd(a, gm, q):
    a, n = list(a), len(a)
    stride, groups = n // 2, 1
    while stride >= 1:
        for g in range(groups):
            for off in range(stride):
                i = 2 * g * stride + off
                j = i + stride
                t = mont(a[j], gm[groups + g], q)
                a[i], a[j] = (a[i] + t) % q, (a[i] - t) % q
        stride, groups = stride // 2, groups * 2
    return a


def ntt_inv(a, igm, q, halve, final):
    a, n = list(a), len(a)
    stride = 1
    while stride <= n // 2:
        groups = n // (2 * stride)
        for g in range(groups):
            for off in range(stride):
                i = 2 * g * stride + off
                j = i + stride
                s, d = (a[i] + a[j]) % q, (a[i] - a[j]) % q
                a[i] = (s + (q if s & 1 else 0)) >> 1 if halve else s
                a[j] = mont(d, igm[groups + g], q)
        stride *= 2
    return [mont(x, final, q) for x in a] if final is not None else a


def brv(x, bits):
    return int(format(x, f"0{bits}b")[::-1], 2)


def ints(v):
    return [int(x, 16) for x in v]


def records(name):
    for line in (ASSETS / "kernel" / name).read_text(encoding="ascii").splitlines():
        yield json.loads(line)


def check_small_q_r32():
    """01 section 3.0: profile 0, 1 on Mont32 with GM32 = GM16 * 2^16 give the 1.0 results (R = 2^16)."""
    import random
    rng = random.Random(20261101)
    one = ROOT / "spec" / "FlexTransform" / "1.0" / "assets"
    count = 0
    for q, logn, min_stride in ((12289, 10, 1), (3329, 8, 2)):
        gm16 = [int(x, 16) for x in (one / f"ntt_q{q}_forward.mem").read_text().split()]
        igm16 = [int(x, 16) for x in (one / f"ntt_q{q}_inverse.mem").read_text().split()]
        gm32 = [w * (1 << 16) % q for w in gm16]
        igm32 = [w * (1 << 16) % q for w in igm16]
        n = 1 << logn
        L = logn - 1 if min_stride == 2 else logn

        def m(a, b, rb):
            return a * b * pow(1 << rb, -1, q) % q

        def fwd(a, gm, rb):
            a, stride, groups = list(a), n // 2, 1
            while stride >= min_stride:
                for g in range(groups):
                    for off in range(stride):
                        i = 2 * g * stride + off
                        t = m(a[i + stride], gm[groups + g], rb)
                        a[i], a[i + stride] = (a[i] + t) % q, (a[i] - t) % q
                stride, groups = stride // 2, groups * 2
            return a

        def inv(a, igm, rb, final):
            a, stride = list(a), min_stride
            while stride <= n // 2:
                groups = n // (2 * stride)
                for g in range(groups):
                    for off in range(stride):
                        i = 2 * g * stride + off
                        s, d = (a[i] + a[i + stride]) % q, (a[i] - a[i + stride]) % q
                        a[i], a[i + stride] = s, m(d, igm[groups + g], rb)
                stride *= 2
            return [m(x, final, rb) for x in a]

        f16 = (1 << 16) * pow(2 ** L, -1, q) % q            # 1.0 factorbar
        f32 = (1 << 32) * pow(2 ** L, -1, q) % q            # 3.0
        c48 = pow(2, 48, q)
        for _ in range(4):
            a = [rng.randrange(q) for _ in range(n)]
            b = [rng.randrange(q) for _ in range(n)]
            assert fwd(a, gm32, 32) == fwd(a, gm16, 16)
            assert inv(a, igm32, 32, f32) == inv(a, igm16, 16, f16)
            assert [m(x, c48, 32) for x in a] == [x * (1 << 16) % q for x in a]                # 0x7
            assert [m(m(x, y, 32), c48, 32) for x, y in zip(a, b)] == [m(x, y, 16) for x, y in zip(a, b)]  # 0x8
            count += 1
    return count


def main():
    n_small = check_small_q_r32()
    man = json.loads((ASSETS / "kernel" / "manifest.json").read_text(encoding="utf-8"))
    for rel, h in man["sha256"].items():
        assert hashlib.sha256((ASSETS / rel).read_bytes()).hexdigest() == h, rel

    gm_fft = [(int(l[:16], 16), int(l[16:], 16)) for l in (ASSETS / "fft_ntrugen_q32_32.mem").read_text().split()]
    n_fft = 0
    for c in records("fft_ntrugen.jsonl"):
        a, logn = ints(c["input"][0]), c["logn"]
        got = fft_ntrugen(a, logn, gm_fft) if c["op"] == "FFT" else ifft_ntrugen(a, logn, gm_fft)
        assert got == ints(c["expected"][0]), (c["op"], logn)
        n_fft += 1

    q = man["constants"]["q8380417"]["q"]
    psi, final = man["constants"]["q8380417"]["psi"], man["constants"]["q8380417"]["intt_final_factor"]
    gm2 = ints((ASSETS / "ntt_q8380417_forward.mem").read_text().split())
    igm2 = ints((ASSETS / "ntt_q8380417_inverse.mem").read_text().split())
    n_q2 = 0
    for c in records("ntt_q8380417.jsonl"):
        for k, (x, e) in enumerate(zip(c["input"], c["expected"])):
            x, e = ints(x), ints(e)
            if c["op"] == "NTT":
                ev = [sum(xi * pow(psi, (2 * brv(j, 8) + 1) * i, q) for i, xi in enumerate(x)) % q for j in range(256)]
                assert e == ev and ntt_inv(e, igm2, q, False, final) == x
            elif c["op"] == "INTT":
                assert ntt_fwd(e, gm2, q) == x
            elif c["op"] == "TOMONT":
                assert e == [v * R32 % q for v in x]
            else:
                assert e == [v * w * pow(R32, -1, q) % q for v, w in zip(x, ints(c["input_b"][k]))]
        n_q2 += 1

    primes, n_p = {}, 0
    for c in records("ntt_prime31.jsonl"):
        if c["kind"] == "nap_prime":
            primes[c["id"]] = c
            continue
        job_primes = [primes[i] for i in c["primes"]] if "primes" in c else [primes[c["prime"]]] * c["jobs"]
        if "primes" in c:                                  # multi-slot: slots (khe_dau + j) mod 16, regions disjoint
            assert [pr["slot"] for pr in job_primes] == [(c["khe_dau"] + j) % 16 for j in range(c["jobs"])]
            n = 1 << c["logn"]
            assert c["jobs"] <= min(8, 64 // n) and len({pr["p"] for pr in job_primes}) == c["jobs"]
            g = max(1, n // 2 - 1)
            spans = sorted((pr["base"], pr["base"] + g) for pr in job_primes)
            assert all(a[1] <= b[0] for a, b in zip(spans, spans[1:])) and spans[-1][1] <= 511
        for k, (x, e) in enumerate(zip(c["input"], c["expected"])):
            pr = job_primes[k]
            p, r2 = int(pr["p"], 16), int(pr["r2"], 16)
            assert (int(pr["p0i"], 16) * p) % R32 == R32 - 1 and r2 == pow(2, 64, p)
            x, e = ints(x), ints(e)
            if c["op"] == "NTT":
                assert ntt_fwd(x, ints(pr["gm"]), p) == e
            elif c["op"] == "INTT":
                assert ntt_inv(x, ints(pr["igm"]), p, True, None) == e
            elif c["op"] == "TOMONT":
                assert e == [v * R32 % p for v in x]
            else:
                assert e == [mont(v, w, p) for v, w in zip(x, ints(c["input_b"][k]))]
        n_p += 1
    print(f"PASS: FFT NTRUGen {n_fft} ca (mã giả của spec = C); q8380417 {n_q2} ca (khớp đánh giá đa thức trực tiếp "
          f"và phép ngược); prime 31 bit {n_p} ca (mã giả của spec = C); hash khớp; profile 0, 1 trên R = 2^32 "
          f"(01 mục 3.0) {n_small} bộ ngẫu nhiên khớp 1.0 ở NTT, NTT ngược, 0x7, 0x8.")


if __name__ == "__main__":
    main()
