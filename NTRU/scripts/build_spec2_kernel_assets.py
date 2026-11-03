"""Kernel-level assets of spec 2.0 for the three new kernels (spec/FlexTransform/2.0/01_so_hoc_kernel.md).

Sources of expected values:
  FFT 64 bit NTRUGen (fmt 5):   vect_FFT / vect_iFFT of the pinned NTRUGen C (model/ntrugen_fft_harness.c)
  NTT prime 31 bit (profile 3): mp_NTT / mp_iNTT / mp_mkgmigm of the pinned NTRUGen C (model/ntrugen_mp31_harness.c);
                                TOMONT / MODMUL and the second job of jobs = 2 by plain modular arithmetic
  NTT q = 8380417 (profile 2):  plain modular arithmetic following the loops of 01; the checker re-derives every
                                NTT output by direct polynomial evaluation (independent oracle)
Root tables: GM_TAB copied bit for bit from ng_fxp.c; q8380417 roots computed from psi = 1753.

Output (spec/FlexTransform/2.0/assets/):
  fft_ntrugen_q32_32.mem      1024 rows, 128 bit: [127:64] real, [63:0] imag (GM_TAB)
  ntt_q8380417_forward.mem    256 rows, 32 bit: GM[k]  = R * psi^brv8(k) mod q,  R = 2^32
  ntt_q8380417_inverse.mem    256 rows, 32 bit: IGM[k] = R * psi^-brv8(k) mod q
  kernel/fft_ntrugen.jsonl, kernel/ntt_q8380417.jsonl, kernel/ntt_prime31.jsonl, kernel/manifest.json

Run: python scripts/build_spec2_kernel_assets.py
"""
import hashlib
import json
import os
import random
import re
import shutil
import struct
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "third_party" / "r8" / "ntrugen" / "src"
ASSETS = ROOT / "spec" / "FlexTransform" / "2.0" / "assets"
KERNEL = ASSETS / "kernel"
BUILD = ROOT / "study" / "build"
SEED = 20261031

Q2, PSI, R32 = 8380417, 1753, 1 << 32
PRIME_INDICES = (0, 1, 161, 321, 322)     # first, second, middle, last two of PRIMES[]
MULTI_INDICES = (0, 1, 2, 80, 161, 240, 321, 322)   # eight different primes for multi-slot commands


def gcc_env():
    gcc = shutil.which("gcc") or r"C:\msys64\mingw64\bin\gcc.exe"
    env = dict(os.environ, PATH=str(Path(gcc).parent) + os.pathsep + os.environ.get("PATH", ""))
    return gcc, env


def run_harness(name, c_file, c_src):
    out_dir = BUILD / name
    out_dir.mkdir(parents=True, exist_ok=True)
    exe, dump = out_dir / "harness.exe", out_dir / "dump.bin"
    gcc, env = gcc_env()
    subprocess.run([gcc, "-O2", "-DNTRUGEN_AVX2=0", f"-I{SRC}", str(ROOT / "model" / c_file), str(SRC / c_src),
                    "-o", str(exe)], check=True, env=env)
    subprocess.run([str(exe), str(dump)], check=True, env=env)
    return dump.read_bytes()


def brv(x, bits):
    return int(format(x, f"0{bits}b")[::-1], 2)


# --- root tables --------------------------------------------------------------------------------

def gm_tab():
    text = (SRC / "ng_fxp.c").read_text()
    body = text[text.index("GM_TAB[1024] = {"):]
    pairs = re.findall(r"FXC\(\s*(\d+)ull,\s*(\d+)ull\)", body)[:1024]
    assert len(pairs) == 1024
    return [(int(a), int(b)) for a, b in pairs]


def q2_tables():
    assert pow(PSI, 256, Q2) == Q2 - 1           # primitive 512-th root of unity
    gm = [R32 * pow(PSI, brv(k, 8), Q2) % Q2 for k in range(256)]
    igm = [R32 * pow(PSI, -brv(k, 8), Q2) % Q2 for k in range(256)]
    return gm, igm


