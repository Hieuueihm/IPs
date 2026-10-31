"""How much of the FN-DSA workload is NTT on FlexTransform, and what on-array reduction costs there.

1. Builds the pinned R8 reference with its bundled NTRUGen under WSL (LP64 gcc), with
   sim/ref/workload_profile.c: every FFT / NTT / root-table kernel is counted and timed per
   phase (keygen, expand, sign, verify) through GNU ld --wrap, or through renamed definitions
   in a generated copy of vrfy.c for the static q = 12289 functions. Arithmetic is the original C.
2. Multiplies the call counts by the cycle projections of docs/architecture_v1.md section 4
   (model/flex_v1_projection.py and the tile model), for both reduction variants.

Run: python scripts/profile_fn_dsa_workload.py   (writes study/results/fn_dsa_workload.md and .json)
     python scripts/profile_fn_dsa_workload.py --lai
     Hybrid reduction (architecture v1): the "on-array" column keeps on-array reduction only for
     32-bit lanes; 16-bit NTT (q = 12289) uses the fixed reducers. Writes fn_dsa_workload_lai.md/.json.
     python scripts/profile_fn_dsa_workload.py --mot-lan
     Single-lane tile (spec 2.0, 10 since 31/10/2026), one 32-bit lane for every q (q = 12289 included,
     R = 2^32, data in format 4): one pass per layer, NTT times from model/single_lane_feed.py (8
     root-pack banks, staggered reads). "On-array" column = the v1 design since 01/11/2026, 1/3 butterfly per tile per cycle, latency
     19 + 2; "dedicated" column = the H2 baseline (v1 from 31/10 to 01/11/2026), 1 per cycle, latency 15 + 2. Reuses the call counts of
     fn_dsa_workload_lai.json (no rebuild). Writes fn_dsa_workload_mot_lan.md/.json.
"""
import importlib.util
import json
import re
import subprocess
import sys
from math import ceil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "third_party" / "r8"
BUILD = ROOT / "study" / "build" / "fn_dsa_workload"
KEYS, SIGS = 4, 8
LAI = "--lai" in sys.argv   # hybrid: 16-bit lanes use the fixed reducers in the "on-array" column
MOT_LAN = "--mot-lan" in sys.argv   # single-lane tile, one pass per layer
SUFFIX = "_mot_lan" if MOT_LAN else "_lai" if LAI else ""
CMD_OVERHEAD = 16          # cycles per kernel command (validate, drain); also reported with 0
LAT_FFT = 8                # pass barrier of the FFT projection (architecture section 4)

R8_FILES = ("codec.c", "common.c", "falcon.c", "fft.c", "fpr.c", "rng.c", "shake.c", "sign.c", "sign_ref.c")
NG_FILES = ("ng_falcon.c", "ng_fxp.c", "ng_gauss.c", "ng_mp31.c", "ng_ntru.c", "ng_poly.c", "ng_zint31.c", "sha3.c")
WRAPPED = ("falcon_inner_FFT", "falcon_inner_iFFT", "falcon_inner_poly_mul_fft", "falcon_inner_poly_split_fft",
           "falcon_inner_poly_merge_fft", "ntrugen_vect_FFT", "ntrugen_vect_iFFT", "ntrugen_mp_NTT",
           "ntrugen_mp_iNTT", "ntrugen_mp_mkgm", "ntrugen_mp_mkigm", "ntrugen_mp_mkgmigm")
MQ_NAMES = ("mq_NTT", "mq_iNTT", "mq_poly_tomonty", "mq_poly_montymul_ntt")


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def wsl(path):
    p = Path(path).resolve()
    return "/mnt/" + p.drive[0].lower() + p.as_posix()[2:]


# --- build and run ------------------------------------------------------------------------------

