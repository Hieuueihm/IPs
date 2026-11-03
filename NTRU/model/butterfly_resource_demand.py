"""Analytical work, service-rate and live-context audit; no new RTL/PPA claim.

Run: python -X utf8 model/butterfly_resource_demand.py
Writes study/results/butterfly_resource_demand.{json,md}.
Counts use the current 3M/wrap/rounding contract and three-pass Montgomery.
"""
import hashlib
import importlib.util
import itertools
import json
import math
import random
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'model' / filename)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def area(path):
    if not path.exists():
        return None
    s = path.read_text()
    result = {'report': path.relative_to(ROOT).as_posix(),
              'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
    for label, key in [('CLB LUTs', 'LUT'), ('CLB Registers', 'FF'),
                       ('DSPs', 'DSP'), ('Block RAM Tile', 'BRAM36_equivalent')]:
        m = re.search(r'^\|\s*' + label + r'\*?\s*\|\s*(\d+(?:\.\d+)?)\s*\|', s, re.M)
        assert m, (path, label)
        result[key] = float(m[1]) if '.' in m[1] else int(m[1])
    return result


def scalar_terms(a, b, width):
    """Exact retained limb terms; arbitrary parallel ordering within a column is legal."""
    limbs = width // 32
    mask = (1 << 32) - 1
    def limb(v, i):
        x = (v >> (32*i)) & mask
        return x - (1 << 32) if i == limbs - 1 and x >> 31 else x
    terms = [(i+j, limb(a, i)*limb(b, j))
             for i in range(limbs) for j in range(limbs)
             if 32*(i+j) < width + width//2]
    return terms


def arithmetic_check(trials=1000):
    ref = load('bf_demand_ref', 'fft_core_plan.py')
    rng = random.Random(20261102)
    counts = {}
    for w in (32, 64, 128):
        edges = [0, 1, -1, -(1 << (w-1)), (1 << (w-1))-1,
                 1 << (w//2), -(1 << (w//2))]
        nscalar = 0
        def mul(a, b):
            nonlocal nscalar
            terms = scalar_terms(a, b, w)
            assert len(terms) == {32: 1, 64: 4, 128: 15}[w]
            rng.shuffle(terms)
            acc = (1 << (w//2 - 1)) + sum(p << (32*c) for c, p in terms)
            got = ref.wrap(acc >> (w//2), w)
            assert got == ref.mul(a, b, w), (w, a, b)
            nscalar += 1
            return got
        for a, b in itertools.product(edges, repeat=2):
            mul(a, b)
        for _ in range(trials):
            ar, ai, wr, wi = [rng.choice(edges) if rng.randrange(5) == 0
                              else ref.wrap(rng.getrandbits(w), w) for _ in range(4)]
            p0, p1 = mul(ar, wr), mul(ai, wi)
            p2 = mul(ref.wrap(ar+ai, w), ref.wrap(wr+wi, w))
            got = ref.wrap(p0-p1, w), ref.wrap(p2-ref.wrap(p0+p1, w), w)
            assert got == ref.cmul(ar, ai, wr, wi, w)
        counts[str(w)] = {'scalar_products': nscalar, 'complex_3M': trials, 'status': 'PASS'}
    return counts


def contexts(interval, last_use):
    events = []
    for j in range(100):
        events.extend([(j*interval, 1), (j*interval+last_use, -1)])
    live = peak = 0
    # Conservatively allocate before release when both happen on one edge.
    for _, change in sorted(events, key=lambda e: (e[0], -e[1])):
        live += change
        peak = max(peak, live)
    assert peak == last_use//interval + 1
    return peak


def main():
    cases = []
    for tag, nbf, products, words, cycles in [
        ('NTT32_N1024', 512*10, 3, 2, 984),
        ('FFT32_N1024', 256*9, 3, 4, 644),
        ('FFT64_N1024', 256*9, 12, 8, 2031),
        ('FFT128_N1024', 256*9, 45, 16, 7510),
    ]:
        work, out = nbf*products, nbf*words
        cases.append(dict(mode=tag, butterfly_count=nbf, products_per_butterfly=products,
                          total_product_slots=work, output_word32_count=out,
                          baseline_cycles=cycles,
                          multiplier_engines_needed_at_baseline=math.ceil(work/cycles),
                          output_pair_lanes_needed_average=math.ceil(out/(2*cycles)),
                          product_only_cycle_bounds={str(p): math.ceil(work/p) for p in (8, 12, 16)},
                          four_pair_output_cycle_bound=math.ceil(out/8)))
    live = []
    for w, interval, last in [(32, 3, 17), (64, 12, 29), (128, 48, 66)]:
        l = w//32
        c = contexts(interval, last)
        power2 = 1 << (c-1).bit_length()
        live.append(dict(width=w, interval=interval, last_use=last,
                         live_contexts=c, power2_context_slots=power2,
                         operand_words_per_array=power2*2*l,
                         sum_words_per_array=power2*l,
                         output_pair_lanes_peak_with_16_engines=math.ceil((16/{32:3,64:12,128:45}[w])*4*l/2),
                         arithmetic_word_addsub_ops=9*l,
                         last_inverse_stage_extra_round_add_ops=4*l))
    assert max(x['operand_words_per_array'] for x in live) == 16
    assert max(x['sum_words_per_array'] for x in live) == 8
    result = dict(date='2026-11-02', kind='analytical audit, not a cycle model of a new architecture',
        assumptions=[
            'Fixed 32x32 engines accepting one integer product each cycle; FFT 3M and current product truncation.',
            'NTT uses three Montgomery passes on these engines; bounds do not cover alternative reductions.',
            'FFT N1024 means 1024 scalar components, 512 complex points, 9 stages, 2304 butterflies.',
            'Cycle bounds exclude pipeline fill, dependencies, memory conflicts, roots, and stage transitions.',
            'One output-pair lane serves two 32-bit words/cycle; this does not include all arithmetic work.',
            'Live-context counts describe current core issue intervals, default LEAF_PD=2 and IN_REG=1.',
            'Smaller buffers change burst acceptance; no compatibility claim for the old four-context tile contract.',
            'No LUT saving is inferred from buffer bit count or adder operation count.',
        ],
        measured={name: area(ROOT/path) for name, path in [
            ('full', 'study/build/core_area/util.rpt'),
            ('nofft_wrapper', 'study/build/core_split/nofft/util.rpt'),
            ('fmt0_wrapper', 'study/build/core_split/fft32/util.rpt'),
            ('historical_fft32_core', 'study/build/at267_core/util.rpt')
        ]},
        demand=cases, liveness=live, arithmetic_checks=arithmetic_check())
    inputs = [ROOT/'model/fft_core_plan.py', ROOT/'hdl/tile/tile_thu.sv', ROOT/'hdl/core_ntt/ntt_core.sv']
    result['current_input_sha256'] = {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs}
    result['script_sha256'] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    out = ROOT/'study/results'
    out.mkdir(exist_ok=True)
    (out/'butterfly_resource_demand.json').write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
    lines = ['# Nhu cầu tài nguyên butterfly — phân tích ngày 02/11/2026', '',
             'Cận giải tích, chưa phải chu kỳ hay PPA của kiến trúc đề xuất.', '',
             '## Cận theo số tích 32×32 và số từ kết quả', '',
             '| Mode | Butterfly | Tích phần/BF | Chu kỳ baseline | Ít nhất engine ở tốc độ đó | Cận chu kỳ 8 / 12 / 16 engine | Ít nhất làn xuất 2 word32/ck (trung bình) |',
             '|---|---:|---:|---:|---:|---|---:|']
    for x in cases:
        lines.append(f"| {x['mode']} | {x['butterfly_count']} | {x['products_per_butterfly']} | {x['baseline_cycles']} | {x['multiplier_engines_needed_at_baseline']} | {' / '.join(str(v) for v in x['product_only_cycle_bounds'].values())} | {x['output_pair_lanes_needed_average']} |")
    lines += ['', '## Số context sống với lịch core hiện tại', '',
              '| FFT W | Cách BF (ck) | Lần dùng cuối (ck) | Context sống | Slot làm tròn lũy thừa 2 | Từ 32 bit mỗi mảng operand | Từ mỗi mảng tổng |',
              '|---|---:|---:|---:|---:|---:|---:|']
    for x in live:
        lines.append('| '+ ' | '.join(str(x[k]) for k in ('width','interval','last_use','live_contexts','power2_context_slots','operand_words_per_array','sum_words_per_array'))+' |')
    lines += ['', '## Giới hạn', '', *['- '+a for a in result['assumptions']], '',
              'Kiểm phép cộng các tích phần theo thứ tự bất kỳ, giữ nguyên wrap/rounding và 3M:', '',
              *[f"- W={w}: {v['scalar_products']} tích vô hướng, {v['complex_3M']} ca 3M PASS." for w,v in result['arithmetic_checks'].items()], '',
              'Đổi thứ tự cộng dùng số nguyên đủ rộng trong kiểm này; chưa chứng minh độ rộng accumulator hữu hạn hoặc pipeline mới.', '',
              'Số đo và hash báo cáo nguồn: [JSON](butterfly_resource_demand.json).']
    (out/'butterfly_resource_demand.md').write_text('\n'.join(lines)+'\n', encoding='utf-8')
    print('\n'.join(lines[:10]))
    print('Arithmetic:', result['arithmetic_checks'])
    print('Reports written; production RTL, PLAN and spec unchanged.')


if __name__ == '__main__':
    main()
