"""NTT modulo a loaded prime (profile 3) on the minimal core (planning model, before RTL).

The core's NTT (model/ntt_core_sched.py: tiles, network, banks, pipeline; model/ntt_core_overlap.py: layer overlap) does
not depend on q except through the tile constants (q, q') and the root table. Profile 3 runs it with q and the root packs
of a loaded slot, for every odd prime q < 2^31, N = 2 .. 1024, and an incomplete transform that stops hmin = 0, 1, 2
layers early (the last layer has distance 2^hmin; the table then has N / 2^hmin roots), as ML-KEM does with hmin = 1.

Root table of a slot (the convention of NTRUGen's mp_mkgmigm and of the fixed profiles): with N' = N / 2^hmin and psi a
primitive 2N'-th root of unity mod q,
    gm[rev(u)]  = psi^u · R mod q,  igm[rev(u)] = (1/2) · psi^(-u) · R mod q,  u = 0 .. N' - 1, R = 2^32
(rev over log2 N' bits). The inverse halves every layer, so it is the exact inverse (factor 1 / N').

Checks:
  - the 323 NTRUGen primes, logn 1..10, both directions, against the C reference (mp_NTT / mp_iNTT) dumped by
    model/ntrugen_mp31_harness.c: by the barrier schedule for every prime, and by the overlap schedule (the one the RTL
    runs) for a spread of primes;
  - the moduli of the survey (study/results/pqc_moduli.md) with their N and hmin, against an independent reference: block
    k of the forward output is a mod (X^(2^hmin) - psi^(2 rev(k) + 1)) (evaluation definition, not a butterfly loop),
    and the inverse must give the input back;
  - the overlap plans for every (logn, hmin, direction) profile 3 can run, written to
    study/results/ntt_prime_overlap.json for scripts/gen_ntt_core.py.

Run: python model/ntt_prime_core.py   (writes study/results/ntt_prime_core.md)
"""
import importlib.util
import json
import random
from array import array
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _load(name, file):
    s = importlib.util.spec_from_file_location(name, ROOT / "model" / file)
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m


sc = _load("ntt_core_sched", "ntt_core_sched.py")
ov = _load("ntt_core_overlap", "ntt_core_overlap.py")
R = 1 << 32
# (application, q, logn, hmin): the survey's NTT moduli with power-of-two rings
SURVEY = [("ML-KEM", 3329, 8, 1), ("ML-DSA", 8380417, 8, 0), ("FN-DSA", 12289, 9, 0), ("FN-DSA", 12289, 10, 0),
          ("HAWK ký", 18433, 9, 0), ("HAWK ký", 18433, 10, 0), ("HAETAE", 64513, 8, 0), ("Kyber vòng 1", 7681, 8, 0),
          ("Saber RNS", 10753, 8, 0), ("Saber qua NTT", 25166081, 8, 1), ("LightSaber qua NTT", 20972417, 8, 2)]


def rev(u, bits):
    return int(f"{u:0{bits}b}"[::-1], 2) if bits else 0