def primes_table():
    text = (SRC / "ng_mp31.c").read_text()
    body = text[text.index("const small_prime PRIMES[]"):]
    rows = re.findall(r"\{\s*(\d+),\s*(\d+),\s*(\d+),\s*(\d+),\s*(\d+),\s*(\d+)\s*\}", body)
    rows = [tuple(map(int, r)) for r in rows if int(r[0])]
    assert len(rows) == 323
    return rows                                    # (p, p0i, R2, g, ig, s)


# --- spec algorithms with plain modular arithmetic (01_so_hoc_kernel.md) -------------------------

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
        stride //= 2
        groups *= 2
    return a


def ntt_inv(a, igm, q, halve, final_factor):
    a, n = list(a), len(a)
    inv2 = pow(2, -1, q)
    stride = 1
    while stride <= n // 2:
        groups = n // (2 * stride)
        for g in range(groups):
            for off in range(stride):
                i = 2 * g * stride + off
                j = i + stride
                s, d = (a[i] + a[j]) % q, (a[i] - a[j]) % q
                a[i] = s * inv2 % q if halve else s
                a[j] = mont(d, igm[groups + g], q)
        stride *= 2
    if final_factor is not None:
        a = [mont(x, final_factor, q) for x in a]
    return a


def hexs(vals, digits):
    return [f"{v:0{digits}x}" for v in vals]


# --- kernel vectors -----------------------------------------------------------------------------

def fft_ntrugen_cases():
    raw = run_harness("ntrugen_fft", "ntrugen_fft_harness.c", "ng_fxp.c")
    pos, cases = 0, []
    while pos < len(raw):
        logn, kind = struct.unpack_from("<QQ", raw, pos)
        pos += 16
        n = 1 << logn
        inp = struct.unpack_from(f"<{n}Q", raw, pos)
        pos += 8 * n
        out = struct.unpack_from(f"<{n}Q", raw, pos)
        pos += 8 * n
        cases.append({"op": "IFFT" if kind else "FFT", "fmt": 5, "profile": 0, "logn": logn, "jobs": 1,
                      "input": [hexs(inp, 16)], "expected": [hexs(out, 16)],
                      "source": "NTRUGen vect_FFT/vect_iFFT (C, NTRUGEN_AVX2=0)"})
    return cases


def q2_cases(rng):
    gm, igm = q2_tables()
    q, n = Q2, 256
    r2 = R32 * R32 % q
    final = R32 * pow(256, -1, q) % q
    patterns = [[0] * n, [q - 1] * n, [1] + [0] * (n - 1), [0, 1] + [0] * (n - 2)]
    patterns += [[rng.randrange(q) for _ in range(n)] for _ in range(6)]
    cases = []
    for op in ("NTT", "INTT", "TOMONT", "MODMUL"):
        for jobs in (1, 2):
            for k in range(0, len(patterns), jobs):
                ins = patterns[k:k + jobs]
                if len(ins) < jobs:
                    continue
                other = [[rng.randrange(q) for _ in range(n)] for _ in range(jobs)]
                if op == "NTT":
                    exp = [ntt_fwd(x, gm, q) for x in ins]
                elif op == "INTT":
                    exp = [ntt_inv(x, igm, q, False, final) for x in ins]
                elif op == "TOMONT":
                    exp = [[mont(v, r2, q) for v in x] for x in ins]
                else:
                    exp = [[mont(v, w, q) for v, w in zip(x, y)] for x, y in zip(ins, other)]
                c = {"op": op, "fmt": 4, "profile": 2, "logn": 8, "jobs": jobs,
                     "input": [hexs(x, 8) for x in ins], "expected": [hexs(x, 8) for x in exp],
                     "source": "plain modular arithmetic; NTT outputs re-derived by direct evaluation in the checker"}
                if op == "MODMUL":
                    c["input_b"] = [hexs(y, 8) for y in other]
                cases.append(c)
    return cases


