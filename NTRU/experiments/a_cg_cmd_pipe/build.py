"""Registered command transactions; the numerical execution core stays isolated."""
from pathlib import Path
import hashlib
import json
import shutil

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
PREV=ROOT/'experiments/a_cg_control_gate'
B=ROOT/'study/build/a_cg_cmd_pipe'

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def rep(s,a,b):
    assert s.count(a)==1,(a,s.count(a))
    return s.replace(a,b)

PAYLOAD=[('cfg_fft',1),('cfg_inverse',1),('cfg_ntrugen',1),('cfg_packed',1),
 ('cfg_jobs_log',3),('cfg_fmt',2),('cfg_hmin',2),('cfg_logn',4),('cfg_q',32),('cfg_qinv',32),
 ('root_dest',16),('root_addr',9),('root_data',32),('desc_stage',4),('desc_mask',16),
 ('desc_root_base',9),('desc_root_mask',5),('desc_gap',16),('load_line',10),('load_data',128),('read_line',10)]
FLAGS=['cfg_valid','root_we','root_commit','desc_we','load_valid','read_valid','start']

def main():
    old=json.loads((PREV/'manifest.json').read_text())
    for p,h in old['source_sha256'].items():assert sha(ROOT/p)==h,('Parent changed',p)
    (HERE/'rtl').mkdir(parents=True,exist_ok=True);B.mkdir(parents=True,exist_ok=True)
    original=(PREV/'rtl/a_cg_fast.sv').read_text()
    header=original[:original.index(');')+2].replace('output reg','output wire')
    core=original.replace('module a_cg_fast (','module a_cg_exec (',1)
    core=rep(core,'wire cfg_accept=state==IDLE && !cfg_pending && cfg_valid;', 'wire cfg_accept=cfg_valid; // Accepted command token from the frontend.')
    core=rep(core,'wire reset_launch=state==IDLE && !cfg_pending && start && !cfg_valid;', 'wire reset_launch=start; // Already accepted in the idle command window.')
    core=rep(core,'wire load_accept=load_valid && load_ready;', 'wire load_accept=load_valid;')
    core=rep(core,'wire read_accept=read_valid && read_ready;', 'wire read_accept=read_valid;')
    core=rep(core,'    wire host_write=state==HLOAD;', '''    // Payload and command token are committed together. No live frontend
    // ready/config gating is distributed to these register enables.
    always @(posedge clk)begin
        if(load_valid)host_data<=load_data;
        if(load_valid || read_valid)host_line<=load_valid ? load_line : read_line;
    end
    wire host_write=state==HLOAD;''')
    core=rep(core,'if (root_we && state==IDLE && !cfg_pending && root_dest[t]) root_mem[root_addr]<=root_data;',
        'if (root_we && root_dest[t]) root_mem[root_addr]<=root_data;')
    core=rep(core,'                if (cfg_valid) begin\n                    if(!cfg_pending)begin','                if (cfg_valid) begin')
    core=rep(core,'roots_valid<=0;desc_valid<=0;error<=0;\n                    end\n                end else if (start) begin\n                    if(!cfg_pending)begin',
        'roots_valid<=0;desc_valid<=0;error<=0;\n                end else if (start) begin')
    core=rep(core,'write_active<=desc[0][45:30]; end\n                    end\n                end else if (load_valid && load_ready) begin',
        'write_active<=desc[0][45:30]; end\n                end else if (load_valid) begin')
    core=rep(core,'host_data<=load_data; host_line<=load_line; host_word<=0; state<=HPREP;', 'host_word<=0; state<=HPREP;')
    core=rep(core,'end else if (read_valid && read_ready) begin\n                    host_line<=read_line; host_word<=0; state<=HPREP;',
        'end else if (read_valid) begin\n                    host_word<=0; state<=HPREP;')
    core=rep(core,'if(read_accept) begin host_line<=read_line;host_word<=0;state<=HPREP;end',
        'if(read_accept) begin host_word<=0;state<=HPREP;end')
    block='''                if (!cfg_pending && root_we) roots_valid<=0;
                if (!cfg_pending && root_commit) roots_valid<=1;
                if (!cfg_pending && desc_we && desc_stage<10) begin
                    desc[desc_stage]<={desc_mask,desc_root_base,desc_root_mask,desc_gap};
                    desc_valid[desc_stage]<=1;
                end
'''
    core=rep(core,block,'')
    core=rep(core,'            if(cfg_pipe[0])begin', '''            if(root_we)roots_valid<=0;
            if(root_commit)roots_valid<=1;
            if(desc_we)desc_valid[desc_stage]<=1;
            if(cfg_pipe[0])begin''')
    core=rep(core,'    integer v;\n    always @(posedge clk)', '''    // The producer qualifies commands once, before registering the entire
    // transaction. Storage only consumes the committed token and payload.
    always @(posedge clk)if(desc_we)
        desc[desc_stage]<={desc_mask,desc_root_base,desc_root_mask,desc_gap};
`ifndef SYNTHESIS
    always @(posedge clk)if(!rst)begin
        if((cfg_valid || start || root_we || root_commit || desc_we) &&
           (state!=IDLE || cfg_pending))$fatal(1,"command committed outside idle window");
        if(load_valid && (state!=IDLE || !configured || cfg_pending))$fatal(1,"load token not executable");
        if(read_valid && ((state!=IDLE && state!=HCATCH) || !configured || cfg_pending))$fatal(1,"read token not executable");
        if(desc_we && desc_stage>=10)$fatal(1,"invalid descriptor token");
        if((cfg_valid && (start||load_valid||read_valid)) || (start && (load_valid||read_valid)) ||
           (load_valid && read_valid))$fatal(1,"multiple main command tokens");
    end
`endif
    integer v;
    always @(posedge clk)''')
    declarations=[];captures=[];connections=['.clk(clk)','.rst(p_rst)']
    for name,width in PAYLOAD:
        dim='' if width==1 else f'[{width-1}:0] '
        declarations.append(f'    (* DONT_TOUCH="yes" *) reg {dim}p_{name};')
        captures.append(f'        p_{name}<={name};')
        connections.append(f'.{name}(p_{name})')
    for name in FLAGS:
        declarations.append(f'    (* DONT_TOUCH="yes" *) reg p_{name};')
        connections.append(f'.{name}(p_{name})')
    connections += ['.cfg_ready(c_cfg_ready)','.load_ready(c_load_ready)','.read_ready(c_read_ready)',
        '.busy(c_busy)','.done(c_done)','.error(c_error)','.cycles(c_cycles)',
        '.read_rsp_valid(c_rsp_valid)','.read_data(c_read_data)']
    wrapper=header+'\n'+ '\n'.join(declarations)+'''
    (* DONT_TOUCH="yes" *) reg p_rst;
    wire c_cfg_ready,c_load_ready,c_read_ready,c_busy,c_done,c_error,c_rsp_valid;
    wire [31:0] c_cycles;
    wire [127:0] c_read_data;
    wire reserved=p_cfg_valid || p_start || p_load_valid || p_read_valid;
    wire window_open=!rst && !p_rst && !reserved;
    assign cfg_ready=window_open && c_cfg_ready;
    assign load_ready=window_open && c_load_ready && !cfg_valid && !start;
    assign read_ready=window_open && c_read_ready && !cfg_valid && !start && !load_valid;
    assign busy=!rst && !p_rst && (c_busy || p_start);
    assign done=!rst && !p_rst && c_done;
    assign error=c_error;
    assign cycles=c_cycles;
    assign read_rsp_valid=!rst && !p_rst && c_rsp_valid;
    assign read_data=c_read_data;
    // Snapshot every payload field. Accepted strobes are the only data enables
    // in the consumer; changing the external pins after handshake is safe.
    always @(posedge clk)begin
        p_rst<=rst;
'''+ '\n'.join(captures)+'''
        if(rst)begin
            p_cfg_valid<=0;p_start<=0;p_load_valid<=0;p_read_valid<=0;
            p_root_we<=0;p_root_commit<=0;p_desc_we<=0;
        end else begin
            p_cfg_valid<=cfg_valid && cfg_ready;
            p_start<=window_open && c_cfg_ready && !cfg_valid && start;
            p_load_valid<=load_valid && load_ready;
            p_read_valid<=read_valid && read_ready;
            p_root_we<=cfg_ready && !cfg_valid && !start && root_we;
            p_root_commit<=cfg_ready && !cfg_valid && !start && root_commit;
            p_desc_we<=cfg_ready && !cfg_valid && !start && desc_we && desc_stage<10;
        end
    end
    (* KEEP_HIERARCHY="yes" *) a_cg_exec u_exec (
        '''+',\n        '.join(connections)+'''
    );
endmodule
'''
    (HERE/'rtl/a_cg_fast.sv').write_text(wrapper+'\n'+core)
    for name in ('tile_a.sv','mul_ss.v'):shutil.copy2(PREV/'rtl'/name,HERE/'rtl'/name)
    for name in ('main.cpp','tb_four_state.sv','application.py','run_sim.ps1','synth.tcl','implement.tcl'):
        text=(PREV/name).read_text().replace('a_cg_control_gate','a_cg_cmd_pipe')
        if name in ('synth.tcl','implement.tcl'):
            text=text.replace('NAME =~ *reset_local_reg && REF_NAME == FDRE','NAME =~ *reset_local_reg')
        if name=='main.cpp':
            text=text.replace('d.start=0;if(!d.done', 'd.start=0;wait([&](){return d.done;},20,"invalid start completion");if(!d.done')
            text=rep(text,'d.load_valid=1;tick();d.load_valid=0;', '''d.load_valid=1;tick();d.load_valid=0;
            d.load_line=1023;for(unsigned j=0;j<4;++j)d.load_data[j]=0xdeadbeefU^(l*4+j);''')
            text=rep(text,'}d.desc_we=0;', '}d.desc_we=0;d.desc_stage=15;d.desc_mask=0;d.desc_root_base=511;d.desc_root_mask=31;d.desc_gap=0;')
            text=rep(text,'}d.root_we=0;d.root_commit=1;', '}d.root_we=0;d.root_dest=0;d.root_addr=511;d.root_data=0xbadc0deU;d.root_commit=1;')
            text=rep(text,'<<" q="<<q<<" errors="', '<<" words="<<nw<<" q="<<q<<" errors="')
        if name=='synth.tcl':
            a=text.index('set checked 0');z=text.index('puts "CONTROL_SYNTH_DONE"',a)
            text=text[:a]+'''set ext [get_ports -filter {DIRECTION == IN && NAME != clk}]
set internal_registers [filter [all_registers] {NAME =~ u_exec/*}]
set direct [get_timing_paths -from $ext -to $internal_registers -max_paths 1]
set f [open [file join $out command_barrier.txt] w]
puts $f "CORE_REGISTERS=[llength $internal_registers]"
puts $f "DIRECT_INPUT_TO_CORE_PATHS=[llength $direct]"
close $f
if {[llength $internal_registers] == 0 || [llength $direct] != 0} {error "Command register barrier incomplete"}
'''+text[z:]
        if name=='report.py':
            text=text.replace("B/'synth/host_ce_fanin.txt'", "B/'synth/command_barrier.txt'")
            text=text.replace('redundant_host_pending_gate_removed=True,','complete_registered_command_transactions=True,')
        (HERE/name).write_text(text)
    old['source_sha256']={p.relative_to(ROOT).as_posix():sha(p) for p in (HERE/'rtl').glob('*')}
    old['routed_control_parent']='experiments/a_cg_control_gate/manifest.json'
    old['routed_control_parent_sha256']=sha(PREV/'manifest.json')
    (HERE/'manifest.json').write_text(json.dumps(old,indent=2)+'\n')
    print('Registered command frontend generated; packet fields and accepted tokens share one clock of latency.')

if __name__=='__main__':main()
