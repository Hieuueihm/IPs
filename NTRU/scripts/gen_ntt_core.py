"""Generate the tables of the minimal NTT core (hdl/core_ntt/) from model/ntt_core_sched.py and the network lists.

Outputs:
  hdl/core_ntt/ntt_core_gen.sv
      ntt_core_layer_rom  per layer (FFT flag and format, min-stride-2 flag, direction, logn, log2 h): tiles in use,
                          first butterfly p_t of each tile, kernel basis in plan order, same-superbank flag, cycles to the
                          next layer's start (affine enumeration, model/ntt_core_sched.py; overlap plan,
                          model/ntt_core_overlap.py; FFT model/fft_core_sched.py, model/fft_wide_sched.py)
      ntt_core_fft_timing FFT read offset of each format and root read stage of each tile (model/fft_wide_sched.py)
      ntt_core_sel        per tile: superbank -> index into the tile's read source lists (hdl/net/ntt_bank_net_s.sv)
      ntt_core_route      per superbank: which tile port reads / writes it this cycle, its row, and the write select
  hdl/core_ntt/root_pack_b<0..3>.mem   4 root-pack banks, 3072 rows x 96 bit: NTT packs, then FFT roots (32 / 64 / 128 bit)
  sim/core_ntt/vectors.txt             golden cases: profile logn op, N inputs, N expected (hex)
  sim/core_ntt/vectors_fft.txt         FFT golden cases: 3 + format, logn, op, N inputs, N expected (hex, 32 bit words)
  sim/core_ntt/vectors_p3.txt          profile 3 (loaded prime) cases: modulus, root tables, inputs, expected

Run: python scripts/gen_ntt_core.py
"""
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
_s = importlib.util.spec_from_file_location("sched", ROOT / "model" / "ntt_core_sched.py")
sched = importlib.util.module_from_spec(_s)
_s.loader.exec_module(sched)

TILES = 16
IW, SW, RW = 9, 5, 7          # butterfly index, superbank, row widths
XW = 4                        # network select width (from the network lists, set in main)
SEG_ROWS = {0: 128, 1: 32, 2: 32}
QS = {0: 12289, 1: 3329, 2: 8380417}


def seg_base(profile, inverse):
    base = 0
    for p in (0, 1, 2):
        for d in (False, True):
            if (p, d) == (profile, inverse):
                return base
            base += SEG_ROWS[p]
    raise KeyError


