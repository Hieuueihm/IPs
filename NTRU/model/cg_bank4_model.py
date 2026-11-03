"""CG bank candidate: four-source read/write network, with physical cycle replay.

NTT hmin bits are separate row planes; FFT components/limbs are row planes.
For M>=64, bank = low5(p) XOR (top_bit(p)<<4), row = p>>5.
Small transforms use a stage-dependent embedding in the 32-bank shuffle graph.
No RTL changes. Run python -X utf8 model/cg_bank4_model.py.
"""
import hashlib
import importlib.util
import json
import random
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MASK32 = (1 << 32) - 1


def load(name, filename):
    s = importlib.util.spec_from_file_location(name, ROOT/'model'/filename)
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m


sc = load('bank4_sc', 'ntt_core_sched.py')
pc = load('bank4_pc', 'ntt_prime_core.py')
fp = load('bank4_fp', 'fft_core_plan.py')
FFT = {1: (3, [16, 17]), 2: (12, [24, 25, 28, 29]),
       4: (48, [45, 48, 50, 51, 60, 63, 65, 66])}


def rol(x, s, n):
    s %= n
    return ((x << s) | (x >> (n-s if s else n))) & ((1 << n)-1)


def bank(p, m, stage):
    n = m.bit_length()-1
    if n == 0:
        return 0
    if n >= 6:
        return (p & 31) ^ (((p >> (n-1)) & 1) << 4)
    return rol(rol(p, -stage, n) << (5-n), stage, 5)