def prime31_cases(rng):
    raw = run_harness("ntrugen_mp31", "ntrugen_mp31_harness.c", "ng_mp31.c")
    words = struct.unpack(f"<{len(raw) // 4}I", raw)
    primes = primes_table()
    pos, records = 0, []
    multi = {}                                     # (prime index, logn) -> (p, p0i, r2, gm, igm, a, a_ntt, b, b_intt)
    for idx in range(323):
        p, p0i, g, ig = words[pos:pos + 4]
        pos += 4 + 67 * 3
        assert (p, p0i, g, ig) == (primes[idx][0], primes[idx][1], primes[idx][3], primes[idx][4])
        r2 = primes[idx][2]
        for logn in range(1, 11):
            n = 1 << logn
            blk = [list(words[pos + k * n:pos + (k + 1) * n]) for k in range(6)]
            pos += 6 * n
            if idx in MULTI_INDICES and n < 64:
                multi[(idx, logn)] = (p, p0i, r2, *blk)
            if idx not in PRIME_INDICES:
                continue
            gm, igm, a, a_ntt, b, b_intt = blk
            pid = f"p{idx}_n{n}"
            records.append({"kind": "nap_prime", "id": pid, "slot": 0, "base": 0, "p": f"{p:08x}",
                            "p0i": f"{p0i:08x}", "r2": f"{r2:08x}", "logn": logn, "tables": 3,
                            "gm": hexs(gm, 8), "igm": hexs(igm, 8), "source": "NTRUGen PRIMES[] and mp_mkgmigm"})
            src_c = "NTRUGen mp_NTT/mp_iNTT (C, NTRUGEN_AVX2=0)"
            records.append({"kind": "op", "prime": pid, "op": "NTT", "fmt": 4, "profile": 3, "logn": logn, "jobs": 1,
                            "input": [hexs(a, 8)], "expected": [hexs(a_ntt, 8)], "source": src_c})
            records.append({"kind": "op", "prime": pid, "op": "INTT", "fmt": 4, "profile": 3, "logn": logn,
                            "jobs": 1, "input": [hexs(b, 8)], "expected": [hexs(b_intt, 8)], "source": src_c})
            if n >= 64:
                # second job: spec algorithm with plain arithmetic, after checking it reproduces the C job above
                assert ntt_fwd(a, gm, p) == a_ntt and ntt_inv(b, igm, p, True, None) == b_intt
                a2 = [rng.randrange(p) for _ in range(n)]
                records.append({"kind": "op", "prime": pid, "op": "NTT", "fmt": 4, "profile": 3, "logn": logn,
                                "jobs": 2, "input": [hexs(a, 8), hexs(a2, 8)],
                                "expected": [hexs(a_ntt, 8), hexs(ntt_fwd(a2, gm, p), 8)],
                                "source": "job 0: C; job 1: spec algorithm, plain modular arithmetic"})
            x = [rng.randrange(p) for _ in range(n)]
            y = [rng.randrange(p) for _ in range(n)]
            records.append({"kind": "op", "prime": pid, "op": "TOMONT", "fmt": 4, "profile": 3, "logn": logn,
                            "jobs": 1, "input": [hexs(x, 8)], "expected": [hexs([mont(v, r2, p) for v in x], 8)],
                            "source": "plain modular arithmetic"})
            records.append({"kind": "op", "prime": pid, "op": "MODMUL", "fmt": 4, "profile": 3, "logn": logn,
                            "jobs": 1, "input": [hexs(x, 8)], "input_b": [hexs(y, 8)],
                            "expected": [hexs([mont(v, w, p) for v, w in zip(x, y)], 8)],
                            "source": "plain modular arithmetic"})
    assert pos == len(words)

    # Multi-slot commands (each tile its own modulus): N < 64, min(8, 64/N) polynomials, one prime per slot.
    for logn in range(1, 6):
        n = 1 << logn
        jobs = min(8, 64 // n)
        first = 12 if logn == 1 else 3                 # logn 1 wraps from slot 15 to slot 0
        g = max(1, n // 2 - 1)                         # bundles per table
        ids, ins_f, exp_f, ins_i, exp_i = [], [], [], [], []
        for j, idx in enumerate(MULTI_INDICES[:jobs]):
            p, p0i, r2, gm, igm, a, a_ntt, b, b_intt = multi[(idx, logn)]
            pid = f"m{idx}_n{n}"
            ids.append(pid)
            records.append({"kind": "nap_prime", "id": pid, "slot": (first + j) % 16, "base": j * g,
                            "p": f"{p:08x}", "p0i": f"{p0i:08x}", "r2": f"{r2:08x}", "logn": logn, "tables": 3,
                            "gm": hexs(gm, 8), "igm": hexs(igm, 8), "source": "NTRUGen PRIMES[] and mp_mkgmigm"})
            ins_f.append(hexs(a, 8))
            exp_f.append(hexs(a_ntt, 8))
            ins_i.append(hexs(b, 8))
            exp_i.append(hexs(b_intt, 8))
        src = "each polynomial: NTRUGen mp_NTT/mp_iNTT (C) for its own prime"
        for op, ins, exp in (("NTT", ins_f, exp_f), ("INTT", ins_i, exp_i)):
            records.append({"kind": "op", "primes": ids, "khe_dau": first, "cung_khe": 0, "op": op, "fmt": 4,
                            "profile": 3, "logn": logn, "jobs": jobs, "input": ins, "expected": exp, "source": src})
    return records


def write_lines(path, lines):
    text = "\n".join(lines) + "\n"
    path.write_text(text, encoding="ascii", newline="\n")
    return hashlib.sha256(text.encode()).hexdigest()


def main():
    KERNEL.mkdir(parents=True, exist_ok=True)
    rng = random.Random(SEED)
    files = {}
    files["fft_ntrugen_q32_32.mem"] = write_lines(ASSETS / "fft_ntrugen_q32_32.mem",
                                                  [f"{re_:016x}{im:016x}" for re_, im in gm_tab()])
    gm, igm = q2_tables()
    files["ntt_q8380417_forward.mem"] = write_lines(ASSETS / "ntt_q8380417_forward.mem", hexs(gm, 8))
    files["ntt_q8380417_inverse.mem"] = write_lines(ASSETS / "ntt_q8380417_inverse.mem", hexs(igm, 8))
    counts = {}
    for name, recs in (("fft_ntrugen.jsonl", fft_ntrugen_cases()), ("ntt_q8380417.jsonl", q2_cases(rng)),
                       ("ntt_prime31.jsonl", prime31_cases(rng))):
        files["kernel/" + name] = write_lines(KERNEL / name, [json.dumps(r, separators=(",", ":")) for r in recs])
        counts[name] = sum(1 for r in recs if r.get("kind", "op") == "op")
    constants = {
        "q8380417": {"q": Q2, "R": "2^32", "qprime": (-pow(Q2, -1, R32)) % R32, "R_mod_q": R32 % Q2,
                     "R2_mod_q": R32 * R32 % Q2, "psi": PSI, "intt_final_factor": R32 * pow(256, -1, Q2) % Q2},
    }
    manifest = {"spec": "FlexTransform 2.0, 01_so_hoc_kernel.md", "generator": "scripts/build_spec2_kernel_assets.py",
                "seed": SEED, "ntrugen_prime_indices": list(PRIME_INDICES), "constants": constants,
                "cases": counts, "sha256": files}
    (KERNEL / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"cases": counts, "constants": constants}, indent=1))


if __name__ == "__main__":
    main()
