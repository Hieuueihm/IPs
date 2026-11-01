"""Generate the tables of the minimal NTT core (hdl/core_ntt/) from model/ntt_core_sched.py and the network lists.

Outputs:
  hdl/core_ntt/ntt_core_gen.sv
      ntt_core_layer_rom  per layer (min-stride-2 flag, direction, logn, log2 h): tiles in use, first butterfly p_t of
                          each tile, kernel basis in plan order, same-superbank flag, cycles to the next layer's start
                          (affine enumeration, model/ntt_core_sched.py; overlap plan, model/ntt_core_overlap.py)
      ntt_core_sel        per tile: superbank -> index into the tile's read source lists (hdl/net/ntt_bank_net_s.sv)
      ntt_core_route      per superbank: which tile port reads / writes it this cycle, its row, and the write select
  hdl/core_ntt/root_pack_b<0..3>.mem   4 root-pack banks, 384 rows x 96 bit: profile 0 / 1 / 2, forward then inverse
  sim/core_ntt/vectors.txt             golden cases: profile logn op, N inputs, N expected (hex)

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
    """Layer table from the overlap plan (study/results/ntt_core_overlap.json, model/ntt_core_overlap.py)."""
    say = L.append
    plans = json.loads((ROOT / "study" / "results" / "ntt_core_overlap.json").read_text())
    rows = {}
    for key, layers in plans.items():
        prof, logn, op = (int(x) for x in key.split(","))
        ms2 = int(prof == 1 and logn == 8)
        inverse = int(op == 6)
        for li, lay in enumerate(layers):
            hlog = lay["h"].bit_length() - 1
            firsts, kernel, count, same = sched.layer_config(logn, lay["h"])
            kern = [kernel[j] for j in lay["order"]]
            delta = layers[li + 1]["delta"] if li + 1 < len(layers) else 0
            row = (firsts, kern, same, delta)
            k = (ms2, inverse, logn, hlog)
            if k in rows:
                assert rows[k][1] == kern and rows[k][3] == delta, ("plans differ between profiles", key, hlog)
            rows[k] = row
    say("// Layer table (one entry per min-stride-2 flag, direction, logn, log2 h): tiles in use, first butterfly of each")
    say("// tile, kernel basis in the order of the overlap plan, same-superbank flag, cycles to the next layer's start.")
    say("module ntt_core_layer_rom (")
    say("    input  wire              ms2, inverse,")
    say("    input  wire [3:0]        logn, hlog,")
    say("    output reg  [15:0]       tv,")
    say(f"    output reg  [16*{IW}-1:0]  p,")
    say(f"    output reg  [5*{IW}-1:0]   kb,")
    say("    output reg  [2:0]        kdim,")
    say("    output reg               same,")
    say("    output reg  [7:0]        delta")
    say(");")
    say("    always @* begin")
    say("        tv = 16'd0; p = 0; kb = 0; kdim = 3'd0; same = 1'b0; delta = 8'd0;")
    say("        case ({ms2, inverse, logn, hlog})")
    for (ms2, inv, logn, hlog), (firsts, kern, same, delta) in sorted(rows.items()):
        assert len(kern) <= 5 and delta < 256
        tv = sum(1 << t for t in firsts)
        pv = sum(firsts.get(t, 0) << (IW * t) for t in range(TILES))
        kv = sum(v << (IW * j) for j, v in enumerate(kern))
        say(f"            10'b{ms2}{inv}_{logn:04b}_{hlog:04b}: begin tv = 16'h{tv:04x}; p = {16 * IW}'h{pv:x}; "
            f"kb = {5 * IW}'h{kv:x}; kdim = 3'd{len(kern)}; same = 1'b{int(same)}; delta = 8'd{delta}; end")
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
    say("    output reg  [16*3-1:0]   sel_xlo, sel_xhi, sel_ylo, sel_yhi")
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
                say(f"            5'd{v}: begin sel_{op}lo[3*{t} +: 3] = 3'd{lo.index(2 * v)}; "
                    f"sel_{op}hi[3*{t} +: 3] = 3'd{hi.index(2 * v + 1)}; end")
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
    say("    output reg  [64*3-1:0]   wsel,")
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
                        f"wsel[3*{2 * s} +: 3] = 3'd{lo.index(f'{t}{op}lo')}; "
                        f"wsel[3*{2 * s + 1} +: 3] = 3'd{hi.index(f'{t}{op}hi')}; end")
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


def root_roms(tabs):
    banks = [[0] * 384 for _ in range(4)]
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
    return len(out)


def main():
    net = json.loads((ROOT / "study" / "results" / "structured_net.json").read_text())
    (ROOT / "hdl" / "core_ntt").mkdir(parents=True, exist_ok=True)
    tabs = sched.Tables()
    root1 = root_roms(tabs)
    L = ["// GENERATED by scripts/gen_ntt_core.py from model/ntt_core_sched.py and study/results/structured_net.json;",
         "// do not edit.", ""]
    layer_rom(L)
    sel_module(L, net)
    route_module(L, net)
    consts_module(L, root1)
    (ROOT / "hdl" / "core_ntt" / "ntt_core_gen.sv").write_text("\n".join(L) + "\n", encoding="ascii", newline="\n")
    n = vectors()
    print(f"wrote hdl/core_ntt/ntt_core_gen.sv, root_pack_b0..3.mem, sim/core_ntt/vectors.txt ({n} cases)")


if __name__ == "__main__":
    main()