def addr(buf, p, plane, m, planes, stage):
    rows = max(1, m//32)
    return bank(p, m, stage), buf*rows*planes + plane*rows + (p >> 5)


def template(m, planes, inverse, fft_l, s, residue, interleaved=False):
    n = m.bit_length()-1
    f = n-1-s if inverse else s
    src_stage, dst_stage = (f+1, f) if inverse else (f, f+1)
    assignment = defaultdict(list)
    for i in range(m//2):
        t = bank(i, m, f) & 15
        assignment[t].append(i)
    ev = []
    for t, indices in sorted(assignment.items()):
        first = 2
        if not fft_l:
            while (residue+first+t//6) % 3:
                first += 1
        for k, i in enumerate(indices):
            for part in range(1 if fft_l else planes):
                per = FFT[fft_l][0] if fft_l else 3
                a = first + per*(k if fft_l else k*planes+part)
                far, near = (i, i+m//2), (2*i, 2*i+1)
                rp, wp = (near, far) if inverse else (far, near)
                e = dict(t=t, k=k, i=i, part=part, A=a, per=per, rp=rp, wp=wp,
                         source_stage=src_stage, dest_stage=dst_stage, s=s, reads=[], writes=[])
                for j in range(planes if fft_l else 1):
                    pl = ((j%2)*fft_l+j//2 if interleaved else j) if fft_l else part
                    rc = a-2+j if fft_l else a-2
                    wc = a+FFT[fft_l][1][j]+2 if fft_l else a+sc.TILE_LAT+1
                    for port, p in enumerate(rp):
                        e['reads'].append((addr(s&1, p, pl, m, planes, src_stage), rc, p, pl, port))
                    for port, p in enumerate(wp):
                        opl=j if fft_l else part
                        e['writes'].append((addr(1-(s&1), p, opl, m, planes, dst_stage), wc, p, opl, port))
                ev.append(e)
    return ev


class Book:
    def __init__(self):
        self.rd, self.wr = defaultdict(set), defaultdict(set)
        self.rt, self.wt, self.last = {}, {}, {}

    def earliest(self, ev, lower, modulus, residue):
        rd, wr = defaultdict(set), defaultdict(set)
        for e in ev:
            lower = max(lower, self.last.get(e['t'], -100000)-e['A']+1)
            for a, c, *_ in e['reads']:
                assert c not in rd[a[0]], ('internal read collision', a, c)
                rd[a[0]].add(c)
                lower = max(lower, self.wt.get(a, -100000)-c+1)
            for a, c, *_ in e['writes']:
                assert c not in wr[a[0]], ('internal write collision', a, c)
                wr[a[0]].add(c)
                lower = max(lower, self.rt.get(a, -100000)-c+1,
                            self.wt.get(a, -100000)-c+1)
        start = lower + ((residue-lower) % modulus)
        while True:
            if (all(not any(start+c in self.rd[b] for c in times) for b,times in rd.items())
                and all(not any(start+c in self.wr[b] for c in times) for b,times in wr.items())):
                return start
            start += modulus

    def take(self, ev, start):
        for e in ev:
            e['A'] += start
            for name, used, latest in [('reads', self.rd, self.rt), ('writes', self.wr, self.wt)]:
                shifted = []
                for a, c, p, pl, port in e[name]:
                    c += start
                    assert c not in used[a[0]], (name, a, c)
                    used[a[0]].add(c)
                    latest[a] = max(latest.get(a, -100000), c)
                    shifted.append((a, c, p, pl, port))
                e[name] = shifted
            self.last[e['t']] = max(self.last.get(e['t'], -1), e['A']+e['per']-1)


CACHE = {}


def plan(m, planes, inverse, fft_l, interleaved=False):
    key = (m, planes, inverse, fft_l, interleaved)
    if key in CACHE:
        return CACHE[key]
    n = m.bit_length()-1
    book, layers, starts, labels = Book(), [], [], list(range(m))
    start = 0
    for s in range(n):
        choices = []
        for residue in range(1 if fft_l else 3):
            ev = template(m, planes, inverse, fft_l, s, residue, interleaved)
            choices.append((book.earliest(ev, start, 1 if fft_l else 3, residue), ev))
        start, ev = min(choices, key=lambda x:x[0])
        book.take(ev, start)
        starts.append(start)
        h = (1 << s) if inverse else m >> (s+1)
        out_labels = [None]*m
        for e in ev:
            cx, cy = (labels[p] for p in e['rp'])
            assert cy == cx+h and (cx//h)%2 == 0
            # FFT roots differ from NTT: base M/h, not M/(2h).
            e['root'] = (m//h if fft_l else m//(2*h)) + cx//(2*h)
            for p, label in zip(e['wp'], (cx, cy)):
                out_labels[p] = label
        assert None not in out_labels
        labels = out_labels
        layers.append(ev)
    assert labels == list(range(m))
    cycles = (max(max(x) for x in book.wr.values()) - min(min(x) for x in book.rd.values())+1) if n else 0
    result = dict(m=m, planes=planes, inverse=inverse, fft_l=fft_l, layers=layers,
                  interleaved=interleaved, starts=starts, cycles=cycles, rows_per_buffer=max(1,m//32)*planes)
    # Every layout is injective, including stage-dependent tiny transforms.
    for st in range(n+1):
        addresses = {addr(0,p,pl,m,planes,st) for p in range(m) for pl in range(planes)}
        assert len(addresses) == m*planes
    CACHE[key] = result
    return result


def replay(pn, data, q=None, gm=None, igm=None):
    """Chronological physical RAM replay; detect stale values, aliases and same-edge hazards."""
    m, planes, inv, fl = (pn[x] for x in ('m','planes','inverse','fft_l'))
    n = m.bit_length()-1
    stage0 = n if inv else 0
    memory = {}
    def word(p, pl):
        if fl:
            return (data[p+(pl//fl)*m] >> (32*(pl%fl))) & MASK32
        return data[p*planes+pl]
    for p in range(m):
        for pl in range(planes):
            a = addr(0,p,pl,m,planes,stage0)
            assert a not in memory
            memory[a] = (word(p,pl), (-1,p,pl))
    events, states = [], []
    for layer in pn['layers']:
        for e in layer:
            idx = len(states)
            states.append(dict(e=e, inputs={}, outputs=None))
            for kind in ('reads','writes'):
                for a,c,p,pl,port in e[kind]:
                    events.append((c,kind,idx,a,p,pl,port))
    for cyc,kind,idx,a,p,pl,port in sorted(events):
        st = states[idx]; e = st['e']; s = e['s']
        if kind == 'reads':
            value, version = memory[a]
            assert version == (s-1,p,pl), ('stale/alias',cyc,a,version,(s-1,p,pl))
            st['inputs'][port,pl] = value
            if len(st['inputs']) == (2*planes if fl else 2):
                if fl:
                    w = 32*fl
                    vals = [fp.wrap(sum(st['inputs'][port,part*fl+k] << (32*k) for k in range(fl)),w)
                            for port in (0,1) for part in (0,1)]
                    ar,ai,br,bi = vals
                    wr,wi = (igm if inv else gm)[e['root']]
                    if inv:
                        tr,ti = fp.cmul(fp.wrap(ar-br,w),fp.wrap(ai-bi,w),wr,wi,w)
                        vals = [fp.wrap(ar+br,w),fp.wrap(ai+bi,w),tr,ti]
                        if s == n-1:
                            vals = [fp.wrap(v+(1 << (n-1)),w) >> n for v in vals]
                    else:
                        tr,ti = fp.cmul(br,bi,wr,wi,w)
                        vals = [fp.wrap(ar+tr,w),fp.wrap(ai+ti,w),fp.wrap(ar-tr,w),fp.wrap(ai-ti,w)]
                    st['outputs'] = {(port,part*fl+k): (vals[2*port+part] >> (32*k)) & MASK32
                                     for port in (0,1) for part in (0,1) for k in range(fl)}
                else:
                    x,y = st['inputs'][0,pl],st['inputs'][1,pl]
                    root = (igm if inv else gm)[e['root']]
                    if inv:
                        sm = (x+y)%q
                        u,v = (sm+(q if sm&1 else 0))>>1, sc.mont32((x-y)%q,root,q)
                    else:
                        t = sc.mont32(y,root,q)
                        u,v = (x+t)%q,(x-t)%q
                    st['outputs'] = {(0,pl):u,(1,pl):v}
        else:
            assert st['outputs'] is not None, ('write before operands',cyc,idx)
            memory[a] = (st['outputs'][port,pl],(s,p,pl))
    final_stage = 0 if inv else n
    buf = n&1
    if fl:
        return [fp.wrap(sum(memory[addr(buf,p,part*fl+k,m,planes,final_stage)][0] << (32*k)
                            for k in range(fl)),32*fl) for part in (0,1) for p in range(m)]
    return [memory[addr(buf,p,pl,m,planes,final_stage)][0] for p in range(m) for pl in range(planes)]


def host_cost(pn):
    m,planes,inv,fl = (pn[x] for x in ('m','planes','inverse','fft_l'))
    n = m.bit_length()-1
    costs = []
    for st in (n if inv else 0, 0 if inv else n):
        cycles = worst = 0
        words = m*planes
        for first in range(0,words,4):
            banks = []
            for i in range(first,min(first+4,words)):
                if fl:
                    scalar,k = divmod(i,fl)
                    part,p = divmod(scalar,m)
                    pl = part*fl+k
                else:
                    p,pl = divmod(i,planes)
                banks.append(bank(p,m,st))
            c = max(Counter(banks).values())
            cycles += c
            worst = max(worst,c)
        costs.append(dict(cycles_128bit_lines_serialized=cycles,max_subcycles_per_line=worst))
    return dict(load=costs[0],readback=costs[1])


def root_schedule(pn):
    rows=0
    for layer in pn['layers']:
        seq=defaultdict(dict)
        for e in layer:
            old=seq[e['t']].setdefault(e['k'],e['root'])
            assert old==e['root']  # NTT hmin row planes reuse the same root.
        periods=[]
        for values in seq.values():
            a=[values[k] for k in sorted(values)]
            p=1
            while not all(v==a[k%p] for k,v in enumerate(a)):
                p*=2
            periods.append(p)
        common=max(periods)
        assert all(common%p==0 for p in periods)
        rows+=common
    return dict(shared_index_rows_per_lane=rows,
                word32_per_lane_one_direction=rows*(pn['planes'] if pn['fft_l'] else 1))


def main():
    rsrc,wsrc = defaultdict(set),defaultdict(set)
    cases = []
    for ln in range(1,11):
        for hm in range(min(2,ln-1)+1):
            for inv in (False,True):
                pn = plan(1 << (ln-hm),1 << hm,inv,0)
                cases.append(dict(mode='NTT',N=1 << ln,hmin=hm,inverse=inv,cycles=pn['cycles'],
                                  rows_per_buffer=pn['rows_per_buffer'],host=host_cost(pn)))
    for ln in range(1,11):
        for fl in (1,2,4):
            for inv in (False,True):
                for inter in (False,True) if fl>1 else (False,):
                    pn = plan(1 << (ln-1),2*fl,inv,fl,inter)
                    cases.append(dict(mode=f'FFT{32*fl}',N=1 << ln,hmin=0,inverse=inv,cycles=pn['cycles'],
                                      interleaved=inter,rows_per_buffer=pn['rows_per_buffer'],host=host_cost(pn)))
    for pn in CACHE.values():
        root_schedule(pn)
        for layer in pn['layers']:
            for e in layer:
                for a,c,p,pl,port in e['reads']:
                    rsrc[e['t'],port].add(a[0])
                for a,c,p,pl,port in e['writes']:
                    wsrc[a[0]].add((e['t'],port))
    assert max(map(len,rsrc.values())) <= 4 and max(map(len,wsrc.values())) <= 4
    print('Topology and physical port/dependency planning:',len(cases),'configurations PASS',flush=True)
    tabs = sc.Tables(); checks = Counter()
    for prof,(q,lns) in sc.PROFILES.items():
        for ln in lns:
            hm = sc.min_stride(q,ln).bit_length()-1
            for op in (5,6):
                pn = plan(1 << (ln-hm),1 << hm,op==6,0)
                for data,expected in sc.golden()[prof,ln,op]:
                    assert replay(pn,data,q,tabs.gm[q],tabs.igm[q]) == expected,(prof,ln,op)
                    checks['NTT_golden'] += 1
    rng = random.Random(7)
    for app,q,ln,hm in pc.SURVEY:
        gm,igm = pc.tables(q,ln,hm)
        data = [rng.randrange(q) for _ in range(1 << ln)]
        f = replay(plan(1 << (ln-hm),1 << hm,False,0),data,q,gm,igm)
        assert f == pc.ref_forward(data,q,ln,hm),app
        assert replay(plan(1 << (ln-hm),1 << hm,True,0),f,q,gm,igm) == data,app
        checks['NTT_survey_configs'] += 1
    print('NTT numeric physical replay:',dict(checks),'PASS',flush=True)
    roots = {w:fp.roots(w) for w in (32,64,128)}
    iroots = {w:fp.roots_inv(w) for w in (32,64,128)}
    for line in (ROOT/'spec/FlexTransform/1.0/assets/kernel_fixtures.jsonl').read_text().splitlines():
        d = json.loads(line); c = d['command']
        if c['op'] not in (0,1) or c['fmt'] > 2:
            continue
        fl=1 << c['fmt'];w=32*fl
        data=[fp.wrap(int(x,16),w) for x in d['a'][0]]
        expected=[fp.wrap(int(x,16),w) for x in d['expected'][0]]
        if c['logn'] == 0:
            assert data == expected,c
            checks[f'FFT{w}_identity_N1'] += 1
            continue
        for inter in (False,True) if fl>1 else (False,):
            pn=plan(1 << (c['logn']-1),2*fl,c['op']==1,fl,inter)
            assert replay(pn,data,gm=roots[w],igm=iroots[w]) == expected,c
            checks[f'FFT{w}_golden'+('_interleaved' if inter else '')] += 1
    print('FFT bit-accurate physical replay:',dict(checks),'PASS',flush=True)
    # Deliberately drop the bank xor: the checker must catch x/y colliding.
    global bank
    real_bank=bank
    try:
        bank=lambda p,m,stage:p&31
        bad=template(64,1,False,0,0,0)
        try:
            Book().earliest(bad,0,3,0)
        except AssertionError:
            checks['mutation_missing_bank_xor_detected']+=1
        else:
            raise AssertionError('Bank collision mutation was not detected')
    finally:
        bank=real_bank
    result = dict(date='2026-11-02',kind='physical RAM cycle model, not RTL or PPA',
        candidate='low5 xor top, factor hmin into row planes, tiny stage embedding',
        read_sources={f'{t}{"xy"[op]}':sorted(v) for (t,op),v in sorted(rsrc.items())},
        write_sources={str(b):sorted(v) for b,v in sorted(wsrc.items())},
        max_read_sources=max(map(len,rsrc.values())),max_write_sources=max(map(len,wsrc.values())),
        cases=cases,checks=dict(checks),
        root_examples={tag:root_schedule(plan(m,planes,False,fl)) for tag,m,planes,fl in
                       [('NTT_N1024',1024,1,0),('FFT32_N1024',512,2,1),('FFT64_N1024',512,4,2),('FFT128_N1024',512,8,4)]},
        limitations=['Assumes current tile scalar-NTT/FFT issue periods and output latencies. Interleaved inputs use the memory-retiming hypothesis; no new RTL or packed16.',
                     'Root values correct in replay; root ROM port implementation and BRAM cost are not modeled.',
                     'Host layout changes; line serialization counted, adapter RTL and buffering not designed.',
                     'Kernel cycles exclude load/readback/configuration/root loading.',
                     'No area/Fmax claim. Four is a found fan-in bound, not a proof of global optimality.'])
    files=[Path(__file__),ROOT/'model/ntt_core_sched.py',ROOT/'model/fft_core_plan.py',ROOT/'model/ntt_prime_core.py',
           ROOT/'spec/FlexTransform/1.0/assets/kernel_fixtures.jsonl',
           ROOT/'spec/FlexTransform/1.0/assets/fft_q64_64.mem',
           ROOT/'spec/FlexTransform/2.0/assets/kernel/ntt_q8380417.jsonl']
    for base,names in [('1.0',['ntt_q12289','ntt_q3329']),('2.0',['ntt_q8380417'])]:
        for name in names:
            for direction in ('forward','inverse'):
                files.append(ROOT/f'spec/FlexTransform/{base}/assets/{name}_{direction}.mem')
    result['sha256']={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    out=ROOT/'study/results'
    (out/'cg_bank4_model.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    lines=['# CG: ứng viên mạng tối đa bốn nguồn mỗi cổng','',
           'Model chu kỳ RAM vật lý; chưa phải RTL, chưa có số LUT/BRAM/timing.','',
           f"Tối đa nguồn đọc: **{result['max_read_sources']}**; nguồn ghi: **{result['max_write_sources']}**.",
           f"{len(cases)} cấu hình cổng/phụ thuộc; kiểm số học: {dict(checks)}.",'',
           '## Chu kỳ tiêu biểu','',
           '| Mode | N | hmin | Chiều | Input xen kẽ | Kernel cycle | Hàng/buffer | Nạp/đọc: tối đa nhịp con mỗi line 128 bit |',
           '|---|---:|---:|---|---|---:|---:|---|']
    for c in cases:
        if (c['mode']=='NTT' and c['N'] in (256,512,1024)) or (c['mode']!='NTT' and c['N']==1024):
            lines.append(f"| {c['mode']} | {c['N']} | {c['hmin']} | {'ngược' if c['inverse'] else 'xuôi'} | {'có' if c.get('interleaved') else 'không'} | {c['cycles']} | {c['rows_per_buffer']} | {c['host']['load']['max_subcycles_per_line']} / {c['host']['readback']['max_subcycles_per_line']} |")
    lines+=['','## Giới hạn','',*['- '+x for x in result['limitations']], '',
            'Nguồn: [model](../../model/cg_bank4_model.py), [JSON, topology đầy đủ và hash](cg_bank4_model.json).']
    (out/'cg_bank4_model.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print('Wrote study/results/cg_bank4_model.{json,md}',flush=True)


if __name__ == '__main__':
    main()
