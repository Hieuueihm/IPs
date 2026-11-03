"""Check paper-note arithmetic; not RTL simulation. No files are modified.

Run: python scripts/check_research_models.py
"""
from fractions import Fraction
from math import ceil, isqrt
from random import Random


def signed_limbs(value, width, limb_width=32):
    assert width % limb_width == 0
    radix = 1 << limb_width
    encoded = value % (1 << width)
    limbs = [(encoded >> offset) & (radix - 1)
             for offset in range(0, width, limb_width)]
    if limbs[-1] & (radix >> 1):
        limbs[-1] -= radix
    return limbs


def schoolbook_signed(a, b, width):
    return sum((ai * bj) << (32 * (i + j))
               for i, ai in enumerate(signed_limbs(a, width))
               for j, bj in enumerate(signed_limbs(b, width)))


def check_signed_examples():
    rng = Random(20261021)
    count = 0
    for width in (64, 128):
        lower, upper = -(1 << (width - 1)), (1 << (width - 1)) - 1
        bounds = (lower, lower + 1, -1, 0, 1, upper - 1, upper)
        pairs = [(a, b) for a in bounds for b in bounds]
        pairs += [(rng.randrange(lower, upper + 1), rng.randrange(lower, upper + 1))
                  for _ in range(100)]
        for a, b in pairs:
            assert schoolbook_signed(a, b, width) == a * b
            count += 1
    print(f"Signed schoolbook: {count} boundary/random pairs passed.")


def is_prime_by_trial_division(q):
    if q < 2:
        return False
    if q % 2 == 0:
        return q == 2
    return all(q % d for d in range(3, isqrt(q) + 1, 2))


def check_ntt_context_examples():
    n = 1024
    for q in (12289, 2013265921):
        assert is_prime_by_trial_division(q)
        assert (q - 1) % (2 * n) == 0
        for candidate in range(2, 1000):
            psi = pow(candidate, (q - 1) // (2 * n), q)
            # For power-of-two n this establishes exact order 2*n.
            if pow(psi, n, q) == q - 1:
                assert pow(psi, 2 * n, q) == 1
                print(f"NTT: q={q}, bits={q.bit_length()}, "
                      f"(q-1)/(2N)={(q-1)//(2*n)}, psi={psi}.")
                break
        else:
            raise AssertionError("No example root found.")


def check_p1_cycle_bounds():
    rows = [("FFT", 512, 9, 1, 2430),
            ("ML-DSA", 256, 8, 2, 624),
            ("ML-KEM", 256, 7, 4, 322)]
    for name, n, stages, rate, reported in rows:
        work = n // 2 * stages
        issue_bound = ceil(Fraction(work, rate))
        assert reported >= issue_bound
        print(f"P1 {name}: BF={work}, ideal_issue={issue_bound}, "
              f"reported={reported}, difference={reported-issue_bound}.")
    print(f"P1 LUT overhead: {(3716-2300)/2300:.2%}.")
    print(f"P1 FF overhead: {(2400-1898)/1898:.2%}.")


def print_capacity_model():
    k, bandwidth = 32, 512
    print("Model K=32 slots 32x32; data R/W each 512 bit/cycle.")
    print("mode | partials/BF | compute BF/cycle | data BF/cycle | min")
    for name, width, complex_mode in [
        ("FFT64", 64, True), ("FFT128", 128, True),
        ("NTT16-study", 16, False), ("NTT32-study", 32, False),
        ("NTT64-study", 64, False),
    ]:
        partials = ceil(Fraction(width, 32)) ** 2 * (4 if complex_mode else 1)
        data_bits = width * (4 if complex_mode else 2)
        compute_rate = Fraction(k, partials)
        data_rate = Fraction(bandwidth, data_bits)
        print(f"{name} | {partials} | {compute_rate} | {data_rate} | "
              f"{min(compute_rate, data_rate)}")
    print("NTT excludes reducer capacity/cost; all rows exclude routing/hazards.")
    print("Twiddle traffic is separate. No FPGA performance has been measured.")


if __name__ == "__main__":
    check_signed_examples()
    check_ntt_context_examples()
    check_p1_cycle_bounds()
    print_capacity_model()
