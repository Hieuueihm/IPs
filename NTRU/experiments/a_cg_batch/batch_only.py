"""Prepare the static batch-only driver's exact subset of the full fixtures."""
from pathlib import Path
import json
import struct

HERE=Path(__file__).resolve().parent
B=HERE.parents[1]/'study/build/a_cg_batch'

def main():
    raw=(B/'fixtures.bin').read_bytes();w=struct.unpack('<'+'I'*(len(raw)//4),raw)
    assert w[0]==0x43474233
    pos=2;records=[];indices=[]
    for i in range(w[1]):
        start=pos;h=w[pos:pos+13];pos+=13
        ns,nr,nw=h[-3:];pos+=4*ns+16*nr+2*nw
        if not h[8]:records.append(w[start:pos]);indices.append(i)
    assert pos==len(w)
    out=[w[0],len(records)]+[v for r in records for v in r]
    (B/'batch_only.bin').write_bytes(struct.pack('<'+'I'*len(out),*out))
    (B/'batch_only_indices.json').write_text(json.dumps(indices)+'\n')
    s=(HERE/'main.cpp').read_text().replace('d.cfg_packed=packed;','')
    s=s.replace('invalid(0,1,0,8380417);invalid(1,1,0,0);','')
    needle='auto native=word(),packed=word(),jl=word(),stages=word(),nr=word(),nw=word();'
    s=s.replace(needle,needle+'if(packed)throw std::runtime_error("packed fixture in static batch core");')
    (B/'batch_only_main.cpp').write_text(s)
    print('Static batch-only fixture cases:',len(records))

if __name__=='__main__':main()
