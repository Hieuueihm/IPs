"""Audit structural illustrations; this does not verify a new RTL netlist."""
from pathlib import Path
import json, hashlib, random
from pypdf import PdfReader
import structural
import structural_detail
from detail_contract import CARDS

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
PORTS=json.loads((ROOT/'rebuild/flextransform/microarchitecture/ports.json').read_text(encoding='utf-8'))['ports']
manifest=json.loads((HERE/'structural_manifest.json').read_text(encoding='utf-8'))
assert len(structural.SHEETS)==58
assert len({s['code'] for s in structural.SHEETS})==58
assert {s['module'] for s in structural.SHEETS if s['module']!='primitive'}==set(PORTS)
for s in structural.SHEETS:
    c=s['circuit']
    for e in c.edges:
        assert e['a'] in c.nodes and e['b'] in c.nodes,(s['code'],e)
        for k,side in [(e['a'],e['ss']),(e['b'],e['ds'])]:c.point(k,side)
for s in manifest['figures']:
    path=HERE/'structural_svg'/s['svg']
    assert hashlib.sha256(path.read_bytes()).hexdigest()==s['sha256']
for name,ports in PORTS.items():assert {p['name'] for p in ports}==set(CARDS[name]['port_semantics'])

def simulate_gates(code,inputs):
    c=next(s['circuit'] for s in structural.SHEETS if s['code']==code)
    values=dict(inputs)
    for _ in range(len(c.nodes)):
        for key,n in c.nodes.items():
            if key in values:continue
            incoming=[e['a'] for e in c.edges if e['b']==key]
            if not incoming or not all(a in values for a in incoming):continue
            ins=[values[a] for a in incoming];kind=n['kind']
            if kind=='XOR':assert len(ins)==2;values[key]=ins[0]^ins[1]
            elif kind=='AND':assert len(ins)==2;values[key]=ins[0]&ins[1]
            elif kind=='OR':assert len(ins)==2;values[key]=ins[0]|ins[1]
            elif kind=='NOT':assert len(ins)==1;values[key]=1-ins[0]
            elif kind=='out':assert len(ins)==1;values[key]=ins[0]
    return values

for a in (0,1):
    for b in (0,1):
        for cin in (0,1):
            v=simulate_gates('S01',{'a':a,'b':b,'cin':cin})
            assert v['sum']==((a+b+cin)&1) and v['cout']==((a+b+cin)>>1)
for d0 in (0,1):
    for d1 in (0,1):
        for sel in (0,1):
            v=simulate_gates('S02B',{'d0':d0,'d1':d1,'s':sel})
            assert v['out']==(d1 if sel else d0)

rng=random.Random(20261107)
for _ in range(10000):
    ql=rng.randrange(3,1<<15)|1;qh=rng.randrange(3,1<<15)|1
    lo=rng.randrange(2*ql);hi=rng.randrange(2*qh)
    A=(hi<<18)|(1<<17)|lo
    B=(((~qh)&0x1ffff)<<18)|(1<<17)|((~ql)&0x1ffff)
    R=(A+B+1)&((1<<36)-1)
    low_result=lo if not((R>>17)&1) else R&65535
    high_result=hi if not((R>>35)&1) else (R>>18)&65535
    assert low_result==lo%ql and high_result==hi%qh

for _ in range(10000):
    th=rng.getrandbits(32);ph=rng.getrandbits(32);nz=rng.randrange(2)
    lo=(th&65535)+(ph&65535)+nz
    hi=(th>>16)+(ph>>16)+(lo>>16)
    assert (hi<<16 | (lo&65535))==th+ph+nz
for fmt in range(3):
    L=1<<fmt;W=32*L
    for case in range(1000):
        words=[rng.getrandbits(32) for _ in range(4)];s=rng.randrange(10)
        if case<10:words=[0xffffffff]*4;s=case
        elif case<20:words=[0xffffffff,0,0xffffffff,0];s=case-10
        j=max(s-1,0)
        out=[];carry=0
        for i,word in enumerate(words):
            start=(i%L)==0;bias=(1<<j) if start and s else 0
            out.append((word+bias+carry)&0xffffffff)
            if start:carry=int(bool(s) and (word>>j)==((1<<(32-j))-1))
            else:carry=int(bool(carry) and word==0xffffffff)
            if (i+1)%L==0:carry=0
        for st in range(0,4,L):
            val=sum(words[st+k]<<(32*k) for k in range(L))
            want=(val+((1<<j) if s else 0))&((1<<W)-1)
            got=sum(out[st+k]<<(32*k) for k in range(L))
            assert got==want

pdf=PdfReader(ROOT/'output/pdf/FlexTransform_Contract_0_2_Toan_hoc_den_RTL.pdf')
landscape=sum(float(p.mediabox.width)>float(p.mediabox.height) for p in pdf.pages)
assert landscape==58
qa=json.loads((HERE/'build_qa.json').read_text(encoding='utf-8'))
assert len(qa['structural_pages'])==58
assert qa['port_semantic_coverage']==444
qa['structural_audit']={'result':'PASS','figures':58,'modules':23,'landscape_pages':58,
 'full_adder_gate_truth_cases':8,'mux_gate_truth_cases':8,'packed_guard_cases':10000,
 'scalar_U_two_adder_cases':10000,'normalizer_carry_cases':3000,'port_semantic_coverage':444,
 'all_svg_hashes_match':True,'all_wire_endpoints_exist':True,
 'scope':'Document schematic topology and formulas only; not RTL verification.'}
(HERE/'build_qa.json').write_text(json.dumps(qa,ensure_ascii=False,indent=2),encoding='utf-8')
print('STRUCTURAL_DOC_PASS: 58 figures, 23 cards, 444 ports; arithmetic illustrations PASS')
