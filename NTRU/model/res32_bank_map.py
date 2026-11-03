"""Verify that RES32 (q8380417, N = 256) needs no new bank map.

RES32 uses the FFT-style logical layout of spec 03.4 with LIMBS = 2: coefficient c
occupies word16 addresses k = 2c (low half) and 2c + 1 (high half), and the fixed
physical map of spec 03.3:

    bank(k) = (k & 63) ^ ((k >> 2) & 0x30) ^ ((k >> 4) & 0x30),  row(k) = k >> 6

Since bank(2c + 1) = bank(2c) ^ 1, the two halves always sit in a bank pair
(2s, 2s + 1) of the same row: a 32-bit "superbank" s = bank(2c) >> 1.

One cycle issues 4 paired frames (4 groups of 4 coefficients in the order of
model/ntt_banked_supply.groups) = 16 coefficients, 16 modmul (one per tile).
Check: every cycle's 16 coefficients hit 16 distinct superbanks, for all 4 paired
passes of N = 256, forward and inverse orders; and the 4 root bundles of a cycle
hit 4 distinct bundle banks with bundle bank = g mod 4.

Run: python model/res32_bank_map.py
"""
import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
_spec = importlib.util.spec_from_file_location("nbs", ROOT / "model" / "ntt_banked_supply.py")
nbs = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(nbs)

LOGN, N = 8, 256
FRAMES_PER_CYCLE = 4


def bank(k):
    return (k & 63) ^ ((k >> 2) & 0x30) ^ ((k >> 4) & 0x30)


def superbank(c):
    return bank(2 * c) >> 1


def main():
    assert all(bank(2 * c + 1) == bank(2 * c) ^ 1 for c in range(4096))
    assert all((2 * c) >> 6 == (2 * c + 1) >> 6 for c in range(4096))
    assert len({(superbank(c), (2 * c) >> 6) for c in range(4096)}) == 4096
    print("PASS: halves of each RES32 coefficient share a row in a bank pair; (superbank,row) is a bijection.")

    worst_data, worst_root, cycles = 0, 0, 0
    for p in range(0, LOGN - 1, 2):
        for inverse in (False, True):
            gs = nbs.groups(LOGN, p, True, inverse=inverse)
            for s in range(0, len(gs), FRAMES_PER_CYCLE):
                frames = gs[s:s + FRAMES_PER_CYCLE]
                coeffs = [c for g in frames for c in g]
                cnt = {}
                for c in coeffs:
                    cnt[superbank(c)] = cnt.get(superbank(c), 0) + 1
                worst_data = max(worst_data, max(cnt.values()))
                ids = sorted({nbs.root_request(g, p, True, N)[0] for g in frames})
                rcnt = {}
                for g in ids:
                    rcnt[g % 4] = rcnt.get(g % 4, 0) + 1
                worst_root = max(worst_root, max(rcnt.values()))
                cycles += 1
    print(f"Checked {cycles} cycles (4 passes × fwd/inv): worst superbank reads/cycle = {worst_data}, "
          f"worst root-bundle reads/bank/cycle (4 banks, g mod 4) = {worst_root}")
    assert worst_data == 1 and worst_root == 1
    print("PASS: RES32 N256 paired schedule is conflict-free with the spec 1.0 physical map.")

    # CR-D: second job placed at word offset (RES16: k = N + c; RES32: k = 2N + 2c).
    # bank() is linear over GF(2) and the offset bits are disjoint from in-job bits,
    # so the offset XORs a constant into every bank index. Check explicitly.
    worst = 0
    for logn in range(6, 11):
        n = 1 << logn
        for base in (0, n):
            for p in range(0, logn - 1, 2):
                gs = nbs.groups(logn, p, True)
                for s in range(0, len(gs), 16):           # RES16: 16 paired frames per cycle
                    ks = [base + c for g in gs[s:s + 16] for c in g]
                    cnt = {}
                    for k in ks:
                        cnt[bank(k)] = cnt.get(bank(k), 0) + 1
                    worst = max(worst, max(cnt.values()))
    for base in (0, 2 * N):
        for p in range(0, LOGN - 1, 2):
            gs = nbs.groups(LOGN, p, True)
            for s in range(0, len(gs), FRAMES_PER_CYCLE):
                ks = [base + 2 * c for g in gs[s:s + FRAMES_PER_CYCLE] for c in g]
                cnt = {}
                for k in ks:
                    cnt[bank(k) >> 1] = cnt.get(bank(k) >> 1, 0) + 1
                worst = max(worst, max(cnt.values()))
    assert worst == 1
    print("PASS: CR-D job offsets (RES16 N64..1024 at k = N; RES32 N256 at k = 2N) keep paired "
          "frames conflict-free (worst reads/bank/cycle = 1).")
    all_sizes()
    base_offsets()
    multi_job_small()


