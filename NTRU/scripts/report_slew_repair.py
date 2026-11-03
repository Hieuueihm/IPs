"""Audit the mapped-cell repair and publish its measured cost without rerunning STA."""
from collections import Counter
from decimal import Decimal
import json
import re
from arith_experiment_common import ROOT,check_hashes,hashes
from repair_stream_slew import block


def main():
    result_path=ROOT/'study/results/stream_slew_repair.json'
    result=json.loads(result_path.read_text())
    check_hashes(result['source_sha256']);check_hashes(result['baseline_result_sha256'])
    previous=json.loads((ROOT/'study/results/banked_stream_sta.json').read_text())['synthesis'][0]
    expected=Counter(previous['cell_types'])
    for edit in result['edits']:
        expected[edit['old_cell']]-=1;expected[edit['new_cell']]+=1
    net_path=ROOT/'study/build/stream_slew_repair'/f"{result['final']['label']}.v"
    net=net_path.read_text()
    actual=Counter(re.findall(r'^  (\w+) \w+ \($',net,re.M))
    assert +expected==actual,'unexpected cell count change'
    lib=(ROOT/'study/tools/stream_sta/NangateOpenCellLibrary_typical.lib').read_text()
    area=Decimal(0)
    for kind,count in actual.items():
        cell=block(lib,'cell',kind)
        area+=Decimal(re.search(r'\barea\s*:\s*([\d.]+)',cell)[1])*count
    final=result['final']
    assert abs(float(area)-final['cell_area_um2'])<1e-4
    assert sum(actual.values())==final['cells']
    assert actual['DFF_X1']==previous['ff_cells']==final['ff_cells']
    assert final['slew_violating_pins']==0 and final['overall']['slack_ns']>=0
    audit={'full_netlist_cell_count':sum(actual.values()),'library_area_sum_um2':str(area),
           'cell_count_matches_resize_only':True,'flipflop_count_unchanged':True,
           'source_sha256':hashes(['scripts/report_slew_repair.py','scripts/repair_stream_slew.py']),
           'evidence_sha256':hashes(['study/results/stream_slew_repair.json'])}
    (ROOT/'study/results/stream_slew_repair_audit.json').write_text(json.dumps(audit,indent=2)+'\n')
    baseline=result['iterations'][0]
    lines=['# Sửa slew của bản banked bằng tăng drive cục bộ','',
           'Ngày 26/10/2026. Đối chứng giữ nguyên RTL và netlist gốc; đây là bước sizing sau mapping trong Nangate45.',
           '', '## Kết quả', '',
           '| Chỉ tiêu | Banked gốc | Sau sửa |','|---|---:|---:|',
           f'| Pin vi phạm max-transition | {baseline["slew_violating_pins"]} | {final["slew_violating_pins"]} |',
           f'| Worst transition slack (ns) | {baseline["worst_transition_slack_ns"]:.4f} | Không vi phạm |',
           f'| Arrival register-to-register (ns) | {baseline["reg_to_reg"]["data_arrival_ns"]:.4f} | {final["reg_to_reg"]["data_arrival_ns"]:.4f} |',
           f'| Worst setup slack ở clock 10ns (ns) | {baseline["overall"]["slack_ns"]:.4f} | {final["overall"]["slack_ns"]:.4f} |',
           f'| Tổng cell area (mm²) | {result["baseline_cell_area_um2"]/1e6:.9f} | {final["cell_area_um2"]/1e6:.9f} |',
           f'| FF cell | {previous["ff_cells"]:,} | {final["ff_cells"]:,} |',
           '',f'Tăng **{final["area_delta_um2"]:.3f} µm²**, tương đương **{final["area_increase_percent"]:.5f}%** diện tích banked gốc.',
           '', '## Đã sửa gì và kiểm thế nào?', '',
           '110 pin gốc thuộc 10 net do NOR4_X1 điều khiển; báo cáo tính cả pin driver và các sink.',
           f'Có {len(result["edits"])} lần đổi cell, qua {len(result["iterations"])-1} vòng sizing/STA:', '']
    for pair,count in sorted(Counter((e['old_cell'],e['new_cell']) for e in result['edits']).items()):
        lines.append(f'- {count} cổng `{pair[0]}` → `{pair[1]}`.')
    lines+=['', 'Không thêm tầng, không đổi phép toán, precision, bit rounding, FIFO hoặc giao thức stall.',
            'Mỗi cặp cell được đối chiếu đầy đủ tên/hướng pin và hàm Boolean trong Liberty. Tất cả kết nối pin giữ nguyên.',
            'Đảo lại đúng các token tên loại cell phải khôi phục toàn bộ netlist gốc từng byte. Đây là chứng cứ tương đương',
            'logic zero-delay của phép sizing; không cần diễn giải kết quả số học khác đi để vượt kiểm tra.',
            '', 'Diện tích được kiểm tra độc lập bằng đếm mọi instance trong netlist đã sửa rồi cộng area từng cell từ Liberty.',
            'Số cell và FF khớp baseline sau các thay thế đã ghi. Không thay giới hạn slew hoặc nới clock/IO constraint.',
            '', '## Phạm vi kết luận', '',
            'Các kiểm tra setup và max-transition đạt trong mô hình **trước layout**, Nangate45 typical 1,1V/25°C,',
            'clock10ns, uncertainty0,1ns, IO delay0,2ns, output load5fF; giống bản gốc. Chưa xác nhận hold closure,',
            'placement, CTS, RC dây, corner signoff, SRAM hoặc FPGA. Kết quả này xử lý vấn đề sizing đã thấy trong',
            'flow tham chiếu; không phải một đóng góp kiến trúc mới hoặc chứng minh Fmax của chip.',
            '', 'RTL vẫn độc lập công nghệ. Với thư viện khác, cần thực hiện sizing/buffering tương ứng sau mapping.',
            'Các phần còn thiếu của full core trong [báo cáo trước](stream_core_results.md) vẫn giữ nguyên phạm vi.',
            '', '## Dữ liệu và chạy lại', '',
            '- [JSON sizing, equivalence và từng vòng STA](../study/results/stream_slew_repair.json).',
            '- [Audit toàn bộ số cell và diện tích](../study/results/stream_slew_repair_audit.json).',
            '- [Script sửa slew](../scripts/repair_stream_slew.py), [script audit/báo cáo](../scripts/report_slew_repair.py).',
            '', 'Trong WSL, đặt LD_LIBRARY_PATH và TCL_LIBRARY như [flow tham chiếu](stream_core_results.md#6-chạy-lại), rồi chạy:', '',
            '~~~sh','python3 scripts/repair_stream_slew.py','python3 scripts/report_slew_repair.py','~~~',
            '', 'Script giữ nguyên các artifact baseline, xuất netlist và log riêng vào `study/build/stream_slew_repair/`.']
    (ROOT/'docs/stream_slew_repair.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    note=('> Cập nhật sizing sau mapping: đã xử lý 110 pin vi phạm slew; '
          f'tăng {final["area_increase_percent"]:.5f}% cell area. '
          '[Kết quả và phạm vi kiểm tra](docs/stream_slew_repair.md).\n')
    p=ROOT/'ARCHITECTURE.md';content=p.read_text(encoding='utf-8')
    content=re.sub(r'^> Cập nhật sizing sau mapping:.*\n','',content,flags=re.M)
    anchor='> Đã có RTL ghép FFT64/128, routing bank, FIFO/stall và đo cell-area/STA Nangate45:\n'
    assert anchor in content
    content=content.replace(anchor,note+anchor)
    p.write_text(content,encoding='utf-8')
    p=ROOT/'docs/stream_core_results.md';content=p.read_text(encoding='utf-8')
    notice='> Cập nhật sau báo cáo này: [sizing cục bộ đã xử lý vi phạm slew](stream_slew_repair.md). Các số baseline bên dưới được giữ để so sánh.\n\n'
    content=re.sub(r'^> Cập nhật sau báo cáo này:.*\n\n','',content,flags=re.M)
    content=content.replace('Ngày 26/10/2026.',notice+'Ngày 26/10/2026.',1)
    p.write_text(content,encoding='utf-8')
    print(json.dumps({'final':final,'audit':audit},indent=2))


if __name__=='__main__':main()
