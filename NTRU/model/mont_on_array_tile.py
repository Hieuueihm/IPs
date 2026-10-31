"""Cycle model of one tile (4 multipliers 16x16) doing Montgomery reduction on the multipliers.

Answers two risks of docs/architecture_v1.md (change 4):
  1. How many bits must be held while a modular multiply waits for its three beats
     (T = a*b, m = T_low*q', m*q), and what does capping the in-flight count cost?
  2. Is the three-beat dependent schedule correct and fast enough under random
     stalls and input bubbles, when a stall freezes the whole tile (clock enable)?

Every job carries real values; each result is checked against a*b*R^-1 mod q.
Two baselines are reported: the same tile with 4 dedicated reducers.

Parameters (cycles):
  LAT_MUL  latency of one multiplier product (DSP pipelining on FPGA: 3..5)
  LAT_ADD  latency of the shared "high part + correction + carry" adder
  LAT_RED  latency of a dedicated reducer (baseline only)

Run: python model/mont_on_array_tile.py   (writes study/results/mont_on_array_tile.md)
"""
from dataclasses import dataclass, field
from pathlib import Path
from random import Random

ROOT = Path(__file__).resolve().parent.parent
LEAVES = 4
SIDE_BITS = 16 + 8          # butterfly operand A kept for A±T, plus a destination tag


@dataclass(frozen=True)
class Profile:
    name: str
    q: int
    rbits: int               # R = 2^rbits
    beat_leaves: tuple       # leaves used by beats (T, m, m*q) inside one tile

    @property
    def qp(self):
        return (-pow(self.q, -1, 1 << self.rbits)) % (1 << self.rbits)


PROFILES = [
    Profile("q12289 (16 bit)", 12289, 16, (1, 1, 1)),
    Profile("q3329 (16 bit)", 3329, 16, (1, 1, 1)),
    Profile("q8380417 (32 bit)", 8380417, 32, (4, 3, 4)),
]


@dataclass
class Job:
    idx: int
    a: int
    b: int
    phase: int = 0           # 0 wait T, 1 T in flight, 2 wait m, 3 m in flight,
                             # 4 wait mq, 5 mq in flight, 6 final add, 7 done
    ready_at: int = 0
    t: int = 0
    m: int = 0
    out: int = None
    born: int = 0
    done_at: int = 0


def held_bits(job, prof):
    """Bits stored outside the multiplier pipelines for this job, in its current phase."""
    r = prof.rbits
    bits = SIDE_BITS
    if job.phase == 2:                 # waiting to issue m: keep T_low and T_high + flag
        bits += r + (2 * r - r) + 1
    elif job.phase in (3, 4):          # m in flight / waiting for m*q: keep T_high + flag, and m
        bits += r + 1 + (r if job.phase == 4 else 0)
    elif job.phase in (5, 6):          # m*q in flight / final add: keep T_high + flag
        bits += r + 1
    return bits


def run(prof, lat_mul, lat_add, cycles, p_stall, p_bubble, cap, seed):
    rng = Random(seed)
    q, rb = prof.q, prof.rbits
    R = 1 << rb
    jobs, active, outputs = [], [], []
    max_inflight = max_bits = 0
    stalled = 0
    t = 0
    while t < cycles:
        t += 1
        if rng.random() < p_stall:            # global clock enable low: nothing moves
            stalled += 1
            for j in active:
                j.ready_at += 1
            continue
        # 1. Products / final add that complete this cycle.
        for j in active:
            if j.phase in (1, 3, 5, 6) and j.ready_at <= t:
                if j.phase == 1:
                    j.t, j.phase = j.a * j.b, 2
                elif j.phase == 3:
                    j.m, j.phase = ((j.t & (R - 1)) * prof.qp) % R, 4
                elif j.phase == 5:
                    j.phase, j.ready_at = 6, t + lat_add
                    j.mq = j.m * q
                else:
                    u = (j.t >> rb) + (j.mq >> rb) + ((j.t & (R - 1)) != 0)
                    assert u == (j.t + j.mq) >> rb and u < 2 * q
                    j.out = u - q if u >= q else u
                    j.phase, j.done_at = 7, t
                    outputs.append(j)
        active = [j for j in active if j.phase != 7]
        # 2. Issue waiting beats of older jobs first (they hold registers), limited by free leaves.
        free = LEAVES
        for j in active:                       # active is kept in admission (= age) order
            beat = {2: 1, 4: 2}.get(j.phase)
            if beat is None:
                continue
            need = prof.beat_leaves[beat]
            if need <= free:
                free -= need
                j.phase, j.ready_at = j.phase + 1, t + lat_mul
        # 3. Admit new jobs straight into their first beat while leaves remain (the butterfly
        #    front-end offers up to one job per free slot; each offer may be a bubble).
        need0 = prof.beat_leaves[0]
        while free >= need0 and len(active) < cap:
            if rng.random() < p_bubble:
                break
            j = Job(len(jobs), rng.randrange(q), rng.randrange(q), born=t)
            j.phase, j.ready_at = 1, t + lat_mul
            jobs.append(j)
            active.append(j)
            free -= need0
        max_inflight = max(max_inflight, len(active))
        max_bits = max(max_bits, sum(held_bits(j, prof) for j in active))
    for j in outputs:
        assert j.out == j.a * j.b * pow(R, -1, q) % q
    in_order = all(outputs[i].idx < outputs[i + 1].idx for i in range(len(outputs) - 1))
    lat = [j.done_at - j.born for j in outputs]
    return {
        "throughput": len(outputs) / cycles,
        "useful_cycles": cycles - stalled,
        "max_inflight": max_inflight,
        "max_bits": max_bits,
        "in_order": in_order,
        "mean_latency": sum(lat) / len(lat) if lat else 0,
        "checked": len(outputs),
    }


