"""Verify document evidence and that all pinned RTL/netlist files stayed unchanged."""
from pathlib import Path
import hashlib
import importlib.util
import json
import re
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
DOC=ROOT/'docs/mo_ta_rtl_hien_tai_z020.md'
FIG=ROOT/'docs/figures/rtl_z020'
BUILD=ROOT/'study/build/rtl_z020_description'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    target=json.loads((ROOT/'experiments/a_cg_z020_dispatch2/manifest.json').read_text())
    original=json.loads((ROOT/'study/results/a_cg_z020_dispatch2.json').read_text())
    for group in (target['source_sha256'],target['byte_identical_source'],original['sha256']):
        for p,h in group.items():assert sha(ROOT/p)==h,('Pinned input changed',p)
    parent=json.loads((ROOT/'experiments/a_cg_cmd_dispatch2/manifest.json').read_text())
    for p,h in parent['baseline']['production_sha256'].items():assert sha(ROOT/p)==h
    metrics=dict(re.findall(r'^(\w+)=(.+)$',(BUILD/'metrics_100.txt').read_text(),re.M))
    assert metrics['PART']=='xc7z020clg400-2'
    assert float(metrics['PERIOD_NS'])==10
    assert float(metrics['ORIGINAL_5NS_WNS'])==-3.604
    assert float(metrics['REGISTER_TO_REGISTER_WNS_NS'])==1.396
    assert float(metrics['REGISTER_TO_REGISTER_WHS_NS'])==.126
    log=(HERE/'timing_console.log').read_text()
    assert 'Z020_100MHZ_ANALYSIS_DONE' in log and 'ERROR:' not in log
    for forbidden in ('synth_design','opt_design','phys_opt_design','place_design','route_design','set_false_path','set_multicycle_path','set_case_analysis'):
        assert not re.search(r'^\s*'+forbidden+r'\b',(HERE/'timing_100.tcl').read_text(),re.M)
    doc=DOC.read_text(encoding='utf-8')
    checked_links=[]
    for link in re.findall(r'!?\[[^\]]*\]\(([^)]+)\)',doc):
        if link.startswith(('https://','http://','#')):continue
        p=(DOC.parent/link.split('#')[0]).resolve()
        assert p.exists(),('Broken document link',link)
        checked_links.append(link)
    figures=json.loads((FIG/'inventory.json').read_text())
    assert len(figures)==8
    for item in figures:
        ET.parse(FIG/(item['name']+'.svg'))
        png=FIG/(item['name']+'.png')
        assert png.exists() and png.read_bytes()[:8]==b'\x89PNG\r\n\x1a\n'
    rows=[]
    for line in (ROOT/'study/build/a_cg_cmd_dispatch2/sim.log').read_text().splitlines():
        if not line.startswith('CASE '):continue
        r={k:int(v) for k,v in re.findall(r'(\w+)=(\d+)',line)}
        r['case_id']=int(line.split()[1]);rows.append(r)
    assert len(rows)==1026 and all(r['errors']==0 for r in rows)
    expected=[
        (0,0,0,8,1,3329,265,1183),(0,0,1,8,1,3329,217,687),
        (0,0,0,8,0,8380417,301,1220),(0,0,0,10,0,12289,985,4594),
        (0,0,1,10,0,12289,505,2578),(1,0,0,10,0,0,453,4060),
        (1,1,0,10,0,0,1752,9047),(1,2,0,10,0,0,6508,25169)]
    latency=[]
    for fft,fmt,packed,ln,hm,q,cy,allcy in expected:
        hits=[r for r in rows if all(r[k]==v for k,v in dict(fft=fft,fmt=fmt,packed=packed,logn=ln,hmin=hm,q=q,jobs=1,native=0,inverse=0,cycles=cy,all_host_cycles=allcy).items())]
        assert hits,(fft,fmt,packed,ln,hm,q)
        r=hits[0];latency.append(dict(**r,kernel_us_at_100MHz=cy/100,driver_us_at_100MHz=allcy/100))
    hier=(ROOT/'study/build/a_cg_z020_dispatch2/synth/util_hier.rpt').read_text()
    entries=[[s.strip() for s in l.split('|')[1:-1]] for l in hier.splitlines() if l.startswith('|')]
    lut_totals={n:sum(int(r[2]) for r in entries if len(r)>3 and r[0]==n and r[2].isdigit()) for n in ('u_as','u_fft_ct','leaves')}
    assert lut_totals['u_as']==7903 and lut_totals['u_fft_ct']==1040
    sp=importlib.util.spec_from_file_location('prior',ROOT/'experiments/a_cg_timing/report.py')
    prior=importlib.util.module_from_spec(sp);sp.loader.exec_module(prior)
    files=[DOC,HERE/'draw_figures.py',HERE/'render_figures.ps1',HERE/'timing_100.tcl',HERE/'check_description.py',
           BUILD/'metrics_100.txt',BUILD/'timing_100.rpt',BUILD/'internal_setup_100.rpt',BUILD/'internal_hold_100.rpt',BUILD/'constraints_100.xdc']
    files += list(FIG.glob('*.svg'))+list(FIG.glob('*.png'))
    result=dict(description=DOC.relative_to(ROOT).as_posix(),source_part=target['part'],RTL_unchanged=True,
        netlist_unchanged=True,existing_synth_reports_unchanged=True,production_RTL_unchanged=True,
        optimization_performed=False,P_and_R_performed=False,figures=8,local_links_checked=len(checked_links),
        clock_100MHz=dict(period_ns=10,internal_WNS_ns=1.396,internal_WHS_ns=.126,
            full_boundary=prior.summary(BUILD/'timing_100.rpt'),kind='timing re-analysis of existing 5 ns synthesized netlist'),
        module_LUT_totals=lut_totals,selected_latency_examples=latency,
        sha256={p.relative_to(ROOT).as_posix():sha(p) for p in files})
    (ROOT/'study/results/rtl_z020_description.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print('DESCRIPTION_CHECK_PASS: 8 figures; links and latency examples verified; RTL/netlist unchanged.')
    print(json.dumps(result['clock_100MHz']))

if __name__=='__main__':main()