def psi_of(q, order):
    """A primitive `order`-th root of unity mod q (order a power of two dividing q - 1)."""
    assert (q - 1) % order == 0
    for g in range(2, q):
        x = pow(g, (q - 1) // order, q)
        if pow(x, order // 2, q) == q - 1:
            return x
    raise ValueError


def tables(q, logn, hmin):
    lp = logn - hmin
    n1 = 1 << lp
    psi = psi_of(q, 2 * n1)
    ipsi, half = pow(psi, -1, q), pow(2, -1, q)
    gm, igm = [0] * n1, [0] * n1
    for u in range(n1):
        gm[rev(u, lp)] = pow(psi, u, q) * R % q
        igm[rev(u, lp)] = half * pow(ipsi, u, q) * R % q
    return gm, igm


def ref_forward(a, q, logn, hmin):
    """Evaluation definition: block k = a mod (X^b - psi^(2 rev(k) + 1)), b = 2^hmin."""
    lp = logn - hmin
    n1, b = 1 << lp, 1 << hmin
    psi = psi_of(q, 2 * n1)
    out = []
    for k in range(n1):
        z = pow(psi, 2 * rev(k, lp) + 1, q)
        blk = [0] * b
        for i, c in enumerate(a):                  # X^i = X^(i mod b) * z^(i div b) mod (X^b - z)
            blk[i % b] = (blk[i % b] + c * pow(z, i // b, q)) % q
        out.append(blk)
    # the butterfly order keeps block k in coefficients k * b .. k * b + b - 1
    return [c for blk in out for c in blk]


class Tabs:
    def __init__(self, q, gm, igm):
        self.gm, self.igm = {q: gm}, {q: igm}


def with_hmin(hmin, fn, *args):
    """Run a schedule function with the last layer at distance 2^hmin (profile 3), restoring the fixed-profile rule."""
    mods = (sc, ov.sc)                              # model/ntt_core_overlap.py loads its own copy of the schedule
    old = [m.min_stride for m in mods]
    for m in mods:
        m.min_stride = lambda q, logn: 1 << hmin
    try:
        return fn(*args)
    finally:
        for m, f in zip(mods, old):
            m.min_stride = f


def overlap_run(q, logn, inverse, a, tabs, hmin):
    layers, events = with_hmin(hmin, ov.plan, q, logn, inverse)
    res, cyc = ov.simulate(q, logn, inverse, a, tabs, events)
    return res, cyc, layers


def ntrugen():
    w = array("I")
    w.frombytes((ROOT / "study" / "build" / "ntrugen_mp31" / "dump.bin").read_bytes())
    pos = 0

    def take(k):
        nonlocal pos
        pos += k
        return w[pos - k:pos].tolist()

    for pi in range(323):
        p, _, _, _ = take(4)
        take(67 * 3)
        for logn in range(1, 11):
            gm, igm, a, nref, b, iref = (take(1 << logn) for _ in range(6))
            yield pi, p, logn, gm, igm, a, nref, b, iref


def main():
    lines = ["# NTT modulo prime nạp được (profile 3) trên lõi tối thiểu (mô hình trước RTL)\n",
             "Mô hình: [model/ntt_prime_core.py](../../model/ntt_prime_core.py). Lịch NTT của lõi (chồng tầng) chạy với q, q′ "
             "và bảng root của một khe; bảng theo quy ước `mp_mkgmigm` của NTRUGen, ngược chia đôi mỗi tầng.\n"]
    # 1. NTRUGen primes against C
    n_bar = n_ov = 0
    spread = {0, 1, 2, 80, 161, 242, 322}
    cyc_ov = {}
    for pi, p, logn, gm, igm, a, nref, b, iref in ntrugen():
        t = Tabs(p, gm, igm)
        r1, _, _ = with_hmin(0, sc.run, p, logn, False, a, t)
        r2, _, _ = with_hmin(0, sc.run, p, logn, True, b, t)
        assert r1 == nref and r2 == iref, (pi, logn)
        n_bar += 2
        if pi in spread:
            o1, c1, _ = overlap_run(p, logn, False, a, t, 0)
            o2, c2, _ = overlap_run(p, logn, True, b, t, 0)
            assert o1 == nref and o2 == iref, (pi, logn, "overlap")
            n_ov += 2
            cyc_ov[logn] = (c1, c2)
    lines.append(f"- 323 prime của NTRUGen, logn 1..10, hai chiều: {n_bar} NTT khớp `mp_NTT` / `mp_iNTT` theo lịch rào chắn; "
                 f"{n_ov} khớp theo lịch chồng tầng (lịch RTL chạy) trên {len(spread)} prime trải đều.\n")
    lines.append("| N | Chu kỳ xuôi / ngược (chồng tầng) |")
    lines.append("|---:|---:|")
    for logn in range(1, 11):
        lines.append(f"| {1 << logn} | {cyc_ov[logn][0]} / {cyc_ov[logn][1]} |")
    # 2. survey moduli against the evaluation definition
    lines.append("\n## Modulus của khảo sát, so với định nghĩa (đánh giá đa thức), và chiều ngược trả lại đầu vào\n")
    lines.append("| Ứng dụng | q | N | Tầng bỏ | Xuôi khớp | Ngược trả lại | Chu kỳ xuôi / ngược |")
    lines.append("|---|---:|---:|---:|---|---|---:|")
    rng = random.Random(20261101)
    for app, q, logn, hmin in SURVEY:
        gm, igm = tables(q, logn, hmin)
        t = Tabs(q, gm, igm)
        ok_f = ok_i = True
        for _ in range(3):
            a = [rng.randrange(q) for _ in range(1 << logn)]
            f, c1, _ = overlap_run(q, logn, False, a, t, hmin)
            ok_f &= f == ref_forward(a, q, logn, hmin)
            back, c2, _ = overlap_run(q, logn, True, f, t, hmin)
            ok_i &= back == a
        assert ok_f and ok_i, (app, q, logn, hmin)
        lines.append(f"| {app} | {q} | {1 << logn} | {hmin} | có | có | {c1} / {c2} |")
    # 3. overlap plans for every (logn, hmin, direction) of profile 3
    plans = {}
    q = 2147473409
    for hmin in (0, 1, 2):
        for logn in range(max(1, hmin + 1), 11):
            for op in (5, 6):
                layers, _ = with_hmin(hmin, ov.plan, q, logn, op == 6)
                plans[f"{logn},{op},{hmin}"] = layers
    (ROOT / "study" / "results" / "ntt_prime_overlap.json").write_text(json.dumps(plans, indent=1) + "\n")
    lines.append(f"\nKế hoạch chồng tầng cho mọi (logn, số tầng bỏ, chiều) của profile 3: {len(plans)} "
                 "([study/results/ntt_prime_overlap.json](ntt_prime_overlap.json)).")
    (ROOT / "study" / "results" / "ntt_prime_core.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
