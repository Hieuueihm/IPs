"""Remove the redundant pending gate from host acceptance without changing phases."""
from pathlib import Path
import hashlib
import json
import shutil

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
PREV=ROOT/'experiments/a_cg_control_pipe'
B=ROOT/'study/build/a_cg_control_gate'

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def rep(s,a,b):
    assert s.count(a)==1,(a,s.count(a))
    return s.replace(a,b)

def main():
    old=json.loads((PREV/'manifest.json').read_text())
    for p,h in old['source_sha256'].items():assert sha(ROOT/p)==h
    (HERE/'rtl').mkdir(parents=True,exist_ok=True);B.mkdir(parents=True,exist_ok=True)
    core=(PREV/'rtl/a_cg_fast.sv').read_text()
    core=rep(core,'assign load_ready = state==IDLE && !cfg_pending && configured && !cfg_valid;',
        'assign load_ready = state==IDLE && configured && !cfg_valid;')
    core=rep(core,'assign read_ready = (state==IDLE || state==HCATCH) && !cfg_pending && configured && !cfg_valid && !load_valid;',
        'assign read_ready = (state==IDLE || state==HCATCH) && configured && !cfg_valid && !load_valid;')
    core=rep(core,'            if (state==IDLE && !cfg_pending) begin','            if (state==IDLE) begin')
    core=rep(core,'                if (cfg_valid) begin\n                    fft<=cfg_fft;',
        '                if (cfg_valid) begin\n                    if(!cfg_pending)begin\n                    fft<=cfg_fft;')
    core=rep(core,'roots_valid<=0;desc_valid<=0;error<=0;\n                end else if (start) begin',
        'roots_valid<=0;desc_valid<=0;error<=0;\n                    end\n                end else if (start) begin\n                    if(!cfg_pending)begin')
    core=rep(core,'write_active<=desc[0][45:30]; end\n                end else if (load_valid && load_ready)',
        'write_active<=desc[0][45:30]; end\n                    end\n                end else if (load_valid && load_ready)')
    core=rep(core,'                if (root_we) roots_valid<=0;', '                if (!cfg_pending && root_we) roots_valid<=0;')
    core=rep(core,'                if (root_commit) roots_valid<=1;', '                if (!cfg_pending && root_commit) roots_valid<=1;')
    core=rep(core,'                if (desc_we && desc_stage<10) begin', '                if (!cfg_pending && desc_we && desc_stage<10) begin')
    core=rep(core,'    assign cfg_ready = state==IDLE && !cfg_pending;', '''    assign cfg_ready = state==IDLE && !cfg_pending;
    // configured remains zero throughout config preparation; it is sufficient
    // to protect host acceptance without routing cfg_pending into host CEs.
`ifndef SYNTHESIS
    always @(posedge clk) if(!rst && cfg_pending)begin
        if(configured || load_ready || read_ready || busy || roots_valid || desc_valid!=0)
            $fatal(1,"host/context exposed during configuration preparation");
    end
`endif''')
    (HERE/'rtl/a_cg_fast.sv').write_text(core)
    for name in ('tile_a.sv','mul_ss.v'):shutil.copy2(PREV/'rtl'/name,HERE/'rtl'/name)
    for name in ('main.cpp','tb_four_state.sv','application.py','run_sim.ps1','synth.tcl','validate.py','implement.tcl','report.py','README.md'):
        text=(PREV/name).read_text().replace('a_cg_control_pipe','a_cg_control_gate')
        if name=='main.cpp':
            text=rep(text,'''        wait([&](){return d.cfg_ready;},20,"configuration pipeline");
        if(d.error)''','''        // Pending commands must be ignored while ready is low. Keep a second
        // config and all conflicting command classes asserted for these clocks.
        d.cfg_valid=1;d.start=1;d.root_we=1;d.root_commit=1;d.desc_we=1;
        d.root_dest=65535;d.root_addr=0;d.root_data=0;d.desc_stage=0;
        d.desc_mask=65535;d.desc_root_base=511;d.desc_root_mask=31;d.desc_gap=1;
        d.load_valid=1;d.read_valid=1;
        wait([&](){return d.cfg_ready;},20,"configuration pipeline");
        d.cfg_valid=0;d.start=0;d.root_we=0;d.root_commit=0;d.desc_we=0;
        d.load_valid=0;d.read_valid=0;
        if(d.error)''')
        if name=='synth.tcl':
            proof='''set checked 0
set dependencies 0
set f [open [file join $out host_ce_fanin.txt] w]
foreach cell [get_cells -hier -filter {NAME =~ host_line_reg*}] {
    set ce [get_pins -of_objects $cell -filter {REF_PIN_NAME == CE}]
    if {[llength $ce] == 0} {continue}
    incr checked
    set starts [all_fanin -flat -startpoints_only -to $ce]
    set source_cells [get_cells -quiet -of_objects $starts]
    set found [filter $source_cells {NAME =~ *cfg_pipe_reg*}]
    incr dependencies [llength $found]
    puts $f "$cell config_pipeline_sources=[llength $found]"
}
puts $f "CHECKED_REGISTERS=$checked"
puts $f "CFG_PIPE_DEPENDENCIES=$dependencies"
close $f
if {$checked == 0 || $dependencies != 0} {error "Redundant host CE dependency remains"}
'''
            text=rep(text,'puts "CONTROL_SYNTH_DONE"',proof+'puts "CONTROL_SYNTH_DONE"')
        if name=='validate.py':
            text=rep(text,"    resource=prior.resource(B/'synth/util.rpt')", '''    fanin=prior.read(B/'synth/host_ce_fanin.txt')
    assert 'CFG_PIPE_DEPENDENCIES=0' in fanin
    resource=prior.resource(B/'synth/util.rpt')''')
        if name=='report.py':
            text=rep(text,"configuration_sequencer_separate_from_compute_FSM=True,", "configuration_sequencer_separate_from_compute_FSM=True,\n        redundant_host_pending_gate_removed=True,")
            text=rep(text,"    combined=json.loads((ROOT/'study/results/a_cg_control.json').read_text())", "    combined=json.loads((ROOT/'study/results/a_cg_control.json').read_text())\n    pending_gate=json.loads((ROOT/'study/results/a_cg_control_pipe.json').read_text())")
            text=rep(text,"        combined_FSM_attempt=dict(resource=combined['resource'],internal_timing=combined['internal_timing']),", "        combined_FSM_attempt=dict(resource=combined['resource'],internal_timing=combined['internal_timing']),\n        pending_gate_attempt=dict(resource=pending_gate['resource'],internal_timing=pending_gate['internal_timing']),")
            text=rep(text,"    artifacts=[HERE/'manifest.json',HERE/'implement.tcl',B/'validation.json',B/'implementation_console.log']", "    artifacts=[HERE/'manifest.json',HERE/'implement.tcl',B/'validation.json',B/'implementation_console.log',B/'synth/host_ce_fanin.txt']")
            anchor="        'The prior combined-FSM prototype is retained separately in `experiments/a_cg_control/`.','',"
            text=rep(text,anchor,anchor+'''
        'The redundant pending gate on host acceptance has been removed. Configured stays zero during all five',
        'setup clocks; simulation checks this invariant while conflicting commands are asserted.',
        'Synthesis requires zero cfg_pipe registers in the combinational fan-in of every host_line clock enable.','',
'''.rstrip())
        if name=='README.md':text+='''
The host path no longer tests cfg_pending twice. configured is cleared on
config acceptance and stays zero until the five setup steps finish. Load/read
acceptance therefore remains blocked during setup without that extra gate.
Only config/start/root/descriptor actions retain their explicit pending guard.
Simulation asserts that no host/context is exposed during setup and drives
conflicting commands while cfg_ready is low. Synthesis checks that cfg_pipe
registers are absent from host_line clock-enable combinational fan-in.
'''
        (HERE/name).write_text(text)
    old['source_sha256']={p.relative_to(ROOT).as_posix():sha(p) for p in (HERE/'rtl').glob('*')}
    old['routed_control_parent']='experiments/a_cg_control_pipe/manifest.json'
    old['routed_control_parent_sha256']=sha(PREV/'manifest.json')
    (HERE/'manifest.json').write_text(json.dumps(old,indent=2)+'\n')
    print('Host acceptance isolated from config pending; arithmetic and five setup clocks unchanged.')

if __name__=='__main__':main()
