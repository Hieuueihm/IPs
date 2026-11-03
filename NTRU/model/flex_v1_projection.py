"""Ceilings and projections for docs/architecture_v1_proposal.md.

Every printed value carries a tag:
  [measured]   copied from RTL profiling (docs/kernel_parallelism_profile.md)
  [model]      exact count from REF16 parameters or study/results/fft_batch_supply.json
  [projection] model + an explicit assumption (pipeline latency L per stage barrier)

REF16: 16 tiles x 4 leaf 16x16 = 64 leaves; store = 64 banks x 16 bit, 1R+1W per bank;
FFT root port R_tw complex roots/cycle (REF16: 1). No RTL of the proposed controller
exists; projections are not speedups.

Run: python model/flex_v1_projection.py  (writes study/results/flex_v1_projection.md)
"""
import json
from math import ceil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LEAVES, BANKS, BANK_BITS = 64, 64, 16
OUT = []

MEASURED = {  # cycles/kernel, docs/kernel_parallelism_profile.md (no-pause run)
    ("FFT", 32, 1024): 52992, ("FFT", 64, 1024): 52992, ("FFT", 128, 1024): 52992,
    ("FFT", 128, 512): 23552,
    ("NTT", 12289, 1024): 800, ("NTT", 12289, 256): 160, ("NTT", 3329, 256): 160,
    ("NTT", 12289, 8): 20, ("NTT", 12289, 16): 20, ("NTT", 12289, 32): 30,
}


def say(s=""):
    print(s)
    OUT.append(s)


def products_per_cycle(width):
    """Exact real/integer products per cycle when one product uses (W/16)^2 leaf slots."""
    return LEAVES // (width // 16) ** 2


def section_law():
    say("## 1. Luật lane theo độ rộng toán hạng [model]\n")
    say("| Miền | Toán hạng | Leaf/tích | Tích/chu kỳ (64 leaf) | Đơn vị công việc/chu kỳ |")
    say("|---|---|---:|---:|---|")
    for w in (32, 64, 128):
        p = products_per_cycle(w)
        say(f"| FFT | W{w} (Q{w//2}.{w//2}) | {(w // 16) ** 2} | {p} | {p / 3:.3g} butterfly (3M) |")
    for w, name in ((16, "RES16: 3329, 12289"), (32, "RES32: 8380417 (đề xuất)")):
        p = products_per_cycle(w)
        say(f"| NTT | {name} | {(w // 16) ** 2} | {p} | {p} butterfly-tầng (1 modmul/BF) |")
    say(f"| NTT | RES32 RNS tổng quát (tùy chọn) | 4 ×3 tích | {products_per_cycle(32)} | "
        f"{products_per_cycle(32) / 3:.3g} modmul (T, m, m·q trên tile) |")
    say("\nCùng một luật cho hai miền: tích/chu kỳ = 64 / (w/16)². Hạng FFT bị bỏ theo contract "
        "(W128: 58/64 leaf) không làm tăng số tích/chu kỳ trong bố trí cây hiện tại.\n")


def data_bank(i):
    """Current REF16 coefficient bank map (same as model/fft_batch_supply.py)."""
    return (i & 63) ^ ((i >> 2) & 48) ^ ((i >> 4) & 48)


