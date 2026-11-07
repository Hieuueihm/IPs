"""Private, matched-part/contract ablations. Never writes accepted source/evidence."""
import hashlib
import json
import re
import shutil
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
BASE=ROOT/'experiments/a_cg_packed4_system160'
PROOF=ROOT/'experiments/a_cg_packed4'
BUILD=ROOT/'study/build/paper_ablation31'
VARIANTS=['reference','single_stream','separate_history','sparse_feed','split_domains','dedicated_mont32']
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def change(s,a,b):
    assert s.count(a)==1,(a[:100],s.count(a))
    return s.replace(a,b)

def split_modules(tile):
    # Share primitive/helper module definitions, but instantiate specialized
    # arithmetic datapaths separately. Preserve all numeric operations.
    start=tile.index('module tile_a2 #(')
    helpers,body=tile[:start],tile[start:]
    declaration=body[:body.index('    localparam [0:0] ARR32')]
    fft=body.replace('module tile_a2 #(','module tile_fft_only #(',1)
    fft=change(fft,'reg  [1:0] md;','wire [1:0] md = MD_FFT;')
    fft=change(fft,'reg        dir, mf;','reg dir; wire mf = 1\'b1;')
    fft=change(fft,"if (rst) begin md <= MD_NTT; dir <= 1'b0; mf <= 1'b0; end\n        else if (en && cfg_we) begin md <= req_mode; dir <= req_dir; mf <= (req_mode == MD_FFT); end",
        "if (rst) dir <= 1'b0;\n        else if (en && cfg_we) dir <= req_dir;")
    ntt=body.replace('module tile_a2 #(','module tile_ntt_only #(',1)
    ntt=change(ntt,'reg        dir, mf;','reg dir; wire mf = 1\'b0;')
    ntt=change(ntt,"if (rst) begin md <= MD_NTT; dir <= 1'b0; mf <= 1'b0; end\n        else if (en && cfg_we) begin md <= req_mode; dir <= req_dir; mf <= (req_mode == MD_FFT); end",
        "if (rst) begin md <= MD_NTT; dir <= 1'b0; end\n        else if (en && cfg_we) begin md <= req_mode; dir <= req_dir; end")
    port_text=declaration[declaration.index('    input  wire         clk'):]
    ports=[]
    for line in port_text.splitlines():
        line=re.sub(r'//.*','',line).strip()
        if not line or line==');':continue
        line=re.sub(r'^(input|output)\s+(wire|reg)\s*','',line)
        line=re.sub(r'\[[^]]+\]','',line)
        ports += [x.strip(' ,') for x in line.split(',') if x.strip(' ,')]
    assert len(ports)==28,ports
    wrapper=declaration+'''
    wire use_fft=(req_mode==2'd1);
    wire rf,rn,idf,idn,vf,vn;
    wire [63:0] df,dn;
    wire [7:0] tf,tn;
    assign idle=idf && idn;
    assign req_ready=use_fft ? rf : rn;
    assign rsp_valid=use_fft ? vf : vn;
    assign rsp_data=use_fft ? df : dn;
    assign rsp_tag=use_fft ? tf : tn;
'''
    for kind,mod in [('f','tile_fft_only'),('n','tile_ntt_only')]:
        mapping={p:p for p in ports}
        mapping.update(idle='id'+kind,req_ready='r'+kind,rsp_valid='v'+kind,rsp_data='d'+kind,rsp_tag='t'+kind)
        mapping['req_valid']='req_valid && '+('use_fft' if kind=='f' else '!use_fft')
        mapping['cfg_we']='cfg_we && '+('use_fft' if kind=='f' else '!use_fft')
        mapping['req_mode']="2'd1" if kind=='f' else "(req_mode==2'd2 ? 2'd2 : 2'd0)"
        if kind=='n':mapping['ext_fft_valid']="1'b0"
        if kind=='f':mapping.update(cfg_q="32'd0",cfg_qinv="32'd0",cfg_halve="1'b0")
        wrapper+='    '+mod+' #(.TREN_MANG(TREN_MANG),.LEAF_PD(LEAF_PD),.IN_REG(IN_REG),.EN_REG(EN_REG),.PHASE(PHASE)) '+kind+' (\n'
        wrapper+=',\n'.join('        .'+p+'('+mapping[p]+')' for p in ports)+'\n    );\n'
    wrapper+='endmodule\n'
    return helpers+fft+'\n'+ntt+'\n'+wrapper

