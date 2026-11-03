"""Exact operation-level checks for FFT/NTT co-design.

Run: python model/arithmetic_reassessment.py
Writes only study/results/arithmetic_reassessment.{json,md}.
No RTL synthesis, clock, latency or memory scheduling is modeled.
"""
from fractions import Fraction
from math import ceil, isqrt
from pathlib import Path
from random import Random
import json

ROOT = Path(__file__).resolve().parent.parent
SEED = 20261025
PROFILES = [
    (3329, 16, "plus"),
    (12289, 16, "plus"),
    (8380417, 32, "minus"),
    (2013265921, 32, "minus"),
    (4293918721, 32, "minus"),
]


def naf(n):
    """Signed non-adjacent constant expansion: sum(sign*2**bit)."""
    terms = []
    bit = 0
    while n:
        if n & 1:
            digit = 2 - n % 4
            terms.append((digit, bit))
            n -= digit
        n //= 2
        bit += 1
    return terms


def constant_mul(x, terms):
    return sum(sign * (x << bit) for sign, bit in terms)


def rne(value, shift):
    if not shift:
        return value
    quotient, remainder = divmod(value, 1 << shift)
    half = 1 << (shift - 1)
    return quotient + int(remainder > half or
                          (remainder == half and quotient & 1))


def signed_wrap(x, width):
    u = x % (1 << width)
    return u - (1 << width) if u >= (1 << (width - 1)) else u


def complex_four(a, b, c, d):
    return a*c - b*d, a*d + b*c


def complex_three_twiddle(a, b, c, d, width, twiddle_width):
    """3 products plus an exact correction for the overflowing data sum."""
    full_sum = a + b
    short_sum = signed_wrap(full_sum, width)
    extra = (full_sum - short_sum) // (1 << width)
    assert extra in (-1, 0, 1)
    assert -(1 << (twiddle_width-1)) <= c+d < (1 << (twiddle_width-1))
    assert -(1 << (twiddle_width-1)) <= d-c < (1 << (twiddle_width-1))
    p = short_sum*c + extra*(c << width)
    q = b*(c+d)
    r = a*(d-c)
    return p-q, p+r, extra


def mont_from_t(t, q, word, polarity, use_constant_logic=True):
    radix = 1 << word
    assert 0 <= t < q*radix
    inv = pow(q, -1, radix)
    coefficient = (-inv) % radix if polarity == "plus" else inv
    if use_constant_logic:
        m = constant_mul(t % radix, naf(coefficient)) % radix
        mq = constant_mul(m, naf(q))
    else:
        m = ((t % radix)*coefficient) % radix
        mq = m*q
    value = t+mq if polarity == "plus" else t-mq
    assert value % radix == 0
    u = value // radix
    if polarity == "plus":
        assert 0 <= u < 2*q
        out = u-q if u >= q else u
    else:
        assert -q < u < q
        out = u+q if u < 0 else u
    assert out == (t * pow(radix, -1, q)) % q
    return out


def barrett_t(t, q):
    shift = 2*q.bit_length()
    assert 0 <= t < 1 << shift
    mu = (1 << shift)//q
    quotient = (t*mu) >> shift
    remainder = t - quotient*q
    assert 0 <= remainder < 2*q
    out = remainder-q if remainder >= q else remainder
    assert out == t % q
    return out


def shoup_full(x, w, q, word):
    radix = 1 << word
    assert 0 <= x < q < radix and 0 <= w < q
    wp = w*radix//q
    quotient = (x*wp)//radix
    remainder = x*w - quotient*q
    assert 0 <= remainder < 2*q
    out = remainder-q if remainder >= q else remainder
    assert out == x*w % q
    return out, remainder


def half_mod(x, q):
    assert 0 <= x < q and q & 1
    out = (x + (x & 1)*q)//2
    assert out == x*pow(2, -1, q) % q
    return out


def bit_reverse(values):
    n = len(values)
    bits = n.bit_length()-1
    return [values[int(f"{i:0{bits}b}"[::-1], 2)] for i in range(n)]