def layer_rom(L):
    """Layer table from the overlap plans (study/results/ntt_core_overlap.json, model/ntt_core_overlap.py, for the fixed
    profiles; study/results/ntt_prime_overlap.json, model/ntt_prime_core.py, for profile 3). A plan depends only on the
    layer structure (logn, number of skipped last layers hmin, direction), not on q, so the table is keyed by those."""
    say = L.append
    plans = []
    for key, layers in json.loads((ROOT / "study" / "results" / "ntt_core_overlap.json").read_text()).items():
        prof, logn, op = (int(x) for x in key.split(","))
        plans.append((int(prof == 1 and logn == 8), logn, op, layers, key))
    for key, layers in json.loads((ROOT / "study" / "results" / "ntt_prime_overlap.json").read_text()).items():
        logn, op, hmin = (int(x) for x in key.split(","))
        plans.append((hmin, logn, op, layers, "p3:" + key))
    rows = {}
    differ = []
    for hmin, logn, op, layers, key in plans:
        inverse = int(op == 6)
        for li, lay in enumerate(layers):
            hlog = lay["h"].bit_length() - 1
            firsts, kernel, count, same = sched.layer_config(logn, lay["h"])
            kern = [kernel[j] for j in lay["order"]]
            delta = layers[li + 1]["delta"] if li + 1 < len(layers) else 0
            row = (firsts, kern, same, delta)
            k = (hmin, inverse, logn, hlog)
            if k in rows and (rows[k][1] != kern or rows[k][3] != delta):
                differ.append((key, hlog))
                continue                              # the first plan found is kept (every plan is valid for any q)
            rows[k] = row
    assert not differ, ("plans differ for the same layer structure", differ[:4])
    fsched = _fft_sched()
    for logn in range(2, 11):                         # FFT 32 bit: key (fft = 1, ms2 = 0, inverse = 0)
        for hlog in range(logn - 1):
            firsts, kernel, count = fsched.layer_config(logn, 1 << hlog)
            # barrier per layer: last write e + 13 of the last butterfly; next start rounded up to the issue phase
            rows[("f", 0, logn, hlog)] = (firsts, kernel, False, 3 * count + 15)
    ws = _wide_sched()
    for f, L in ((1, 2), (2, 4)):                    # FFT 64 / 128 bit: one entry per block, repeated on its L tiles
        for logn in range(2, 11):
            for hlog in range(logn - 1):
                first, kernel, count = ws.layer_blocks(logn, 1 << hlog, L)
                firsts = {(b * L) | k: pb for b, pb in first.items() for k in range(L)}
                rows[(f"f{f}", 0, logn, hlog)] = (firsts, kernel, False, ws.delta(L, count))
    say("// Layer table (one entry per FFT flag and format, skipped last NTT layers, direction, logn, log2 h): tiles in use, first butterfly")
    say("// of each tile, kernel basis in the order of the overlap plan, same-superbank flag, cycles to the next layer's")
    say("// start. FFT 32 bit entries (model/fft_core_sched.py) use the FFT's logn and direction 0.")
    say("module ntt_core_layer_rom (")
    say("    input  wire              fft,")
    say("    input  wire [1:0]        fmt,")
    say("    input  wire [1:0]        hmin,")
    say("    input  wire              inverse,")
    say("    input  wire [3:0]        logn, hlog,")
    say("    output reg  [15:0]       tv,")
    say(f"    output reg  [16*{IW}-1:0]  p,")
    say(f"    output reg  [6*{IW}-1:0]   kb,")
    say("    output reg  [2:0]        kdim,")
    say("    output reg               same,")
    say("    output reg  [9:0]        delta")
    say(");")
    say("    always @* begin")
    say("        tv = 16'd0; p = 0; kb = 0; kdim = 3'd0; same = 1'b0; delta = 10'd0;")
    say("        case ({fft, fmt, hmin, inverse, logn, hlog})")
    for (ms2, inv, logn, hlog), (firsts, kern, same, delta) in sorted(rows.items(), key=lambda kv: str(kv[0])):
        fft = int(str(ms2).startswith("f"))
        fmt = int(ms2[1:]) if fft and len(ms2) > 1 else 0
        hm = 0 if fft else ms2
        assert len(kern) <= 6 and delta < 1024
        tv = sum(1 << t for t in firsts)
        pv = sum(firsts.get(t, 0) << (IW * t) for t in range(TILES))
        kv = sum(v << (IW * j) for j, v in enumerate(kern))
        say(f"            14'b{fft}{fmt:02b}{hm:02b}{inv}_{logn:04b}_{hlog:04b}: begin tv = 16'h{tv:04x}; p = {16 * IW}'h{pv:x}; "
            f"kb = {6 * IW}'h{kv:x}; kdim = 3'd{len(kern)}; same = 1'b{int(same)}; delta = 10'd{delta}; end")
    say("            default: ;")
    say("        endcase")
    say("    end")
    say("endmodule")
    say("")


def sel_module(L, net):
    say = L.append
    say("// Index of a superbank in each tile's read source lists (ntt_bank_net_s: read_lo / read_hi).")
    say("module ntt_core_sel (")
    say(f"    input  wire [16*{SW}-1:0]  sx, sy,")
    say(f"    output reg  [16*{XW}-1:0]   sel_xlo, sel_xhi, sel_ylo, sel_yhi")
    say(");")
    say("    always @* begin")
    say("        sel_xlo = 0; sel_xhi = 0; sel_ylo = 0; sel_yhi = 0;")
    for t in range(TILES):
        for op, s in (("x", "sx"), ("y", "sy")):
            lo, hi = net["read_lo"][f"{t}{op}"], net["read_hi"][f"{t}{op}"]
            sb = sorted({b >> 1 for b in lo})
            assert sb == sorted({b >> 1 for b in hi})
            say(f"        case ({s}[{SW}*{t} +: {SW}])")
            for v in sb:
                say(f"            5'd{v}: begin sel_{op}lo[{XW}*{t} +: {XW}] = {XW}'d{lo.index(2 * v)}; "
                    f"sel_{op}hi[{XW}*{t} +: {XW}] = {XW}'d{hi.index(2 * v + 1)}; end")
            say("            default: ;")
            say("        endcase")
    say("    end")
    say("endmodule")
    say("")


