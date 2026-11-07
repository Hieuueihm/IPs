"""Collect measured evidence; never turn incomplete runs into positive results."""
import argparse
from collections import Counter,defaultdict
import hashlib
import json
from pathlib import Path
import re
import struct

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
OUT=ROOT/'study/build/paper_ablation31'
NAMES=['reference','single_stream','separate_history','sparse_feed','split_domains','dedicated_mont32']
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def records(file):
    b=file.read_bytes();w=struct.unpack('<'+'I'*(len(b)//4),b);assert w[0]==0x43474233
    pos=2;rows=[]
    for _ in range(w[1]):
        h=w[pos:pos+13];pos+=13;ns,nr,nw=h[10:]
        d=w[pos:pos+4*ns];pos+=4*ns
        payload=w[pos:pos+16*nr+2*nw];pos+=16*nr+2*nw
        # Only descriptor gap, every fourth descriptor word, may change.
        norm=tuple(h)+tuple(v for i,v in enumerate(d) if i%4!=3)+tuple(payload)
        rows.append(hashlib.sha256(struct.pack('<'+'I'*len(norm),*norm)).hexdigest())
    assert pos==len(w);return rows
def synth_report(d):
    p=d/'synth/util.rpt'
    if not p.exists():return None
    text=p.read_text()
    assert 'Vivado v.2018.1' in text and '7z020clg400-2' in text,'Mixed tool/device synthesis evidence'
    def cell(label):
        m=re.search(r'^\|\s*'+re.escape(label)+r'\s*\|\s*(\d+)\s*\|',text,re.M);assert m,label;return int(m[1])
    out=dict(LUT=cell('Slice LUTs*'),FF=cell('Slice Registers'),LUTRAM=cell('LUT as Distributed RAM'),SRL=cell('LUT as Shift Register'))
    mp=d/'synth/metrics.txt'
    if mp.exists():
        for line in mp.read_text().splitlines():
            k,v=line.split('=');out[k]=float(v) if '.' in v else int(v)
    out['complete']=(d/'synth/synthesized.dcp').exists()
    return out
def cycles(d):
    p=d/'sim.log'
    if not p.exists():return {},False
    text=p.read_text();rows={}
    for line in text.splitlines():
        if not line.startswith('CASE '):continue
        m=re.match(r'CASE (\d+) ',line);v=dict(re.findall(r'(\w+)=(\d+)',line));rows[int(m[1])]={k:int(x) for k,x in v.items()}
    complete='TOTAL cases=1026 errors=0 PASS' in text
    if complete:assert len(rows)==1026 and all(x['errors']==0 for x in rows.values())
    return rows,complete
def decompose():
    p=OUT/'decomposition/routed_hierarchy.rpt'
    groups=defaultdict(lambda:[0]*8)
    rows=[]
    for line in p.read_text().splitlines():
        if not line.startswith('|'):continue
        a=[x.strip() for x in line.split('|')[1:-1]]
        if len(a)==10 and a[2].isdigit():rows.append((a[0],[int(x) for x in a[2:]]))
    for n,v in rows:
        if n=='system_wrapper':groups['routed_system']=v
        if n=='inst' and v[0]>30000:groups['accelerator']=v
        if n=='(inst)' and v[0]<1000:groups['AXI_host']=v
        if n=='core':groups['core']=v
        if n=='u_exec':groups['executor']=v
        if n=='(u_exec)':groups['executor_direct_memory_and_route']=v
        if n.startswith('engine['):cat='tiles_inclusive'
        elif n.startswith('(engine'):cat='tile_mixed_direct'
        elif n=='leaves':cat='leaf_array_and_fusion'
        elif n=='u_as':cat='shared_addsub'
        elif n=='d_mcw':cat='FFT_control_delay'
        elif n.startswith('g_arr32'):cat='Montgomery_delay_alignment'
        else:continue
        groups[cat]=[a+b for a,b in zip(groups[cat],v)]
    groups['PS_AXI_clock_reset_shell']=[a-b for a,b in zip(groups['routed_system'],groups['accelerator'])]
    groups['core_frontend']=[a-b for a,b in zip(groups['core'],groups['executor'])]
    actual_tile=[a-b for a,b in zip(groups['executor'],groups['executor_direct_memory_and_route'])]
    groups['tiles_after_parent_accounting']=actual_tile
    groups['tile_cross_hierarchy_residual']=[a-b for a,b in zip(actual_tile,groups['tiles_inclusive'])]
    summed=[sum(groups[k][i] for k in ['tile_mixed_direct','leaf_array_and_fusion','shared_addsub','FFT_control_delay','Montgomery_delay_alignment']) for i in range(8)]
    groups['tile_internal_combining_residual']=[a-b for a,b in zip(groups['tiles_inclusive'],summed)]
    ff=Counter()
    for line in (OUT/'decomposition/primitive_samples.tsv').read_text().splitlines()[1:]:
        name,ref,typ=line.split('\t')
        if ref.startswith('FD') and 'u_tile/' in name:
            family=re.sub(r'\[\d+\]','[]',name.split('u_tile/',1)[1]);ff[family]+=1
    return dict(columns=['LUT','logic_LUT','LUTRAM','SRL','FF','RAMB36','RAMB18','DSP48'],groups=dict(groups),source_sha256=sha(p),largest_tile_register_families=dict(ff.most_common(30)))
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--partial',action='store_true');args=ap.parse_args()
    report=dict(part='xc7z020clg400-2',period_ns=6.25,scope='OOC a_cg_axil: AXI host + full core + data/root RAM; not PS7 shell',variants={},decomposition=decompose())
    baseline=records(OUT/'reference/fixtures.bin')
    for n in NAMES:
        d=OUT/n;src=HERE/'variants'/n
        cy,passed=cycles(d)
        normalized=records(d/'fixtures.bin') if (d/'fixtures.bin').exists() else []
        fixture_ok=normalized==baseline
        r=dict(synth=synth_report(d),simulation_pass=passed,cases_completed=len(cy),same_arithmetic_payload=fixture_ok,
               arithmetic_payload_sha256=hashlib.sha256('\n'.join(normalized).encode()).hexdigest(),
               source_sha256={p.name:sha(p) for p in (src/'rtl').iterdir()},planner_sha256=sha(src/'planner.py'),cycles=cy)
        for name,path in [('extra',d/'extra_verified.json'),('application_records',d/'application/rtl_records.json'),('application_verification',d/'application/application_results.json')]:
            if path.exists():r[name]=json.loads(path.read_text())
        r['evidence_sha256']={str(p.relative_to(d)):sha(p) for p in [d/'fixtures.bin',d/'sim.log',d/'synth/util.rpt',d/'synth/setup.rpt',d/'synth/metrics.txt',d/'extra_verified.json',d/'application/rtl_records.json',d/'application/application_results.json'] if p.exists()}
        if not args.partial:
            assert passed and fixture_ok and r['synth'] and r['synth']['complete'],(n,'missing synthesis/simulation or arithmetic drift')
            assert r['synth']['BLACKBOX']==0
            assert 'reset' in r.get('extra',{}),(n,'reset evidence missing')
            if n!='reference':assert 'four_state' in r.get('extra',{}),(n,'four-state evidence missing')
            assert r.get('application_records',{}).get('calls')==74,(n,'C records missing')
            app=r.get('application_verification',{})
            assert len(app.get('independent_verification',[]))==4,(n,'independent verifier missing')
            assert len(app.get('artifacts_sha256',{}))==14,(n,'application artifact comparisons missing')
            assert len(app.get('negative_live_input',[]))==2,(n,'negative input guards missing')
        report['variants'][n]=r
    if not args.partial:
        ref=report['variants']['reference']['cycles']
        for n in ['separate_history','split_domains']:
            assert all(x['cycles']==report['variants'][n]['cycles'][i]['cycles'] for i,x in ref.items()),(n,'cycle drift')
        for n in ['single_stream','sparse_feed','dedicated_mont32']:
            for i,x in ref.items():
                if x['fft'] or (not x['packed'] and n!='dedicated_mont32') or (x['packed'] and n=='dedicated_mont32'):
                    assert x['cycles']==report['variants'][n]['cycles'][i]['cycles'],(n,i,'unrelated cycle drift')
        initial=json.loads((HERE/'input_manifest.json').read_text())
        for n,d in report['variants'].items():
            assert d['source_sha256']==initial['variants'][n]['source_sha256'],(n,'RTL changed after preparation')
        assert initial['accepted_registry_sha256']==sha(ROOT/'experiments/BASELINE.json'),'Accepted baseline registry changed'
        report['checks']=dict(all_arithmetic_payloads_identical=True,unrelated_cycles_unchanged=True,RTL_unchanged_since_preparation=True,
                              accepted_registry_unchanged=True,clock_xdc_sha256=sha(ROOT/'experiments/a_cg_packed4/clock.xdc'),
                              reference_byte_identical_to_accepted=all((HERE/'variants/reference/rtl'/p.name).read_bytes()==p.read_bytes() for p in (ROOT/'experiments/a_cg_packed4_system160/rtl').iterdir()))
    (OUT/'results.json').write_text(json.dumps(report,indent=2)+'\n')
    for n,r in report['variants'].items():print(n,r['synth'],r['simulation_pass'],r['same_arithmetic_payload'],flush=True)
if __name__=='__main__':main()
