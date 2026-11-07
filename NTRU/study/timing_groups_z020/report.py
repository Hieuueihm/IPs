"""Summarize read-only timing queries on the retained 10 ns routed checkpoint."""
from pathlib import Path
import csv
import hashlib
import json
import re

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
B=ROOT/'study/build/a_cg_z020_100mhz'
P=B/'path_groups'
LABELS={
 'all_internal':'Đường xấu nhất toàn lõi: rounding host',
 'except_rounding':'Toàn lõi, bỏ nhóm rs_sum',
 'tile_all':'Mọi đường đến tile, gồm nạp cấu hình',
 'tile_to_tile':'Giữa các thanh ghi trong mảng tile',
 'fft_accumulator':'MAC/tích lũy FFT và chốt product limb',
 'fft_T':'Ghép tích phức FFT: wps / t5',
 'operand_stage':'Tầng toán hạng / cộng-trừ đầu vào tile',
 'fft_limb_sums':'Tổng hai thành phần FFT / bộ nhớ tổng',
 'montgomery':'Các thanh ghi u32 / r32r của Montgomery',
 'multiplier':'Mảng nhân, ghép tích và thanh ghi lá',
 'tile_response':'Chốt dữ liệu/tag/valid đầu ra tile',
 'bank_to_tile':'Dữ liệu BRAM → req_x/req_y',
 'host_read_select':'Dữ liệu BRAM → dòng đọc host',
 'host_line_capture_all':'Mọi nguồn → dòng đọc host',
 'host_shift':'Bộ dịch/đường ra → FF phản hồi host',
 'data_bank_write':'Đầu vào bank dữ liệu (địa chỉ/data/enable)',
 'root_load':'Đầu vào root BRAM (load/địa chỉ/enable)',
 'root_to_tile':'Dữ liệu root BRAM → các đích trong tile',
 'program_broadcast':'Chương trình FFT → thanh ghi chương trình tile',
 'context_config':'Nạp q/qprime/format/mode vào tile',
 'reset_from_frontend':'Reset frontend → các thanh ghi trong lõi',
}

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    for file,marker in [('console.log','TIMING_GROUP_INSPECTION_DONE'),('supplement_console.log','TIMING_GROUP_SUPPLEMENT_DONE')]:
        log=(HERE/file).read_text(errors='replace')
        assert marker in log and 'ERROR:' not in log,file
    log=(HERE/'console.log').read_text(errors='replace')
    assert 'ORIGINAL_TIMING_REPRODUCED setup=0.032 hold=0.051' in log
    rows={}
    for name in ('groups.tsv','groups_supplement.tsv'):
        for r in csv.DictReader((P/name).open(),delimiter='\t'):rows[r['group']]=r
    assert len(rows)==21
    groups=[]
    for key,r in rows.items():
        assert r['slack_ns'] not in ('NONE','NO_PATH'),r
        report=P/f'{key}.rpt'
        s=report.read_text(errors='replace')
        m=re.search(r'Data Path Delay:\s*([\d.]+)ns\s*\(logic ([\d.]+)ns.*?route ([\d.]+)ns',s)
        assert m,report
        slack=float(r['slack_ns'])
        first=float(re.search(r'Slack \((?:MET|VIOLATED)\)\s*:\s*([-\d.]+)ns',s)[1])
        assert abs(first-slack)<.002,(key,slack,first)
        groups.append(dict(group=key,label=LABELS[key],source_cell_count=int(r['sources']),destination_cell_count=int(r['endpoints']),
            slack_ns=slack,logic_levels=int(r['logic_levels']),source=r['startpoint'],destination=r['endpoint'],
            data_delay_ns=float(m[1]),logic_delay_ns=float(m[2]),route_delay_ns=float(m[3]),
            report=report.relative_to(ROOT).as_posix()))
    assert next(g for g in groups if g['group']=='all_internal')['slack_ns']==.032
    assert next(g for g in groups if g['group']=='except_rounding')['slack_ns']==.206
    for n in ('a_cg_fast.sv','tile_a.sv','mul_ss.v'):
        assert (ROOT/'experiments/a_cg_z020_100mhz/rtl'/n).read_bytes()==(B/'rtl_run'/n).read_bytes()
    files=[HERE/'inspect.tcl',HERE/'supplement.tcl',HERE/'report.py',B/'route10/routed.dcp',B/'route10/run_config.txt',
        B/'route10/metrics.txt',P/'groups.tsv',P/'groups_supplement.tsv']+[P/f"{g['group']}.rpt" for g in groups]
    result=dict(part='xc7z020clg400-2',clock_ns=10,HD_CLK_SRC='BUFGCTRL_X0Y16',
        kind='read-only timing group analysis of existing routed checkpoint',
        baseline_setup_reproduced_ns=.032,baseline_hold_reproduced_ns=.051,
        RTL_changed=False,netlist_optimized=False,placement_or_routing_rerun=False,
        groups=groups,scope_notes=[
            'Groups overlap; the minimum of each group is reported. Counts are cells, not timing endpoint pins.',
            'All queries retain original clock, uncertainty and I/O timing; no path exceptions or case analysis.',
            'Data-bank and root-bank input groups include control/address/data paths to the BRAM cells.',
            'Results describe this 10 ns routed implementation, not a fresh implementation at 125/150/178 MHz.',
            'No mode-dependent path is declared false or exempted from timing.'],
        sha256={p.relative_to(ROOT).as_posix():sha(p) for p in files})
    out=ROOT/'study/results/z020_100mhz_timing_groups'
    out.with_suffix('.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    rows=['# Timing các nhóm đường trên bản Z020 dưới 30k LUT','',
        'Ngày 04/11/2026. Đọc lại checkpoint `a_cg_z020_100mhz/route10/routed.dcp`, clock 10 ns.',
        'Đã khôi phục đúng `HD.CLK_SRC=BUFGCTRL_X0Y16` và tái lập setup +0,032 ns, hold +0,051 ns trước khi truy vấn.',
        'Không đổi RTL, không tối ưu netlist hoặc chạy lại placement/routing, không thêm ngoại lệ timing.','',
        '## Kết luận','',
        'Rounding host là đường xấu nhất, nhưng các nhóm reset, nạp context/root và cộng-trừ tile cũng còn ít margin.',
        'Bỏ riêng các đích rs_sum khỏi truy vấn thì setup xấu nhất vẫn chỉ +0,206 ns. Vì vậy không thể suy ra rằng chỉ',
        'sửa rounding là lõi sẽ đạt lại 150–178 MHz. Bộ nhân và MAC FFT có nhiều margin hơn các nhóm trên.','',
        '## Đường xấu nhất của từng nhóm','',
        'Các nhóm chồng lấp nhau, không cộng số lượng giữa các nhóm. Các số dưới đây là setup slack tại 10 ns.',
        'Một nhóm đo đến các thanh ghi có tên toán học vẫn có thể bị giới hạn bởi tín hiệu chọn/địa chỉ/enable của khối đó.','',
        '| Nhóm | Slack | Trễ dữ liệu | Logic | Routing | Mức logic |',
        '|---|---:|---:|---:|---:|---:|']
    broad={'except_rounding','tile_all','tile_to_tile'}
    for g in sorted((x for x in groups if x['group'] not in broad),key=lambda x:x['slack_ns']):
        rows.append(f"| [{g['label']}](../{g['report']}) | {g['slack_ns']:+.3f} ns | {g['data_delay_ns']:.3f} ns | {g['logic_delay_ns']:.3f} ns | {g['route_delay_ns']:.3f} ns | {g['logic_levels']} |")
    rows+=['','## Các truy vấn bao quát','']
    for g in (x for x in groups if x['group'] in broad):
        rows.append(f"- {g['label']}: **{g['slack_ns']:+.3f} ns**, `{g['source']}` → `{g['destination']}`.")
    rows+=['','## Phải đọc kết quả thế nào?','',
        '1. **Rounding:** chuỗi carry dài là một nguyên nhân thật ở RTL. Khối này có phần lớn trễ nằm ở logic.',
        '2. **Reset, hằng số, root và phát chương trình:** nhiều đường có rất ít logic nhưng routing dài. Đó là độ trễ',
        '   của bố trí/nối dây hiện tại; không có nghĩa các phép toán này tự cần 9 ns. Chúng vẫn phải đóng timing, dù chỉ',
        '   hoạt động lúc cấu hình hoặc khởi động.',
        '3. **Trong tile:** còn các đường cộng/trừ và chọn dữ liệu sát ngưỡng. Mảng DSP không phải đại diện cho toàn bộ',
        '   thời gian của butterfly; các khối chuẩn bị và ghép kết quả cũng phải tính.',
        '4. **Fmax:** công cụ đã thực hiện implementation với mục tiêu 10 ns. Nhiều đường chỉ được rút ngắn đủ để đạt',
        '   mục tiêu này. Không quy trực tiếp slack trong bản route này thành giới hạn tần số tối đa của kiến trúc.',
        '5. **Hold:** toàn bộ đường nội bộ vẫn có hold tối thiểu +0,051 ns theo checkpoint gốc. Bảng ở trên là setup,',
        '   không dùng nó để kết luận về hold ở một clock khác. Các cổng I/O OOC vẫn cần timing tích hợp riêng.','',
        '## Startpoint và endpoint cụ thể','']
    for g in sorted(groups,key=lambda x:x['slack_ns']):
        rows += [f"### {g['label']}", '',f"`{g['source']}` → `{g['destination']}`.",
            f"Slack {g['slack_ns']:+.3f} ns; {g['logic_levels']} mức logic. [Ba đường chậm nhất của nhóm](../{g['report']}).",'']
    rows+=['[JSON kết quả và hash đầu vào](../study/results/z020_100mhz_timing_groups.json).','']
    (ROOT/'docs/timing_cac_khoi_z020_100mhz.md').write_text('\n'.join(rows),encoding='utf-8')
    print('TIMING_GROUP_REPORT_PASS: 21 groups; original timing reproduced; no RTL or implementation changes.')
    for g in sorted(groups,key=lambda x:x['slack_ns']):print(f"{g['group']}: {g['slack_ns']:+.3f} ns; logic {g['logic_delay_ns']:.3f}; route {g['route_delay_ns']:.3f}")

if __name__=='__main__':main()
