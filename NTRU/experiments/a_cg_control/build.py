"""Isolated control-path retiming from the pinned prepare_split source."""
from pathlib import Path
import hashlib
import json
import shutil

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
B=ROOT/'study/build/a_cg_control'

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def rep(s,a,b):
    assert s.count(a)==1,(a,s.count(a))
    return s.replace(a,b)

def main():
    manifest=json.loads((ROOT/'experiments/a_cg_prepare_split_baseline/manifest.json').read_text())
    for group in ('source_sha256','production_sha256'):
        for p,h in manifest[group].items():assert sha(ROOT/p)==h,('Frozen file changed',p)
    src=ROOT/'experiments/a_cg_prepare_split_baseline/rtl'
    (HERE/'rtl').mkdir(parents=True,exist_ok=True);B.mkdir(parents=True,exist_ok=True)
    core=(src/'a_cg_fast.sv').read_text()
    core=rep(core,'RUN=8, HPREP=9;', 'RUN=8, HPREP=9, CFG0=10, CFG1=11, CFG2=12, CFG3=13, CFG4=14;')
    core=rep(core,'    reg [3:0] state;', '''    reg [3:0] state;
    reg [2:0] cfg_jobs_q;
    reg [3:0] cfg_plane_q;
    reg [4:0] cfg_row_q;
    reg cfg_bad_q;
    // Reset prediction is valid only for an accepted idle start. Its local
    // registered replicas are asserted in RESET_TILE, with no extra kernel clock.
    wire reset_launch=state==IDLE && start && !cfg_valid;
''')
    core=rep(core,'        wire unused_idle;', '''        (* DONT_TOUCH="yes" *) reg reset_local;
        (* DONT_TOUCH="yes" *) reg config_local;
        always @(posedge clk)begin
            reset_local <= rst || reset_launch;
            config_local <= !rst && state==RESET_TILE;
        end
`ifndef SYNTHESIS
        always @(posedge clk) if(!rst)begin
            if(state==RESET_TILE && reset_local!==1'b1)$fatal(1,"local reset not asserted");
            if(state==CONFIG_TILE && reset_local!==1'b0)$fatal(1,"local reset overlaps tile config");
            if(config_local!==(state==CONFIG_TILE))$fatal(1,"local config pulse changed phase");
        end
`endif
        wire unused_idle;''')
    core=rep(core,'.clk(clk),.rst(tile_rst),.en(1\'b1)', '.clk(clk),.rst(reset_local),.en(1\'b1)')
    core=rep(core,'.cfg_we(state==CONFIG_TILE)', '.cfg_we(config_local)')
    a=core.index('    wire [3:0] cfg_logm=');z=core.index('    integer v;',a)
    old=core[a:z]
    # Independent frozen decode retained only as a simulation assertion. It uses
    # captured request values, never the external pins after the acceptance edge.
    reference=old
    mapping={'cfg_jobs_log':'cfg_jobs_q','cfg_ntrugen':'native64','cfg_inverse':'inverse',
        'cfg_packed':'packed16','cfg_fft':'fft','cfg_fmt':'fmt','cfg_hmin':'hmin',
        'cfg_logn':'logn','cfg_qinv':'qi','cfg_q':'q'}
    import re
    reference=re.sub(r'\b('+'|'.join(sorted(mapping,key=len,reverse=True))+r')\b',lambda m:mapping[m[0]],reference)
    reference=re.sub(r'\bcfg_(logm|base_log|bank_cap|bank_jobs|row_jobs|plane_log|row_log|bad)\b',r'ref_\1',reference)
    core=core[:a]+'''    // Five configuration setup clocks. Each dependent decode starts from
    // registers; host requests resume only after CFG4 returns to IDLE.
    wire [3:0] bank_capacity=logm<5 ? 5-logm : 0;
    wire [4:0] row_exponent={1'b0,rowlog}+{1'b0,cfg_plane_q};
`ifndef SYNTHESIS
'''+reference+'''    always @(posedge clk) if(!rst && state==CFG4)begin
        if(cfg_bad_q!==ref_bad || logm!==ref_logm || base_log!==ref_base_log[2:0] ||
           bank_jobs_log!==ref_bank_jobs[2:0] || row_jobs_log!==ref_row_jobs[2:0] ||
           cfg_plane_q!==ref_plane_log || cfg_row_q!==ref_row_log ||
           planes!==(4'd1<<ref_plane_log))$fatal(1,"pipelined config differs from frozen decode");
    end
`endif
'''+core[z:]
    core=rep(core,'            state<=IDLE; configured<=0;', '            cfg_jobs_q<=0;cfg_plane_q<=0;cfg_row_q<=0;cfg_bad_q<=0;\n            state<=IDLE; configured<=0;')
    a=core.index('                    logn<=cfg_logn; logm<=cfg_logm;');z=core.index('                end else if (start)',a)
    core=core[:a]+'''                    logn<=cfg_logn;cfg_jobs_q<=cfg_jobs_log;
                    q<=cfg_q;qi<=cfg_qinv;configured<=0;
                    roots_valid<=0;desc_valid<=0;error<=0;state<=CFG0;
'''+core[z:]
    anchor='            if(state==HPREP)begin'
    core=rep(core,anchor,'''            if(state==CFG0)begin
                logm<=fft ? (logn==0 ? 0 : logn-1) : logn-((packed16 && hmin==0) ? 1 : hmin);
                base_log<=fft ? fmt+1 : ((packed16 && hmin!=0) ? hmin-1 : hmin);
                hmin_eff<=packed16 && hmin!=0 ? hmin-1 : hmin;
                job_word_log<=fft ? logn+fmt : logn-packed16;
                cfg_bad_q<=logn>10 || fmt==3 || cfg_jobs_q>4 ||
                    (native64 && (!fft || fmt!=1)) || (packed16 && (fft || q>=32768)) ||
                    (!fft && (hmin>2 || hmin>=logn || !q[0] || q<3 || q[31]));
                state<=CFG1;
            end
            if(state==CFG1)begin
                rowlog<=logm>5 ? logm-5 : 0;
                stages<=logm+(!fft && packed16 && hmin==0);
                bank_jobs_log<=cfg_jobs_q<bank_capacity ? cfg_jobs_q : bank_capacity;
                state<=CFG2;
            end
            if(state==CFG2)begin
                row_jobs_log<=cfg_jobs_q-bank_jobs_log;
                cfg_plane_q<={1'b0,base_log}+({1'b0,cfg_jobs_q}-{1'b0,bank_jobs_log});
                state<=CFG3;
            end
            if(state==CFG3)begin
                cfg_row_q<=row_exponent;
                planes<=4'd1<<cfg_plane_q;
                cfg_bad_q<=cfg_bad_q || cfg_plane_q>3 || row_exponent>7;
                state<=CFG4;
            end
            if(state==CFG4)begin
                rows_per_buf<=8'd1<<cfg_row_q;
                configured<=!cfg_bad_q;error<=cfg_bad_q;state<=IDLE;
            end
'''+anchor)
    (HERE/'rtl/a_cg_fast.sv').write_text(core)
    tile=(src/'tile_a.sv').read_text()
    tile=rep(tile,'        reg        rsign;', '        (* DONT_TOUCH="yes" *) reg rsign; // Preserve the local sign-control sink.')
    (HERE/'rtl/tile_a.sv').write_text(tile)
    shutil.copy2(src/'mul_ss.v',HERE/'rtl/mul_ss.v')
    main=(ROOT/'experiments/a_cg_host_opt/main.cpp').read_text()
    main=rep(main,'#include <map>','#include <map>\n#include <set>')
    main=main.replace('tick();d.cfg_valid=0;', 'tick();d.cfg_valid=0;wait([&](){return d.cfg_ready;},20,"configuration pipeline");')
    main=rep(main,'    for(unsigned c=0;c<count;++c){','''    std::set<unsigned> aborted;
    unsigned abort_checks=0;
    for(unsigned c=0;c<count;++c){
        auto fixture_position=f.tellg();''')
    # During the five setup clocks, poison the pins to prove capture semantics.
    before='d.cfg_valid=1;tick();d.cfg_valid=0;wait([&](){return d.cfg_ready;},20,"configuration pipeline");\n        if(d.error)'
    after='''d.cfg_valid=1;tick();d.cfg_valid=0;
        d.cfg_fft=!fft;d.cfg_fmt=3;d.cfg_logn=15;d.cfg_hmin=3;d.cfg_packed=!packed;
        d.cfg_jobs_log=7;d.cfg_q=0;d.cfg_qinv=0;d.cfg_ntrugen=!native;d.cfg_inverse=!inv;
        wait([&](){return d.cfg_ready;},20,"configuration pipeline");
        if(d.error)'''
    main=rep(main,before,after)
    main=rep(main,'        wait([&](){return d.done;},200000,"kernel timeout");','''        unsigned mode_key=fft|(fmt<<1)|(packed<<3)|(native<<4)|(inv<<5);
        if(ln>=7 && d.busy && !aborted.count(mode_key)){
            aborted.insert(mode_key);
            for(int n=0;n<8;++n)tick();
            if(!d.busy)throw std::runtime_error("abort test did not interrupt computation");
            d.rst=1;tick();d.rst=0;tick();tick();
            if(d.busy||d.load_ready)throw std::runtime_error("single-edge reset did not invalidate context");
            ++abort_checks;f.clear();f.seekg(fixture_position);--c;continue;
        }
        wait([&](){return d.done;},200000,"kernel timeout");''')
    main=rep(main,'    std::cout<<"TOTAL cases="', '    std::cout<<"RESET_ABORT modes="<<abort_checks<<" PASS"<<std::endl;\n    std::cout<<"TOTAL cases="')
    (HERE/'main.cpp').write_text(main)
    tb=(ROOT/'experiments/a_cg_host_opt/tb_four_state.sv').read_text()
    tb=rep(tb,'            cfg_valid=1;tick();cfg_valid=0;', '''            cfg_valid=1;tick();cfg_valid=0;nwait=0;
            while(cfg_ready!==1 && nwait<20)begin tick();nwait=nwait+1;end
            if(cfg_ready!==1)$fatal(1,"config pipeline timeout");''')
    (HERE/'tb_four_state.sv').write_text(tb)
    app=(ROOT/'experiments/a_cg_host_opt/application_prepare_split.py').read_text()
    app=app.replace('a_cg_host_opt/prepare_split','a_cg_control').replace('a_cg_host_opt/application_prepare_split.py','a_cg_control/application.py')
    (HERE/'application.py').write_text(app)
    frozen={'baseline':manifest,'source_sha256':{p.relative_to(ROOT).as_posix():sha(p) for p in (HERE/'rtl').glob('*')},
        'fixtures_sha256':{str(p.relative_to(ROOT)):sha(p) for p in [ROOT/'study/build/a_cg_batch/fixtures.bin',ROOT/'study/build/a_cg_batch/four_state.bin']}}
    (HERE/'manifest.json').write_text(json.dumps(frozen,indent=2)+'\n')
    print('Control-path fork generated; five config setup clocks, identical kernel schedule.')

if __name__=='__main__':main()
