"""Read-only consistency check for the rebuild design pack; not RTL verification."""
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys

sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent.parent
ROOT=HERE.parents[1]

def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def layout(fft,fmt,ln,hm,packed,jl):
    n=max(ln-1,0) if fft else ln-(1 if packed and hm==0 else hm)
    bl=fmt+1 if fft else max(0,hm-packed)
    bj=min(jl,max(0,5-n));rj=jl-bj
    assert bl+rj<=3 and max(0,n-5)+bl+rj<=7
    return dict(n=n,m=1<<n,base_log=bl,base=1<<bl,bj=bj,rj=rj,
                planes=1<<(bl+rj),rows=1<<max(0,n-5),stages=n+int(packed and hm==0),
                jobs=1<<jl,job_word_log=ln+fmt if fft else ln-packed)

def main():
    cfg=json.loads((HERE/'design.json').read_text(encoding='utf-8'))
    lock=json.loads((HERE/'reference_lock.json').read_text(encoding='utf-8'))
    assert cfg['status'] in ('design_only','microarchitecture_locked') and not cfg['rtl_implemented']
    assert cfg['reference_baseline']==lock['reference_baseline']
    prof=cfg['profile']
    assert prof['tiles']*prof['leaves_per_tile']==prof['dsp_target']==64
    assert prof['data_banks']+prof['root_banks']==prof['ramb18_target']==48
    assert abs(prof['period_ns']*prof['system_clock_mhz']-1000)<1e-9
    assert prof['write_context_entries']>=cfg['limits']['logn_max']
    assert prof['command_payload_bits']>=138
    pipe=cfg['pipeline_contract'] if 'pipeline_contract' in cfg else cfg['pipeline_proposal']
    assert pipe['fused_latency']%3!=0
    assert pipe['fft_real_product_slots']==[1,4,15]
    assert pipe['fft_butterfly_periods']==[3,12,45]
    assert len(set(cfg['commands'].values()))==len(cfg['commands'])==9
    for name,bundle in cfg['bundle_layouts'].items():
        bits=[]
        for field,(hi,lo) in bundle['fields'].items():
            assert 0<=lo<=hi<bundle['width'],(name,field)
            bits.extend(range(lo,hi+1))
        assert sorted(bits)==list(range(bundle['width'])),('bundle gap/overlap',name)
    assert cfg['bundle_layouts']['cfg_ctx']['width']==prof['cfg_context_bits']
    assert cfg['bundle_layouts']['write_ctx']['width']==prof['write_context_bits']
    if cfg['status']=='microarchitecture_locked':
        mc=cfg['microarchitecture_contract']
        frozen=json.loads((HERE/mc['lock']).read_text())
        assert frozen['contract_version']==mc['version'] and not frozen['RTL_verified'] and not frozen['PPA_verified']
        for path,sha in frozen['files_sha256'].items():assert digest(ROOT/path)==sha,('locked contract changed; version review required',path)
        ports=json.loads((HERE/mc['ports']).read_text())
        timing=json.loads((HERE/mc['timing']).read_text())
        fsm=json.loads((HERE/mc['fsm']).read_text())
        assert ports['contract']==timing['contract']==fsm['contract']==mc['version']=='0.2'
        expected={Path(x.strip()).stem for x in (HERE/'rtl/filelist.planned').read_text().splitlines() if x.strip() and not x.startswith('#') and x.endswith('.sv')}
        assert set(ports['ports'])==expected
        for name,ps in ports['ports'].items():
            assert len({p['name'] for p in ps})==len(ps),(name,'duplicate port')
            assert all(p['width']>0 and p['direction'] in ('input','output') for p in ps)
        assert pipe['raw_leaf_latency']==3 and pipe['fused_latency']==5
        assert timing['read_to_tile_accept']==2 and timing['tile_rsp_to_bank_commit']==1
        assert timing['ntt']['rsp_ct']==pipe['ntt_ct_output_after_accept_edge']==21
        assert timing['ntt']['rsp_gs']==pipe['ntt_gs_output_after_accept_edge']==20
        report=json.loads((ROOT/mc['full_report']).read_text())
        assert report['status']=='MODEL_PASS' and report['full'] and report['cases']==730,'Need full liveness report'
        assert len(report['extra']['negative_controls'])==11
        for path,sha in report['sha256'].items():assert digest(ROOT/path)==sha,('liveness report stale',path)
        for profile in timing['fft']:
            assert (HERE/'microarchitecture/cycles'/f'{profile}.csv').is_file()
    docs={}
    for name in cfg['documents']:
        p=HERE/name;assert p.is_file(),name;docs[name]=p.read_text(encoding='utf-8')
        for dest in re.findall(r'\]\(([^\s)]+)\)',docs[name]):
            if dest.startswith(('http:','https:','#')):continue
            dest=dest.split('#',1)[0]
            assert (p.parent/dest).exists(),(name,'broken link',dest)
    for rid in cfg['requirements']:
        assert rid in docs['spec/01_requirements.md'] and rid in docs['spec/06_verification.md'],rid
    planned=[x.strip() for x in (HERE/'rtl/filelist.planned').read_text().splitlines() if x.strip() and not x.startswith('#')]
    assert len(planned)==len(set(planned))
    alltext='\n'.join(docs.values())
    assert all(Path(f).stem in alltext for f in planned),'Undocumented module'
    for name,sha in lock['files_sha256'].items():
        p=ROOT/name;assert p.is_file(),('missing reference',name)
        assert digest(p)==sha,('reference changed',name)
    baseline=json.loads((ROOT/'experiments/BASELINE.json').read_text())
    assert baseline['id']==cfg['reference_baseline']
    c_manifest=json.loads((ROOT/'study/vectors/r8/manifest.json').read_text())
    for name,sha in c_manifest['source_sha256'].items():
        assert digest(ROOT/'third_party/r8'/name)==sha,('C reference drift',name)
    for entry in c_manifest['files']+c_manifest['rom_files']:
        assert digest(ROOT/'study/vectors/r8'/entry['file'])==entry['sha256'],('C vector/ROM drift',entry['file'])
    # Compare every bounded canonical layout tuple with the pinned planner.
    # No golden generation, CAD job or write into the accepted experiment.
    spec=importlib.util.spec_from_file_location('rebuild_readonly_reference',ROOT/'experiments/a_cg_packed4/planner.py')
    old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
    checked=valid=0
    for fft in (0,1):
        for fmt in ((0,1,2) if fft else (0,)):
            for ln in range(0 if fft else 1,11):
                for hm in ((0,) if fft else range(min(2,ln-1)+1)):
                    for pk in ((0,) if fft else (0,1)):
                        for jl in range(5):
                            checked+=1
                            try:a=layout(fft,fmt,ln,hm,pk,jl)
                            except AssertionError:a=None
                            try:b=old.config(fft,fmt,ln,hm,pk,jl)
                            except AssertionError:b=None
                            assert a==b,('layout drift',fft,fmt,ln,hm,pk,jl,a,b)
                            if a is not None:
                                valid+=1
                                assert 2*a['rows']*a['planes']<=prof['data_rows']
                                assert a['stages']<=prof['descriptor_entries']
    # The target table must reproduce the completed reference ablation data.
    measured=json.loads((ROOT/'study/build/paper_ablation31/results.json').read_text())['variants']['reference']['cycles']
    cases=json.loads((ROOT/'study/build/paper_ablation31/reference/fixtures.json').read_text())
    for target in cfg['reference_cycles_forward']:
        found=[]
        for i,c in enumerate(cases):
            if c['inverse'] or any(c[k]!=target[k] for k in ('fft','fmt','logn','hmin','packed','jobs_log','native')):continue
            if 'q' in target and c['q']!=target['q']:continue
            found.append(measured[str(i)]['cycles'])
        assert found and set(found)=={target['cycles']},('reference cycle mismatch',target['name'],found)
    print(f'DESIGN_PACK_PASS documents={len(docs)} planned_sources={len(planned)} references={len(lock["files_sha256"])} C_sources={len(c_manifest["source_sha256"])} layout_tuples={checked} valid={valid}')
    print('Status:',cfg['status'],'; no new RTL simulated, synthesized or signed off.')

if __name__=='__main__':main()
