"""Gate physical implementation on the frozen vectors and live application replay."""
from pathlib import Path
import hashlib
import importlib.util
import json
import re

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
B=ROOT/'study/build/a_cg_control'
sp=importlib.util.spec_from_file_location('prior',ROOT/'experiments/a_cg_timing/report.py')
prior=importlib.util.module_from_spec(sp);sp.loader.exec_module(prior)

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    pinned=json.loads((HERE/'manifest.json').read_text())
    for group in (pinned['source_sha256'],pinned['fixtures_sha256'],pinned['baseline']['source_sha256'],pinned['baseline']['production_sha256']):
        for p,h in group.items():assert sha(ROOT/p)==h,('Pinned input changed',p)
    assert (HERE/'rtl/mul_ss.v').read_bytes()==(ROOT/'experiments/a_cg_prepare_split_baseline/rtl/mul_ss.v').read_bytes()
    tile=(HERE/'rtl/tile_a.sv').read_text().replace(
        '        (* DONT_TOUCH="yes" *) reg rsign; // Preserve the local sign-control sink.',
        '        reg        rsign;')
    assert tile==(ROOT/'experiments/a_cg_prepare_split_baseline/rtl/tile_a.sv').read_text()
    rows=prior.parse_sim(B/'sim.log')
    parent=prior.parse_sim(ROOT/'study/build/a_cg_host_opt/prepare_split/sim.log')
    assert len(rows)==len(parent)==1026
    for a,b in zip(rows,parent):
        assert a['cycles']==b['cycles'],('Kernel schedule changed',a,b)
        assert a['all_host_cycles']==b['all_host_cycles']+5,('Unexpected interface latency',a,b)
    abort=re.search(r'RESET_ABORT modes=(\d+) PASS',prior.read(B/'sim.log'))
    assert abort and int(abort[1])==12
    assert 'FOUR_STATE TOTAL cases=38 PASS' in prior.read(B/'four_state.log')
    app=json.loads((B/'application/application_results.json').read_text())
    calls=json.loads((B/'application/rtl_records.json').read_text())
    old_app=json.loads((ROOT/'study/build/a_cg_host_opt/prepare_split/application/application_results.json').read_text())
    assert calls['calls']==74 and len(app['artifacts_sha256'])==14
    assert app['artifacts_sha256']==old_app['artifacts_sha256']
    assert len(app['independent_verification'])==4 and all(x['valid']==0 and x['wrong_message']!=0 for x in app['independent_verification'])
    assert len(app['negative_live_input'])==2 and all(x['code']==7 for x in app['negative_live_input'])
    assert 'CONTROL_SYNTH_DONE' in prior.read(B/'synthesis_console.log')
    metrics=prior.read(B/'synth/metrics.txt')
    for v in ('ROOT_RAMB18=16','DATA_RAMB18=32','DSP48=64','BLACKBOX=0','LOCAL_RESETS=16','LOCAL_CONFIGS=16'):assert v in metrics,v
    resource=prior.resource(B/'synth/util.rpt')
    result=dict(numeric_cases=1026,kernel_cycles_identical=True,configuration_extra_clocks=5,
        four_state_cases=38,reset_abort_modes=12,live_C_calls=74,verified_signatures=4,
        identical_C_artifacts=14,negative_live_inputs=2,packed16_preserved=True,
        arithmetic_RTL_unchanged=True,production_RTL_changed=False,synthesis_resource=resource,
        synthesis_internal_setup=prior.path(B/'synth/internal_setup.rpt'),
        sha256={p.relative_to(ROOT).as_posix():sha(p) for p in [HERE/'manifest.json',HERE/'main.cpp',
            HERE/'tb_four_state.sv',HERE/'synth.tcl',B/'sim.log',B/'four_state.log',
            B/'application/application_results.json',B/'application/rtl_records.json',B/'synth/synthesized.dcp']})
    (B/'validation.json').write_text(json.dumps(result,indent=2)+'\n')
    print('CONTROL_VALIDATION_PASS: 1026 vectors, 38 four-state, 12 reset modes, 74 C calls, 4 signatures, kernel cycles unchanged')
    print(json.dumps(resource))

if __name__=='__main__':main()
