"""Adopt the validated host fork as immutable baseline; generate next experiments."""
from pathlib import Path
import hashlib
import importlib.util
import json
import shutil

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
B=ROOT/'study/build/a_cg_host_opt'
BASE=ROOT/'experiments/a_cg_host_baseline'
OLD=ROOT/'experiments/a_cg_timing'
VARIANTS=('direction','fields','prepare','prepare_local','select','prepare_split','select_split')

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def rep(s,a,b):
    assert s.count(a)==1,(a,s.count(a))
    return s.replace(a,b)

def direction(s):
    s=rep(s,'    reg [1:0] host_word;', '    reg [1:0] host_word;\n    reg host_direction;')
    s=rep(s,'    wire read_accept=read_valid && read_ready;', '''    wire read_accept=read_valid && read_ready;
    always @(posedge clk)
        if(rst) host_direction<=0;
        else if(load_accept) host_direction<=0;
        else if(read_accept) host_direction<=1;''')
    assert s.count('inverse ^ host_read')==3
    s=s.replace('inverse ^ host_read','inverse ^ host_direction')
    s=rep(s,'(host_read && stages[0] ? rows_per_buf : 0)',
            '(host_direction && stages[0] ? rows_per_buf : 0)')
    s=rep(s,'    wire [12:0] total_words=', '''`ifndef SYNTHESIS
    always @(posedge clk) if(!rst)begin
        if(host_read && !host_direction)$fatal(1,"read map direction not captured");
        if(host_write && host_direction)$fatal(1,"write map direction not captured");
    end
`endif
    wire [12:0] total_words=''')
    return s

def fields(s):
    s=rep(s,'(({5\'b0,rd_plane} << rowlog) + (stage_idx[0] ? rows_per_buf : 0))',
        '(({5\'b0,rd_plane} << rowlog) | (stage_idx[0] ? rows_per_buf : 0))')
    s=rep(s,'(({5\'b0,out_plane}<<rowlog) + (!write_stage[0] ? rows_per_buf : 0))',
        '(({5\'b0,out_plane}<<rowlog) | (!write_stage[0] ? rows_per_buf : 0))')
    s=rep(s,'(host_read && stages[0] ? rows_per_buf : 0)+({5\'d0,host_base_plane}<<rowlog)+(host_base_p>>5)',
        '(host_read && stages[0] ? rows_per_buf : 0)|({5\'d0,host_base_plane}<<rowlog)|(host_base_p>>5)')
    s=rep(s,'wr_plane_base + (write_far ? ((out_k>>1) + ((out_k[0]!=(b>>4)) ? far_y_offset : 0)) : out_k)',
        'wr_plane_base | (write_far ? ((out_k>>1) | ((out_k[0]!=(b>>4)) ? far_y_offset : 0)) : out_k)')
    s=rep(s,'rd_plane_base + (read_near ? k : ((k>>1) + ((k[0]!=(b>>4)) ? far_y_offset : 0)))',
        'rd_plane_base | (read_near ? k : ((k>>1) | ((k[0]!=(b>>4)) ? far_y_offset : 0)))')
    # Independent legacy addition expressions remain simulation-only and are
    # compared only when the corresponding physical RAM port is active.
    s=rep(s,'        integer hcount,hidx;', '''        wire [7:0] ref_wr_base=({5'b0,out_plane}<<rowlog)+(!write_stage[0]?rows_per_buf:0);
        wire [7:0] ref_rd_base=({5'b0,rd_plane}<<rowlog)+(stage_idx[0]?rows_per_buf:0);
        wire [7:0] ref_wr_row=ref_wr_base+(write_far?((out_k>>1)+((out_k[0]!=(b>>4))?far_y_offset:0)):out_k);
        wire [7:0] ref_rd_row=ref_rd_base+(read_near?k:((k>>1)+((k[0]!=(b>>4))?far_y_offset:0)));
        wire [7:0] ref_host_base=(host_read&&stages[0]?rows_per_buf:0)+({5'd0,host_base_plane}<<rowlog)+(host_base_p>>5);
        integer hcount,hidx;''')
    s=rep(s,'            if(state==RUN && ren && wen && ra==wa)', '''            if(ren && !host_read && rd_row!==ref_rd_row)$fatal(1,"OR read address mismatch");
            if(wen && !host_write && wr_row!==ref_wr_row)$fatal(1,"OR write address mismatch");
            if((hr||hw) && host_base_row!==ref_host_base)$fatal(1,"OR host address mismatch");
            if(state==RUN && ren && wen && ra==wa)''')
    return s