@dataclass
class Frame:
    idx: int
    x: list
    w: tuple                  # plain roots (w_common, w0, w1); operands use w*R mod q
    born: int = 0
    stage: int = 0            # 0 layer 1 running, 1 layer 2 running, 2 done
    jobs: list = field(default_factory=list)
    y: list = None
    z: list = None
    ready_at: int = 0         # time the butterfly add/sub of the current layer finishes
    done_at: int = 0


def run_frames(prof, lat_mul, lat_add, lat_bf, cycles, p_stall, cap, seed, dedicated=False,
               lat_red=2):
    """Two-layer NTT frames (CT, 4 coefficients, roots [w_common, w0, w1]) on one tile.

    Layer 1: BF(x0,x2,wc), BF(x1,x3,wc); layer 2: BF(y0,y1,w0), BF(y2,y3,w1).
    BF(a,b,w): t = Mont(b, wR) = b*w mod q; (a+t, a-t) mod q, taking lat_bf cycles.
    Reduction either on the multipliers (3 beats) or in a dedicated reducer (lat_red).
    """
    rng = Random(seed)
    q, rb = prof.q, prof.rbits
    R = 1 << rb
    frames, active, done = [], [], []
    max_frames = max_bits = stalled = 0
    t = 0
    beats = (prof.beat_leaves[0],) if dedicated else prof.beat_leaves

    def new_job(a, wr, frame):
        j = Job(len(frame.jobs), a, wr, born=t)
        j.frame = frame
        frame.jobs.append(j)
        return j

    def jobs_in(f):
        return [j for j in f.jobs if j.phase != 7]

    while t < cycles:
        t += 1
        if rng.random() < p_stall:                 # global clock enable low: every timer waits
            stalled += 1
            for f in active:
                if f.ready_at:
                    f.ready_at += 1
                for j in f.jobs:
                    j.ready_at += 1
                    if j.phase == 7 and j.done_at > t - 1:
                        j.done_at += 1
            continue
        # 1. Advance multiplier beats / reductions finishing now.
        for f in active:
            for j in f.jobs:
                if j.phase in (1, 3, 5, 6) and j.ready_at <= t:
                    if dedicated and j.phase == 1:
                        j.out, j.phase = j.a * j.b * pow(R, -1, q) % q, 7
                        j.done_at = t + lat_red
                    elif j.phase == 1:
                        j.t, j.phase = j.a * j.b, 2
                    elif j.phase == 3:
                        j.m, j.phase = ((j.t & (R - 1)) * prof.qp) % R, 4
                    elif j.phase == 5:
                        j.mq, j.phase, j.ready_at = j.m * q, 6, t + lat_add
                    else:
                        u = (j.t >> rb) + (j.mq >> rb) + ((j.t & (R - 1)) != 0)
                        j.out = u - q if u >= q else u
                        j.phase, j.done_at = 7, t
        # 2. Layer completion -> butterfly add/sub -> next layer or frame done.
        for f in active:
            layer_jobs = f.jobs[-2:]
            if f.stage < 2 and all(j.phase == 7 and j.done_at <= t for j in layer_jobs) and f.ready_at == 0:
                f.ready_at = max(j.done_at for j in layer_jobs) + lat_bf
            if f.ready_at and f.ready_at <= t:
                j1, j2 = layer_jobs
                if f.stage == 0:
                    x = f.x
                    f.y = [(x[0] + j1.out) % q, (x[1] + j2.out) % q,
                           (x[0] - j1.out) % q, (x[1] - j2.out) % q]
                    f.stage, f.ready_at = 1, 0
                    new_job(f.y[1], f.w[1] * R % q, f)
                    new_job(f.y[3], f.w[2] * R % q, f)
                else:
                    y = f.y
                    f.z = [(y[0] + j1.out) % q, (y[0] - j1.out) % q,
                           (y[2] + j2.out) % q, (y[2] - j2.out) % q]
                    f.stage, f.done_at = 2, t
                    done.append(f)
        active = [f for f in active if f.stage != 2]
        # 3. Issue waiting beats, oldest frame and job first.
        free = LEAVES
        for f in active:
            for j in f.jobs:
                beat = {0: 0, 2: 1, 4: 2}.get(j.phase)
                if beat is None:
                    continue
                need = beats[beat]
                if need <= free:
                    free -= need
                    j.phase = j.phase + 1
                    j.ready_at = t + lat_mul
        # 4. Admit a new frame when nothing older waits to start and the cap allows.
        waiting = any(j.phase == 0 for f in active for j in f.jobs)
        if not waiting and len(active) < cap and free >= beats[0]:
            x = [rng.randrange(q) for _ in range(4)]
            w = tuple(rng.randrange(1, q) for _ in range(3))
            f = Frame(len(frames), x, w, born=t)
            frames.append(f)
            active.append(f)
            for xi in (x[2], x[3]):
                j = new_job(xi, w[0] * R % q, f)
                if beats[0] <= free:
                    free -= beats[0]
                    j.phase, j.ready_at = 1, t + lat_mul
        max_frames = max(max_frames, len(active))
        bits = 0
        for f in active:
            bits += 4 * rb + 8                     # four coefficients / intermediates + tag
            bits += sum(held_bits(j, prof) - SIDE_BITS for j in jobs_in(f))
        max_bits = max(max_bits, bits)
    for f in done:                                # reference: plain modular CT, two layers
        x, (wc, w0, w1) = f.x, f.w
        t1, t2 = x[2] * wc % q, x[3] * wc % q
        y = [(x[0] + t1) % q, (x[1] + t2) % q, (x[0] - t1) % q, (x[1] - t2) % q]
        t3, t4 = y[1] * w0 % q, y[3] * w1 % q
        z = [(y[0] + t3) % q, (y[0] - t3) % q, (y[2] + t4) % q, (y[2] - t4) % q]
        assert f.z == z
    in_order = all(done[i].idx < done[i + 1].idx for i in range(len(done) - 1))
    lat = [f.done_at - f.born for f in done]
    return {"frame_rate": len(done) / cycles, "min_latency": min(lat), "mean_latency": sum(lat) / len(lat),
            "max_frames": max_frames, "max_bits": max_bits, "in_order": in_order, "checked": len(done)}


