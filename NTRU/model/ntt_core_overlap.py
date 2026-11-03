"""Layer overlap for the minimal NTT core: start each layer a fixed time after the previous one, before its writes end.

Base: model/ntt_core_sched.py (same tiles, phases, network, banks, pipeline offsets). There, layer L + 1 reads only
after the last write of layer L. Here layer L + 1 starts at S_{L+1} = S_L + delta_L, where delta_L is the smallest
value (searched) such that
  - every coefficient is read after the write that produced it (write at W, read at e > W);
  - no bank gets two reads or two writes in one cycle, and no pack bank two different packs, across all layers in flight;
  - each tile accepts at most one butterfly per accepting cycle, in order (its layer L + 1 work after its layer L work);
  - every butterfly of layer L is issued (first read) before S_{L+1}: the RTL switches the layer table for all tiles at
    once, so a tile cannot still be issuing layer L after the switch.
The schedule does not depend on data, so delta_L is a table entry (logn, h, direction). Each layer may also take its
kernel basis in another order (which bit of k selects which basis vector); for every layer the search picks the order
that gives the smallest delta, greedily in execution order.

Values are then simulated in cycle order (a read sees every write committed in an earlier cycle) and compared with the
golden vectors, so a missed dependency shows up as a mismatch, not only as a failed check.

Run: python model/ntt_core_overlap.py   (writes study/results/ntt_core_overlap.md and .json)
"""
import importlib.util
import itertools
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
_s = importlib.util.spec_from_file_location("sched", ROOT / "model" / "ntt_core_sched.py")
sc = importlib.util.module_from_spec(_s)
_s.loader.exec_module(sc)

LAT = sc.TILE_LAT


def layer_events(logn, h, kernel_order, start, prev_last_accept):
    """Butterflies of one layer started at `start`: list of dicts, or None if a tile would accept out of order."""
    n = 1 << logn
    firsts, kernel, count, same = sc.layer_config(logn, h)
    kern = [kernel[j] for j in kernel_order]
    ev = []
    for t, p in firsts.items():
        e = start
        while (sc.PHASE[t] + e + 2 + same) % 3:
            e += 1
        if prev_last_accept.get(t, -10) >= e + 2 + same:
            return None
        for k in range(count):
            ek = e + 3 * k
            i = sc.enum(p, kern, k)
            cx, cy = sc.pair(i, h)
            A = ek + 2 + same
            r = sc.root_index(n, h, cx)
            ev.append({"t": t, "A": A, "cx": cx, "cy": cy, "r": r,
                       "rx": ek, "ry": ek + same,
                       "wx": A + LAT + 1, "wy": A + LAT + 1 + same,
                       "pack": None if r < 2 else (r >> 1) - 1, "pread": ek + same})
    return ev


class Book:
    """Resources used so far: per cycle reads / writes per superbank, packs per pack bank; last write per coefficient."""

    def __init__(self):
        self.rd, self.wr, self.pk = {}, {}, {}
        self.last_w = {}

    def fits(self, ev):
        rd, wr, pk = {}, {}, {}
        for b in ev:
            sx, sy = sc.superbank(b["cx"]), sc.superbank(b["cy"])
            for cyc, s in ((b["rx"], sx), (b["ry"], sy)):
                if s in self.rd.get(cyc, ()) or s in rd.get(cyc, ()):
                    return False
                rd.setdefault(cyc, set()).add(s)
            for cyc, s in ((b["wx"], sx), (b["wy"], sy)):
                if s in self.wr.get(cyc, ()) or s in wr.get(cyc, ()):
                    return False
                wr.setdefault(cyc, set()).add(s)
            for c, cyc in ((b["cx"], b["rx"]), (b["cy"], b["ry"])):
                if self.last_w.get(c, -1) >= cyc:
                    return False
            if b["pack"] is not None:
                bank = b["pack"] % sc.PB
                cur = {**self.pk.get(b["pread"], {}), **pk.get(b["pread"], {})}
                if bank in cur and cur[bank] != b["pack"]:
                    return False
                pk.setdefault(b["pread"], {})[bank] = b["pack"]
        return True

    def add(self, ev):
        for b in ev:
            sx, sy = sc.superbank(b["cx"]), sc.superbank(b["cy"])
            for cyc, s in ((b["rx"], sx), (b["ry"], sy)):
                self.rd.setdefault(cyc, set()).add(s)
            for cyc, s in ((b["wx"], sx), (b["wy"], sy)):
                self.wr.setdefault(cyc, set()).add(s)
            self.last_w[b["cx"]] = b["wx"]
            self.last_w[b["cy"]] = b["wy"]
            if b["pack"] is not None:
                self.pk.setdefault(b["pread"], {})[b["pack"] % sc.PB] = b["pack"]