def prepare(s):
    s=direction(s)
    s=rep(s,'CONFIG_TILE=5, SETTLE=6, STAGE=7, RUN=8;',
        'CONFIG_TILE=5, SETTLE=6, STAGE=7, RUN=8, HPREP=9;')
    s=rep(s,'assign busy = state>=RESET_TILE;',
        'assign busy = state>=RESET_TILE && state<=RUN;')
    s=rep(s,'host_word<=0; state<=HLOAD;','host_word<=0; state<=HPREP;')
    s=rep(s,'host_word<=0; state<=HREAD;','host_word<=0; state<=HPREP;')
    s=rep(s,'host_word<=0;state<=HREAD;','host_word<=0;state<=HPREP;')
    s=rep(s,'            if(state==HLOAD) begin', '''            if(state==HPREP)begin
                host_word<=0;state<=host_direction?HREAD:HLOAD;
            end
            if(state==HLOAD) begin''')
    a=s.index('        assign host_bank[hw]=')
    z=s.index('        always @(posedge clk) begin',a)
    old=s[a:z]
    bank=old.split('assign host_bank[hw]=',1)[1].split(';',1)[0]
    row=old.split('assign host_row[hw]=',1)[1].split(';',1)[0]
    oob=old.split('assign host_oob[hw]=',1)[1].split(';',1)[0]
    s=s[:a]+f'''        wire [4:0] mapped_bank={bank};
        wire [7:0] mapped_row={row};
        wire mapped_oob={oob};
        reg [4:0] bank_q;
        reg [7:0] row_q;
        reg [1:0] phase_q;
        reg oob_q;
        always @(posedge clk) if(state==HPREP)begin
            bank_q<=mapped_bank;row_q<=mapped_row;phase_q<=phase;oob_q<=mapped_oob;
        end
        assign host_bank[hw]=bank_q;
        assign host_row[hw]=row_q;
        assign host_select[hw]=((phase_q & host_submask)==host_sub);
        assign host_oob[hw]=oob_q;
`ifndef SYNTHESIS
        always @(posedge clk) if(!rst && (host_read||host_write))begin
            if(bank_q!==mapped_bank || row_q!==mapped_row || phase_q!==phase || oob_q!==mapped_oob)
                $fatal(1,"prepared host map changed during service");
        end
`endif
'''+s[z:]
    return s

def select(s):
    s=direction(s)
    old='''                if(host_read && host_select[hj] && !host_oob[hj] && host_bank[hj]==b) begin hr=1;hra=host_row[hj];end
                if(host_write && host_select[hj] && !host_oob[hj] && host_bank[hj]==b) begin
                    hw=1;hwa=host_row[hj];hwd=host_data_sel[32*hj+:32];
                end'''
    new='''                // One valid word per physical bank/phase (asserted below).
                // Shared decode; OR is parallel and has no priority ordering.
                if(host_select[hj] && !host_oob[hj] && host_bank[hj]==b) begin
                    hr=host_read;hw=host_write;
                    hra=hra|host_row[hj];hwa=hwa|host_row[hj];
                    hwd=hwd|host_data_sel[32*hj+:32];
                end'''
    return rep(s,old,new)

def split_fft(tile):
    sp=importlib.util.spec_from_file_location('previous_builder_split',OLD/'build.py')
    prior=importlib.util.module_from_spec(sp);sp.loader.exec_module(prior)
    tile=prior.raw(tile)
    module='''// Exact wrap32 FFT post-adder; kept separate from GS/NTT correction.
module fft_ct_addsub #(parameter integer W=32)(
    input wire [W-1:0] a,b,input wire ci,bi,
    output wire [W-1:0] s,d,output wire co,bo
);
    (* use_dsp="no" *) wire [W:0] sum={1'b0,a}+{1'b0,b}+{{W{1'b0}},ci};
    (* use_dsp="no" *) wire [W:0] diff={1'b0,a}-{1'b0,b}-{{W{1'b0}},bi};
    assign s=sum[W-1:0];assign co=sum[W];
    assign d=diff[W-1:0];assign bo=diff[W];
endmodule

'''
    at=tile.index('module tile_a2 #(');tile=tile[:at]+module+tile[at:]
    tile=rep(tile,'    reg  [31:0] wy0l, wy0p, wy1l, wy1p;', '''    wire [31:0] fft_ct_s,fft_ct_d;
    wire fft_ct_co,fft_ct_bo;
    (* keep_hierarchy="yes" *) fft_ct_addsub u_fft_ct(
        .a(side_t),.b(t5),.ci(as_ci),.bi(as_bi),
        .s(fft_ct_s),.d(fft_ct_d),.co(fft_ct_co),.bo(fft_ct_bo));
    reg  [31:0] wy0l, wy0p, wy1l, wy1p;''')
    tile=rep(tile,'wfc <= as_co; wfb <= as_bo;',
        'wfc <= (mf && !dir) ? fft_ct_co : as_co; wfb <= (mf && !dir) ? fft_ct_bo : as_bo;')
    tile=rep(tile,'wy0l <= dir ? ry0[31:0] : us;  wy1l <= dir ? ry1[31:0] : ud;',
        'wy0l <= dir ? ry0[31:0] : fft_ct_s;  wy1l <= dir ? ry1[31:0] : fft_ct_d;')
    return tile

