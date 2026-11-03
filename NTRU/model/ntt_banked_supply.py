"""Executable 64x16-bit bank/16x48-bit root-bundle supply experiment.

One read AND one write per bank per cycle are assumed. This is not a RAM RTL
or cycle-accurate controller. No physical interconnect delay is modeled.
"""
from collections import Counter
import importlib.util
import json
from pathlib import Path
from random import Random
import sys

ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/'scripts'))
from arith_experiment_common import hashes
spec=importlib.util.spec_from_file_location('tile_ref',ROOT/'scripts/prototype_ntt_cluster.py')
ref=importlib.util.module_from_spec(spec);spec.loader.exec_module(ref)


def bank(index):
    return (index&63)^((index>>2)&0x30)^((index>>4)&0x30)


def column(bit):
    return bit if bit<6 else 4+((bit-4)&1)


def expand(value,bits):
    return sum(((value>>i)&1)<<b for i,b in enumerate(bits))


def groups(logn,p,paired,aware=True,inverse=False):
    used={p,p+1} if paired else {p}
    free=[b for b in range(logn) if b not in used]
    if not paired and aware:
        # Five independent bank columns, so 32 BFs occupy 64 different banks.
        seen={column(p)};front=[]
        for b in free:
            if column(b) not in seen:
                seen.add(column(b));front.append(b)
        free=front+[b for b in free if b not in front]
    if paired:
        return [[expand(g,free)+j*(1<<p) for j in range(4)] for g in range(1<<(logn-2))]
    pairs=[[expand(g,free),expand(g,free)+(1<<p)] for g in range(1<<(logn-1))]
    # Two BFs per tile: mode2 CT uses (0,2),(1,3), GS uses (0,1),(2,3).
    return [([*a,*b] if inverse else [a[0],b[0],a[1],b[1]]) for a,b in zip(pairs[::2],pairs[1::2])]


def rounds(indices,mapping):
    return max(Counter(mapping(i) for i in indices).values(),default=0)


def root_request(positions,p,paired,n):
    if paired:
        g=(n>>(p+2))+(positions[0]>>(p+2))
        return [g]
    # Tail reads parent bundle; root g is one of its two children, except g=1.
    gs={(n>>(p+1))+(i>>(p+1)) for i in positions}
    return sorted({max(1,g>>1) for g in gs})