def fft_stages(n, width, lanes, inverse=False):
    """Batches per stage, as model/fft_batch_supply.py (FFT or IFFT), with root indices."""
    hn, limbs = n // 2, width // 16
    span, groups = (2, hn) if inverse else (hn, 2)
    out = []
    for _ in range(n.bit_length() - 2):
        bfs = [([g * span + o, g * span + o + hn, g * span + o + span // 2,
                 g * span + o + span // 2 + hn], groups + g)
               for g in range(groups // 2) for o in range(span // 2)]
        batches = []
        for s in range(0, len(bfs), lanes):
            chunk = bfs[s:s + lanes]
            addr = [i * limbs + l for idx, _ in chunk for i in idx for l in range(limbs)]
            cnt = {}
            for a in addr:
                cnt[data_bank(a)] = cnt.get(data_bank(a), 0) + 1
            batches.append((len(chunk), max(cnt.values()), (len(addr) + 63) // 64,
                            sorted({r for _, r in chunk})))
        out.append(batches)
        span, groups = (span * 2, groups // 2) if inverse else (span // 2, groups * 2)
    return out


def fft_projection(width, n, r_tw, lat, ideal_map, lanes=None, inverse=False):
    """Stage time = max(compute, data rounds, root-bank rounds) + L; roots interleaved idx mod R_tw."""
    lanes = lanes or {32: 16, 64: 4, 128: 1}[width]
    total = 0
    worst = {"compute": 0, "data": 0, "twiddle": 0}
    for batches in fft_stages(n, width, lanes, inverse):
        compute = sum(ceil(3 * b / products_per_cycle(width)) for b, *_ in batches)
        data = sum(cap if ideal_map else rd for _, rd, cap, _ in batches)
        twiddle = 0
        for *_, roots in batches:
            per_bank = {}
            for r in roots:
                per_bank[r % r_tw] = per_bank.get(r % r_tw, 0) + 1
            twiddle += max(per_bank.values())
        stage = max(compute, data, twiddle)
        for k, v in (("compute", compute), ("data", data), ("twiddle", twiddle)):
            if v == stage:
                worst[k] += 1
        total += stage + lat
    return total, worst


def section_fft(supply):
    say("## 2. FFT N1024: dự báo cycle/kernel [projection]\n")
    say("Giả định: controller tách đọc/tính/ghi, II = 1 theo batch, đọc và ghi song song (1R+1W), "
        "rào chắn giữa tầng tốn L chu kỳ. Batch và map bank giống "
        "`model/fft_batch_supply.py` (kiểm khớp bên dưới); root store xen kẽ theo idx mod R_tw, "
        "đếm chính xác số lần đọc mỗi bank root; không cache root giữa batch. "
        "Đo hiện tại [measured] = 52 992 cycle cho cả ba W.\n")
    for w in (32, 64, 128):   # consistency with the JSON produced by fft_batch_supply.py
        case = next(c for c in supply["cases"]
                    if c["n"] == 1024 and c["width_bits"] == w and c["op"] == "FFT")
        mine = fft_stages(1024, w, case["proposed_butterflies_per_batch"])
        for s, b in zip(case["stages"], mine):
            assert s["data_read_rounds_sum"] == sum(x[1] for x in b)
            assert s["root_reads_sum_no_cross_batch_cache"] == sum(len(x[3]) for x in b)
    say("- PASS batch/map khớp `study/results/fft_batch_supply.json` (W32/64/128, N1024).\n")
    say("| W | Batch | Map bank | R_tw | L | Cycle/kernel | So với đo | Tầng chặn bởi tính/dữ liệu/twiddle |")
    say("|---:|---|---|---:|---:|---:|---:|---|")
    rows = {}
    for w in (32, 64, 128):
        cyc, worst = fft_projection(w, 1024, 1, 8, False, lanes=1)
        rows[(w, "b1", 1, 8)] = cyc
        say(f"| {w} | 1 BF (chỉ pipeline) | hiện tại | 1 | 8 | {cyc} | "
            f"{MEASURED[('FFT', w, 1024)] / cyc:.1f}× | "
            f"{worst['compute']}/{worst['data']}/{worst['twiddle']} |")
    for w in (32, 64, 128):
        for ideal in (False, True):
            for r in (1, 4, 16):
                for lat in (0, 8):
                    if lat == 0 and not (r == 16 and ideal):
                        continue
                    cyc, worst = fft_projection(w, 1024, r, lat, ideal)
                    rows[(w, ideal, r, lat)] = cyc
                    say(f"| {w} | {{32: 16, 64: 4, 128: 1}}[w] | {'lý tưởng' if ideal else 'hiện tại'} | "
                        f"{r} | {lat} | {cyc} | {MEASURED[('FFT', w, 1024)] / cyc:.1f}× | "
                        f"{worst['compute']}/{worst['data']}/{worst['twiddle']} |"
                        .replace("{32: 16, 64: 4, 128: 1}[w]", str({32: 16, 64: 4, 128: 1}[w]) + " BF"))
    for c in supply["cases"]:                       # IFFT and all N: consistency with JSON
        mine = fft_stages(c["n"], c["width_bits"], c["proposed_butterflies_per_batch"],
                          c["op"] == "IFFT")
        for s, b in zip(c["stages"], mine):
            assert s["data_read_rounds_sum"] == sum(x[1] for x in b)
            assert s["root_reads_sum_no_cross_batch_cache"] == sum(len(x[3]) for x in b)
    say("\n- PASS batch/map khớp JSON cho mọi case FFT và IFFT, N4..N1024.\n")
    say("FFT và IFFT, N512/N1024, map hiện tại, L = 8 (A1 + A2, có/không B):\n")
    say("| Op | N | W | R_tw = 1 | R_tw = 4 | T128/T_W (R_tw = 4) |")
    say("|---|---:|---:|---:|---:|---:|")
    for inv in (False, True):
        for n in (512, 1024):
            t128 = fft_projection(128, n, 4, 8, False, inverse=inv)[0]
            for w in (32, 64, 128):
                r1 = fft_projection(w, n, 1, 8, False, inverse=inv)[0]
                r4 = fft_projection(w, n, 4, 8, False, inverse=inv)[0]
                rows[("IFFT" if inv else "FFT", n, w)] = r4
                say(f"| {'IFFT' if inv else 'FFT'} | {n} | {w} | {r1} | {r4} | {t128 / r4:.2f} |")
    say("\nĐộ nhạy theo L (map hiện tại, R_tw = 4, batch theo W):\n")
    say("| W | L = 8 | L = 12 | L = 16 |")
    say("|---:|---:|---:|---:|")
    for w in (32, 64, 128):
        vals = [fft_projection(w, 1024, 4, lat, False)[0] for lat in (8, 12, 16)]
        say(f"| {w} | " + " | ".join(str(v) for v in vals) + " |")
    say("")
    return rows


# Leaf slots per modmul with reduction on the array, scheduled inside one tile
# (model/mont_on_array_tile.py): 16 bit = 3 beats × 1 leaf; 32 bit = 3 beats × 4 leaves
# (the m beat needs only 3 of 4 leaves, model/arch_checks.py D2, but the 4th cannot be reused
# by another 32-bit job of the same tile).
LEAVES_PER_MODMUL_ON_ARRAY = {16: 3, 32: 12}


def ntt_projection(layers, n, jobs, width, lat, paired=True, on_array=False):
    """Cycles for one batch of `jobs` polynomials of size n.

    on_array=True: Montgomery reduction products (m, m·q) also run on the shared array.
    """
    lanes = (LEAVES / LEAVES_PER_MODMUL_ON_ARRAY[width] if on_array
             else products_per_cycle(width))   # modmul per cycle
    coeff_per_cycle = BANKS * BANK_BITS // width
    passes = ceil(layers / 2) if paired else layers
    total = 0
    left = layers
    for _ in range(passes):
        lyr = 2 if (paired and left >= 2) else 1
        left -= lyr
        bf = jobs * (n // 2) * lyr
        compute = ceil(bf / lanes)
        data = ceil(jobs * n / coeff_per_cycle)
        total += max(compute, data) + lat
    return total


def res32_with_rounds(layers, n, rounds, lat):
    """RES32: paired batch = 16 coefficients, single-layer batch = 32; each batch takes `rounds` reads."""
    total, left = 0, layers
    for _ in range(ceil(layers / 2)):
        lyr = 2 if left >= 2 else 1
        left -= lyr
        compute = ceil((n // 2) * lyr / products_per_cycle(32))
        data = (n // (16 if lyr == 2 else 32)) * rounds
        total += max(compute, data) + lat
    return total


def interleave2(layers, n, width, lat, on_array):
    """Two polynomials on two contexts: per pass max(2·frame, frame + L); returns cycles per job."""
    lanes = (LEAVES / LEAVES_PER_MODMUL_ON_ARRAY[width] if on_array else products_per_cycle(width))
    cpc = BANKS * BANK_BITS // width
    total, left = 0, layers
    for _ in range(ceil(layers / 2)):
        lyr = 2 if left >= 2 else 1
        left -= lyr
        frame = max(ceil((n // 2) * lyr / lanes), ceil(n / cpc))
        total += max(2 * frame, frame + lat)
    return total / 2


def section_ntt_on_array():
    say("## 3c. NTT khi rút gọn Montgomery chạy trên mảng nhân [projection, đã thay bằng mục 3d]\n")
    say("Mục này dùng cùng L cho cả hai cách rút gọn nên đánh giá quá lạc quan; tài liệu dùng mục 3d.\n")
    say("16 bit: 3 leaf/phép nhân modulo → 21,3 phép/chu kỳ; 32 bit: 3 lượt × 4 leaf trong một tile → "
        "5,33 phép/chu kỳ (model/mont_on_array_tile.py). Cùng giả định với mục 3.\n")
    say("| Trường hợp | Rút gọn riêng, L=8 | Trên mảng, L=8 | Trên mảng, L=12 | Trên mảng, L=16 | "
        "Trên mảng, 2 đa thức xen kẽ (mỗi đa thức), L=8 | Đo hiện tại |")
    say("|---|---:|---:|---:|---:|---:|---:|")
    for name, q, w, n, layers in (("q12289 N1024", 12289, 16, 1024, 10),
                                  ("q12289 N256", 12289, 16, 256, 8),
                                  ("q3329 N256", 3329, 16, 256, 7),
                                  ("q8380417 N256 (32 bit)", None, 32, 256, 8)):
        ded = ntt_projection(layers, n, 1, w, 8)
        arr = [ntt_projection(layers, n, 1, w, lat, on_array=True) for lat in (8, 12, 16)]
        il = interleave2(layers, n, w, 8, True)
        meas = MEASURED.get(("NTT", q, n), "—")
        say(f"| {name} | {ded} | {arr[0]} | {arr[1]} | {arr[2]} | {il:g} | {meas} |")
    say("\nMô hình ở L đo được (ngưỡng giả thuyết = 1,25 × mô hình), L = 9: "
        + ", ".join(f"{nm} = {ntt_projection(ly, n, 1, w, 9, on_array=True)}"
                    for nm, w, n, ly in (("q12289 N1024", 16, 1024, 10), ("q12289 N256", 16, 256, 8),
                                         ("q8380417 N256", 32, 256, 8)))
        + f", 2 đa thức q12289 N256 = {interleave2(8, 256, 16, 9, True):g}/đa thức.\n")


def section_ntt_latency_aware():
    """Pass time from the tile model's two-layer frames: frames/(16*rate) + frame latency + read/write."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("tile", ROOT / "model" / "mont_on_array_tile.py")
    tile = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(tile)
    rw = 2                                    # one RAM read + one write cycle around a frame
    say("## 3d. NTT có tính độ trễ nhịp hai tầng [projection]\n")
    say("Tốc độ nhịp và độ trễ nhịp lấy từ mô hình tile (`model/mont_on_array_tile.py`, nhịp hai tầng, "
        f"tầng 2 chờ tầng 1); thêm {rw} chu kỳ đọc/ghi RAM. Mỗi lượt = số nhịp/(16 × tốc độ) + độ trễ. "
        "Xen kẽ 2 đa thức: mỗi lượt max(2·F, F + độ trễ).\n")
    say("| Trường hợp | Độ trễ bộ nhân | Rút gọn | Nhịp/chu kỳ/tile | Độ trễ nhịp | Một đa thức | "
        "Hai đa thức xen kẽ (mỗi đa thức) | Đo hiện tại |")
    say("|---|---:|---|---:|---:|---:|---:|---:|")
    profs = {16: tile.PROFILES[0], 32: tile.PROFILES[2]}
    rows = {}
    for name, w, n, layers, q in (("q12289 N1024", 16, 1024, 10, 12289), ("q12289 N256", 16, 256, 8, 12289),
                                  ("q8380417 N256 (32 bit)", 32, 256, 8, None)):
        for lat_mul in (3, 4):
            for ded in (True, False):
                r = tile.run_frames(profs[w], lat_mul, 1, 1, 1500, 0.0, 10 ** 9, seed=1, dedicated=ded)
                rate = 1 / round(1 / r["frame_rate"])          # 1, 1/3, 1/4, 1/12 frames/cycle/tile
                lat = r["min_latency"] + rw
                frames = n // 4
                f = ceil(frames / (16 * rate))
                passes = layers // 2
                one = passes * (f + lat)
                two = passes * max(2 * f, f + lat) / 2
                rows[(name, lat_mul, ded)] = (one, two)
                meas = MEASURED.get(("NTT", q, n), "—")
                say(f"| {name} | {lat_mul} | {'riêng' if ded else 'trên mảng'} | {rate:.3g} | {lat} | {one} | "
                    f"{two:g} | {meas} |")
    say("\nTỉ lệ chậm của rút gọn trên mảng so với rút gọn riêng (độ trễ bộ nhân 4):")
    for name in ("q12289 N1024", "q12289 N256", "q8380417 N256 (32 bit)"):
        d1, d2 = rows[(name, 4, True)]
        a1, a2 = rows[(name, 4, False)]
        say(f"- {name}: một đa thức {a1 / d1:.2f}×, hai đa thức xen kẽ {a2 / d2:.2f}×")
    say("")
    return rows


def section_ntt_prime31():
    """NTT modulo a 31-bit NTRUGen prime (32-bit lanes, on-array reduction), N = 2..1024, incl. root load."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("tile", ROOT / "model" / "mont_on_array_tile.py")
    tile = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(tile)
    rw = 2                                     # RAM read + write around a frame
    r = tile.run_frames(tile.PROFILES[2], 4, 1, 1, 1500, 0.0, 10 ** 9, seed=1)
    rate = 16 / round(1 / r["frame_rate"])     # frames/cycle for 16 tiles (4/3)
    lat = r["min_latency"] + rw
    say("## 3e. NTT modulo prime 31 bit của NTRUGen (lane 32 bit, rút gọn trên mảng) [projection]\n")
    say(f"Độ trễ bộ nhân 4; {rate:.3g} nhịp/chu kỳ cho 16 tile, độ trễ nhịp {lat} (mô hình tile, cấu hình 32 bit). "
        "Lượt một tầng cuối khi logn lẻ: n/2 butterfly ở 16/3 phép nhân modulo/chu kỳ, lấy độ trễ bằng một nhịp "
        "(cận trên). Xung đột bank ở N1024 (20% chu kỳ đọc hai lượt) không làm chậm: phần tính chỉ dùng "
        "1,33 trong 4 nhịp/chu kỳ mà bộ nhớ cấp được. Nạp prime theo spec 2.0 (02 mục 3): host ghi vùng C "
        "(1 dòng đầu + N/4 dòng 128 bit mỗi bảng), rồi phép nạp xếp ~N/2 gói mỗi bảng qua 4 bank "
        "(ước lượng thấp nhất N/8 chu kỳ mỗi bảng). Một lần nạp ở N lớn nhất dùng được cho mọi N nhỏ hơn.\n")
    say("| N | Lượt hai tầng | Lượt một tầng | NTT (chu kỳ) | Host ghi vùng C, một bảng / hai bảng (dòng) | "
        "Phép nạp, một bảng / hai bảng (chu kỳ, thấp nhất) |")
    say("|---:|---:|---:|---:|---:|---:|")
    rows = {}
    for logn in range(1, 11):
        n = 1 << logn
        paired, single = logn // 2, logn % 2
        t = paired * (ceil((n // 4) / rate) + lat) + single * (ceil((n // 2) / (16 / 3)) + lat)
        lines1, lines2 = 1 + ceil(n / 4), 1 + ceil(n / 2)
        load1 = max(1, n // 8)
        rows[n] = (t, lines2, 2 * load1)
        say(f"| {n} | {paired} | {single} | {t} | {lines1} / {lines2} | {load1} / {2 * load1} |")
    say("")
    return rows


def section_ntt():
    say("## 3. NTT: dự báo cycle/batch [projection]\n")
    say("Giả định: frame II = 1, đọc/ghi song song, map bank không xung đột cho hai tầng "
        "(đã kiểm 28 case ở docs/stream_core_results.md cho RES16), rào chắn L chu kỳ/lượt.\n")
    say("| Profile | N | Job/batch | Tầng | Đo hiện tại (1 job) | L=0 | L=8 | Cycle/job ở L=8 | So với đo/job |")
    say("|---|---:|---:|---:|---:|---:|---:|---:|---:|")
    cases = [("q12289 RES16", 12289, 16, 1024, 10, 1), ("q12289 RES16", 12289, 16, 256, 8, 1),
             ("q3329 RES16", 3329, 16, 256, 7, 1), ("q12289 RES16", 12289, 16, 8, 3, 8),
             ("q12289 RES16", 12289, 16, 16, 4, 4), ("q12289 RES16", 12289, 16, 32, 5, 2),
             ("q8380417 RES32 (đề xuất)", None, 32, 256, 8, 1)]
    for name, q, w, n, layers, jobs in cases:
        c0 = ntt_projection(layers, n, jobs, w, 0)
        c8 = ntt_projection(layers, n, jobs, w, 8)
        meas = MEASURED.get(("NTT", q, n))
        ratio = f"{meas / (c8 / jobs):.1f}×" if meas else "—"
        say(f"| {name} | {n} | {jobs} | {layers} | {meas if meas else '—'} | {c0} | {c8} | "
            f"{c8 / jobs:.1f} | {ratio} |")
    say("\nRES32 dùng 2 bank/hệ số (32 hệ số/chu kỳ), 1 tile/modmul (16 modmul/chu kỳ); "
        "chưa có RTL nên không có số đo. Không xung đột bank (mục 3b). Nếu xung đột 2 lượt, "
        f"dự báo sẽ là {res32_with_rounds(8, 256, 2, 8)} cycle — giữ để đối chiếu.\n")
    say("Độ nhạy theo L (L đo được của frame NTT hiện tại ≈ 9: READ, LATCH, ISSUE, 5 chờ mảng, WRITE):\n")
    say("| Profile | N | L = 8 | L = 12 | L = 16 |")
    say("|---|---:|---:|---:|---:|")
    for name, w, n, layers in (("q12289 RES16", 16, 1024, 10), ("q12289 RES16", 16, 256, 8),
                               ("q8380417 RES32", 32, 256, 8)):
        say(f"| {name} | {n} | " + " | ".join(str(ntt_projection(layers, n, 1, w, lat))
                                             for lat in (8, 12, 16)) + " |")
    say("")
    say("Xen kẽ hai context (REF16 có 2 context) cho hai đa thức độc lập cùng cấu hình, mỗi lượt "
        "tốn max(2·frame, frame + L) chu kỳ cho cả hai [projection, L = 8]:\n")
    say("| Profile | N | Tầng | 1 job, L=8 | 2 job xen kẽ | Cycle/job | So với đo/job |")
    say("|---|---:|---:|---:|---:|---:|---:|")
    for name, q, w, n, layers in (("q12289 RES16", 12289, 16, 1024, 10),
                                  ("q12289 RES16", 12289, 16, 256, 8),
                                  ("q8380417 RES32 (đề xuất)", None, 32, 256, 8)):
        lat = 8
        lanes, cpc = products_per_cycle(w), BANKS * BANK_BITS // w
        total, left = 0, layers
        for _ in range(ceil(layers / 2)):
            lyr = 2 if left >= 2 else 1
            left -= lyr
            frame = max(ceil((n // 2) * lyr / lanes), ceil(n / cpc))
            total += max(2 * frame, frame + lat)
        one = ntt_projection(layers, n, 1, w, lat)
        meas = MEASURED.get(("NTT", q, n))
        say(f"| {name} | {n} | {layers} | {one} | {total} | {total / 2:.1f} | "
            f"{(f'{meas / (total / 2):.1f}×') if meas else '—'} |")
    say("")


def section_res32_banks():
    say("## 3b. RES32: cặp bank có cấp đủ hai tầng không? [model]\n")
    say("Hệ số 32 bit chiếm hai bank 16 bit cùng row → 32 'siêu bank'. Mỗi chu kỳ phát 4 frame "
        "paired (16 hệ số, 16 modmul) hoặc 16 BF một tầng (32 hệ số). Nhóm hệ số theo thứ tự "
        "của `model/ntt_banked_supply.py` (groups). Đếm số lượt đọc tối đa mỗi siêu bank.\n")
    import importlib.util
    import sys
    sys.path.insert(0, str(ROOT / "scripts"))
    spec = importlib.util.spec_from_file_location("nbs", ROOT / "model" / "ntt_banked_supply.py")
    nbs = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(nbs)
    maps = {"bank(2c) >> 1 — layout spec 03.4 (LIMBS = 2), chốt": lambda c: nbs.bank(2 * c) >> 1,
            "bank(c) >> 1 — sai: map áp lên chỉ số hệ số": lambda c: nbs.bank(c) >> 1,
            "c & 31 — sai: bỏ qua map spec": lambda c: c & 31}
    say("| Map siêu bank | N | Kiểu | Lượt đọc tối đa/chu kỳ |")
    say("|---|---:|---|---:|")
    best = {}
    for name, mp in maps.items():
        for logn in (8, 10):
            for paired in (True, False):
                worst = 0
                ps = range(0, logn - 1, 2) if paired else range(logn)
                for p in ps:
                    gs = nbs.groups(logn, p, paired)
                    per_cycle = 4 if paired else 8      # groups of 4 coefficients per cycle
                    for s in range(0, len(gs), per_cycle):
                        idx = [c for g in gs[s:s + per_cycle] for c in g]
                        worst = max(worst, nbs.rounds(idx, mp))
                best[(name, logn, paired)] = worst
                say(f"| `{name}` | {1 << logn} | {'paired' if paired else 'một tầng'} | {worst} |")
    say("\n1 = không xung đột (II = 1). Với layout của spec (hệ số c ở word 2c, 2c + 1), thứ tự nhóm hiện có "
        "không xung đột; kiểm chi tiết (cả root bundle) ở `model/res32_bank_map.py`.\n")
    return best


def section_ceiling_check(fft_rows):
    say("## 4. Kiểm tra trần chỉ-tính-toán [model]\n")
    for w in (32, 64, 128):
        bf_per_cycle = products_per_cycle(w) / 3
        floor = ceil(2304 / bf_per_cycle)
        say(f"- FFT{w} N1024: 2 304 butterfly / {bf_per_cycle:.3g} BF/chu kỳ ≥ {floor} cycle → "
            f"tăng tối đa {MEASURED[('FFT', w, 1024)] / floor:.1f}× so với đo.")
        best = min(v for (ww, *_), v in fft_rows.items() if ww == w)
        assert best >= floor
    floor = ceil(1024 * 10 / 2 / products_per_cycle(16))
    say(f"- NTT q12289 N1024: 5 120 butterfly / 64 ≥ {floor} cycle → tối đa "
        f"{MEASURED[('NTT', 12289, 1024)] / floor:.1f}× so với đo 800.")
    say("")


def main():
    supply = json.loads((ROOT / "study" / "results" / "fft_batch_supply.json").read_text(encoding="utf-8"))
    section_law()
    rows = section_fft(supply)
    section_ntt()
    section_ntt_on_array()
    section_ntt_latency_aware()
    section_ntt_prime31()
    section_res32_banks()
    section_ceiling_check(rows)
    out = ROOT / "study" / "results" / "flex_v1_projection.md"
    out.write_text("# Trần và dự báo cho đề xuất kiến trúc v1\n\n" + "\n".join(OUT) + "\n",
                   encoding="utf-8")
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
