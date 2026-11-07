"""Historical bootstrap of v0, before sharing T-high history.

Current canonical candidate is rtl/; this is NOT a generator for that final
revision. Refuses to overwrite rtl/ and never edits the accepted baseline.
"""
from pathlib import Path
import shutil

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
BASE = ROOT / 'experiments/a_cg_z020_system160'


def replace(s, old, new):
    assert s.count(old) == 1, (old[:100], s.count(old))
    return s.replace(old, new)


def main():
    rtl = HERE / 'rtl'
    assert not rtl.exists(), 'Preserve an existing candidate; do not regenerate over edits.'
    shutil.copytree(BASE / 'rtl', rtl)
    s = (rtl / 'tile_a.sv').read_text()
    s = replace(s, '((ntt && ph == 2\'d0) || mf)',
                '((ntt && (ph == 2\'d0 || (mp && ph == 2\'d1))) || mf)')
    s = replace(s, 'wire        rq_sign;', 'wire        rq_sign;\n    wire rq_group;')
    s = replace(s, 'reg        rn, rslot, r5;', 'reg        rn, rslot, r5, rgroup;')
    s = replace(s, 'rroot <= req_root; rtag <= req_tag; rsign <= req_sign; rslot <= `TL_SLOT(req_slot);',
                'rroot <= req_root; rtag <= req_tag; rsign <= req_sign; rslot <= `TL_SLOT(req_slot); rgroup <= ph == 1;')
    s = replace(s, 'assign rq_ntt = rn;  assign rq_data = rdat;  assign rq_slot = rslot;',
                'assign rq_ntt = rn;  assign rq_data = rdat;  assign rq_slot = rslot; assign rq_group = rgroup;')
    s = replace(s, 'assign rq_ntt = fire && ntt;  assign rq_data = req_data;  assign rq_slot = `TL_SLOT(req_slot);',
                'assign rq_ntt = fire && ntt;  assign rq_data = req_data;  assign rq_slot = `TL_SLOT(req_slot); assign rq_group = ph == 1;')
    s = replace(s, 'reg        rqd_ntt, rqd_5, rqd_slot, rqd_sign;', 'reg        rqd_ntt, rqd_5, rqd_slot, rqd_sign, rqd_group;')
    s = replace(s, 'rqd_slot <= rq_slot; rqd_sign <= rq_sign;', 'rqd_slot <= rq_slot; rqd_sign <= rq_sign; rqd_group <= rq_group;')
    s = replace(s, 'reg v1,v5,sc1;', 'reg v1,v5,sc1,group1;')
    s = replace(s, 'g1<=rqd_tag;sc1<=rqd_sign;', 'g1<=rqd_tag;sc1<=rqd_sign;group1<=rqd_group;')
    s = replace(s, 'wire [64:0]  lf;', '''wire [64:0]  lf;
    wire [131:0] raw_p;
    wire [31:0] packed_a [0:1], packed_b [0:1];''')
    s = replace(s, '.zh(mp), .a(la), .b(lb), .sa(lsa), .sb(lsb), .p(), .f(lf)',
                '.zh(1\'b0), .a(la), .b(lb), .sa(lsa), .sb(lsb), .p(raw_p), .f(lf)')
    s = replace(s, '''        wire [31:0] lfh = mp ? {lf[63:48], lf[31:16]} : lf[63:32];''',
                '''        // Each two-leaf stream keeps the baseline five-clock feedback latency.
        // Raw products emerge after LEAF clocks; bypass fusion using two alignment registers.
        wire [63:0] pp [0:1];
        wire [33:0] pth [0:1];
        wire final_group;
        tl_delay #(.W(1), .D(3*FUSE)) d_group (.clk(clk), .en(ce), .d(group1), .q(final_group));
        genvar pg;
        for (pg=0;pg<2;pg=pg+1) begin: packed_stream
            reg [2*FUSE:1] pv;
            reg [1:0] sel;
            wire [63:0] products = {raw_p[(2*pg+1)*33+:32],raw_p[(2*pg)*33+:32]};
            tl_delay #(.W(64), .D(2)) d_align (.clk(clk), .en(ce), .d(products), .q(pp[pg]));
            wire [31:0] lo = {pp[pg][47:32],pp[pg][15:0]};
            wire [31:0] hi = {pp[pg][63:48],pp[pg][31:16]};
            wire [1:0] nz = {|pp[pg][47:32],|pp[pg][15:0]};
            tl_delay #(.W(34), .D(2*FUSE)) d_th (.clk(clk), .en(ce), .d({nz,hi}), .q(pth[pg]));
            always @(posedge clk) begin
                if(rst) begin pv<=0;sel<=0;end
                else if(ce) begin
                    pv<={pv[2*FUSE-1:1],v1 && mp && group1==pg};
                    sel<=pv[2*FUSE-1] ? 2'd2 : pv[FUSE-1] ? 2'd1 : 2'd0;
                end
            end
            assign packed_a[pg]=sel==0 ? a1 : lo;
            assign packed_b[pg]=sel==0 ? w1 : sel==1 ? (ks[FUSE] ? qi1 : qi0) : (ks[2*FUSE] ? q1 : q0);
`ifndef SYNTHESIS
            always @(posedge clk) if(!rst && ce && mp &&
                ((pv[FUSE] && pv[2*FUSE]) || ((v1 && group1==pg) && (pv[FUSE] || pv[2*FUSE]))))
                $fatal(1,"packed stream multiplier collision");
`endif
        end
        wire [63:0] selected_pp = final_group ? pp[1] : pp[0];
        wire [31:0] lfh = mp ? {selected_pp[63:48],selected_pp[31:16]} : lf[63:32];''')
    s = replace(s, 'wire [33:0] th32;', 'wire [33:0] th32, th32_normal;\n        assign th32 = mp ? (final_group ? pth[1] : pth[0]) : th32_normal;')
    s = replace(s, '.d({lnz, lfh}), .q(th32)', '.d({lnz, lf[63:32]}), .q(th32_normal)')
    s = replace(s, 'if (!rst && ce && (mbz || v1 || vs[FUSE] || vs[2*FUSE]) && (A32 !== A32_ref || B32 !== B32_ref))',
                'if (!rst && ce && !mp && (mbz || v1 || vs[FUSE] || vs[2*FUSE]) && (A32 !== A32_ref || B32 !== B32_ref))')
    s = replace(s, 'lsb = mbz ? {1\'b0, msb, msb, 1\'b0} : 4\'d0;', '''lsb = mbz ? {1'b0, msb, msb, 1'b0} : 4'd0;
        if(mp && ARR32) begin
            la={packed_a[1],packed_a[0]};
            lb={packed_b[1],packed_b[0]};
            lsa=0;lsb=0;
        end''')
    # The alternative dedicated reducer cannot accept packed16; give these wires a defined value.
    s = replace(s, 'end else begin : g_ded32\n', 'end else begin : g_ded32\n        assign packed_a[0]=0; assign packed_a[1]=0; assign packed_b[0]=0; assign packed_b[1]=0;\n')
    s = '// PRIVATE packed4 candidate: two independent packed16 streams on all four existing leaves.\n' + s
    (rtl / 'tile_a.sv').write_text(s)
    s = (rtl / 'a_cg_fast.sv').read_text()
    s = replace(s, '(beat==0 && ph==1)', '(beat==0 && (ph==1 || (packed16 && ph==2)))')
    (rtl / 'a_cg_fast.sv').write_text(s)
    for name in ['planner.py','extra_cases.py','application.py','main.cpp']:
        shutil.copy2(BASE / name, HERE / name)
    s = (HERE / 'planner.py').read_text()
    s = replace(s, "a=2+per*(k*((1<<c['rj']) if fft else c['planes'])+part)",
                "seq=k*((1<<c['rj']) if fft else c['planes'])+part\n                    a=2+(3*(seq//2)+seq%2 if packed else per*seq)")
    # Keep the established period-3 alignment at stage boundaries; each stage starts on stream A.
    (HERE / 'planner.py').write_text(s)
    s = (HERE / 'application.py').read_text().replace('a_cg_z020_system160','a_cg_packed4')
    (HERE / 'application.py').write_text(s)
    print('PRIVATE_FORK_CREATED', HERE)


if __name__ == '__main__':
    main()
