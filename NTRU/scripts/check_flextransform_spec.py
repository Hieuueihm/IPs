"""Read-only FT-SPEC-1.0 package checks. This does NOT simulate or certify RTL."""
import hashlib
import importlib.util
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / 'spec/FlexTransform/1.0'
ASSETS = SPEC / 'assets'


def load(path):
    return json.loads(path.read_text(encoding='utf-8'))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def module(path, name):
    s=importlib.util.spec_from_file_location(name,path)
    m=importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m


def ordinary_ntt(op, a, b, logn, q, tables):
    """Independent ordinary modular arithmetic; no Montgomery reducer call."""
    rinv=pow(65536,-1,q)
    if op=='TOMONT':
        return [x*65536%q for x in a]
    if op=='MODMUL':
        return [x*y*rinv%q for x,y in zip(a,b)]
    n=1<<logn
    minimum=2 if q==3329 and n==256 else 1
    x=a[:]
    if op=='NTT':
        stride=n//2
        while stride>=minimum:
            groups=n//(2*stride)
            for i in range(n):
                if i%(2*stride)<stride:
                    g=i//(2*stride)
                    t=x[i+stride]*(tables[q,False][groups+g]*rinv%q)%q
                    x[i],x[i+stride]=(x[i]+t)%q,(x[i]-t)%q
            stride//=2
    else:
        stride=minimum
        while stride<n:
            groups=n//(2*stride)
            for i in range(n):
                if i%(2*stride)<stride:
                    g=i//(2*stride)
                    u,v=x[i],x[i+stride]
                    x[i]=(u+v)%q
                    x[i+stride]=(u-v)*(tables[q,True][groups+g]*rinv%q)%q
            stride*=2
        scale=pow(n//minimum,-1,q)
        x=[v*scale%q for v in x]
    return x


def main():
    report=dict(spec='FT-SPEC-1.0',rtl_simulated=False,checks={},limitations=[
        'Checks documents/assets/oracle only; no new RTL has been implemented or simulated.',
        'Protocol assertions, batching RTL, reset/flush and application integration remain implementation verification obligations.',
        'No physical timing/area/power or side-channel certification.'])
    manifest=load(SPEC/'manifest.json')
    actual={p.relative_to(SPEC).as_posix() for p in SPEC.rglob('*')
            if p.is_file() and p.name!='manifest.json' and '__pycache__' not in p.parts}
    require(actual==set(manifest['files']),'release file set mismatch')
    for name,digest in manifest['files'].items():
        require(sha(SPEC/name)==digest,f'hash mismatch {name}')
    for name,digest in manifest['tools'].items():
        require(sha(ROOT/name)==digest,f'tool hash mismatch {name}')
    report['checks']['manifest']=dict(files=len(actual),tools=len(manifest['tools']))
    req=load(SPEC/'requirements.json')
    records=req['requirements']
    ids={r['id'] for r in records}
    tests=set(req['test_ids'])
    require(len(ids)==len(records),'duplicate requirement')
    for r in records:
        require(bool(r['shall']) and (SPEC/r['section']).is_file(),f'bad requirement {r}')
        require(bool(r['test_ids']) and set(r['test_ids'])<=tests,f'unmapped requirement {r}')
    dv=(SPEC/'04_verification_acceptance.md').read_text(encoding='utf-8')
    for t in tests:
        require(f'| {t} |' in dv,f'undefined test {t}')
    referenced=set()
    links=0
    for p in SPEC.rglob('*.md'):
        text=p.read_text(encoding='utf-8')
        for group,start,end in re.findall(r'FT-([A-Z]+)-(\d{3})(?:\.\.(\d{3}))?',text):
            for i in range(int(start),int(end or start)+1):
                rid=f'FT-{group}-{i:03}'
                require(rid in ids,f'undefined requirement {rid} in {p.name}')
                referenced.add(rid)
        for target in re.findall(r'\]\(([^)]+)\)',text):
            if '://' in target or target.startswith('#'):
                continue
            target=target.split('#')[0]
            require((p.parent/target).is_file(),f'broken link {p.name}: {target}')
            links+=1
    require(ids<=referenced,'requirements absent from documents')
    report['checks']['traceability']=dict(requirements=len(ids),test_suites=len(tests),links=links)
    m=module(ASSETS/'reference_model.py','ft_release_oracle')
    profile=load(SPEC/'profiles.json')
    interface=load(SPEC/'interface.json')
    ports=interface['ports']
    require(len({p['name'] for p in ports})==len(ports),'duplicate port')
    protocol=(SPEC/'02_interfaces_protocol.md').read_text(encoding='utf-8')
    for p in ports:
        require(p['direction'] in ('input','output') and p['width']>0,'invalid port')
        require(p['name'] in protocol,f'undocumented external port {p["name"]}')
    expected_widths=dict(cmd_op_i=4,cmd_fmt_i=2,cmd_profile_i=2,cmd_logn_i=4,
        cmd_jobs_m1_i=3,cmd_tag_i=32,cmd_reserved_i=8,cpl_tag_o=32,cpl_status_o=8,
        cpl_job_mask_o=8,cpl_cycles_o=64,cpl_active_cycles_o=64,mem_req_store_i=2,
        mem_req_addr_i=16,mem_req_wdata_i=128,mem_req_strb_i=16,mem_rsp_rdata_o=128,
        mem_rsp_status_o=3)
    require({p['name']:p['width'] for p in ports}=={p['name']:expected_widths.get(p['name'],1) for p in ports},'port width mismatch')
    require(interface['command_status']==dict(OK=0,BAD_RESERVED=1,BAD_OP=2,BAD_FMT=3,
        BAD_PROFILE=4,BAD_LOGN=5,BAD_JOBS=6,ABORTED=16,INTERNAL_FAULT=17),'command enum')
    require(interface['memory_status']==dict(OK=0,BAD_STORE=1,BAD_ALIGN=2,RANGE=3,STATE=4),'memory enum')
    legal=[]
    for op in range(16):
        for fmt in range(4):
            for q in range(4):
                for logn in range(16):
                    for jobs in range(1,9):
                        c=dict(op=op,fmt=fmt,profile=q,logn=logn,jobs=jobs,reserved=0)
                        if m.validate(c)==0:
                            legal.append(c)
    key=lambda c:(c['op'],c['fmt'],c['profile'],c['logn'],c['jobs'],c['reserved'])
    require({key(c) for c in legal}=={key(c) for c in profile['legal_commands']},'legal tuple mismatch')
    require(len(legal)==300,'unexpected legal tuple count')
    for r in load(ASSETS/'command_fixtures.json'):
        require(m.validate(r['command'])==r['expected_status'],'command fixture mismatch')
    report['checks']['interface_profiles']=dict(ports=len(ports),legal_commands=len(legal))
    roots=m.read_roots(ASSETS)
    require(len(roots[0])==1024,'FFT ROM rows')
    for line in (ASSETS/'fft_q64_64.mem').read_text().splitlines():
        require(bool(re.fullmatch('[0-9a-f]{64}',line)),'FFT ROM line format')
    for q in (12289,3329):
        fwd,inv=roots[1][q,False],roots[1][q,True]
        require(len(fwd)==len(inv)==(1024 if q==12289 else 128),'NTT ROM rows')
        for a,b in zip(fwd,inv):
            require(0<=a<q and 0<=b<q and a*b%q==pow(65536,2,q),'inverse root/domain mismatch')
        if q==3329:
            for k,a in enumerate(fwd):
                require(a==65536*pow(17,int(f'{k:07b}'[::-1],2),q)%q,'q3329 root formula')
        const=next(p for p in profile['ntt_profiles'] if p['q']==q)
        require((const['qprime']*q)%65536==65535 and const['r_mod_q']==65536%q and
                const['r2_mod_q']==pow(65536,2,q),'modulus constants')
        for logn,factor in const['intt_factorbar_by_logn'].items():
            l=int(logn); stages=l-(q==3329 and l==8)
            require(factor==65536*pow(1<<stages,-1,q)%q,'normalization factorbar')
    report['checks']['rom']=dict(fft_complex_rows=1024,ntt_scalar_rows=2304)
    primitives=load(ASSETS/'primitive_fixtures.json')
    for r in primitives:
        if r['kind']=='mont':
            want=r['a']*r['b']*pow(65536,-1,r['q'])%r['q']
            require(r['expected']==want==m.mont(r['a'],r['b'],r['q']),'Mont fixture')
        else:
            w=r['width']; a=int(r['a'],16); a=a-(1<<w) if a>>(w-1) else a
            if r['kind']=='fixed_mul':
                b=int(r['b'],16); b=b-(1<<w) if b>>(w-1) else b
                # Independent quotient formulation of the normative rounding.
                want=(2*a*b+(1<<(w//2)))//(1<<(w//2+1))
            else:
                s=r['shift']; bias=0 if s==0 else 1<<(s-1)
                value=(a+bias)%(1<<w)
                want=(value-(1<<w) if value>>(w-1) else value)>>s
            require(want%(1<<w)==int(r['expected'],16),'fixed primitive fixture')
    fixtures=[json.loads(line) for line in (ASSETS/'kernel_fixtures.jsonl').read_text().splitlines()]
    require(len(fixtures)==len(legal) and len({r['id'] for r in fixtures})==len(fixtures),'kernel fixture IDs')
    require({key(r['command']) for r in fixtures}=={key(c) for c in legal},'missing legal tuple fixture')
    old=module(ROOT/'model/r8_golden.py','ft_old_limb_oracle') if (ROOT/'model/r8_golden.py').is_file() else None
    core=old.Core([x for pair in roots[0] for x in pair],16) if old else None
    narrow=module(ROOT/'model/fixed_kernel_oracle.py','ft_old_narrow_oracle') if (ROOT/'model/fixed_kernel_oracle.py').is_file() else None
    cross=0
    decode=lambda jobs:[[int(x,16) for x in job] for job in jobs]
    for r in fixtures:
        c=r['command']; a,b,expected=map(decode,(r['a'],r['b'],r['expected']))
        require(m.evaluate(c,a,b,roots)==expected,f'fixture mismatch {r["id"]}')
        op=next(k for k,v in m.OPS.items() if v==c['op'])
        w=r['word_bits']
        require(w==m.WIDTHS[c['fmt']],'fixture width')
        require(r['output_store']==(2 if op in ('SPLIT','MERGE') else 0),'fixture destination')
        for job in r['a']+r['b']+r['expected']:
            require(all(bool(re.fullmatch(f'[0-9a-f]{{{w//4}}}',x)) for x in job),'hex word width')
        if c['fmt']==3:
            q=(12289,3329)[c['profile']]
            for j in range(c['jobs']):
                require(ordinary_ntt(op,a[j],b[j],c['logn'],q,roots[1])==expected[j],f'ordinary NTT {r["id"]}')
                if op=='NTT':
                    require(m.ntt_kernel('INTT',expected[j],[],c['logn'],q,roots[1])==a[j],'NTT/INTT roundtrip')
                cross+=1
        elif w==128 and core:
            rec=dict(op=op,logn=c['logn'],a=[f'{x:032x}' for x in a[0]],b=[f'{x:032x}' for x in b[0]])
            y,z=core.evaluate(rec)
            require([x% (1<<128) for x in y+(z or [])]==expected[0],f'limb oracle {r["id"]}')
            cross+=1
        elif w<128 and narrow:
            out=narrow.evaluate(op,a[0],b[0],c['logn'],w,[x for pair in roots[0] for x in pair])
            require([x% (1<<w) for x in out]==expected[0],f'narrow oracle {r["id"]}')
            cross+=1
    report['checks']['fixtures']=dict(kernels=len(fixtures),primitives=len(primitives),independent_job_oracle_comparisons=cross)
    seen=set()
    for k in range(8192):
        bank=(k&63)^((k>>2)&0x30)^((k>>4)&0x30)
        row=k>>6
        require((bank,row) not in seen and 0<=bank<64 and 0<=row<128,'bank map alias')
        seen.add((bank,row))
        if k<64:
            require(bank==k and row==0,'small job bank coloring')
    # Host line addressing and byte enables, independent of format.
    for addr in range(0,16384,16):
        words=[(addr//2+i)&65535 for i in range(8)]
        raw=sum(v<<(16*i) for i,v in enumerate(words))
        for i,v in enumerate(words):
            require((raw>>(16*i))&65535==v,'line endian')
        for strobe in [0,65535]+[1<<i for i in range(16)]:
            old_bytes=[0xa5]*16
            new=[(raw>>(8*i))&255 if strobe&(1<<i) else old_bytes[i] for i in range(16)]
            require(all(new[i]==0xa5 for i in range(16) if not strobe&(1<<i)),'byte enable preservation')
    for c in legal:
        n=1<<c['logn']; size=n*m.WIDTHS[c['fmt']]//8*c['jobs']
        require(size<=16384,'store capacity')
        if c['fmt']==3 and c['jobs']>1:
            banks=[(k&63)^((k>>2)&0x30)^((k>>4)&0x30) for k in range(n*c['jobs'])]
            require(len(set(banks))==len(banks),'multi-job bank overlap')
    report['checks']['memory_mapping']=dict(unique_word_addresses=len(seen),host_lines=1024)
    # Baseline cross-check is optional for a copied spec package; report it separately.
    baseline=ROOT/'study/build/kernel_engine/cases.json'
    provenance=load(ASSETS/'provenance.json')
    source_checks=[]
    for s in provenance['source_files']:
        p=ROOT/s['path']
        source_checks.append(dict(path=s['path'],present=p.is_file(),hash_match=sha(p)==s['sha256'] if p.is_file() else None))
        if p.is_file():
            require(sha(p)==s['sha256'],f'provenance source changed: {s["path"]}')
    report['checks']['source_provenance']=source_checks
    if baseline.is_file():
        count=0
        for r in load(baseline):
            fmt=r['width'] if m.OPS[r['op']]<5 else 3
            c=dict(op=m.OPS[r['op']],fmt=fmt,profile=r['profile'],logn=r['logn'],jobs=1,reserved=0)
            mask=(1<<m.WIDTHS[fmt])-1
            cvt=lambda x:(int(x,16) if isinstance(x,str) else x)&mask
            a=[[cvt(x) for x in r['a']]]; b=[[cvt(x) for x in r.get('b',[])]]
            expected=[[cvt(x) for x in r['out']+r.get('out1',[])]]
            require(m.evaluate(c,a,b,roots)==expected,f'existing baseline expected {count}')
            count+=1
        report['checks']['baseline_expected_records']=count
    report['status']='PASS'
    out=ROOT/'study/results/flextransform_spec_check.json'
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False,indent=2))


if __name__=='__main__':
    main()
