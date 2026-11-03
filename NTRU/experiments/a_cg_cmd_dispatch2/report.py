"""Report isolated two-stage delivery, without claiming OOC I/O hold closure."""
from pathlib import Path
import hashlib
import importlib.util
import json
import re

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
B=ROOT/'study/build/a_cg_cmd_dispatch2'
R=B/'route'
sp=importlib.util.spec_from_file_location('helpers',ROOT/'experiments/a_cg_control_gate/report.py')
helpers=importlib.util.module_from_spec(sp);sp.loader.exec_module(helpers)
prior=helpers.prior
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    sp=importlib.util.spec_from_file_location('gate',HERE/'validate.py')
    gate=importlib.util.module_from_spec(sp);sp.loader.exec_module(gate);gate.main()
    validation=json.loads((B/'validation.json').read_text())
    log=prior.read(B/'implementation_cold_console.log')
    assert 'CONTROL_IMPLEMENT_DONE' in log and 'ERROR:' not in log
    metrics=dict(re.findall(r'^(\w+)=([-\d.]+)\s*$',prior.read(R/'metrics.txt'),re.M))
    for key,n in [('ROOT_RAMB18',16),('DATA_RAMB18',32),('DSP48',64),('BLACKBOX',0),('LOCAL_RESETS',16),('LOCAL_CONFIGS',16)]:
        assert int(metrics[key])==n,(key,metrics[key])
    resource=prior.resource(R/'util.rpt');full=prior.summary(R/'timing.rpt')
    internal=dict(WNS_ns=float(metrics['REGISTER_TO_REGISTER_WNS_NS']),WHS_ns=float(metrics['REGISTER_TO_REGISTER_WHS_NS']))
    execution=dict(WNS_ns=float(metrics['EXECUTION_CORE_WNS_NS']),WHS_ns=float(metrics['EXECUTION_CORE_WHS_NS']))
    setup_met='Slack (VIOLATED)' not in prior.read(R/'internal_setup.rpt')
    hold_met='Slack (VIOLATED)' not in prior.read(R/'internal_hold.rpt')
    counts={m[1].strip(' .'):int(m[2]) for m in re.finditer(r'# of\s+(.+?)\s*:\s*(\d+)',prior.read(R/'route_status.rpt'))}
    assert counts['fully routed nets']==counts['routable nets'] and counts['nets with routing errors']==0
    drc=[dict(rule=a,severity=b,description=c.strip(),count=int(d)) for a,b,c,d in re.findall(
        r'^\|\s*(\S+)\s*\|\s*(Warning|Critical Warning|Error)\s*\|\s*([^|]+)\|\s*(\d+)\s*\|',prior.read(R/'drc.rpt'),re.M)]
    assert drc and not any(x['severity'] in ('Error','Critical Warning') for x in drc)
    parent=json.loads((ROOT/'study/results/a_cg_cmd_frontreserve.json').read_text())
    result=dict(kind='two command stages plus registered read response: actual OOC P&R',clock_ns=5,
        part='xczu7ev-ffvc1156-2-e',resource=resource,synthesis_resource=validation['synthesis_resource'],
        internal_timing=internal,execution_core_only_timing=execution,full_boundary_timing=full,
        internal_200MHz_setup_hold_pass=internal['WNS_ns']>=0 and internal['WHS_ns']>=0 and setup_met and hold_met,
        whole_boundary_200MHz_setup_hold_pass=full['WNS_ns']>=0 and full['WHS_ns']>=0,
        internal_setup_report_met=setup_met,internal_hold_report_met=hold_met,
        internal_setup_paths=helpers.paths(R/'internal_setup.rpt'),internal_hold_paths=helpers.paths(R/'internal_hold.rpt'),
        execution_setup_paths=helpers.paths(R/'execution_setup.rpt'),
        validation=validation,parent=dict(name='a_cg_cmd_frontreserve',resource=parent['resource'],internal_timing=parent['internal_timing']),
        route_status_counts=counts,drc_rules=drc,production_RTL_changed=False,retained_baseline_changed=False,
        command_capture_stages=2,read_response_stages_added=1,arithmetic_RTL_changed=False,
        kernel_cycles_unchanged=True,place_directive='AltSpreadLogic_high',route_directive='RuntimeOptimized',
        latency_vs_parent=dict(main_command_delivery_extra_clocks=1,root_descriptor_extra_latency=1,
            root_descriptor_throughput_words_per_clock=1,main_command_min_spacing=3,
            read_response_extra_clocks=1,total_per_transform='2*ceil(words/4)+3 clocks'),
        limitations=['Full host and root storage included; no board or partition pin placement.',
            'Added stages do not repair the unmodelled external port-to-first-register route.',
            'Parent worst external hold path had 0 ns data delay and unset routing, with min input delay 0 ns.',
            'All original clock, max/min I/O delays and uncertainty constraints are retained.',
            'Actual host clock/data integration is required to close and validate the interface.',
            'No post-route simulation or board run; PQC checks establish reference agreement for the tested cases.'])
    artifacts=[HERE/'manifest.json',HERE/'build.py',HERE/'validate.py',HERE/'report.py',HERE/'implement_cold.tcl',
        HERE/'tb_pipeline_reset.sv',HERE/'run_pipeline_reset.ps1',B/'pipeline_reset.log',
        B/'validation.json',B/'implementation_cold_console.log']
    artifacts += [B/'synth'/n for n in ('dispatch_barrier.txt','reservation_permission.txt','frontend_reset_barrier.txt','command_barrier.txt')]
    artifacts += [R/n for n in ('routed.dcp','util.rpt','util_hier.rpt','timing.rpt','internal_setup.rpt','internal_hold.rpt',
        'execution_setup.rpt','execution_hold.rpt','reset_feed.rpt','reset_tree.rpt','config_boundary.rpt',
        'route_status.rpt','drc.rpt','metrics.txt','constraints.xdc','run_config.txt')]
    result['sha256']={p.relative_to(ROOT).as_posix():sha(p) for p in artifacts}
    out=ROOT/'study/results/a_cg_cmd_dispatch2'
    out.with_suffix('.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    verdict='ĐẠT' if result['internal_200MHz_setup_hold_pass'] else 'CHƯA ĐẠT'
    lines=['# Kết quả thêm pipeline lệnh và trả dữ liệu đọc','',f'**Timing thanh ghi nội bộ tại 200 MHz: {verdict}.**','',
        '| Bản P&R | LUT | FF | Setup WNS | Hold |','|---|---:|---:|---:|---:|']
    for name,a,t in [('Baseline frontreserve',parent['resource'],parent['internal_timing']),('Dispatch2',resource,internal)]:
        lines.append(f"| {name} | {a['LUT']:,} | {a['FF']:,} | {t['WNS_ns']:+.3f} ns | {t['WHS_ns']:+.3f} ns |")
    lines+=['',f"DSP/RAMB18: {resource['DSP']}/{resource['RAMB18']}, gồm 16 root và 32 bank dữ liệu.",
        f"Timing toàn biên OOC: setup {full['WNS_ns']:+.3f} ns, hold {full['WHS_ns']:+.3f} ns.",'',
        '## Thay đổi RTL','',
        'Thêm một tầng chuyển lệnh: dữ liệu, địa chỉ và token của mọi loại lệnh cùng đi qua thanh ghi thứ hai.',
        'Giữ chỗ cho lệnh đang nằm trong cả hai tầng, ngăn cấu hình hoặc start vượt qua lệnh trước.',
        'Thêm một tầng cho cặp read_data/read_rsp_valid, xóa token khi reset hoặc reset trễ đang hoạt động.',
        'Busy bao phủ cả hai tầng start. RTL số học trong tile và bộ nhân giữ nguyên từng byte.','',
        '## Độ trễ và kiểm tra','',
        'Số chu kỳ kernel giữ nguyên. So với baseline frontreserve: mỗi lệnh chính giao chậm thêm một clock,',
        'mỗi kết quả đọc chậm thêm một clock; khoảng cách tối thiểu giữa lệnh chính từ 2 lên 3 clock.',
        'Root/descriptor thêm một clock trễ nhưng vẫn nhận một từ mỗi clock.',
        'Tổng chi phí trên mỗi transform tăng 2*ceil(words/4)+3 clock, kiểm tra trên toàn bộ 1.026 ca.',
        'Qua 1.026 vector, 38 ca bốn trạng thái, 12 nhóm reset, 74 lần gọi transform từ C và 4 xác minh chữ ký.',
        '14 artifact ứng dụng giống bản C tham chiếu; 2 đầu vào sai bị từ chối. Packed16 được giữ.',
        'Netlist xác nhận không có đường bỏ qua tầng chuyển lệnh hoặc tầng trả dữ liệu đọc.','',
        '## Giới hạn I/O','',
        'Không được hiểu thêm pipeline là đã sửa lỗi hold ngay tại chân OOC. Đường desc_stage[2] tới',
        'thanh ghi đầu tiên của baseline có trễ dữ liệu được mô hình là 0 ns vì cổng chưa được route.',
        'Tầng pipeline mới nằm sau thanh ghi đó. Cần tích hợp nguồn phát dữ liệu và clock thực tế để',
        'kiểm tra lại giao tiếp; không nới ràng buộc và không thêm ngoại lệ timing trong thử nghiệm này.',
        'RTL chính và baseline đã chọn chưa đổi; chưa chạy board hoặc tạo bitstream.','',
        '## Đường setup nội bộ chậm nhất','', '```json',json.dumps(result['internal_setup_paths'][:3],indent=2),'```','']
    out.with_suffix('.md').write_text('\n'.join(lines),encoding='utf-8')
    print(json.dumps({k:result[k] for k in ('resource','internal_timing','full_boundary_timing','internal_200MHz_setup_hold_pass')},indent=2))

if __name__=='__main__': main()