def root_2n(q, n):
    assert (q-1) % (2*n) == 0
    for a in range(2, 1000):
        root = pow(a, (q-1)//(2*n), q)
        if pow(root, n, q) == q-1:
            return root
    raise AssertionError("Root not found")


def ntt_ct(values, omega, q, word, polarity):
    """Natural I/O using input bit reversal; canonical data, Montgomery roots."""
    a = bit_reverse(values)
    n = len(a)
    radix = 1 << word
    span = 2
    while span <= n:
        for start in range(0, n, span):
            for j in range(span//2):
                wr = pow(omega, j*n//span, q)*radix % q
                left = a[start+j]
                right = mont_from_t(a[start+j+span//2]*wr, q, word, polarity)
                a[start+j] = (left+right) % q
                a[start+j+span//2] = (left-right) % q
        span *= 2
    return a


def intt_gs_half(values, omega_inverse, q, word, polarity):
    """Inverse DIF with exact modular halving every stage; natural output."""
    a = list(values)
    n = len(a)
    radix = 1 << word
    span = n
    while span >= 2:
        for start in range(0, n, span):
            for j in range(span//2):
                left, right = a[start+j], a[start+j+span//2]
                wr = pow(omega_inverse, j*n//span, q)*radix % q
                product = mont_from_t(((left-right) % q)*wr, q, word, polarity)
                a[start+j] = half_mod((left+right) % q, q)
                a[start+j+span//2] = half_mod(product, q)
        span //= 2
    return bit_reverse(a)


def dft_mod(a, omega, q):
    n = len(a)
    return [sum(a[j]*pow(omega, j*k, q) for j in range(n)) % q
            for k in range(n)]


def pair_mul_three(a0, a1, b0, b1, zeta, q):
    p0 = a0*b0 % q
    p1 = a1*b1 % q
    p2 = ((a0+a1) % q)*((b0+b1) % q) % q
    return (p0+zeta*p1) % q, (p2-p0-p1) % q


def product_tables():
    fft = []
    for width in (32, 64, 128):
        limbs = ceil(width/32)
        expanded = ceil((width+1)/32)
        fft.append({
            "width": width, "4M": 4*limbs*limbs,
            "3M_generic_expanded": 2*limbs*limbs+expanded*expanded,
            "3M_twiddle_expanded": 2*limbs*limbs+expanded*limbs,
            "3M_twiddle_carry_corrected": 3*limbs*limbs,
            "GS_expanded_4M": 4*expanded*limbs,
        })
    ntt = []
    for q, word, polarity in PROFILES:
        b = q.bit_length()
        mu = (1 << (2*b))//q
        t_bits = ((q-1)**2).bit_length()
        coeff = ((-pow(q, -1, 1 << word)) % (1 << word)
                 if polarity == "plus" else pow(q, -1, 1 << word))
        estimate_products = ceil(t_bits/32)*ceil(mu.bit_length()/32)
        ntt.append({
            "q": q, "q_bits": b, "word": word, "polarity": polarity,
            "mont_coefficient": coeff, "q_naf": naf(q),
            "mont_coefficient_naf": naf(coeff),
            "constant_adds_proxy": len(naf(q))+len(naf(coeff))-2,
            "barrett_shift": 2*b, "barrett_mu": mu,
            "barrett_T_bits": t_bits, "barrett_mu_bits": mu.bit_length(),
            "barrett_estimate_full_product_slots": estimate_products,
            "barrett_slots_with_q_generic": 1+estimate_products+1,
            "barrett_slots_with_q_constant_network": 1+estimate_products,
            "mont_generic_slots": 3,
            "mont_constant_network_product_slots": 1,
        })
    return fft, ntt


def run_checks():
    rng = Random(SEED)
    counts = {}
    n = 0
    corrections = set()
    for width, twidth in ((32,32), (64,64), (128,128), (64,32), (128,64)):
        lo, hi = -(1 << (width-1)), (1 << (width-1))-1
        scale = 1 << (twidth-2)
        diag = isqrt(scale*scale//2)
        roots = [(scale,0),(-scale,0),(0,scale),(0,-scale),
                 (diag,diag),(-diag,-diag),(diag,-diag)]
        data = (lo, lo+1, -1, 0, 1, hi-1, hi)
        cases = [(a,b,c,d) for a in data for b in data for c,d in roots]
        for _ in range(1000):
            c = rng.randint(-scale, scale)
            cap = isqrt(scale*scale-c*c)
            d = rng.randint(-cap, cap)
            cases.append((rng.randint(lo,hi),rng.randint(lo,hi),c,d))
        for a,b,c,d in cases:
            reference = complex_four(a,b,c,d)
            re, im, extra = complex_three_twiddle(a,b,c,d,width,twidth)
            assert (re,im) == reference
            assert (rne(re,twidth-2),rne(im,twidth-2)) == (
                rne(reference[0],twidth-2),rne(reference[1],twidth-2))
            corrections.add(extra)
            n += 1
    assert corrections == {-1,0,1}
    counts["complex_3M_vs_4M_pairs"] = n

    modular = 0
    half_count = 0
    lazy_count = 0
    for q, word, polarity in PROFILES:
        for constant in (q, pow(q,-1,1<<word), (-pow(q,-1,1<<word))%(1<<word)):
            terms = naf(constant)
            assert sum(s*(1<<b) for s,b in terms) == constant
            for x in (0,1,(1<<word)-1):
                assert constant_mul(x, terms) == x*constant
        edge = (0,1,q//2,q-2,q-1)
        pairs = [(a,b) for a in edge for b in edge]
        pairs += [(rng.randrange(q),rng.randrange(q)) for _ in range(5000)]
        for a,b in pairs:
            t = a*b
            assert mont_from_t(t,q,word,polarity) == mont_from_t(
                t,q,word,polarity,False)
            barrett_t(t,q)
            shoup_full(a,b,q,word)
            assert ((a+b) % q, (a-b) % q) == (
                a+b-q if a+b>=q else a+b, a-b+q if a<b else a-b)
            half_mod(a,q)
            half_count += 1
            modular += 1
        # Exhaust every possible encoded residue for the two small PQC primes.
        if q <= 12289:
            for x in range(q):
                half_mod(x,q)
                half_count += 1
        if 4*q < (1<<word):
            for _ in range(1000):
                t = rng.randrange(2*q)*rng.randrange(2*q)
                mont_from_t(t,q,word,polarity)
                lazy_count += 1
    counts["modular_operand_pairs_all_backends"] = modular
    counts["modular_half_inputs"] = half_count
    counts["lazy_montgomery_pairs_valid_bound"] = lazy_count

    # Full/low/high product: exact slice dependencies, not a hardware model.
    slice_count = 0
    for width in (32,64,128):
        for limb in (16,32):
            radix = 1<<limb
            length = width//limb
            for _ in range(500):
                a,b = rng.getrandbits(width),rng.getrandbits(width)
                al = [(a>>(i*limb)) & (radix-1) for i in range(length)]
                bl = [(b>>(i*limb)) & (radix-1) for i in range(length)]
                full = sum(x*y << ((i+j)*limb)
                           for i,x in enumerate(al) for j,y in enumerate(bl))
                low = sum(x*y << ((i+j)*limb)
                          for i,x in enumerate(al) for j,y in enumerate(bl)
                          if i+j<length) % (1<<width)
                assert full == a*b and low == (a*b) % (1<<width)
                slice_count += 1
    counts["full_low_product_pairs"] = slice_count

    transforms = 0
    convolutions = 0
    for q,word,polarity in PROFILES:
        for n in (8,16):
            psi = root_2n(q,n)
            omega = psi*psi % q
            for _ in range(10):
                a = [rng.randrange(q) for _ in range(n)]
                b = [rng.randrange(q) for _ in range(n)]
                fa = ntt_ct(a,omega,q,word,polarity)
                assert fa == dft_mod(a,omega,q)
                assert intt_gs_half(fa,pow(omega,-1,q),q,word,polarity) == a
                inv = ntt_ct(fa,pow(omega,-1,q),q,word,polarity)
                assert [x*pow(n,-1,q)%q for x in inv] == a
                transforms += 1
                # Twisted cyclic NTT implements negacyclic convolution.
                ta = [x*pow(psi,i,q)%q for i,x in enumerate(a)]
                tb = [x*pow(psi,i,q)%q for i,x in enumerate(b)]
                aa = ntt_ct(ta,omega,q,word,polarity)
                bb = ntt_ct(tb,omega,q,word,polarity)
                product = [x*y%q for x,y in zip(aa,bb)]
                out = intt_gs_half(product,pow(omega,-1,q),q,word,polarity)
                out = [x*pow(psi,-i,q)%q for i,x in enumerate(out)]
                reference = [0]*n
                for i,x in enumerate(a):
                    for j,y in enumerate(b):
                        reference[(i+j)%n] += x*y*(1 if i+j<n else -1)
                assert out == [x%q for x in reference]
                convolutions += 1
    counts["small_ntt_dft_and_inverse_cases"] = transforms
    counts["negacyclic_convolution_cases"] = convolutions

    for _ in range(5000):
        q=3329
        a0,a1,b0,b1,zeta = [rng.randrange(q) for _ in range(5)]
        assert pair_mul_three(a0,a1,b0,b1,zeta,q) == (
            (a0*b0+zeta*a1*b1)%q,(a0*b1+a1*b0)%q)
    counts["basemul_karatsuba_pairs"] = 5000

    # Exact rational split/merge: no assertion about fixed-point error.
    for _ in range(100):
        ar,ai,br,bi = [Fraction(rng.randint(-100,100)) for _ in range(4)]
        wr,wi = Fraction(3,5),Fraction(4,5)
        er,ei = (ar+br)/2,(ai+bi)/2
        dr,di = (ar-br)/2,(ai-bi)/2
        or_,oi = dr*wr+di*wi,di*wr-dr*wi
        pr,pi = or_*wr-oi*wi,or_*wi+oi*wr
        assert (er+pr,ei+pi,er-pr,ei-pi)==(ar,ai,br,bi)
    counts["rational_split_merge_cases"] = 100

    B=1<<32
    a=b=B*B-1
    a0,b0=a%(B),b%(B)
    a1,b1=a//B,b//B
    high_wrong=a1*b1+(a0*b1+a1*b0)//B
    high_exact=a1*b1+(a0*b1+a1*b0+(a0*b0)//B)//B
    assert high_exact==(a*b)//(B*B) and high_wrong!=high_exact
    _,shoup_r=shoup_full(9,140,251,8)
    assert shoup_r==256 and (shoup_r%256)%251 != 9*140%251
    assert 1+rne(1,1)==1 and rne(3,1)==2
    pw_im=2*((1<<31)-1)**2
    assert rne(pw_im,16) >= (1<<33)
    regressions={
        "high_product_dropped_carry":{"exact":high_exact,"wrong":high_wrong},
        "shoup_q_near_radix":{"q":251,"R":256,"x":9,"w":140,
                              "remainder":256,"correct":5},
        "rounding_location":{"round_product_then_add":1,"round_after_add":2},
        "pointwise_not_unit_twiddle":{"rounded_imag":rne(pw_im,16),
                                      "signed_W_plus_2_max":(1<<33)-1},
    }
    return counts, regressions


def main():
    counts, regressions=run_checks()
    fft,ntt=product_tables()
    result={"seed":SEED,"scope":"Exact algebra/range checks and operation counts; no RTL/PPA",
            "checks":counts,"counterexamples":regressions,
            "fft_product_counts_L32":fft,"ntt_profiles":ntt}
    dest=ROOT/"study"/"results"
    dest.mkdir(parents=True,exist_ok=True)
    (dest/"arithmetic_reassessment.json").write_text(
        json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    md=["# Operation-level FFT/NTT reassessment",
        "", "Analytical counts and exact checks. No area, Fmax or end-to-end throughput measured.",
        "", "## Checks", ""]
    md += [f"- {key}: {value}" for key,value in counts.items()]
    md += ["", "## FFT full-product slots, 32-bit limbs", "",
           "| W | 4M | 3M generic W+1 | 3M twiddle W+1 | 3M carry correction | GS W+1 / 4M |",
           "|---:|---:|---:|---:|---:|---:|"]
    for r in fft:
        md.append(f"| {r['width']} | {r['4M']} | {r['3M_generic_expanded']} | "
                  f"{r['3M_twiddle_expanded']} | {r['3M_twiddle_carry_corrected']} | "
                  f"{r['GS_expanded_4M']} |")
    md += ["", "3M counts exclude extra adders, correction, coefficient storage and routing.",
           "", "## Reduction profiles", "",
           "| q | word | Montgomery polarity | coefficient | q NAF terms | coefficient NAF terms | Barrett mu |",
           "|---:|---:|---|---:|---|---|---:|"]
    for r in ntt:
        md.append(f"| {r['q']} | {r['word']} | {r['polarity']} | "
                  f"{r['mont_coefficient']} | {r['q_naf']} | "
                  f"{r['mont_coefficient_naf']} | {r['barrett_mu']} |")
    md += ["", "NAF terms are (sign, shift). They are not measured gate/adder costs.",
           "", "## Counterexamples", "", "~~~json",
           json.dumps(regressions,indent=2),"~~~"]
    (dest/"arithmetic_reassessment.md").write_text("\n".join(md)+"\n",encoding="utf-8")
    print(json.dumps(counts,indent=2))
    print("Wrote study/results/arithmetic_reassessment.{json,md}")


if __name__=="__main__":
    main()