def plan(q, logn, inverse):
    """Greedy: for each layer in order, the (delta, kernel order) with the earliest start. Returns layers and events."""
    book = Book()
    last_accept = {}
    layers = []
    events = []
    start = 0
    for li, h in enumerate(sc.layers(q, logn, inverse)):
        _, kernel, _, _ = sc.layer_config(logn, h)
        best = None
        lo = start if li == 0 else max(layers[-1]["start"] + 1, max(b["rx"] for b in events[-1]) + 1)
        s = lo
        while best is None:
            for order in itertools.permutations(range(len(kernel))):
                ev = layer_events(logn, h, order, s, last_accept)
                if ev is not None and book.fits(ev):
                    best = (s, order, ev)
                    break
            if best is None:
                s += 1
        s, order, ev = best
        book.add(ev)
        for b in ev:
            last_accept[b["t"]] = max(last_accept.get(b["t"], -10), b["A"])
        layers.append({"h": h, "start": s, "order": list(order),
                       "delta": None if li == 0 else s - layers[-1]["start"]})
        events.append(ev)
    return layers, events


def simulate(q, logn, inverse, data, tabs, events):
    """Run the values in cycle order; a read sees writes committed in earlier cycles."""
    roots = tabs.igm[q] if inverse else tabs.gm[q]
    mem = list(data)
    pend = {}                                       # cycle -> list of (c, value)
    reads = sorted(((b["rx"], b) for ev in events for b in ev), key=lambda x: x[0])
    allb = sorted((b for ev in events for b in ev), key=lambda b: b["A"])
    last = max(b["wy"] for b in allb)
    cyc_reads = {}
    for b in allb:
        cyc_reads.setdefault(b["rx"], []).append(("x", b))
        cyc_reads.setdefault(b["ry"], []).append(("y", b))
    got = {}
    for cyc in range(0, last + 2):
        for op, b in cyc_reads.get(cyc, []):        # reads of this cycle see writes of earlier cycles only
            got[(id(b), op)] = mem[b["cx"] if op == "x" else b["cy"]]
            if (id(b), "x") in got and (id(b), "y") in got:
                x, y, w = got[(id(b), "x")], got[(id(b), "y")], roots[b["r"]]
                if inverse:
                    s_, d = (x + y) % q, (x - y) % q
                    zx, zy = (s_ + (q if s_ & 1 else 0)) >> 1, sc.mont32(d, w, q)
                else:
                    tt = sc.mont32(y, w, q)
                    zx, zy = (x + tt) % q, (x - tt) % q
                pend.setdefault(b["wx"], []).append((b["cx"], zx))
                pend.setdefault(b["wy"], []).append((b["cy"], zy))
        for c, v in pend.get(cyc, []):              # writes commit at the end of their cycle
            mem[c] = v
    first = min(b["rx"] for b in allb)
    return mem, last - first + 1


def main():
    tabs = sc.Tables()
    gold = sc.golden()
    lines = ["# Chồng tầng trong lõi NTT tối thiểu\n",
             "Mô hình: [model/ntt_core_overlap.py](../../model/ntt_core_overlap.py). Tầng sau bắt đầu sau tầng trước một "
             "khoảng cố định (tìm nhỏ nhất, kèm thứ tự cơ sở nhân của mỗi tầng), thay vì chờ lần ghi cuối. Giá trị chạy theo "
             "đúng thứ tự chu kỳ và so với vector vàng.\n",
             "| Profile | N | Chiều | Ca vàng | Khớp | Chu kỳ, rào chắn | Chu kỳ, chồng tầng | Giảm | Khoảng cách các tầng |",
             "|---:|---:|---|---:|---|---:|---:|---:|---|"]
    table = {}
    for prof, (q, lns) in sc.PROFILES.items():
        for logn in lns:
            for op in (5, 6):
                inverse = op == 6
                layers, events = plan(q, logn, inverse)
                cases = gold[(prof, logn, op)]
                ok = True
                for a, e in cases:
                    res, cyc = simulate(q, logn, inverse, a, tabs, events)
                    ok &= res == e
                    _, base, _ = sc.run(q, logn, inverse, a, tabs)
                assert ok, (prof, logn, op)
                table[f"{prof},{logn},{op}"] = layers
                deltas = " ".join(str(l["delta"]) for l in layers[1:])
                lines.append(f"| {prof} | {1 << logn} | {'ngược' if inverse else 'xuôi'} | {len(cases)} | có | {base} | "
                             f"{cyc} | {100 * (1 - cyc / base):.0f}% | {deltas} |")
    (ROOT / "study" / "results" / "ntt_core_overlap.json").write_text(json.dumps(table, indent=1) + "\n")
    (ROOT / "study" / "results" / "ntt_core_overlap.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
