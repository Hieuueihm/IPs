"""Isolated two-stage command delivery plus registered read response."""
from pathlib import Path
import hashlib
import json
import re
import shutil

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
PREV=ROOT/'experiments/a_cg_cmd_frontreserve'
B=ROOT/'study/build/a_cg_cmd_dispatch2'
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
    boundary=s.index('module a_cg_exec (')
    wrapper=s[:boundary]
    fields=[(w or '',n) for w,n in re.findall(r'    \(\* DONT_TOUCH="yes" \*\) reg (\[[^\]]+\] )?(p_\w+);',wrapper) if n!='p_rst']
    flags={'p_cfg_valid','p_start','p_load_valid','p_read_valid','p_root_we','p_root_commit','p_desc_we'}
    assert len(flags)==7 and len(fields)==28,len(fields)
    declarations='\n'.join('    (* DONT_TOUCH="yes" *) reg '+w+'q_'+n[2:]+';' for w,n in fields)
    wrapper=rep(wrapper,'    wire c_cfg_ready,c_load_ready,c_read_ready,c_busy,c_done,c_error,c_rsp_valid;', declarations+'''
    (* DONT_TOUCH="yes" *) reg accepted_main_d;
    (* DONT_TOUCH="yes" *) reg rsp_valid_q;
    (* DONT_TOUCH="yes" *) reg [127:0] rsp_data_q;
    wire c_cfg_ready,c_load_ready,c_read_ready,c_busy,c_done,c_error,c_rsp_valid;''')
    wrapper=rep(wrapper,'(c_busy || p_start)','(c_busy || p_start || q_start)')
    wrapper=rep(wrapper,'assign read_rsp_valid=!rst && !p_rst && c_rsp_valid;',
        'assign read_rsp_valid=!rst && !p_rst && rsp_valid_q;')
    wrapper=rep(wrapper,'assign read_data=c_read_data;', '''assign read_data=rsp_data_q;
    // Read payload and its token advance together. Delayed reset also flushes
    // a response that the execution stage generated on the raw reset edge.
    always @(posedge clk)begin
        rsp_data_q<=c_read_data;
        if(rst || p_rst)rsp_valid_q<=0;
        else rsp_valid_q<=c_rsp_valid;
    end''')
    captures='\n'.join('        q_'+n[2:]+'<='+n+';' for _,n in fields if n not in flags)
    clear='\n'.join('            q_'+n[2:]+'<=0;' for _,n in fields if n in flags)
    advance='\n'.join('            q_'+n[2:]+'<='+n+';' for _,n in fields if n in flags)
    wrapper=rep(wrapper,'        p_read_line<=read_line;','        p_read_line<=read_line;\n'+captures)
    wrapper=rep(wrapper,'            reserved<=0;', '            reserved<=0;\n            accepted_main_d<=0;\n'+clear)
    wrapper=rep(wrapper,'            reserved <= frontend_live && !reserved && main_request_i;', '''            reserved <= accepted_main_d || (frontend_live && !reserved && main_request_i);
            accepted_main_d <= frontend_live && !reserved && main_request_i;
'''+advance)
    wrapper=rep(wrapper,'if(reserved !== (p_cfg_valid || p_start || p_load_valid || p_read_valid))', '''if(accepted_main_d !== (p_cfg_valid || p_start || p_load_valid || p_read_valid))
            $fatal(1,"first-stage occupancy differs from accepted token");
        if(reserved !== (p_cfg_valid || p_start || p_load_valid || p_read_valid ||
                         q_cfg_valid || q_start || q_load_valid || q_read_valid))''')
    a=wrapper.index('    (* KEEP_HIERARCHY="yes" *) a_cg_exec u_exec (')
    instance=wrapper[a:]
    for _,n in fields:
        instance=instance.replace('('+n+')','(q_'+n[2:]+')')
    wrapper=wrapper[:a]+instance
    s=wrapper+s[boundary:]
    (HERE/'rtl/a_cg_fast.sv').write_text(s)
    for name in ('tile_a.sv','mul_ss.v'): shutil.copy2(PREV/'rtl'/name,HERE/'rtl'/name)
    for name in ('main.cpp','tb_four_state.sv','application.py','run_sim.ps1','synth.tcl','validate.py','implement_cold.tcl'):
        t=(PREV/name).read_text().replace('a_cg_cmd_frontreserve','a_cg_cmd_dispatch2')
        if name=='synth.tcl':
            t=rep(t,'puts "CONTROL_SYNTH_DONE"', '''set first_regs [filter [all_registers] {NAME =~ p_* && NAME != p_rst_reg}]
set second_regs [filter [all_registers] {NAME =~ q_*}]
set bypass [get_timing_paths -from $first_regs -to $internal_registers -max_paths 1]
set response_bypass [get_timing_paths -from $internal_registers -to [get_ports {read_data[*] read_rsp_valid}] -max_paths 1]
set f [open [file join $out dispatch_barrier.txt] w]
puts $f "FIRST_STAGE_REGISTERS=[llength $first_regs]"
puts $f "SECOND_STAGE_REGISTERS=[llength $second_regs]"
puts $f "FIRST_STAGE_TO_CORE_BYPASS=[llength $bypass]"
puts $f "CORE_TO_READ_RESPONSE_BYPASS=[llength $response_bypass]"
close $f
if {[llength $first_regs] == 0 || [llength $second_regs] == 0 || [llength $bypass] != 0 || [llength $response_bypass] != 0} {error "Additional pipeline barrier incomplete"}
puts "CONTROL_SYNTH_DONE"''')
        if name=='validate.py':
            t=rep(t,"expected=2*((new['words']+3)//4)+2", "expected=4*((new['words']+3)//4)+5")
            t=rep(t,'    result=dict(reservation_permission_logic_levels=1,', '''    dispatch=prior.read(B/'synth/dispatch_barrier.txt')
    for label in ('FIRST_STAGE_TO_CORE_BYPASS=0','CORE_TO_READ_RESPONSE_BYPASS=0'):
        assert label in dispatch,label
    assert 'PIPELINE_RESET command_stages=2 response_flush=1 PASS' in prior.read(B/'pipeline_reset.log')
    result=dict(pipeline_reset_command_stages_checked=2,response_flush_checked=True,command_capture_stages=2,registered_read_response=True,reservation_permission_logic_levels=1,''')
            t=t.replace('configuration_extra_clocks_vs_retained=6,load_read_extra_clocks_per_line_vs_control_gate=1,',
                'configuration_extra_clocks_vs_retained=7,load_read_extra_clocks_per_line_vs_control_gate=2,')
            t=t.replace('start_extra_clocks_vs_control_gate=1,root_descriptor_throughput_words_per_clock=1,',
                'start_extra_clocks_vs_control_gate=2,read_response_extra_clocks=1,root_descriptor_latency_clocks=2,root_descriptor_throughput_words_per_clock=1,')
            t=t.replace('# Config and start each cross one capture edge. Every load/read line\n        # crosses one more edge; root/descriptor writes remain one per clock.',
                '# Two capture edges for each main command, plus one final response\n        # drain edge. Side writes retain one-packet-per-clock throughput.')
        if name=='implement_cold.tcl':
            t=t.replace('variant=late_qualified_reservation_cold','variant=two_command_stages_read_response_cold')
        if name=='run_sim.ps1':
            t=rep(t,"Write-Output 'CONTROL_FUNCTIONAL_DONE'", "& ./experiments/a_cg_cmd_dispatch2/run_pipeline_reset.ps1\nWrite-Output 'CONTROL_FUNCTIONAL_DONE'")
        (HERE/name).write_text(t)
    old['source_sha256']={p.relative_to(ROOT).as_posix():sha(p) for p in (HERE/'rtl').glob('*')}
    old['routed_control_parent']='experiments/a_cg_cmd_frontreserve/manifest.json'
    old['routed_control_parent_sha256']=sha(PREV/'manifest.json')
    (HERE/'manifest.json').write_text(json.dumps(old,indent=2)+'\n')
    (HERE/'README.md').write_text('''# Two command stages and registered read response

Private child of a_cg_cmd_frontreserve; production and retained baselines unchanged.
All accepted command flags and payloads cross a second unconditional payload
register stage. Two-stage occupancy blocks conflicting main commands until delivery;
root and descriptor streams still accept one word per clock. Read response data
and valid share another stage, flushed on raw or delayed reset. Busy covers both
queued start stages. Arithmetic and kernel schedule are unchanged.

Relative to the parent: command delivery +1 clock, root/descriptor latency +1
clock (throughput unchanged), read response +1 clock. Main host commands have
three-clock spacing instead of two. This is a timing/latency tradeoff.

The external input-to-first-register OOC hold warning is NOT fixed by these stages.
The parent's worst path has zero modelled data delay because boundary routing and
partition-pin positions are absent. Actual host/clock integration is needed to
close that interface; no clock/IO constraints or false paths are changed here.
Full host/root included in synthesis and cold P&R, at the original 5 ns target.
''')
    print('Generated second command stage and read response pipeline; arithmetic unchanged.')

if __name__=='__main__': main()
