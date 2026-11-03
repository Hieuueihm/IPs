"""Factor occupancy qualification after independent main-command priority decode."""
from pathlib import Path
import hashlib
import json
import shutil

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
PREV=ROOT/'experiments/a_cg_cmd_frontreset'
B=ROOT/'study/build/a_cg_cmd_frontreserve'
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
    s=rep(s,'    wire cfg_open_i,load_open_i,read_open_i;', '''    wire main_request_i;
    // Decode request priority without permission/occupancy; apply those local
    // FFs only at the final occupancy gate, not through the read-token chain.
    (* KEEP_HIERARCHY="yes" *) a_cg_main_request u_main_request (
        .cfg_available(c_cfg_ready),.load_available(c_load_ready),.read_available(c_read_ready),
        .cfg_valid(cfg_valid),.start(start),.load_valid(load_valid),.read_valid(read_valid),
        .request(main_request_i)
    );
    wire cfg_open_i,load_open_i,read_open_i;''')
    s=rep(s,'            reserved <= cfg_fire_i || start_fire_i || load_fire_i || read_fire_i;',
        '            reserved <= frontend_live && !reserved && main_request_i;')
    s+='''
// Same priority as accepted tokens: config/start preempt load, which preempts
// read even when its corresponding availability is low. Side writes do not
// reserve the main-command slot. No reset/live/occupancy input enters here.
module a_cg_main_request (
    input wire cfg_available,load_available,read_available,
    input wire cfg_valid,start,load_valid,read_valid,
    output wire request
);
    assign request=(cfg_valid || start) ? cfg_available :
                   load_valid ? load_available : (read_valid && read_available);
endmodule
'''
    (HERE/'rtl/a_cg_fast.sv').write_text(s)
    for name in ('tile_a.sv','mul_ss.v'): shutil.copy2(PREV/'rtl'/name,HERE/'rtl'/name)
    for name in ('main.cpp','tb_four_state.sv','application.py','run_sim.ps1','synth.tcl','validate.py','implement_cold.tcl','report.py'):
        t=(PREV/name).read_text().replace('a_cg_cmd_frontreset','a_cg_cmd_frontreserve')
        if name=='synth.tcl':
            t=rep(t,'puts "CONTROL_SYNTH_DONE"', '''set permission_path [get_timing_paths -from [get_cells frontend_live_reg] -to [get_pins reserved_reg/D] -delay_type max -max_paths 1]
set levels [get_property LOGIC_LEVELS $permission_path]
report_timing -from [get_cells frontend_live_reg] -to [get_pins reserved_reg/D] -delay_type max -max_paths 1 -file [file join $out reservation_permission.rpt]
set f [open [file join $out reservation_permission.txt] w]
puts $f "PERMISSION_TO_RESERVATION_LOGIC_LEVELS=$levels"
close $f
if {[llength $permission_path] != 1 || $levels > 1} {error "Permission traverses more than final reservation gate"}
puts "CONTROL_SYNTH_DONE"''')
        if name=='validate.py':
            t=rep(t,'    result=dict(frontend_reset_isolated=True,numeric_cases=1026', '''    reservation=prior.read(B/'synth/reservation_permission.txt')
    assert 'PERMISSION_TO_RESERVATION_LOGIC_LEVELS=1' in reservation
    result=dict(reservation_permission_logic_levels=1,frontend_reset_isolated=True,numeric_cases=1026''')
        if name=='implement_cold.tcl':
            t=t.replace('variant=local_frontend_reset_decode_cold','variant=late_qualified_reservation_cold')
        if name=='report.py':
            t=t.replace("'a_cg_cmd_credit']", "'a_cg_cmd_credit','a_cg_cmd_frontreset']")
            t=t.replace("frontend_reset_isolated=True,", "frontend_reset_isolated=True,reservation_permission_logic_levels=1,")
            t=t.replace("B/'synth/frontend_reset_barrier.txt',", "B/'synth/frontend_reset_barrier.txt',B/'synth/reservation_permission.txt',")
            t=t.replace("        'One permission register is added; packet latency, priority and kernel cycles remain unchanged.',", "        'Reservation now qualifies an independent priority decode with permission/occupancy at its final LUT.',\n        'Synthesis proves exactly one LUT from local permission to reservation. Protocol equality is asserted.',\n        'Packet latency, priority and kernel cycles remain unchanged.',")
        (HERE/name).write_text(t)
    old['source_sha256']={p.relative_to(ROOT).as_posix():sha(p) for p in (HERE/'rtl').glob('*')}
    old['routed_control_parent']='experiments/a_cg_cmd_frontreset/manifest.json'
    old['routed_control_parent_sha256']=sha(PREV/'manifest.json')
    (HERE/'manifest.json').write_text(json.dumps(old,indent=2)+'\n')
    (HERE/'README.md').write_text('''# Late-qualified command reservation

Isolated child of a_cg_cmd_frontreset. Routed parent failed frontend permission
to reservation through three LUTs and 5.431 ns routing. Independent request
priority decode has no live/reset/occupancy input. Reservation D applies local
permission and occupancy at the final gate, avoiding the accepted-read OR chain.
All accepted flags, payload, protocol latency and arithmetic remain identical.
Existing occupancy-equals-token-OR assertion checks protocol equivalence.
Synthesis requires exactly one logic level from permission to reservation D.
Full vectors, four-state, reset abort and live C replay gate cold OOC P&R.
Host/root included; 5 ns unchanged; no edits to production or retained baselines.
''')
    print('Generated late-qualified reservation fork; arithmetic and latency unchanged.')

if __name__=='__main__': main()