def dedicated(prof, lat_mul, lat_red, p_stall, p_bubble):
    """Baseline: 4 dedicated reducers (16 bit) or 1 per tile (32 bit); fully pipelined."""
    per_cycle = LEAVES // max(prof.beat_leaves[0], 1) if prof.rbits == 16 else 1
    inflight = per_cycle * (lat_mul + lat_red)
    return {"throughput": per_cycle * (1 - p_stall) * (1 - p_bubble),
            "max_inflight": inflight, "max_bits": inflight * SIDE_BITS}


def main():
    out = []
    say = lambda s="": (print(s), out.append(s))
    say("# Mô hình chu kỳ: rút gọn Montgomery trên mảng nhân của một tile\n")
    say("Một tile = 4 bộ nhân 16×16. Mỗi phép nhân modulo đi 3 lượt (T, m, m·q) trên các bộ nhân, rồi qua "
        "bộ cộng chung. Stall = dừng toàn tile (clock-enable). Mọi kết quả được so với a·b·R⁻¹ mod q.")
    say(f"Bit giữ thêm mỗi phép = toán hạng A + tag ({SIDE_BITS} bit) + phần T/m đang chờ "
        "(không tính thanh ghi bên trong bộ nhân, trên FPGA nằm trong DSP).\n")
    total_checked = 0

    say("## 1. Không stall, không giới hạn số phép đang chạy\n")
    say("| Modulus | Độ trễ nhân | Phép/chu kỳ (trên mảng) | Phép/chu kỳ (rút gọn riêng) | Đang chạy tối đa | "
        "Bit giữ tối đa (trên mảng) | Bit giữ (rút gọn riêng, độ trễ rút gọn 2) | Độ trễ TB | Đúng thứ tự |")
    say("|---|---:|---:|---:|---:|---:|---:|---:|---|")
    for prof in PROFILES:
        for lat_mul in (3, 4, 5):
            r = run(prof, lat_mul, 1, 20000, 0.0, 0.0, 10 ** 9, seed=lat_mul)
            d = dedicated(prof, lat_mul, 2, 0.0, 0.0)
            total_checked += r["checked"]
            say(f"| {prof.name} | {lat_mul} | {r['throughput']:.3f} | {d['throughput']:.3f} | "
                f"{r['max_inflight']} | {r['max_bits']} | {d['max_bits']} | {r['mean_latency']:.1f} | "
                f"{'có' if r['in_order'] else 'không'} |")

    say("\n## 2. Giới hạn số phép đang chạy (đổi bit giữ lấy tốc độ), độ trễ nhân 4\n")
    say("| Modulus | Giới hạn | Phép/chu kỳ | Bit giữ tối đa |")
    say("|---|---:|---:|---:|")
    for prof in PROFILES:
        caps = (16, 12, 8, 6, 4) if prof.rbits == 16 else (6, 4, 3, 2, 1)
        for cap in caps:
            r = run(prof, 4, 1, 20000, 0.0, 0.0, cap, seed=cap)
            total_checked += r["checked"]
            say(f"| {prof.name} | {cap} | {r['throughput']:.3f} | {r['max_bits']} |")

    say("\n## 3. Stall và bubble ngẫu nhiên, độ trễ nhân 4, không giới hạn\n")
    say("| Modulus | Xác suất stall | Xác suất bubble | Phép/chu kỳ | Tỉ lệ so với không stall | Đúng thứ tự | Số phép đã kiểm |")
    say("|---|---:|---:|---:|---:|---|---:|")
    for prof in PROFILES:
        base = run(prof, 4, 1, 40000, 0.0, 0.0, 10 ** 9, seed=7)["throughput"]
        for ps, pb in ((0.1, 0.0), (0.3, 0.0), (0.0, 0.2), (0.2, 0.2)):
            r = run(prof, 4, 1, 40000, ps, pb, 10 ** 9, seed=int(ps * 100 + pb * 10))
            total_checked += r["checked"]
            say(f"| {prof.name} | {ps} | {pb} | {r['throughput']:.3f} | {r['throughput'] / base:.3f} | "
                f"{'có' if r['in_order'] else 'không'} | {r['checked']} |")

    say("\n## 4. Nhịp NTT hai tầng (4 hệ số, tầng 2 chờ tầng 1), cộng/trừ butterfly 1 chu kỳ\n")
    say("| Modulus | Rút gọn | Độ trễ nhân | Nhịp/chu kỳ/tile | Độ trễ nhịp tối thiểu | Độ trễ nhịp TB | "
        "Nhịp đang chạy tối đa | Bit giữ tối đa | Đúng thứ tự |")
    say("|---|---|---:|---:|---:|---:|---:|---:|---|")
    frame_checked = 0
    for prof in PROFILES[:1] + PROFILES[2:]:
        for lat_mul in (3, 4):
            for ded in (True, False):
                r = run_frames(prof, lat_mul, 1, 1, 6000, 0.0, 10 ** 9, seed=lat_mul, dedicated=ded)
                frame_checked += r["checked"]
                say(f"| {prof.name} | {'riêng' if ded else 'trên mảng'} | {lat_mul} | {r['frame_rate']:.3f} | "
                    f"{r['min_latency']} | {r['mean_latency']:.1f} | {r['max_frames']} | {r['max_bits']} | "
                    f"{'có' if r['in_order'] else 'không'} |")
    for ps in (0.1, 0.3):
        r = run_frames(PROFILES[0], 4, 1, 1, 6000, ps, 10 ** 9, seed=11)
        frame_checked += r["checked"]
        say(f"| q12289, stall {ps} | trên mảng | 4 | {r['frame_rate']:.3f} | {r['min_latency']} | "
            f"{r['mean_latency']:.1f} | {r['max_frames']} | {r['max_bits']} | {'có' if r['in_order'] else 'không'} |")
    say(f"\nNhịp hai tầng đã kiểm so với NTT số nguyên: {frame_checked}, không sai khác.")
    say(f"\nTổng số phép nhân modulo đã kiểm kết quả: {total_checked}, không sai khác.\n")
    (ROOT / "study" / "results" / "mont_on_array_tile.md").write_text("\n".join(out) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