def build():
    BUILD.mkdir(parents=True, exist_ok=True)
    text = (SRC / "vrfy.c").read_text()
    decl = "\n" + "".join(f"static void {n}(uint16_t *, unsigned);\n" for n in MQ_NAMES[:3])
    decl += "static void mq_poly_montymul_ntt(uint16_t *, const uint16_t *, unsigned);\n"
    assert text.count('#include "inner.h"') == 1
    text = text.replace('#include "inner.h"', '#include "inner.h"' + decl)
    for name in MQ_NAMES:
        text, count = re.subn(r"(?m)^" + name + r"\(", f"wp_original_{name}(", text)
        assert count == 1, name
    text += '\n#include "workload_profile_ntt.inc"\n'
    (BUILD / "vrfy_profiled.c").write_text(text)
    flags = "-O2 -std=gnu11 -fno-strict-aliasing -DFALCON_FPR_MODE=2 -DFALCON_AVX2=0 -DFALCON_RAND_WIN32=0 " \
            f"-I{wsl(SRC)} -I{wsl(ROOT / 'sim' / 'ref')}"
    sources = [wsl(SRC / f) for f in R8_FILES] + [wsl(SRC / "ntrugen" / "src" / f) for f in NG_FILES]
    sources += [wsl(BUILD / "vrfy_profiled.c"), wsl(ROOT / "sim" / "ref" / "workload_profile.c")]
    wraps = ",".join(f"--wrap={s}" for s in WRAPPED)
    script = (f"set -e; cd {wsl(BUILD)}; gcc -dM -E - </dev/null | grep -q '__SIZEOF_LONG__ 8'; "
              f"gcc -g -no-pie {flags} {' '.join(sources)} -Wl,{wraps} -lm -o workload_profile")
    subprocess.run(["wsl", "-e", "bash", "-lc", script], check=True)


def run(logn):
    out = subprocess.run(["wsl", "-e", "bash", "-lc", f"{wsl(BUILD)}/workload_profile {logn} {KEYS} {SIGS}"],
                         check=True, capture_output=True, text=True, timeout=3600)
    return json.loads(out.stdout)


# --- cycle projections ---------------------------------------------------------------------------

