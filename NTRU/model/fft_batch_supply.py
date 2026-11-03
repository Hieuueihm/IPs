"""Static port-demand analysis for proposed FFT packing, not a new RTL simulation.

Each candidate batch is serviced in isolation. Count distinct rows per physical
bank and distinct roots per batch; do not infer an implemented speedup.
"""
from collections import Counter
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def bank(i):return (i&63)^((i>>2)&48)^((i>>4)&48)


def analyze(n,width,inverse=False):
    hn=n//2;limbs=width//16;lanes={32:16,64:4,128:1}[width]
    span=2 if inverse else hn;groups=hn if inverse else 2;stages=[]
    for stage in range(n.bit_length()-2):
        butterflies=[]
        for g in range(groups//2):
            for offset in range(span//2):
                j=g*span+offset
                butterflies.append(([j,j+hn,j+span//2,j+span//2+hn],groups+g))
        assert len(butterflies)==n//4
        batches=[]
        for start in range(0,len(butterflies),lanes):
            chunk=butterflies[start:start+lanes]
            addresses=[i*limbs+l for indices,root in chunk for i in indices for l in range(limbs)]
            assert len(set(addresses))==len(addresses)
            by_bank=Counter(bank(a) for a in addresses)
            batches.append({'butterflies':len(chunk),'read_bank_beats':len(addresses),
                'data_read_rounds':max(by_bank.values()),'write_rounds':max(by_bank.values()),
                'capacity_only_min_rounds':(len(addresses)+63)//64,
                'distinct_twiddles':len({root for indices,root in chunk}),'real_product_issue_beats':3})
        stages.append({'stage':stage,'span':span,'batches':len(batches),
            'data_read_rounds_min':min(b['data_read_rounds'] for b in batches),
            'data_read_rounds_max':max(b['data_read_rounds'] for b in batches),
            'distinct_twiddles_min':min(b['distinct_twiddles'] for b in batches),
            'distinct_twiddles_max':max(b['distinct_twiddles'] for b in batches),
            'data_read_rounds_sum':sum(b['data_read_rounds'] for b in batches),
            'root_reads_sum_no_cross_batch_cache':sum(b['distinct_twiddles'] for b in batches),
            'capacity_only_min_rounds_max':max(b['capacity_only_min_rounds'] for b in batches)})
        span=span*2 if inverse else span//2;groups=groups//2 if inverse else groups*2
    return {'n':n,'width_bits':width,'op':'IFFT' if inverse else 'FFT',
        'proposed_butterflies_per_batch':lanes,'stages':stages}


def main():
    cases=[analyze(1<<logn,width,inv) for logn in range(2,11) for width in (32,64,128) for inv in (False,True)]
    result={'scope':'Static isolated-batch port demand; current bank map, one FFT root ROM read per cycle; no cross-batch root cache. No candidate controller RTL or speedup claim.',
        'cases':cases}
    out=ROOT/'study/results/fft_batch_supply.json';out.write_text(json.dumps(result,indent=2)+'\n')
    for c in cases:
        if c['n']==1024 and c['op']=='FFT':
            print(c['width_bits'],c['proposed_butterflies_per_batch'],[(s['data_read_rounds_max'],s['distinct_twiddles_max']) for s in c['stages']])


if __name__=='__main__':main()