def dedicated(tile):
    # Scalar NTT32 gets a feed-forward multiplier for each reduction product.
    # Five-clock stages retain E32=17. Packed16/FFT use unchanged shared leaves.
    tile=change(tile,"((ntt && (ph == 2'd0 || (mp && ph == 2'd1))) || mf)",
        "(((md==MD_NTT) || (mp && (ph==0 || ph==1))) || mf)")
    tile=change(tile,'wire [31:0] lfh = mp ? {selected_pp[63:48],selected_pp[31:16]} : lf[63:32];',
        '''reg [31:0] dm [0:FUSE-1];
        reg [63:0] dp [0:FUSE-1];
        integer di;
        wire [31:0] dqi=ks[FUSE] ? qi1 : qi0;
        wire [31:0] dq=ks[2*FUSE] ? q1 : q0;
        always @(posedge clk) if(ce) begin
            dm[0]<=lf[31:0]*dqi;
            dp[0]<=dm[FUSE-1]*{32'd0,dq};
            for(di=1;di<FUSE;di=di+1)begin dm[di]<=dm[di-1];dp[di]<=dp[di-1];end
        end
        wire [31:0] lfh = mp ? {selected_pp[63:48],selected_pp[31:16]} : dp[FUSE-1][63:32];''')
    tile=change(tile,'assign A32 = asel == 2\'d0 ? wmx[mxa] : asel == 2\'d1 ? wmsx[msxa] : asel == 2\'d2 ? lfl : a1;',
        "assign A32 = !mf && !mp ? a1 : asel == 2'd0 ? wmx[mxa] : asel == 2'd1 ? wmsx[msxa] : asel == 2'd2 ? lfl : a1;")
    tile=change(tile,"assign B32 = bsel == 2'd0 ? wmw[mwa] : bsel == 2'd1 ? wmsw[mswa] :",
        "assign B32 = !mf && !mp ? w1 : bsel == 2'd0 ? wmw[mwa] : bsel == 2'd1 ? wmsw[mswa] :")
    tile=change(tile,'if (!rst && ce && !mp && (mbz || v1 || vs[FUSE] || vs[2*FUSE]) && (A32 !== A32_ref || B32 !== B32_ref))',
        'if (!rst && ce && mf && (mbz || v1 || vs[FUSE] || vs[2*FUSE]) && (A32 !== A32_ref || B32 !== B32_ref))')
    # II1 needs more than the baseline 16 side entries. Only side RAM changes;
    # FFT's limb memories and all arithmetic semantics are unchanged.
    tile=change(tile,'reg  [3:0]    nwa, nra;','reg [4:0] nwa,nra;')
    tile=change(tile,'reg  [41:0] wma  [0:15];','reg  [41:0] wma  [0:31];')
    return tile

def main():
    assert not (HERE/'variants').exists(),'Preserve existing ablation sources'
    accepted=json.loads((ROOT/'experiments/BASELINE.json').read_text())
    assert accepted['id']=='a_cg_packed4_system160'
    BUILD.mkdir(parents=True,exist_ok=True)
    matrix={}
    for name in VARIANTS:
        out=HERE/'variants'/name;rtl=out/'rtl';shutil.copytree(BASE/'rtl',rtl)
        tile=(rtl/'tile_a.sv').read_text();core=(rtl/'a_cg_fast.sv').read_text()
        planner=(PROOF/'planner.py').read_text().replace('parents[2]', 'parents[4]')
        if name=='single_stream':
            tile=change(tile,"(ph == 2'd0 || (mp && ph == 2'd1))","(ph == 2'd0)")
            tile=change(tile,'group1<=rqd_group;','group1<=1\'b0;')
        if name=='separate_history':tile=(PROOF/'variants/separate_history/tile_a.sv').read_text()
        if name in ['single_stream','sparse_feed']:
            core=change(core,"(ph==1 || (packed16 && ph==2))","(ph==1)")
            planner=change(planner,"3*(seq//2)+seq%2 if packed else per*seq","per*seq")
        if name=='split_domains':tile=split_modules(tile)
        if name=='dedicated_mont32':
            tile=dedicated(tile)
            core=change(core,"(ph==1 || (packed16 && ph==2))","(!packed16 || ph==1 || ph==2)")
            planner=change(planner,"a=2+(3*(seq//2)+seq%2 if packed else per*seq)",
                "a=2+(3*(seq//2)+seq%2 if packed else per*seq if fft else seq)")
            planner=planner.replace("per=cg.FFT[fl][0] if fft else 3","per=cg.FFT[fl][0] if fft else 3 if packed else 1")
            planner=planner.replace("period=cg.FFT[fl][0] if fft else 3","period=cg.FFT[fl][0] if fft else 3 if packed else 1")
        (rtl/'tile_a.sv').write_text(tile);(rtl/'a_cg_fast.sv').write_text(core)
        (out/'planner.py').write_text(planner)
        (out/'extra_cases.py').write_text((PROOF/'extra_cases.py').read_text().replace('parents[2]', 'parents[4]'))
        matrix[name]=dict(source_sha256={p.name:sha(p) for p in rtl.iterdir()},planner_sha256=sha(out/'planner.py'))
        # Identical physical PS7/clock/AXI system; only arithmetic/schedule source differs.
        for script in ['create_project.tcl','implement.tcl']:
            s=(BASE/script).read_text().replace('[file dirname [info script]] ../..]', '[file dirname [info script]] ../../../..]')
            s=s.replace('set exp [file join $root experiments a_cg_packed4_system160]',f'set exp [file join $root experiments paper_ablation31 variants {name}]')
            s=s.replace('set out [file join $root study build a_cg_packed4_system160',f'set out [file join $root study build paper_ablation31 {name}')
            s=s.replace('[file join $root study build a_cg_packed4_system160 system_synth.dcp]',f'[file join $root study build paper_ablation31 {name} system_synth.dcp]')
            s=s.replace('acg_packed4_qiming','acg_ablate_'+name)
            (out/script).write_text(s)
        shutil.copy2(BASE/'signoff.tcl',out/'signoff.tcl')
    manifest=dict(accepted_baseline=accepted['id'],accepted_registry_sha256=sha(ROOT/'experiments/BASELINE.json'),
        part='xc7z020clg400-2',clock_mhz=160,variants=matrix)
    (HERE/'input_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    from provision_auxiliary import main as provision
    provision()
    print('PRIVATE_ABLATIONS_PREPARED',len(matrix))

if __name__=='__main__':main()
