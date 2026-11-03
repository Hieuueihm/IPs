"""Isolated RTL fork: local ingress permission and reset-free token decode."""
from pathlib import Path
import hashlib
import json
import shutil

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
PREV=ROOT/'experiments/a_cg_cmd_credit'
B=ROOT/'study/build/a_cg_cmd_frontreset'
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def rep(s,a,b):
    assert s.count(a)==1,(a,s.count(a))
    return s.replace(a,b)

def main():
    old=json.loads((PREV/'manifest.json').read_text())
    for p,h in old['source_sha256'].items(): assert sha(ROOT/p)==h
    (HERE/'rtl').mkdir(parents=True,exist_ok=True)
    B.mkdir(parents=True,exist_ok=True)
    s=(PREV/'rtl/a_cg_fast.sv').read_text()
    s=rep(s,'    wire window_open=!rst && !p_rst && !reserved;\n    assign cfg_ready=window_open && c_cfg_ready;\n    assign load_ready=window_open && c_load_ready && !cfg_valid && !start;\n    assign read_ready=window_open && c_read_ready && !cfg_valid && !start && !load_valid;', '''    // Distinct low-fanout permission FF; execution reset does not feed token D.
    (* DONT_TOUCH="yes" *) reg frontend_live;
    wire cfg_open_i,load_open_i,read_open_i;
    wire cfg_fire_i,start_fire_i,load_fire_i,read_fire_i;
    wire root_fire_i,commit_fire_i,desc_fire_i;
    (* KEEP_HIERARCHY="yes" *) a_cg_command_decode u_command_decode (
        .live(frontend_live),.reserved(reserved),
        .cfg_available(c_cfg_ready),.load_available(c_load_ready),.read_available(c_read_ready),
        .cfg_valid(cfg_valid),.start(start),.load_valid(load_valid),.read_valid(read_valid),
        .root_we(root_we),.root_commit(root_commit),.desc_we(desc_we),.desc_stage(desc_stage),
        .cfg_open(cfg_open_i),.load_open(load_open_i),.read_open(read_open_i),
        .cfg_fire(cfg_fire_i),.start_fire(start_fire_i),.load_fire(load_fire_i),.read_fire(read_fire_i),
        .root_fire(root_fire_i),.commit_fire(commit_fire_i),.desc_fire(desc_fire_i)
    );
    // Asserting reset masks the public interface immediately. The synchronous
    // reset on flag FFs dominates capture, so token decode need not include rst.
    assign cfg_ready=!rst && cfg_open_i;
    assign load_ready=!rst && load_open_i;
    assign read_ready=!rst && read_open_i;''')
    s=rep(s,'        p_rst<=rst;','        p_rst<=rst;\n        frontend_live<=!rst;')
    s=rep(s,'''            reserved <= (cfg_valid && cfg_ready) ||
                (window_open && c_cfg_ready && !cfg_valid && start) ||
                (load_valid && load_ready) || (read_valid && read_ready);
            p_cfg_valid<=cfg_valid && cfg_ready;
            p_start<=window_open && c_cfg_ready && !cfg_valid && start;
            p_load_valid<=load_valid && load_ready;
            p_read_valid<=read_valid && read_ready;
            p_root_we<=cfg_ready && !cfg_valid && !start && root_we;
            p_root_commit<=cfg_ready && !cfg_valid && !start && root_commit;
            p_desc_we<=cfg_ready && !cfg_valid && !start && desc_we && desc_stage<10;''', '''            reserved <= cfg_fire_i || start_fire_i || load_fire_i || read_fire_i;
            p_cfg_valid<=cfg_fire_i;
            p_start<=start_fire_i;
            p_load_valid<=load_fire_i;
            p_read_valid<=read_fire_i;
            p_root_we<=root_fire_i;
            p_root_commit<=commit_fire_i;
            p_desc_we<=desc_fire_i;''')
    s=rep(s,'    always @(posedge clk)if(!rst)begin\n        if(reserved', '''    always @(posedge clk)if(!rst)begin
        if(frontend_live !== !p_rst)
            $fatal(1,"frontend permission differs from delayed reset complement");
        if(reserved''')
    s+='''
// No raw reset or global execution-reset input crosses this boundary. All
// accepted flags share this priority contract; payload capture is unchanged.
module a_cg_command_decode (
    input wire live,reserved,cfg_available,load_available,read_available,
    input wire cfg_valid,start,load_valid,read_valid,root_we,root_commit,desc_we,
    input wire [3:0] desc_stage,
    output wire cfg_open,load_open,read_open,
    output wire cfg_fire,start_fire,load_fire,read_fire,root_fire,commit_fire,desc_fire
);
    wire open=live && !reserved;
    assign cfg_open=open && cfg_available;
    assign load_open=open && load_available && !cfg_valid && !start;
    assign read_open=open && read_available && !cfg_valid && !start && !load_valid;
    assign cfg_fire=cfg_open && cfg_valid;
    assign start_fire=cfg_open && !cfg_valid && start;
    assign load_fire=load_open && load_valid;
    assign read_fire=read_open && read_valid;
    assign root_fire=cfg_open && !cfg_valid && !start && root_we;
    assign commit_fire=cfg_open && !cfg_valid && !start && root_commit;
    assign desc_fire=cfg_open && !cfg_valid && !start && desc_we && desc_stage<10;
endmodule
'''
    (HERE/'rtl/a_cg_fast.sv').write_text(s)
    for name in ('tile_a.sv','mul_ss.v'): shutil.copy2(PREV/'rtl'/name,HERE/'rtl'/name)
    for name in ('main.cpp','tb_four_state.sv','application.py','run_sim.ps1','synth.tcl','validate.py','implement_cold.tcl','report.py'):
        t=(PREV/name).read_text().replace('a_cg_cmd_credit','a_cg_cmd_frontreset')
        if name=='synth.tcl':
            t=rep(t,'puts "CONTROL_SYNTH_DONE"', '''set dest [get_pins -of_objects [get_cells p_load_valid_reg] -filter {REF_PIN_NAME == D}]
set cone [all_fanin -flat -startpoints_only -to $dest]
set source_cells [get_cells -quiet -of_objects $cone]
set global_reset [filter $source_cells {NAME == p_rst_reg}]
set raw_reset [filter $cone {NAME == rst}]
set local_live [filter $source_cells {NAME == frontend_live_reg}]
set f [open [file join $out frontend_reset_barrier.txt] w]
puts $f "LOAD_GLOBAL_RESET_DEPENDENCIES=[llength $global_reset]"
puts $f "LOAD_RAW_RESET_D_DEPENDENCIES=[llength $raw_reset]"
puts $f "LOAD_LOCAL_PERMISSION_DEPENDENCIES=[llength $local_live]"
close $f
if {[llength $global_reset] != 0 || [llength $raw_reset] != 0 || [llength $local_live] != 1} {error "Ingress reset isolation failed"}
puts "CONTROL_SYNTH_DONE"''')
        if name=='validate.py':
            t=rep(t,'    result=dict(numeric_cases=1026', '''    reset_barrier=prior.read(B/'synth/frontend_reset_barrier.txt')
    for label in ('LOAD_GLOBAL_RESET_DEPENDENCIES=0','LOAD_RAW_RESET_D_DEPENDENCIES=0','LOAD_LOCAL_PERMISSION_DEPENDENCIES=1'):
        assert label in reset_barrier,label
    result=dict(frontend_reset_isolated=True,numeric_cases=1026''')
        if name=='implement_cold.tcl':
            t=t.replace('variant=complete_commands_local_occupancy_cold','variant=local_frontend_reset_decode_cold')
        if name=='report.py':
            t=t.replace("B/'validation.json',RUNLOG,B/'implementation_console.log',", "B/'validation.json',RUNLOG,B/'synth/frontend_reset_barrier.txt',")
            t=t.replace("incremental_attempt='Vivado 2018.1 EXCEPTION_ACCESS_VIOLATION during reference legality checking; no placement result',", "frontend_reset_isolated=True,")
            t=t.replace("'a_cg_cmd_pipe']", "'a_cg_cmd_pipe','a_cg_cmd_credit']")
            a=t.index("        'The attempted incremental import crashed")
            b=t.index("        'Production HDL and retained baselines",a)
            t=t[:a]+'''        'This RTL fork separates the frontend permission flip-flop from execution reset and decodes',
        'accepted flags without raw reset in their D cones. Public readies retain immediate reset masking.',
        'Synthesis proves the load-token D cone uses the local permission and neither global nor raw reset.',
        'One permission register is added; packet latency, priority and kernel cycles remain unchanged.',
        'A fresh cold implementation uses the same placement/routing directives and constraints as its parent.',
'''+t[b:]
        (HERE/name).write_text(t)
    old['source_sha256']={p.relative_to(ROOT).as_posix():sha(p) for p in (HERE/'rtl').glob('*')}
    old['routed_control_parent']='experiments/a_cg_cmd_credit/manifest.json'
    old['routed_control_parent_sha256']=sha(PREV/'manifest.json')
    (HERE/'manifest.json').write_text(json.dumps(old,indent=2)+'\n')
    (HERE/'README.md').write_text('''# Local frontend reset and token decode

Isolated child of a_cg_cmd_credit. Adds one preserved frontend permission FF,
equivalent to the complement of the delayed execution reset. Token D functions
are decoded in a kept hierarchy with no raw reset or execution reset input.
Public ready outputs still mask raw reset, and accepted flag registers retain
synchronous reset. Same command latency, priority, arithmetic and kernel schedule.

Synthesis must prove execution/global reset and raw reset absent from load-token
D fan-in. Functional gate includes frozen vectors, four-state simulation, reset
abort and live C application replay. Full host/root included in OOC synth/P&R.
Production RTL and selected baselines are unchanged. Constraints remain 5 ns.
''')
    print('Generated local frontend permission/decode fork; packet latency unchanged.')

if __name__=='__main__': main()