def base_offsets():
    """Spec 2.0: a command carries a base word address per store. If the base is a multiple of the
    footprint rounded up to a power of two (at least 8 words), the base bits are disjoint from the
    in-footprint bits, bank() only XORs a constant, and every read group keeps its conflict count.
    Check it for RES16 (N 8..1024) and RES32 (N 4..1024), paired passes, every legal base."""
    def worst(addrs_per_cycle, sb):
        w = 0
        for ks in addrs_per_cycle:
            cnt = {}
            for k in ks:
                b = bank(k) >> 1 if sb else bank(k)
                cnt[b] = cnt.get(b, 0) + 1
            w = max(w, max(cnt.values()))
        return w

    checked = 0
    for limbs, logns in ((1, range(3, 11)), (2, range(2, 11))):
        for logn in logns:
            n = 1 << logn
            foot = max(8, 1 << (n * limbs - 1).bit_length())
            per_cycle = 16 if limbs == 1 else FRAMES_PER_CYCLE
            groups = [g for p in range(0, logn - 1, 2) for g in nbs.groups(logn, p, True)]
            cycles = [groups[s:s + per_cycle] for s in range(0, len(groups), per_cycle)]
            ref = worst([[limbs * c for g in cyc for c in g] for cyc in cycles], limbs == 2)
            for base in range(0, 8192 - foot + 1, foot):
                got = worst([[base + limbs * c for g in cyc for c in g] for cyc in cycles], limbs == 2)
                assert got == ref, (limbs, n, base, got, ref)
                checked += 1
    print(f"PASS: {checked} (layout, N, base) cases: a base aligned to the power-of-two footprint keeps the "
          "bank-conflict count of base 0.")


def multi_job_small():
    """Spec 2.0, profile 3, N < 64: up to min(8, 64/N) polynomials (one prime each) in one command,
    polynomial j at words 2(j*N + i). Frames of all jobs are issued together, 4 frames (16
    coefficients) per read group in job order. Report the worst reads per 32-bit superbank."""
    print("\nRES32 nhiều đa thức, N < 64 (mỗi nhóm đọc 16 hệ số):")
    print("| N | Số đa thức | Nhóm đọc | Nhóm phải đọc hai lượt | Đọc tối đa/siêu bank |")
    print("|---:|---:|---:|---:|---:|")
    out = {}
    for logn in range(2, 6):
        n = 1 << logn
        jobs = min(8, 64 // n)
        bad = tot = worst = 0
        for inverse in (False, True):
            passes = [(p, True) for p in range(0, logn - 1, 2)] + ([(logn - 1, False)] if logn % 2 else [])
            for p, paired in passes:
                frames = [[j * n + c for c in g] for j in range(jobs)
                          for g in nbs.groups(logn, p, paired, inverse=inverse)]
                for s in range(0, len(frames), 4):
                    cnt = {}
                    for c in (c for f in frames[s:s + 4] for c in f):
                        cnt[superbank(c)] = cnt.get(superbank(c), 0) + 1
                    tot += 1
                    bad += max(cnt.values()) > 1
                    worst = max(worst, max(cnt.values()))
        out[n] = (jobs, tot, bad, worst)
        print(f"| {n} | {jobs} | {tot} | {bad} | {worst} |")
    return out


def all_sizes():
    """Same layout for N = 2..1024 (for 31-bit primes of NTRUGen).

    Every cycle reads 16 coefficients: 4 paired frames, or, in the single-layer last pass
    of an odd logn, 4 groups of two butterflies. N = 2 is one butterfly on coefficients
    0 and 1, which sit in superbanks 0 and 1.
    """
    assert superbank(0) != superbank(1)
    print("\nRES32, mọi N (xuôi + ngược; lượt một tầng cuối khi log N lẻ; N = 2 là một butterfly, không xung đột):")
    print("| N | Chu kỳ | Chu kỳ xung đột | Đọc tối đa/siêu bank | Root tối đa/bank |")
    print("|---:|---:|---:|---:|---:|")
    for logn in range(2, 11):
        n = 1 << logn
        bad = tot = wd = wr = 0
        for inverse in (False, True):
            passes = [(p, True, FRAMES_PER_CYCLE) for p in range(0, logn - 1, 2)]
            if logn % 2:
                passes.append((logn - 1, False, 4))
            for p, paired, per_cycle in passes:
                gs = nbs.groups(logn, p, paired, inverse=inverse)
                for s in range(0, len(gs), per_cycle):
                    frames = gs[s:s + per_cycle]
                    cnt, rcnt = {}, {}
                    for c in (c for g in frames for c in g):
                        cnt[superbank(c)] = cnt.get(superbank(c), 0) + 1
                    for g in {r for f in frames for r in nbs.root_request(f, p, paired, n)}:
                        rcnt[g % 4] = rcnt.get(g % 4, 0) + 1
                    tot += 1
                    bad += max(cnt.values()) > 1
                    wd, wr = max(wd, max(cnt.values())), max(wr, max(rcnt.values()))
        print(f"| {n} | {tot} | {bad} ({100 * bad / tot:.0f}%) | {wd} | {wr} |")


if __name__ == "__main__":
    main()