def main():
    previous=json.loads((ROOT/'study/results/a_cg_timing.json').read_text(encoding='utf-8'))
    for p,h in previous['sha256'].items():
        if p.startswith('experiments/a_cg_timing/host/rtl/') or p.startswith('study/build/a_cg_timing/host/synth/'):
            assert sha(ROOT/p)==h,('Accepted baseline changed',p)
    for p,h in previous['frozen']['production'].items():assert sha(ROOT/p)==h
    B.mkdir(parents=True,exist_ok=True);(BASE/'rtl').mkdir(parents=True,exist_ok=True)
    for p in (OLD/'host/rtl').glob('*'):
        dest=BASE/'rtl'/p.name
        if dest.exists():assert dest.read_bytes()==p.read_bytes(),('Immutable baseline changed',dest)
        else:shutil.copy2(p,dest)
    baseline=next(r for r in previous['results'] if r['variant']=='host')
    manifest=dict(name='registered-host packed16 baseline',adopted_by_user=True,
        source='experiments/a_cg_timing/host/rtl',evidence='study/results/a_cg_timing.json',
        evidence_sha256=sha(ROOT/'study/results/a_cg_timing.json'),resource=baseline['resource'],
        internal_timing=baseline['internal_timing'],full_timing=baseline['full_timing'],
        clock_xdc_sha256=sha(OLD/'clock.xdc'),production_sha256=previous['frozen']['production'],
        source_sha256={p.relative_to(ROOT).as_posix():sha(p) for p in (BASE/'rtl').glob('*')})
    (BASE/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    core=(BASE/'rtl/a_cg_fast.sv').read_text();tile=(BASE/'rtl/tile_a.sv').read_text()
    sp=importlib.util.spec_from_file_location('previous_builder',OLD/'build.py')
    prior=importlib.util.module_from_spec(sp);sp.loader.exec_module(prior)
    for v in VARIANTS:
        r=HERE/v/'rtl';r.mkdir(parents=True,exist_ok=True);(B/v).mkdir(exist_ok=True)
        c=direction(core) if v=='direction' else fields(core) if v=='fields' else select(core) if v in ('select','select_split') else prepare(core)
        t=prior.local(tile) if v=='prepare_local' else split_fft(tile) if v in ('prepare_split','select_split') else tile
        (r/'a_cg_fast.sv').write_text(c);(r/'tile_a.sv').write_text(t)
        shutil.copy2(BASE/'rtl/mul_ss.v',r/'mul_ss.v')
    shutil.copy2(OLD/'clock.xdc',HERE/'clock.xdc')
    shutil.copy2(OLD/'main.cpp',HERE/'main.cpp');shutil.copy2(OLD/'tb_four_state.sv',HERE/'tb_four_state.sv')
    sim=(OLD/'run_sim.ps1').read_text().replace("'base','host','local','raw','all'","'direction','fields','prepare','prepare_local','select','prepare_split','select_split'")
    sim=sim.replace("$Variant='all'","$Variant='prepare'").replace('a_cg_timing','a_cg_host_opt')
    (HERE/'run_sim.ps1').write_text(sim)
    synth=(OLD/'synth.tcl').read_text().replace('{base host local raw all}','{direction fields prepare prepare_local select prepare_split select_split}').replace('a_cg_timing','a_cg_host_opt')
    (HERE/'synth.tcl').write_text(synth)
    for v in VARIANTS:
        app=(OLD/'application_host.py').read_text().replace('study/build/a_cg_timing/host',f'study/build/a_cg_host_opt/{v}')
        app=app.replace('/experiments/a_cg_timing/application_host.py',f'/experiments/a_cg_host_opt/application_{v}.py')
        (HERE/f'application_{v}.py').write_text(app)
    print('Adopted immutable host baseline; generated',', '.join(VARIANTS))

if __name__=='__main__':main()