def route_module(L, net):
    say = L.append
    rd_src = {s: [] for s in range(32)}
    for t in range(TILES):
        for op in "xy":
            for b in net["read_lo"][f"{t}{op}"]:
                rd_src[b >> 1].append((t, op))
    say("// Per superbank: the read request (enable, row) and the write request (select, enable, row) of the tile port")
    say("// that uses it this cycle. Bank-indexed assignment guarantees at most one user per superbank per cycle.")
    say("// Superbanks arrive one-hot (decoded in the address stage), so each candidate is one AND.")
    say("module ntt_core_route (")
    say("    input  wire              clk,")
    say("    input  wire [16*32-1:0]  rxo, ryo,          // read superbank one-hot, already gated by valid")
    say(f"    input  wire [16*{RW}-1:0]  rxr, ryr,")
    say("    output reg  [63:0]       re,")
    say(f"    output reg  [64*{RW}-1:0]  ra,")
    say("    input  wire [16*32-1:0]  wxo, wyo,          // write superbank one-hot, already gated by valid")
    say(f"    input  wire [16*{RW}-1:0]  wxr, wyr,")
    say(f"    output reg  [64*{XW}-1:0]   wsel,")
    say("    output reg  [63:0]       wen,")
    say(f"    output reg  [64*{RW}-1:0]  wa          // registered: RAM write one cycle after wsel / wen")
    say(");")
    say(f"    reg [{RW}-1:0] row;")
    say("    always @* begin")
    say("        re = 64'd0; ra = 0; wen = 64'd0; wsel = 0;")
    for s in range(32):
        terms_v, terms_r = [], []
        for (t, op) in rd_src[s]:
            o, rw = ("rxo", "rxr") if op == "x" else ("ryo", "ryr")
            terms_v.append(f"{o}[{32 * t + s}]")
            terms_r.append(f"({{{RW}{{{o}[{32 * t + s}]}}}} & {rw}[{RW}*{t} +: {RW}])")
        if terms_v:
            v = " | ".join(terms_v)
            rr = " | ".join(terms_r)
            say(f"        re[{2 * s}] = {v}; re[{2 * s + 1}] = re[{2 * s}];")
            say(f"        row = {rr};")
            say(f"        ra[{RW}*{2 * s} +: {RW}] = row; ra[{RW}*{2 * s + 1} +: {RW}] = row;")
    for s in range(32):
        lo, hi = net["write"][str(2 * s)], net["write"][str(2 * s + 1)]
        for t in range(TILES):
            for op in "xy":
                if f"{t}{op}lo" in lo:
                    assert f"{t}{op}hi" in hi
                    o = "wxo" if op == "x" else "wyo"
                    say(f"        if ({o}[{32 * t + s}]) begin wen[{2 * s}] = 1'b1; wen[{2 * s + 1}] = 1'b1; "
                        f"wsel[{XW}*{2 * s} +: {XW}] = {XW}'d{lo.index(f'{t}{op}lo')}; "
                        f"wsel[{XW}*{2 * s + 1} +: {XW}] = {XW}'d{hi.index(f'{t}{op}hi')}; end")
    say("    end")
    say("    // write row of each superbank, registered to meet the network's registered write data")
    say("    always @(posedge clk) begin")
    for s in range(32):
        terms = []
        for t in range(TILES):
            for op in "xy":
                if f"{t}{op}lo" in net["write"][str(2 * s)]:
                    o, rw = ("wxo", "wxr") if op == "x" else ("wyo", "wyr")
                    terms.append(f"({{{RW}{{{o}[{32 * t + s}]}}}} & {rw}[{RW}*{t} +: {RW}])")
        expr = " | ".join(terms) if terms else f"{RW}'d0"
        say(f"        wa[{RW}*{2 * s} +: {RW}] <= {expr};")
        say(f"        wa[{RW}*{2 * s + 1} +: {RW}] <= {expr};")
    say("    end")
    say("endmodule")
    say("")


