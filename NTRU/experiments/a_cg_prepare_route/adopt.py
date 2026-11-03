"""Freeze the exact 37,917-LUT candidate selected by the user."""
from pathlib import Path
import hashlib
import importlib.util
import json
import re
import shutil

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
SRC=ROOT/'experiments/a_cg_host_opt/prepare_split/rtl'
B=ROOT/'study/build/a_cg_host_opt/prepare_split'
DEST=ROOT/'experiments/a_cg_prepare_split_baseline'

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    sp=importlib.util.spec_from_file_location('r',ROOT/'experiments/a_cg_timing/report.py')
    r=importlib.util.module_from_spec(sp);sp.loader.exec_module(r)
    assert 'TIMING_SYNTH_DONE variant=prepare_split' in r.read(B/'vivado.log')
    resource=r.resource(B/'synth/util.rpt');assert resource['LUT']==37917 and resource['DSP']==64 and resource['RAMB18']==48
    rows=r.parse_sim(B/'sim.log');ref=r.parse_sim(ROOT/'study/build/a_cg_timing/host/sim.log')
    assert all(a['cycles']==b['cycles'] for a,b in zip(rows,ref))
    assert 'FOUR_STATE TOTAL cases=38 PASS' in r.read(B/'four_state.log')
    assert 'FFT_SPLIT_EQUIVALENCE cases=100256 PASS' in r.read(ROOT/'study/build/a_cg_host_opt/split_check/result.log')
    app=json.loads((B/'application/application_results.json').read_text())
    calls=json.loads((B/'application/rtl_records.json').read_text())
    assert calls['calls']==74 and len(app['artifacts_sha256'])==14
    assert len(app['independent_verification'])==4 and all(x['valid']==0 for x in app['independent_verification'])
    old=json.loads((ROOT/'experiments/a_cg_host_baseline/manifest.json').read_text())
    for p,h in old['production_sha256'].items():assert sha(ROOT/p)==h
    (DEST/'rtl').mkdir(parents=True,exist_ok=True)
    for p in SRC.glob('*'):
        d=DEST/'rtl'/p.name
        if d.exists():assert d.read_bytes()==p.read_bytes(),('Selected baseline changed',d)
        else:shutil.copy2(p,d)
    evidence=[B/'synth/synthesized.dcp',B/'synth/util.rpt',B/'synth/timing.rpt',B/'synth/metrics.txt',B/'sim.log',B/'four_state.log',B/'application/application_results.json',B/'application/rtl_records.json']
    manifest=dict(name='prepared host + exact split FFT post-adder',selected_by_user=True,physical_approval='pending',
        source='experiments/a_cg_host_opt/prepare_split/rtl',resource_synth=resource,
        clock_ns=5,numeric_cases=1026,four_state_cases=38,C_transform_calls=74,verified_signatures=4,
        source_sha256={p.relative_to(ROOT).as_posix():sha(p) for p in (DEST/'rtl').glob('*')},
        evidence_sha256={p.relative_to(ROOT).as_posix():sha(p) for p in evidence},
        production_sha256=old['production_sha256'],production_RTL_changed=False)
    (DEST/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    (HERE/'selected_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print('Selected 37917-LUT baseline frozen; simulation/C validation PASS')

if __name__=='__main__':main()
