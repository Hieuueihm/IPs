"""A local occupancy register replaces feedback from distributed opcode flags."""
from pathlib import Path
import hashlib
import json
import shutil

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
PREV=ROOT/'experiments/a_cg_cmd_pipe'
B=ROOT/'study/build/a_cg_cmd_credit'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def rep(s,a,b):
    assert s.count(a)==1,(a,s.count(a))
    return s.replace(a,b)

def main():
    old=json.loads((PREV/'manifest.json').read_text())
    for p,h in old['source_sha256'].items():assert sha(ROOT/p)==h
    (HERE/'rtl').mkdir(parents=True,exist_ok=True);B.mkdir(parents=True,exist_ok=True)
    s=(PREV/'rtl/a_cg_fast.sv').read_text()
    s=rep(s,'    wire reserved=p_cfg_valid || p_start || p_load_valid || p_read_valid;',
        '    (* DONT_TOUCH="yes" *) reg reserved;')
    s=rep(s,'        if(rst)begin\n            p_cfg_valid<=0;', '        if(rst)begin\n            reserved<=0;\n            p_cfg_valid<=0;')
    s=rep(s,'        end else begin\n            p_cfg_valid<=cfg_valid && cfg_ready;', '''        end else begin
            reserved <= (cfg_valid && cfg_ready) ||
                (window_open && c_cfg_ready && !cfg_valid && start) ||
                (load_valid && load_ready) || (read_valid && read_ready);
            p_cfg_valid<=cfg_valid && cfg_ready;''')
    s=rep(s,'    (* KEEP_HIERARCHY="yes" *) a_cg_exec u_exec (', '''`ifndef SYNTHESIS
    always @(posedge clk)if(!rst)begin
        if(reserved !== (p_cfg_valid || p_start || p_load_valid || p_read_valid))
            $fatal(1,"command occupancy differs from accepted main token");
    end
`endif
    (* KEEP_HIERARCHY="yes" *) a_cg_exec u_exec (''')
    # Consumers do not qualify an already accepted token a second time. The
    # frontend enforces priority and its occupancy bit blocks queued commands.
    s=rep(s,'assign load_ready = state==IDLE && configured && !cfg_valid;',
        'assign load_ready = state==IDLE && configured;')
    s=rep(s,'assign read_ready = (state==IDLE || state==HCATCH) && configured && !cfg_valid && !load_valid;',
        'assign read_ready = (state==IDLE || state==HCATCH) && configured;')
    (HERE/'rtl/a_cg_fast.sv').write_text(s)
    for name in ('tile_a.sv','mul_ss.v'):shutil.copy2(PREV/'rtl'/name,HERE/'rtl'/name)
    for name in ('main.cpp','tb_four_state.sv','application.py','run_sim.ps1','synth.tcl','validate.py'):
        text=(PREV/name).read_text().replace('a_cg_cmd_pipe','a_cg_cmd_credit')
        if name=='synth.tcl':
            proof='''set dest [get_pins -of_objects [get_cells p_load_valid_reg] -filter {REF_PIN_NAME == D}]
set sources [get_cells -quiet -of_objects [all_fanin -flat -startpoints_only -to $dest]]
set bad [filter $sources {NAME == p_cfg_valid_reg}]
set f [open [file join $out occupancy_barrier.txt] w]
puts $f "LOAD_FLAG_P_CFG_DEPENDENCIES=[llength $bad]"
puts $f "OCCUPANCY_REGISTERS=[llength [get_cells -filter {NAME == reserved_reg}]]"
close $f
if {[llength $bad] != 0 || [llength [get_cells -filter {NAME == reserved_reg}]] != 1} {error "Distributed opcode feedback remains"}
'''
            text=rep(text,'puts "CONTROL_SYNTH_DONE"',proof+'puts "CONTROL_SYNTH_DONE"')
        if name=='validate.py':
            text=rep(text,"    result=dict(numeric_cases=1026", '''    occupancy=prior.read(B/'synth/occupancy_barrier.txt')
    assert 'LOAD_FLAG_P_CFG_DEPENDENCIES=0' in occupancy and 'OCCUPANCY_REGISTERS=1' in occupancy
    result=dict(numeric_cases=1026''')
        if name=='README.md':text+='''
The capture-stage occupancy is now a separate preserved flip-flop, not an OR of
opcode flags placed near their consumers. It equals the accepted-main-token OR
at every clock, checked in simulation. The consumer's readiness no longer tests
queued opcode flags; the frontend already enforces priority and occupancy.
This removes p_cfg_valid-to-p_load_valid feedback without changing any latency.
'''
        (HERE/name).write_text(text)
    old['source_sha256']={p.relative_to(ROOT).as_posix():sha(p) for p in (HERE/'rtl').glob('*')}
    old['routed_control_parent']='experiments/a_cg_cmd_pipe/manifest.json'
    old['routed_control_parent_sha256']=sha(PREV/'manifest.json')
    (HERE/'manifest.json').write_text(json.dumps(old,indent=2)+'\n')
    print('Occupancy register generated; packet latency and kernel schedule unchanged.')

if __name__=='__main__':main()
