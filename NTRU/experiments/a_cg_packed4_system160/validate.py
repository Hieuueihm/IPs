"""Read-only functional audit for the accepted four-leaf baseline; no RTL simulation rerun."""
import argparse
import hashlib
import json
import re
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
BUILD=ROOT/'study/build/a_cg_packed4_system160'
FUNCTIONAL=ROOT/'study/build/a_cg_packed4'
PROVIDER=ROOT/'experiments/a_cg_packed4'
def read(p):return p.read_text(encoding='utf-8-sig',errors='replace')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def cases(p):return [dict(re.findall(r'(\w+)=(\S+)',line)) for line in read(p).splitlines() if line.startswith('CASE ')]

def verify():
    frozen=json.loads(read(BUILD/'input_manifest.json'))
    proof=json.loads(read(FUNCTIONAL/'results.json'))
    assert sha(FUNCTIONAL/'results.json')==frozen['validated_results_sha256']
    for name,h in frozen['source_sha256'].items():
        assert sha(HERE/'rtl'/name)==sha(PROVIDER/'rtl'/name)==h
        assert proof['source_sha256'][name]==h
        assert (HERE/'rtl'/name).read_bytes()==(FUNCTIONAL/'rtl_final'/name).read_bytes()
    current=cases(FUNCTIONAL/'sim.log')
    previous=cases(ROOT/'study/build/a_cg_z020_system160/sim.log')
    assert len(current)==len(previous)==1026
    packed=0
    for n,o in zip(current,previous):
        for key in ['fft','fmt','logn','hmin','inverse','packed','jobs','native','words','q']:assert n[key]==o[key]
        assert n['errors']=='0'
        if n['packed']=='1':
            packed+=1
            assert int(n['cycles'])<=int(o['cycles'])
        else:assert n['cycles']==o['cycles']
    assert packed==252 and 'TOTAL cases=1026 errors=0 PASS' in read(FUNCTIONAL/'sim.log')
    assert 'AXI_PROTOCOL decoupled_aw_w=1 b_stall=1 r_stall=1 wstrb=1 invalid_access=1 PASS' in read(FUNCTIONAL/'sim.log')
    assert 'AXI_RESET aw_split=1 w_split=1 b_pending=1 r_pending=1 PASS' in read(FUNCTIONAL/'axil_reset.log')
    tile=read(FUNCTIONAL/'tile_shared.log')
    assert 'PACKED4_TILE packets=16800 butterflies=33600 PASS' in tile
    assert 'PACKED4_RESET both_streams_inflight=1 PASS' in tile
    spans=[int(n) for n in re.findall(r'first_to_last_clocks=(\d+)',tile)]
    assert len(spans)==28 and min(spans)>=448 and max(spans)<=449
    assert 'FOUR_STATE TOTAL cases=10 PASS' in read(FUNCTIONAL/'four_state.log')
    app=json.loads(read(FUNCTIONAL/'application/application_results.json'))
    oldapp=json.loads(read(ROOT/'study/build/a_cg_z020_system160/application/application_results.json'))
    assert app['artifacts_sha256']==oldapp['artifacts_sha256'] and len(app['artifacts_sha256'])==14
    assert len(app['independent_verification'])==4
    assert all(v['valid']==0 and v['wrong_message']!=0 for v in app['independent_verification'])
    assert len(app['negative_live_input'])==2 and all(v['code']==7 for v in app['negative_live_input'])
    assert json.loads(read(FUNCTIONAL/'application/rtl_records.json'))['calls']==74
    # Reset IP/clock wiring is unchanged; distinguish inherited IP tests from new arithmetic coverage.
    assert (HERE/'signoff.tcl').read_bytes()==(ROOT/'experiments/a_cg_z020_system160/signoff.tcl').read_bytes()
    assert 'GENERATED_RESET startup=1 lock_gate=1 ps_reset=1 lock_loss=1 aux_polarity=1 PASS' in read(ROOT/'study/build/a_cg_z020_system160/reset_sim/run.log')
    return dict(cases=1026,packed_cases=252,nonpacked_cases=774,nonpacked_cycles_unchanged=True,
        packed_cycles_not_increased=True,axi_protocol=True,axi_reset=True,packed_tile_packets=16800,
        packed_tile_butterflies=33600,packed_four_state_cases=10,packed_reset_abort=True,
        c_calls=74,identical_artifacts=14,signatures=4,negative_live_inputs=2,
        generated_reset_test='inherited unchanged PS7/reset integration',rtl_equal_to_verified_candidate=True)

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--emit-summary',action='store_true');args=parser.parse_args()
    result=verify();path=BUILD/'functional_verified.json'
    text=json.dumps(result,indent=2)+'\n'
    if args.emit_summary:
        if path.exists():assert read(path)==text,'Do not overwrite a different accepted functional summary'
        else:path.write_text(text,encoding='utf-8')
    elif path.exists():assert json.loads(read(path))==result
    print('PACKED4_FUNCTIONAL_PASS',json.dumps(result))

if __name__=='__main__':main()
