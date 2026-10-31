"""Audit evidence and publish the full-island reference measurements in Markdown."""
import hashlib
import json
import re
from arith_experiment_common import ROOT,check_hashes,hashes

RESULTS=ROOT/'study/results'
BUILD=ROOT/'study/build/stream_sta'


def main():
    evidence={}
    for name in ('flex_stream_validation','banked_stream_validation','ntt_banked_supply','stream_sta','banked_stream_sta'):
        obj=json.loads((RESULTS/(name+'.json')).read_text())
        check_hashes(obj['source_sha256'])
        evidence[name]=obj
    rows=evidence['stream_sta']['synthesis']+evidence['banked_stream_sta']['synthesis']
    audits=[]
    for row in rows:
        check_hashes(row['rtl_sha256'])
        top=row['top'];net=BUILD/(top+'.v');sta_net=BUILD/(top+'_sta.v')
        assert hashlib.sha256(net.read_bytes()).hexdigest()==row['netlist_sha256']
        assert hashlib.sha256(sta_net.read_bytes()).hexdigest()==row['sta_netlist_sha256']
        log=(BUILD/(top+'_sta.log')).read_text()
        assert not re.search(r'^Error:',log,re.M)
        # All untimed endpoints must be directly constant-driven ports.
        text=sta_net.read_text();constants=set()
        pattern=r"assign\s+(\w+)(?:\[(\d+)(?::(\d+))?\])?\s*=\s*\d+'b([01]+);"
        for port,hi,lo,value in re.findall(pattern,text):
            if hi:
                for bit in range(int(lo or hi),int(hi)+1):constants.add(f'{port}[{bit}]')
            else:constants.add(port)
        found=re.search(r'Warning: There (?:are|is) \d+ unconstrained endpoints?\.\n((?:  [^\n]+\n)+)',log)
        endpoints=found[1].split() if found else []
        assert all(e in constants for e in endpoints),(top,[e for e in endpoints if e not in constants])
        assert 'no clock' not in log.lower() and 'combinational loop' not in log.lower()
        # Preserve source-level FF endpoints to identify the real bottleneck.
        original=net.read_text();points={}
        for key in ('startpoint','endpoint'):
            instance=row['reg_to_reg'][key].split()[0]
            match=re.search(r'\bDFF_X1 '+re.escape(instance)+r' \(([\s\S]*?)\n  \);',original)
            if match:
                q=re.search(r'\.Q\((.*?)\)',match[1])
                points[key+'_q']=q[1] if q else ''
        suffix=log.split('END_OVERALL',1)[1].strip()
        slew=re.findall(r'^\S+\s+(\d+\.\d+)\s+(\d+\.\d+)\s+(-?\d+\.\d+)\s+\(VIOLATED\)',suffix,re.M)
        audits.append({'top':top,'constant_unconstrained_endpoints':len(endpoints),
                       'max_transition_report_empty':not suffix,
                       'max_transition_violating_pins':len(slew),
                       'max_transition_worst_reported_slack_ns':min((float(v[2]) for v in slew),default=0),
                       'transition_report_decimal_digits':2,'critical_ff_signals':points})
    index={r['top']:r for r in rows}
    def increase(a,b):return 100*(index[a]['cell_area_um2']/index[b]['cell_area_um2']-1)
    overhead={'stall_vs_plain_percent':increase('stream_stall','stream_plain'),
              'queue_vs_stall_percent':increase('stream_buffered','stream_stall'),
              'bank_route_vs_buffered_percent':increase('flex_stream_banked','stream_buffered'),
              'complete_vs_plain_percent':increase('flex_stream_banked','stream_plain')}
    summary={'overheads':overhead,'sta_audit':audits,'source_sha256':hashes(['scripts/report_stream_results.py']),
             'evidence_sha256':hashes([f'study/results/{name}.json' for name in evidence])}
    (RESULTS/'stream_core_summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    labels={'stream_plain':'Mảng, không stall/queue','stream_stall':'Mảng + global stall',
            'stream_buffered':'+ queue hai phần tử','flex_stream_banked':'+ gather/scatter bank'}
    table=['| Cấu hình | Cell area (mm²) | FF cell | Arrival R→R (ns) | Worst setup slack @10ns (ns) |',
           '|---|---:|---:|---:|---:|']
    for r in rows:
        table.append(f'| {labels[r["top"]]} | {r["cell_area_um2"]/1e6:.6f} | {r["ff_cells"]:,} | {r["reg_to_reg"]["data_arrival_ns"]:.4f} | {r["overall"]["slack_ns"]:.4f} |')
    table+=['',f'Global stall tăng area {overhead["stall_vs_plain_percent"]:.2f}%; queue tăng thêm '
            f'{overhead["queue_vs_stall_percent"]:.2f}%; gather/scatter tăng thêm '
            f'{overhead["bank_route_vs_buffered_percent"]:.2f}% so với bản buffered. Toàn bản banked tăng '
            f'{overhead["complete_vs_plain_percent"]:.2f}% so với mảng không stall/queue.',
            '', 'Arrival R→R gồm clock-to-Q và logic đến D, chưa cộng setup. Slack có tính setup và uncertainty.',
            'Các endpoint không được timing đều là cổng nối hằng, đã kiểm trong netlist; reset được loại có chủ đích.',
            'Ba bản chưa có bank router không có vi phạm max-transition trong log. Bản banked còn '
            f'{audits[-1]["max_transition_violating_pins"]} pin vi phạm slew; log làm tròn cho thấy transition0,21ns so với limit0,20ns '
            '(worst reported slack −0,01ns). Đây là số pin, không phải số net độc lập. '
            '**Chưa đóng timing về điện; cần sửa buffer/drive/fanout rồi đo lại.** '
            'Không xem setup slack dương hoặc arrival thấp hơn của bản banked là bằng chứng routing tăng Fmax.',
            '', '[JSON ba đối chứng](../study/results/stream_sta.json), [JSON banked](../study/results/banked_stream_sta.json),',
            '[audit và phần trăm overhead](../study/results/stream_core_summary.json).',
            'Bản banked dùng cùng map/buffer/size flow, thêm cleanup node dangling trước ABC buffer;',
            're-export cho OpenSTA được kiểm không đổi số lượng từng loại cell vật lý.']
    p=ROOT/'docs/stream_core_results.md';content=p.read_text(encoding='utf-8')
    start='<!-- STA_TABLE -->';end='<!-- END_STA_TABLE -->'
    replacement=start+'\n\n'+'\n'.join(table)+'\n\n'+end
    if end in content:content=re.sub(re.escape(start)+r'[\s\S]*?'+re.escape(end),lambda _:replacement,content)
    else:content=content.replace(start,replacement)
    p.write_text(content,encoding='utf-8')
    p=ROOT/'ARCHITECTURE.md';content=p.read_text(encoding='utf-8')
    heading='## 16. Ghép FFT rộng, cấp bank NTT và đo toàn mảng'
    following_sections=''
    if heading in content:
        before,rest=content.split(heading,1)
        for next_heading in re.finditer(r'^## (\d+)\. ',rest,re.M):
            if int(next_heading[1])>16:
                following_sections=rest[next_heading.start():];break
        content=before.rstrip()+'\n'
    banked=index['flex_stream_banked']
    content+='\n'+heading+'\n\n'+f'''[Báo cáo chi tiết](docs/stream_core_results.md), [kiểm chứng](study/results/flex_stream_validation.json),
[banked RTL](study/results/banked_stream_validation.json), [số đo](study/results/stream_core_summary.json).

Đã triển khai prototype 16 tile × bốn leaf16. Cùng mảng cho 16 tích FFT32, bốn FFT64
hoặc một FFT128 mỗi giao dịch; đây là tích thực, chưa là butterfly FFT phức đầy đủ.
Chọn dấu ở limb cao, raw65, ghép modulo96/192 bit và rounding cuối từng tích.
FFT128 giữ Q64.64 R8; FFT32/64 hiện là contract tự định nghĩa, chưa so reference thấp precision.

22.724 giao dịch mảng không sai khác; 19.968 tích RTL đưa lại bốn kernel FFT/iFFT C R8
N512/N1024, khớp 3.072 word. Có 16.217 chu kỳ output stall và 1.000 giao dịch đổi cấu hình nhanh.
Không dùng kết quả này để nói đã thay full core phần cứng vào signer.

64 data-bank 16 bit 1R+1W, XOR bank map và thứ tự tầng lẻ theo bank cấp được 16 nhóm
hai tầng mỗi lượt. 16 root-bank 48 bit lưu bundle ba root; tốn gần 1,5× bảng phẳng mỗi chiều.
28 transform case không xung đột; gather/array/scatter RTL khớp 376 lượt NTT trong 1.328
giao dịch mixed. RAM row generator, root RAM và stage controller vẫn là model/host.
Mode0 cần 128 hệ số/cycle nên không được nuôi đủ bởi 64 bank; N8 chỉ dùng hai trong 16 tile.

Nangate45 typical, trước layout, cell area toàn banked {banked['cell_area_um2']/1e6:.6f} mm²,
arrival R→R {banked['reg_to_reg']['data_arrival_ns']:.4f}ns và setup slack {banked['overall']['slack_ns']:.4f}ns ở clock10ns.
Gồm routing logic, compact reducer, fusion, queue và global stall; chưa SRAM/CTS/wire RC/power.
Toàn bản banked tăng area {overhead['complete_vs_plain_percent']:.2f}% so với mảng không stall/queue.
Banked còn {audits[-1]['max_transition_violating_pins']} pin vi phạm slew (log làm tròn: worst −0,01ns), chưa đóng timing về điện.
Không dùng arrival thấp hơn sau mapping để kết luận thêm routing làm tăng Fmax.
Đây là chi phí cấu hình trong cùng thiết kế, chưa chứng minh thắng các core FFT/NTT chuyên dụng.

Giữ hướng radix-2 một/hai tầng và exact fusion. Chưa khóa 16 tile; bước full-core cần
RAM/controller có hazard handling, FFT complex butterfly/normalization và NTT C differential,
rồi đo FPGA hoặc physical implementation ở target cụ thể.
'''
    if following_sections:content+='\n'+following_sections
    p.write_text(content,encoding='utf-8')
    print(json.dumps(summary,indent=2))


if __name__=='__main__':main()