FFT_BASE = {False: 384, True: 576}   # FFT 32 bit root rows: 192 per bank per direction (roots 0..767)
# FFT 64 / 128 bit: root k limb l at bank k mod 4, row base + (k div 4) L + l (model/fft_wide_sched.py)
WIDE_BASE = {(2, False): 768, (2, True): 1152, (4, False): 1536, (4, True): 2304}
ROM_ROWS = 3328                     # + 256 rows of profile-3 packs written by the host (zero in the file)


def _wide_sched():
    s = importlib.util.spec_from_file_location("fft_wide_sched", ROOT / "model" / "fft_wide_sched.py")
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m


def _fft_sched():
    s = importlib.util.spec_from_file_location("fft_sched", ROOT / "model" / "fft_core_sched.py")
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m


def root_roms(tabs):
    """4 banks x 3072 rows x 96 bit, read through two ports. NTT packs [GM[g], GM[2g], GM[2g+1]] in rows 0..383; FFT 32 bit
    roots from row 384: root k of a direction at bank k mod 4, row base + k div 4, as [95:64] = wi, [63:32] = wr (the
    two "children" the network takes as one 64-bit pair), [31:0] = 0. FFT 64 / 128 bit from row 768: limb l of root k at
    bank k mod 4, row base + (k div 4) L + l, as [95:64] = limb l of wi, [63:32] = limb l of wr."""
    banks = [[0] * ROM_ROWS for _ in range(4)]
    fs = _fft_sched()
    for inverse in (False, True):
        tab = fs.plan.roots_inv(32) if inverse else fs.plan.roots(32)
        for k in range(768):                        # root index N/2 + N/4 - 1 <= 767 for N <= 1024
            wr, wi = tab[k]
            banks[k % 4][FFT_BASE[inverse] + k // 4] = ((wr & 0xFFFFFFFF) << 32) | ((wi & 0xFFFFFFFF) << 64)
        for L in (2, 4):
            tab = fs.plan.roots_inv(32 * L) if inverse else fs.plan.roots(32 * L)
            m = (1 << (32 * L)) - 1
            for k in range(768):
                wr, wi = (x & m for x in tab[k])
                for l in range(L):
                    banks[k % 4][WIDE_BASE[(L, inverse)] + (k // 4) * L + l] = \
                        (((wr >> (32 * l)) & 0xFFFFFFFF) << 32) | (((wi >> (32 * l)) & 0xFFFFFFFF) << 64)
    root1 = {}
    for prof in (0, 1, 2):
        q = QS[prof]
        for inverse in (False, True):
            tab = tabs.igm[q] if inverse else tabs.gm[q]
            base = seg_base(prof, inverse)
            for g in range(1, len(tab) // 2):          # 3329: 128 roots (7 layers at N = 256), packs 1..63
                pos = g - 1
                word = tab[g] | (tab[2 * g] << 32) | (tab[2 * g + 1] << 64)
                banks[pos % 4][base + pos // 4] = word
            root1[(prof, inverse)] = tab[1]
    for b in range(4):
        (ROOT / "hdl" / "core_ntt" / f"root_pack_b{b}.mem").write_text(
            "\n".join(f"{w:024x}" for w in banks[b]) + "\n", encoding="ascii", newline="\n")
    return root1


def timing_module(L):
    """FFT timing constants of the RTL from the schedule models: data read offset D (cycles from a block's issue to its
    first read) and, per tile, the cycle after the issue of its root read's address stage."""
    ws = _wide_sched()
    say = L.append
    say("// FFT timing (model/fft_core_sched.py, model/fft_wide_sched.py): data read offset of the format; per tile, the")
    say("// cycle after a butterfly's issue of the tile's root address stage (format 0: 1 + (t >> 2) mod 3; formats 1, 2:")
    say("// D + k - lead of the block - 1, k = limb of the tile).")
    say("module ntt_core_fft_timing (")
    say("    input  wire [1:0]       fmt,")
    say("    output reg  [3:0]       d,")
    say("    output reg  [16*4-1:0]  droot")
    say(");")
    say("    always @* begin")
    say("        case (fmt)")
    dr0 = sum((1 + (t >> 2) % 3) << (4 * t) for t in range(TILES))
    say(f"            2'd0: begin d = 4'd4; droot = 64'h{dr0:016x}; end")
    for f, Lw in ((1, 2), (2, 4)):
        lb = Lw.bit_length() - 1
        vals = []
        for t in range(TILES):
            v = ws.D[Lw] + (t & (Lw - 1)) - ws.RS[Lw][t >> lb] - 1
            assert 1 <= v <= ws.Q[Lw]
            vals.append(v)
        dr = sum(v << (4 * t) for t, v in enumerate(vals))
        say(f"            2'd{f}: begin d = 4'd{ws.D[Lw]}; droot = 64'h{dr:016x}; end")
    say("            default: begin d = 4'd0; droot = 64'd0; end")
    say("        endcase")
    say("    end")
    say("endmodule")
    say("")


def consts_module(L, root1):
    say = L.append
    say("// Per profile: q, q' = -q^-1 mod 2^32, root 1 of each direction, base row of each root-pack segment.")
    say("module ntt_core_consts (")
    say("    input  wire [1:0]  profile,")
    say("    input  wire        inverse,")
    say("    output reg  [31:0] q, qinv, root1,")
    say("    output reg  [8:0]  pbase")
    say(");")
    say("    always @* begin")
    say("        q = 32'd0; qinv = 32'd0; root1 = 32'd0; pbase = 9'd0;")
    say("        case ({profile, inverse})")
    for prof in (0, 1, 2):
        q = QS[prof]
        qinv = (-pow(q, -1, 1 << 32)) % (1 << 32)
        for inverse in (False, True):
            say(f"            3'b{prof:02b}{int(inverse)}: begin q = 32'd{q}; qinv = 32'd{qinv}; "
                f"root1 = 32'd{root1[(prof, inverse)]}; pbase = 9'd{seg_base(prof, inverse)}; end")
    say("            default: ;")
    say("        endcase")
    say("    end")
    say("endmodule")
    say("")


def vectors():
    gold = sched.golden()
    out = []
    for (prof, logn, op), cases in sorted(gold.items()):
        for a, e in cases:
            out.append(f"{prof} {logn} {op} " + " ".join(f"{x:x}" for x in a) + " " + " ".join(f"{x:x}" for x in e))
    (ROOT / "sim" / "core_ntt").mkdir(parents=True, exist_ok=True)
    (ROOT / "sim" / "core_ntt" / "vectors.txt").write_text("\n".join(out) + "\n", encoding="ascii", newline="\n")
    # FFT 32 bit (format 0), 1.0 kernel fixtures, logn >= 2: "3 logn op ..." with op 0 = FFT, 1 = FFT ngược
    fft = []
    for line in (ROOT / "spec" / "FlexTransform" / "1.0" / "assets" / "kernel_fixtures.jsonl").read_text().splitlines():
        d = json.loads(line)
        c = d["command"]
        if c["op"] in (0, 1) and c["fmt"] <= 2 and c["logn"] >= 2:
            L = 1 << c["fmt"]
            words = lambda vs: [f"{(int(x, 16) >> (32 * l)) & 0xFFFFFFFF:x}" for x in vs for l in range(L)]
            fft.append(f"{3 + c['fmt']} {c['logn']} {c['op']} " + " ".join(words(d["a"][0])) + " " +
                       " ".join(words(d["expected"][0])))
    (ROOT / "sim" / "core_ntt" / "vectors_fft.txt").write_text("\n".join(fft) + "\n", encoding="ascii", newline="\n")
    return len(out) + len(fft) + vectors_p3()


P3_PRIMES = (0, 1, 161, 322)                      # indexes into NTRUGen's PRIMES (0 and 1 are HAWK's two primes)
P3_SURVEY = [(3329, 8, 1), (8380417, 8, 0), (12289, 10, 0), (18433, 9, 0), (18433, 10, 0), (64513, 8, 0),
             (7681, 8, 0), (10753, 8, 0), (25166081, 8, 1), (20972417, 8, 2)]


def vectors_p3():
    """Profile 3 (loaded prime): "6 logn op hmin p p0i ng gm[ng] igm[ng] in[N] expected[N]" (hex; ng = N >> hmin, the
    table length). NTRUGen primes: inputs and expected values from the C reference dump (model/ntrugen_mp31.py);
    the moduli of study/results/pqc_moduli.md: tables and expected values from model/ntt_prime_core.py (forward by the
    evaluation definition; inverse gets a forward output and must give the input back)."""
    import random
    from array import array
    s = importlib.util.spec_from_file_location("ntt_prime_core", ROOT / "model" / "ntt_prime_core.py")
    pc = importlib.util.module_from_spec(s)
    s.loader.exec_module(pc)
    out = []

    def line(logn, op, hmin, q, gm, igm, a, e):
        p0i = (-pow(q, -1, 1 << 32)) % (1 << 32)
        h = lambda v: " ".join(f"{x:x}" for x in v)
        return f"6 {logn} {op} {hmin} {q:x} {p0i:x} {len(gm):x} {h(gm)} {h(igm)} {h(a)} {h(e)}"

    w = array("I")
    w.frombytes((ROOT / "study" / "build" / "ntrugen_mp31" / "dump.bin").read_bytes())
    pos = 0
    for pi in range(323):
        p = w[pos]
        pos += 4 + 67 * 3
        for logn in range(1, 11):
            n = 1 << logn
            gm, igm, a, nref, b, iref = (w[pos + k * n:pos + (k + 1) * n].tolist() for k in range(6))
            pos += 6 * n
            if pi in P3_PRIMES:
                out.append(line(logn, 5, 0, p, gm, igm, a, nref))
                out.append(line(logn, 6, 0, p, gm, igm, b, iref))
    rng = random.Random(20261102)
    for q, logn, hmin in P3_SURVEY:
        gm, igm = pc.tables(q, logn, hmin)
        a = [rng.randrange(q) for _ in range(1 << logn)]
        f = pc.ref_forward(a, q, logn, hmin)
        out.append(line(logn, 5, hmin, q, gm, igm, a, f))
        out.append(line(logn, 6, hmin, q, gm, igm, f, a))
    (ROOT / "sim" / "core_ntt" / "vectors_p3.txt").write_text("\n".join(out) + "\n", encoding="ascii", newline="\n")
    return len(out)


def main():
    global XW
    net = json.loads((ROOT / "study" / "results" / "structured_net.json").read_text())
    XW = (max(len(v) for v in list(net["read_lo"].values()) + list(net["write"].values())) - 1).bit_length()
    (ROOT / "hdl" / "core_ntt").mkdir(parents=True, exist_ok=True)
    tabs = sched.Tables()
    root1 = root_roms(tabs)
    L = ["// GENERATED by scripts/gen_ntt_core.py from model/ntt_core_sched.py and study/results/structured_net.json;",
         "// do not edit.", ""]
    layer_rom(L)
    sel_module(L, net)
    route_module(L, net)
    consts_module(L, root1)
    timing_module(L)
    (ROOT / "hdl" / "core_ntt" / "ntt_core_gen.sv").write_text("\n".join(L) + "\n", encoding="ascii", newline="\n")
    n = vectors()
    print(f"wrote hdl/core_ntt/ntt_core_gen.sv, root_pack_b0..3.mem, sim/core_ntt/vectors.txt ({n} cases)")


if __name__ == "__main__":
    main()
