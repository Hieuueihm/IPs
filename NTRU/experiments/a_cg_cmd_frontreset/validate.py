"""Validate the complete registered-command interface before implementation."""
from pathlib import Path
import hashlib
import importlib.util
import json
import re

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
B=ROOT/'study/build/a_cg_cmd_frontreset'
sp=importlib.util.spec_from_file_location('prior',ROOT/'experiments/a_cg_timing/report.py')
prior=importlib.util.module_from_spec(sp);sp.loader.exec_module(prior)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    pinned=json.loads((HERE/'manifest.json').read_text())
    for group in (pinned['source_sha256'],pinned['fixtures_sha256'],pinned['baseline']['source_sha256'],pinned['baseline']['production_sha256']):
        for p,h in group.items():assert sha(ROOT/p)==h,('Pinned file changed',p)
    for name in ('tile_a.sv','mul_ss.v'):
        assert (HERE/'rtl'/name).read_bytes()==(ROOT/'experiments/a_cg_control_gate/rtl'/name).read_bytes()
    rows=prior.parse_sim(B/'sim.log')
    reference=prior.parse_sim(ROOT/'study/build/a_cg_control_gate/sim.log')
    assert len(rows)==len(reference)==1026
    for i,(new,old) in enumerate(zip(rows,reference)):
        assert new['cycles']==old['cycles'],('Kernel changed',i,new,old)
        # Config and start each cross one capture edge. Every load/read line
        # crosses one more edge; root/descriptor writes remain one per clock.
        expected=2*((new['words']+3)//4)+2
        assert new['all_host_cycles']-old['all_host_cycles']==expected,('Interface cost',i,expected,new,old)
    assert 'RESET_ABORT modes=12 PASS' in prior.read(B/'sim.log')
    assert 'FOUR_STATE TOTAL cases=38 PASS' in prior.read(B/'four_state.log')
    app=json.loads((B/'application/application_results.json').read_text())
    calls=json.loads((B/'application/rtl_records.json').read_text())
    oldapp=json.loads((ROOT/'study/build/a_cg_control_gate/application/application_results.json').read_text())
    assert calls['calls']==74 and len(app['artifacts_sha256'])==14
    assert app['artifacts_sha256']==oldapp['artifacts_sha256']
    assert len(app['independent_verification'])==4 and all(x['valid']==0 and x['wrong_message']!=0 for x in app['independent_verification'])
    assert len(app['negative_live_input'])==2 and all(x['code']==7 for x in app['negative_live_input'])
    assert 'CONTROL_SYNTH_DONE' in prior.read(B/'synthesis_console.log')
    metrics=prior.read(B/'synth/metrics.txt')
    for label in ('ROOT_RAMB18=16','DATA_RAMB18=32','DSP48=64','BLACKBOX=0','LOCAL_RESETS=16','LOCAL_CONFIGS=16'):assert label in metrics,label
    barrier=prior.read(B/'synth/command_barrier.txt')
    assert 'DIRECT_INPUT_TO_CORE_PATHS=0' in barrier
    assert int(re.search(r'CORE_REGISTERS=(\d+)',barrier)[1])>0
    occupancy=prior.read(B/'synth/occupancy_barrier.txt')
    assert 'LOAD_FLAG_P_CFG_DEPENDENCIES=0' in occupancy and 'OCCUPANCY_REGISTERS=1' in occupancy
    reset_barrier=prior.read(B/'synth/frontend_reset_barrier.txt')
    for label in ('LOAD_GLOBAL_RESET_DEPENDENCIES=0','LOAD_RAW_RESET_D_DEPENDENCIES=0','LOAD_LOCAL_PERMISSION_DEPENDENCIES=1'):
        assert label in reset_barrier,label
    result=dict(frontend_reset_isolated=True,numeric_cases=1026,kernel_cycles_identical=True,four_state_cases=38,reset_abort_modes=12,
        live_C_calls=74,verified_signatures=4,identical_C_artifacts=14,negative_live_inputs=2,
        packed16_preserved=True,arithmetic_RTL_unchanged=True,production_RTL_changed=False,
        configuration_extra_clocks_vs_retained=6,load_read_extra_clocks_per_line_vs_control_gate=1,
        start_extra_clocks_vs_control_gate=1,root_descriptor_throughput_words_per_clock=1,
        direct_input_to_core_paths=0,synthesis_resource=prior.resource(B/'synth/util.rpt'),
        sha256={p.relative_to(ROOT).as_posix():sha(p) for p in [HERE/'manifest.json',HERE/'main.cpp',HERE/'tb_four_state.sv',
            HERE/'synth.tcl',B/'sim.log',B/'four_state.log',B/'application/application_results.json',
            B/'application/rtl_records.json',B/'synth/synthesized.dcp',B/'synth/command_barrier.txt']})
    (B/'validation.json').write_text(json.dumps(result,indent=2)+'\n')
    print('COMMAND_VALIDATION_PASS: 1026 vectors, 38 four-state, 12 abort modes, 74 C calls, 4 signatures; kernel cycles unchanged')
    print(json.dumps(result['synthesis_resource']))

if __name__=='__main__':main()