def run_case(q,n,incomplete,inverse,rng,transactions=None):
    logn=n.bit_length()-1
    forward,backward,_=ref.stages(q,n,incomplete)
    layers=backward if inverse else forward
    p_order=list(range(logn-1,(0 if incomplete else -1),-1))
    if inverse:p_order=p_order[::-1]
    initial=[rng.randrange(q) for _ in range(n)];current=initial[:]
    rows=[]
    for stage in range(0,len(layers),2):
        paired=stage+1<len(layers)
        p=min(p_order[stage:stage+2]) if paired else p_order[stage]
        planned=groups(logn,p,paired,True,inverse)
        expected=ref.apply_layer(current,layers[stage],q,inverse)
        if paired:expected=ref.apply_layer(expected,layers[stage+1],q,inverse)
        # Explicit bank RAM read/write, bijective row+bank address, no alias.
        ram={(bank(i),i>>6):v for i,v in enumerate(current)}
        assert len(ram)==n
        out=current[:];read_rounds=naive=unaware=root_rounds=0;max_roots=0
        naive_groups=groups(logn,p,paired,False,inverse)
        mode=1 if paired else 2
        layer0={i:(j,w) for i,j,w in layers[stage]}
        layer1={i:(j,w) for i,j,w in layers[stage+1]} if paired else {}
        for start in range(0,len(planned),16):
            chunk=planned[start:start+16];indices=sum(chunk,[])
            assert len(set(indices))==len(indices)
            r=rounds(indices,bank);assert r==1
            read_rounds+=r;naive+=rounds(indices,lambda i:i&63)
            unaware+=rounds(sum(naive_groups[start:start+16],[]),bank)
            requests=sorted({g for positions in chunk for g in root_request(positions,p,paired,n)})
            root_round=rounds(requests,lambda g:g&15)
            assert root_round==1
            root_rounds+=root_round;max_roots=max(max_roots,len(requests))
            bank_read=[0]*64;bank_write=[0]*64;encoded=[];write_mask=0
            for positions in chunk:
                values=[ram[bank(i),i>>6] for i in positions]
                a,b,c,d=positions
                if paired:
                    w=[layer0[a][1],layer0[c][1],layer1[a][1],layer1[b][1]] if inverse else \
                      [layer0[a][1],layer0[b][1],layer1[a][1],layer1[c][1]]
                else:
                    w=[layer0[a][1],layer0[c][1]] if inverse else [layer0[a][1],layer0[b][1]]
                roots=ref.encode_roots(mode,inverse,w,q)
                result=ref.oracle(mode,q==3329,inverse,ref.pack(values),roots)
                encoded.append(roots)
                for k,i in enumerate(positions):
                    out[i]=(result>>(16*k))&65535
                    bank_read[bank(i)]=current[i];bank_write[bank(i)]=out[i];write_mask|=1<<bank(i)
            if transactions is not None:
                offset=bank(indices[0]);assert offset&15==0
                control=(p<<28)|((offset>>4)<<26)|(logn<<22)
                transactions.append((1,0,mode,int(q==3329),int(inverse),ref.pack(bank_read),
                                     ref.pack(encoded,(3 if paired else 2)*16),ref.pack(bank_write),control,write_mask))
        assert out==expected
        current=out
        rows.append({'stage':stage,'paired':paired,'low_stride_bit':p,
                     'data_read_beats':read_rounds,'data_write_beats':read_rounds,
                     'modulo_bank_read_beats':naive,'xor_without_tail_reorder_beats':unaware,
                     'root_bundle_beats':root_rounds,'max_distinct_bundles_per_beat':max_roots,
                     'active_coefficients_per_full_beat':min(n,64)})
    ordinary=initial[:]
    for layer in layers:ordinary=ref.apply_layer(ordinary,layer,q,inverse)
    assert current==ordinary
    return {'q':q,'n':n,'incomplete':incomplete,'inverse':inverse,'passes':rows,
            'total_read_beats':sum(r['data_read_beats'] for r in rows),
            'modulo_bank_read_beats':sum(r['modulo_bank_read_beats'] for r in rows)}


def main():
    rng=Random(20261026);rows=[]
    for q,sizes in ((12289,(8,16,32,64,128,256,512,1024)),(3329,(8,16,32,64,128,256))):
        for n in sizes:
            for inverse in (False,True):
                rows.append(run_case(q,n,q==3329 and n==256,inverse,rng))
    result={'configuration':{'data_banks':64,'data_word_bits':16,'ports_per_bank':'1R+1W',
                             'bank_function':'(i&63)^((i>>2)&0x30)^((i>>4)&0x30)',
                             'data_depth_at_n1024':16,'data_capacity_bits_at_n1024':16384,
                             'root_banks':16,'root_bundle_bits':48,'root_depth_at_n1024':32,
                             'root_capacity_bits_per_direction_at_n1024':24576},
            'cases':rows,'mismatches':0,'data_bank_conflicts':0,'root_bank_conflicts':0,
            'source_sha256':hashes(['model/ntt_banked_supply.py','scripts/prototype_ntt_cluster.py']),
            'limits':['Pass-level bank and exact arithmetic model, not SRAM/controller RTL.',
                      'Bundles store GM[g],GM[2g],GM[2g+1]; repeated requests broadcast.',
                      'Root bundle RAM duplicates roots (about 1.5x flat table per direction).',
                      'Read/write beats exclude RAM latency, pipeline drain, stalls and normalization.',
                      'Mode0 four-BF/tile needs 128 coefficients/cycle; 64 banks feed only mode1 or mode2 at II=1.']}
    dest=ROOT/'study/results/ntt_banked_supply.json';dest.write_text(json.dumps(result,indent=2)+'\n')
    for row in rows:
        if row['n'] in (8,256,512,1024):
            print(row['q'],row['n'],'GS' if row['inverse'] else 'CT','read',row['total_read_beats'],'modulo',row['modulo_bank_read_beats'])
    print('PASS',len(rows),'transform cases; zero conflicts')


if __name__=='__main__':main()