def make_cost_single_lane(proj):
    """Costs for the single-lane tile; rates in butterflies per cycle for the whole core (16 tiles)."""
    feed = load("feed", ROOT / "model" / "single_lane_feed.py")
    # one 32-bit lane: q = 12289 (width 16) runs on the same engine as the 31-bit primes
    rate = {(w, ded): 16 if ded else 16 / 3 for w in (16, 32) for ded in (False, True)}
    lat = {(w, ded): 17 if ded else 21 for w in (16, 32) for ded in (False, True)}
    cache = {}

    def fed(logn, jobs):
        key = (logn, jobs)
        if key not in cache:
            bases = [0, 0] if (jobs == 2 and logn >= 6) else None
            cache[key] = feed.ntt_cycles(logn, False, jobs, 8, bases=bases)[1]
        return cache[key]

    def ntt_batch(width, logn, jobs, ded):
        n = 1 << logn
        if ded:
            return fed(logn, jobs)
        lt = lat[(32, False)]
        if jobs == 1:
            return logn * (ceil((n // 2) / rate[(32, False)]) + lt)
        if n >= 64:
            f = ceil((n // 2) / rate[(32, False)])
            return logn * max(2 * f, f + lt)
        return logn * (ceil((n // 2) / (rate[(32, False)] / jobs)) + lt)

    def ntt(width, logn, ded):
        return ntt_batch(width, logn, 1, ded)

    def pointwise(width, n, ded):
        return ceil(n / rate[(width, ded)]) + lat[(width, ded)]

    fft_cache = {}

    def fft(width, n, inverse):
        if n < 4:
            return 0
        key = (width, n, inverse)
        if key not in fft_cache:
            fft_cache[key] = proj.fft_projection(width, n, 4, LAT_FFT, False, inverse=inverse)[0]
        return fft_cache[key]

    def cost(kind, logn, ded):
        n = 1 << logn
        if kind == "r8_fft":
            return fft(128, n, False), 0
        if kind == "r8_ifft":
            return fft(128, n, True) + n * 128 // 1024 + LAT_FFT, 0
        if kind == "r8_cmul":
            return ceil(1.5 * n) + LAT_FFT, 0
        if kind in ("r8_split", "r8_merge"):
            return ceil(0.75 * n) + LAT_FFT, 0
        if kind == "ng_fft":
            return fft(64, n, False), 0
        if kind == "ng_ifft":
            return fft(64, n, True), 0
        if kind == "q12289_ntt":
            return ntt(16, logn, ded), 0
        if kind == "q12289_intt":
            return ntt(16, logn, ded) + pointwise(16, n, ded), 0
        if kind == "q12289_tomont":
            return pointwise(16, n, ded), 0                 # Mont(x, 2^48 mod q) = x * 2^16
        if kind == "q12289_modmul":
            return 2 * pointwise(16, n, ded), 0             # Mont(Mont(a, b), 2^48 mod q) = a * b * 2^-16
        if kind in ("p31_ntt", "p31_intt"):
            return ntt(32, logn, ded), 0
        if kind in ("p31_mkgm", "p31_mkigm"):
            return max(1, n // 8), 1 + n // 4
        if kind == "p31_mkgmigm":
            return 2 * max(1, n // 8), 1 + n // 2
        raise KeyError(kind)

    return cost, rate, lat, ntt_batch


def make_cost():
    proj = load("proj", ROOT / "model" / "flex_v1_projection.py")
    tile = load("tile", ROOT / "model" / "mont_on_array_tile.py")
    rate, lat = {}, {}
    for w, prof in ((16, tile.PROFILES[0]), (32, tile.PROFILES[2])):
        for ded in (False, True):
            r = tile.run_frames(prof, 4, 1, 1, 1500, 0.0, 10 ** 9, seed=1, dedicated=ded)
            rate[(w, ded)] = 16 / round(1 / r["frame_rate"])        # frames/cycle, 16 tiles
            lat[(w, ded)] = r["min_latency"] + 2                       # + RAM read and write
    if LAI:
        rate[(16, False)], lat[(16, False)] = rate[(16, True)], lat[(16, True)]
    if MOT_LAN:
        return make_cost_single_lane(proj)
    fft_cache = {}

    def fft(width, n, inverse):
        if n < 4:
            return 0
        key = (width, n, inverse)
        if key not in fft_cache:
            fft_cache[key] = proj.fft_projection(width, n, 4, LAT_FFT, False, inverse=inverse)[0]
        return fft_cache[key]

    def ntt(width, logn, ded):
        """Paired passes plus a single-layer tail when logn is odd; modmul/cycle = 4 x frames/cycle."""
        n, fr, lt = 1 << logn, rate[(width, ded)], lat[(width, ded)]
        t = (logn // 2) * (ceil((n // 4) / fr) + lt)
        if logn % 2:
            t += ceil((n // 2) / (4 * fr)) + lt
        return t

    def pointwise(width, n, ded):
        return ceil(n / (4 * rate[(width, ded)])) + lat[(width, ded)]

    def ntt_batch(width, logn, jobs, ded):
        """One command with `jobs` polynomials (spec 2.0, 00 section 4).

        N < 64: the jobs sit in different tiles and share each pass; N >= 64, jobs = 2: two contexts,
        each pass costs max(2F, F + latency) for both polynomials (architecture section 4)."""
        n, fr, lt = 1 << logn, rate[(width, ded)], lat[(width, ded)]
        paired, tail = logn // 2, logn % 2
        f, t = ceil((n // 4) / fr), ceil((n // 2) / (4 * fr))
        if jobs == 1:
            return ntt(width, logn, ded)
        if n >= 64:
            return paired * max(2 * f, f + lt) + tail * max(2 * t, t + lt)
        return paired * (ceil(jobs * (n // 4) / fr) + lt) + tail * (ceil(jobs * (n // 2) / (4 * fr)) + lt)

    def cost(kind, logn, ded):
        """(core cycles, host lines) for one call."""
        n = 1 << logn
        if kind == "r8_fft":
            return fft(128, n, False), 0
        if kind == "r8_ifft":
            return fft(128, n, True) + n * 128 // 1024 + LAT_FFT, 0      # final division pass
        if kind == "r8_cmul":
            return ceil(1.5 * n) + LAT_FFT, 0                            # n/2 complex mul x 3 products
        if kind in ("r8_split", "r8_merge"):
            return ceil(0.75 * n) + LAT_FFT, 0                           # n/4 complex mul x 3 products
        if kind == "ng_fft":
            return fft(64, n, False), 0
        if kind == "ng_ifft":
            return fft(64, n, True), 0
        if kind == "q12289_ntt":
            return ntt(16, logn, ded), 0
        if kind == "q12289_intt":
            return ntt(16, logn, ded) + pointwise(16, n, ded), 0          # final normalisation pass
        if kind in ("q12289_tomont", "q12289_modmul"):
            return pointwise(16, n, ded), 0
        if kind in ("p31_ntt", "p31_intt"):
            return ntt(32, logn, ded), 0
        if kind in ("p31_mkgm", "p31_mkigm"):
            return max(1, n // 8), 1 + n // 4                             # load one table (spec 2.0, 02 section 3)
        if kind == "p31_mkgmigm":
            return 2 * max(1, n // 8), 1 + n // 2
        raise KeyError(kind)

    return cost, rate, lat, ntt_batch


GROUP = {"r8_fft": "FFT", "r8_ifft": "FFT", "r8_cmul": "FFT", "r8_split": "FFT", "r8_merge": "FFT",
         "ng_fft": "FFT", "ng_ifft": "FFT", "q12289_ntt": "NTT", "q12289_intt": "NTT", "q12289_tomont": "NTT",
         "q12289_modmul": "NTT", "p31_ntt": "NTT", "p31_intt": "NTT", "p31_mkgm": "NẠP ROOT",
         "p31_mkigm": "NẠP ROOT", "p31_mkgmigm": "NẠP ROOT"}


def is_identity(kind, logn):
    """FFT / iFFT with logn <= 1 and NTT with logn = 0 leave the data unchanged."""
    return (GROUP[kind] == "FFT" and kind.endswith(("fft", "ifft")) and logn <= 1) or \
        (kind.startswith("p31_") and kind.endswith(("ntt", "intt")) and logn == 0)


def analyse(res, cost, overhead):
    """Per phase and per single operation: cycles by group for both variants, host lines, software ns."""
    ops = {"keygen": res["keys"], "expand": res["keys"], "sign": res["keys"] * res["sigs_per_key"],
           "verify": res["keys"] * res["sigs_per_key"]}
    out = {}
    for ph, d in res["phases"].items():
        row = {"sw_ms": d["ns"] / ops[ph] / 1e6, "sw_kernel_ms": {}, "calls": {}, "host_lines": 0}
        for ded in (False, True):
            row[ded] = {"FFT": 0, "NTT": 0, "NẠP ROOT": 0}
        for k in d["kernels"]:
            g = GROUP[k["kind"]]
            if is_identity(k["kind"], k["logn"]):
                continue                                   # host skips it: no command, no cycles
            row["calls"][g] = row["calls"].get(g, 0) + k["calls"] / ops[ph]
            row["sw_kernel_ms"][g] = row["sw_kernel_ms"].get(g, 0) + k["ns"] / ops[ph] / 1e6
            for ded in (False, True):
                cyc, lines = cost(k["kind"], k["logn"], ded)
                row[ded][g] += (cyc + overhead) * k["calls"] / ops[ph]
                if not ded:
                    row["host_lines"] += lines * k["calls"] / ops[ph]
        out[ph] = row
    return out


def keygen_batched(res, cost, ntt_batch, overhead, key="p31_batches"):
    """Keygen cycles per key when prime NTTs run as the recorded batches (same prime, or across primes)."""
    keys = res["keys"]
    d = res["phases"]["keygen"]
    out = {}
    for ded in (False, True):
        other = sum((cost(k["kind"], k["logn"], ded)[0] + overhead) * k["calls"] for k in d["kernels"]
                    if k["kind"] not in ("p31_ntt", "p31_intt") and not is_identity(k["kind"], k["logn"]))
        ntt = sum((ntt_batch(32, b["logn"], b["jobs"], ded) + overhead) * b["count"] for b in d[key]
                  if b["logn"] > 0)
        out[ded] = {"ntt": ntt / keys, "total": (other + ntt) / keys}
    return out


def site_lines(sites):
    """Map return addresses to file:line of the call (address - 1) with addr2line."""
    addrs = sorted({s for p in sites for s in (p["first"], p["joined"])})
    if not addrs:
        return {}
    args = " ".join(hex(int(a, 16) - 1) for a in addrs)
    out = subprocess.run(["wsl", "-e", "bash", "-lc", f"addr2line -e {wsl(BUILD)}/workload_profile {args}"],
                         check=True, capture_output=True, text=True).stdout.split()
    return {a: Path(loc).name for a, loc in zip(addrs, out)}


IFACES = (("Giao diện 1.0: một giao dịch, không burst", 2.0), ("Burst / pipeline 128 bit", 1.0),
          ("Burst / pipeline 256 bit", 0.5))


def io_section(lines, raw, summary, batched):
    """Host <-> core traffic per operation under three residency assumptions and three host interfaces."""
    lines.append("\n## Chép dữ liệu giữa host và lõi\n")
    lines.append("Dòng 128 bit host phải ghi vào / đọc ra lõi cho dữ liệu của kernel (`sim/ref/workload_profile.c`), "
                 "chưa gồm bảng root (cột riêng). Ba cách tính:\n"
                 "- **không giữ lại**: mọi đầu vào ghi vào, mọi đầu ra đọc ra;\n"
                 "- **giữ đầu vào**: không ghi lại đầu vào nếu lõi còn giữ đúng nội dung đó từ kernel trước (tới 48 KiB, "
                 "bỏ bộ đệm dùng lâu nhất); đầu ra vẫn đọc ra hết;\n"
                 "- **giữ cả hai** (cận dưới): đầu ra chỉ đọc khi host sửa bộ đệm đó, khi bị đẩy ra, hoặc cuối pha. "
                 "Không thấy được lúc host chỉ đọc mà không sửa.\n\n"
                 "Hai cách giữ lại cần lệnh chỉ ra được địa chỉ bộ đệm trong vùng nhớ; lệnh của 1.0 luôn dùng địa chỉ 0.\n")
    for logn in (9, 10):
        n = 1 << logn
        r = raw[logn]
        ops = {"keygen": r["keys"], "expand": r["keys"], "sign": r["keys"] * r["sigs_per_key"],
               "verify": r["keys"] * r["sigs_per_key"]}
        lines.append(f"### N = {n} (mỗi thao tác)\n")
        lines.append("| Pha | Chu kỳ tính | Dòng: không giữ | giữ đầu vào | giữ cả hai | Dòng bảng root | "
                     + " | ".join(f"Tổng, {name}, không giữ" for name, _ in IFACES) + " | Tổng, burst 128, giữ cả hai |")
        lines.append("|---|---:|---:|---:|---:|---:|" + "---:|" * len(IFACES) + "---:|")
        for ph in ("keygen", "expand", "sign", "verify"):
            io = r["phases"][ph]["io_lines"]
            k = ops[ph]
            a = (io["in_all"] + io["out_all"]) / k
            b = (io["in_miss"] + io["out_all"]) / k
            c = (io["in_miss"] + io["out_lazy"]) / k
            roots = summary[n][ph]["host_lines"]
            comp = batched[(n, "x")][False]["total"] if ph == "keygen" else summary[n][ph]["total_on_array"]
            tot = [comp + cpl * (a + roots) for _, cpl in IFACES]
            best = comp + 1.0 * (c + roots)
            lines.append(f"| {ph} | {comp:.0f} | {a:.0f} | {b:.0f} | {c:.0f} | {roots:.0f} | "
                         + " | ".join(f"{t:.0f} ({100 * (t - comp) / t:.0f}% chép)" for t in tot)
                         + f" | {best:.0f} ({100 * (best - comp) / best:.0f}% chép) |")
        lines.append("")
    lines.append("Chu kỳ tính của sinh khóa đã gồm ghép khác prime (thay đổi 9). Chép và tính được cộng nối tiếp "
                 "(chưa chồng nhau), đúng với giao diện 1.0 vì host không được truy cập bộ nhớ khi lõi đang chạy.\n")


def main():
    cost, rate, lat, ntt_batch = make_cost()
    if MOT_LAN:
        raw = {int(k): v for k, v in json.loads((ROOT / "study" / "results" / "fn_dsa_workload_lai.json")
                                                 .read_text()).items()}
    else:
        build()
        raw = {logn: run(logn) for logn in (9, 10)}
    (ROOT / "study" / "results" / f"fn_dsa_workload{SUFFIX}.json").write_text(json.dumps(raw, indent=1) + "\n")
    lines = ["# FN-DSA trên FlexTransform: NTT chiếm bao nhiêu, rút gọn trên mảng tốn bao nhiêu\n",
             f"Bản chuẩn R8 + NTRUGen đi kèm, build WSL gcc LP64, `FALCON_FPR_MODE=2`, AVX2 tắt. {KEYS} khóa × "
             f"{SIGS} chữ ký mỗi N. Mọi lời gọi kernel được đếm và đo thời gian phần mềm "
             "(`sim/ref/workload_profile.c`). Chu kỳ phần cứng = số lời gọi × dự báo của kiến trúc v1 mục 4 "
             f"(độ trễ bộ nhân 4), cộng {CMD_OVERHEAD} chu kỳ mỗi lệnh. Số liệu tính cho **một** lần sinh khóa / mở "
             "rộng khóa / ký / kiểm.\n",
             (f"**Tile một làn, một lane 32 bit** (spec 2.0, 10 từ 31/10/2026): mọi q, kể cả 12289, chạy trên cùng "
              f"Montgomery R = 2^32, dữ liệu dạng 4. Butterfly/chu kỳ của lõi: trên mảng (thiết kế v1 từ 01/11/2026) "
              f"{rate[(32, False)]:.3g}, riêng (bản đối chứng) {rate[(32, True)]:.3g}. Độ trễ mỗi lượt (gồm đọc/ghi RAM): {lat[(32, False)]} / "
              f"{lat[(32, True)]}. Thời gian NTT lấy từ model/single_lane_feed.py (xung đột bank và gói root). Số lời gọi "
              "lấy lại từ fn_dsa_workload_lai.json; cột \"trên mảng\" là thiết kế v1 từ 01/11/2026. Giao diện giữ R = 2^16 của 1.0 cho "
              "q = 12289: `tomonty` là một lượt Mont(x, 2^48 mod q); `montymul_ntt` là hai lượt, Mont(a, b) rồi nhân "
              "2^48 mod q.\n") if MOT_LAN else
             (f"Tốc độ nhịp NTT (16 tile): 16 bit trên mảng {rate[(16, False)]:.3g}, riêng {rate[(16, True)]:.3g}; "
             f"32 bit trên mảng {rate[(32, False)]:.3g}, riêng {rate[(32, True)]:.3g} nhịp/chu kỳ. Độ trễ nhịp "
             f"(gồm đọc/ghi RAM): 16 bit {lat[(16, False)]} / {lat[(16, True)]}, 32 bit {lat[(32, False)]} / "
             f"{lat[(32, True)]}.\n")]
    summary = {}
    for logn in (9, 10):
        n = 1 << logn
        lines.append(f"## N = {n}\n")
        lines.append("### Số lời gọi và thời gian phần mềm (mỗi thao tác)\n")
        lines.append("| Pha | Thời gian phần mềm (ms) | Lời gọi FFT | Lời gọi NTT | Lời gọi tạo bảng root | "
                     "Phần mềm trong FFT | trong NTT | trong tạo bảng |")
        lines.append("|---|---:|---:|---:|---:|---:|---:|---:|")
        an = analyse(raw[logn], cost, CMD_OVERHEAD)
        for ph, r in an.items():
            sw = r["sw_ms"]
            pct = {g: 100 * r["sw_kernel_ms"].get(g, 0) / sw for g in ("FFT", "NTT", "NẠP ROOT")}
            lines.append(f"| {ph} | {sw:.3f} | {r['calls'].get('FFT', 0):.0f} | {r['calls'].get('NTT', 0):.0f} | "
                         f"{r['calls'].get('NẠP ROOT', 0):.0f} | {pct['FFT']:.1f}% | {pct['NTT']:.1f}% | "
                         f"{pct['NẠP ROOT']:.1f}% |")
        lines.append("\n### Chu kỳ phần cứng dự báo (mỗi thao tác)\n")
        lines.append("| Pha | FFT | NTT trên mảng | NTT riêng | Nạp root (lõi) | Host ghi vùng C (dòng) | "
                     "Tổng trên mảng | Tổng riêng | Tăng | NTT/tổng (trên mảng) |")
        lines.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
        summary[n] = {}
        for ph, r in an.items():
            a, d = r[False], r[True]
            ta = a["FFT"] + a["NTT"] + a["NẠP ROOT"]
            td = d["FFT"] + d["NTT"] + d["NẠP ROOT"]
            inc = 100 * (ta / td - 1) if td else 0
            share = 100 * a["NTT"] / ta if ta else 0
            summary[n][ph] = {"total_on_array": ta, "total_dedicated": td, "increase_pct": inc,
                              "ntt_share_pct": share, "host_lines": r["host_lines"]}
            lines.append(f"| {ph} | {a['FFT']:.0f} | {a['NTT']:.0f} | {d['NTT']:.0f} | {a['NẠP ROOT']:.0f} | "
                         f"{r['host_lines']:.0f} | {ta:.0f} | {td:.0f} | {inc:+.1f}% | {share:.1f}% |")
        an0 = analyse(raw[logn], cost, 0)
        lines.append("\nKhông tính chi phí cố định mỗi lệnh: tăng " + ", ".join(
            f"{ph} {100 * ((r[False]['FFT'] + r[False]['NTT'] + r[False]['NẠP ROOT']) / max(1, r[True]['FFT'] + r[True]['NTT'] + r[True]['NẠP ROOT']) - 1):+.1f}%"
            for ph, r in an0.items()) + ".\n")
    lines.append("## NTT của sinh khóa theo kích thước (lời gọi mỗi lần sinh khóa, N = 1024)\n")
    lines.append("| logn | NTT prime 31 bit | NTT ngược | Tạo bảng (gm, igm, cả hai) | Chu kỳ một NTT, trên mảng / riêng |")
    lines.append("|---:|---:|---:|---:|---:|")
    calls = {}
    for k in raw[10]["phases"]["keygen"]["kernels"]:
        calls[(k["kind"], k["logn"])] = k["calls"] / raw[10]["keys"]
    for logn in range(0, 11):
        c = [calls.get((kd, logn), 0) for kd in ("p31_ntt", "p31_intt", "p31_mkgm", "p31_mkigm", "p31_mkgmigm")]
        if any(c):
            one = "đồng nhất, host bỏ qua" if logn == 0 else \
                f"{cost('p31_ntt', logn, False)[0]} / {cost('p31_ntt', logn, True)[0]}"
            lines.append(f"| {logn} | {c[0]:.0f} | {c[1]:.0f} | {c[2]:.0f} / {c[3]:.0f} / {c[4]:.0f} | {one} |")
    lines.append("")

    lines.append("## Ghép nhiều đa thức cùng prime vào một lệnh (sinh khóa)\n")
    lines.append("Một lời gọi NTT prime 31 bit được ghép vào lô đang mở khi: ngay sau lời gọi cuối của lô (không có kernel "
                 "nào khác xen giữa), cùng chiều, cùng logn, cùng prime, cùng bảng root, mảng không chồng lên nhau, và "
                 "lô chưa vượt giới hạn của spec 2.0 (N < 64: jobs · N ≤ 32, tối đa 8; N ≥ 64: tối đa 2). Chỗ gọi của "
                 "các lời gọi được ghép liệt kê ở cuối để kiểm tính độc lập trong mã nguồn.\n")
    lines.append("| N | Chu kỳ sinh khóa, một đa thức mỗi lệnh: trên mảng / riêng | Tăng | Có ghép: trên mảng / riêng "
                 "| Tăng | Có ghép, trên mảng so với không ghép, riêng |")
    lines.append("|---:|---:|---:|---:|---:|---:|")
    batched = {}
    for logn in (9, 10):
        a1 = summary[1 << logn]["keygen"]
        kb = keygen_batched(raw[logn], cost, ntt_batch, CMD_OVERHEAD)
        batched[1 << logn] = kb
        lines.append(f"| {1 << logn} | {a1['total_on_array']:.0f} / {a1['total_dedicated']:.0f} | "
                     f"{a1['increase_pct']:+.1f}% | {kb[False]['total']:.0f} / {kb[True]['total']:.0f} | "
                     f"{100 * (kb[False]['total'] / kb[True]['total'] - 1):+.1f}% | "
                     f"{100 * (kb[False]['total'] / a1['total_dedicated'] - 1):+.1f}% |")
    lines.append("\n### Cận trên khi ghép **khác prime** (mỗi tile một modulus)\n")
    lines.append("Trong một đoạn chỉ có công việc NTT prime 31 bit (không có kernel loại khác xen giữa), các lời gọi cùng "
                 "chiều và cùng logn với N < 64 được gom thành lệnh tới min(8, 64/N) đa thức, dù khác prime (mỗi đa "
                 "thức nằm trên các tile riêng, mỗi tile một modulus). N ≥ 64 giữ một prime mỗi lệnh. Giả định vòng "
                 "lặp theo prime tách được (các làn RNS độc lập); đây là cận trên. Nạp bảng root giữ nguyên số lần.\n")
    lines.append("| N | Ghép khác prime: trên mảng / riêng | Tăng | Trên mảng so với không ghép, riêng | "
                 "NTT sinh khóa, trên mảng: không ghép → ghép khác prime |")
    lines.append("|---:|---:|---:|---:|---:|")
    for logn in (9, 10):
        a1 = summary[1 << logn]["keygen"]
        kx = keygen_batched(raw[logn], cost, ntt_batch, CMD_OVERHEAD, "p31_cross_prime_batches")
        k1 = keygen_batched(raw[logn], cost, ntt_batch, CMD_OVERHEAD, "p31_batches")
        batched[(1 << logn, "x")] = kx
        single_ntt = sum((cost(k["kind"], k["logn"], False)[0] + CMD_OVERHEAD) * k["calls"]
                         for k in raw[logn]["phases"]["keygen"]["kernels"]
                         if k["kind"] in ("p31_ntt", "p31_intt") and k["logn"] > 0) / raw[logn]["keys"]
        lines.append(f"| {1 << logn} | {kx[False]['total']:.0f} / {kx[True]['total']:.0f} | "
                     f"{100 * (kx[False]['total'] / kx[True]['total'] - 1):+.1f}% | "
                     f"{100 * (kx[False]['total'] / a1['total_dedicated'] - 1):+.1f}% | "
                     f"{single_ntt:.0f} → {kx[False]['ntt']:.0f} |")
    io_section(lines, raw, summary, batched)
    if MOT_LAN:
        # q = 12289 buffers: one 16-bit cell per coefficient before, one 32-bit word (format 4) now. Lines of
        # those buffers without reuse: NTT, iNTT, tomonty one buffer in and out, montymul two in, one out.
        lines.append("\n### Dạng 4 cho q = 12289\n")
        lines.append("Một lane 32 bit: hệ số q = 12289 lưu dạng 4 (một từ 32 bit), nên mọi dòng chép của bộ đệm q = 12289 "
                     "tăng gấp đôi. Cột dưới đây là số dòng của các bộ đệm đó khi không giữ lại (dạng 3) và phần tăng thêm; "
                     "bảng chép ở trên vẫn tính theo dạng 3.\n")
        lines.append("| N | Pha | Dòng bộ đệm q = 12289, dạng 3 | Thêm do dạng 4 | So với dòng không giữ |")
        lines.append("|---:|---|---:|---:|---:|")
        for logn in (9, 10):
            n, r = 1 << logn, raw[logn]
            ops = {"keygen": r["keys"], "expand": r["keys"], "sign": r["keys"] * r["sigs_per_key"],
                   "verify": r["keys"] * r["sigs_per_key"]}
            for ph in ("keygen", "expand", "sign", "verify"):
                mq = sum(k["calls"] * (3 if k["kind"] == "q12289_modmul" else 2) * (2 * (1 << k["logn"]) // 16)
                         for k in r["phases"][ph]["kernels"] if k["kind"].startswith("q12289")) / ops[ph]
                io = r["phases"][ph]["io_lines"]
                allio = (io["in_all"] + io["out_all"]) / ops[ph]
                lines.append(f"| {n} | {ph} | {mq:.0f} | +{mq:.0f} | +{100 * mq / allio:.1f}% |")
        lines.append("")
    lines.append("\nPhân bố lô cùng prime (sinh khóa N = 1024, mỗi lần sinh khóa):\n")
    lines.append("| Chiều | logn | Số đa thức mỗi lô | Số lô |")
    lines.append("|---|---:|---:|---:|")
    for b in raw[10]["phases"]["keygen"]["p31_batches"]:
        if b["logn"] > 0:
            lines.append(f"| {'xuôi' if b['dir'] == 0 else 'ngược'} | {b['logn']} | {b['jobs']} | "
                         f"{b['count'] / raw[10]['keys']:.1f} |")
    loc = site_lines(raw[10]["site_pairs"] + raw[9]["site_pairs"])
    lines.append("\nCác cặp chỗ gọi được ghép (lời gọi đầu lô → lời gọi được ghép), N = 1024:\n")
    lines.append("| Lời gọi đầu lô | Lời gọi được ghép | Số lần |")
    lines.append("|---|---|---:|")
    for sp in sorted(raw[10]["site_pairs"], key=lambda s: -s["count"]):
        lines.append(f"| {loc.get(sp['first'], sp['first'])} | {loc.get(sp['joined'], sp['joined'])} | {sp['count']} |")
    lines.append("")
    (ROOT / "study" / "results" / f"fn_dsa_workload{SUFFIX}.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
