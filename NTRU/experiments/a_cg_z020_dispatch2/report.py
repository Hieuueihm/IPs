"""XC7Z020 synthesis resources; timing remains an estimate until P&R."""
from pathlib import Path
import hashlib
import importlib.util
import json
import re

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
B=ROOT/'study/build/a_cg_z020_dispatch2'
S=B/'synth'
sp=importlib.util.spec_from_file_location('prior',ROOT/'experiments/a_cg_timing/report.py')
prior=importlib.util.module_from_spec(sp);sp.loader.exec_module(prior)
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def resource(p):
    s=p.read_text()
    def value(label):
        m=re.search(r'^\|\s*(?:'+label+r')\*?\s*\|\s*(\d+)\s*\|',s,re.M)
        assert m,(p,label)
        return int(m[1])
    return dict(LUT=value('Slice LUTs|CLB LUTs'),FF=value('Slice Registers|CLB Registers'),
                DSP=value('DSPs'),RAMB18=value('RAMB18'),RAMB36=value('RAMB36/FIFO'))

def main():
    manifest=json.loads((HERE/'manifest.json').read_text())
    for p,h in {**manifest['source_sha256'],**manifest['byte_identical_source']}.items():
        assert sha(ROOT/p)==h,p
    for evidence in (manifest['functional_evidence'],manifest['parent_manifest']):
        assert sha(ROOT/evidence['path'])==evidence['sha256']
    for n in ('mul_ss.v','tile_a.sv','a_cg_fast.sv'):
        assert (HERE/'rtl'/n).read_bytes()==(ROOT/'experiments/a_cg_cmd_dispatch2/rtl'/n).read_bytes()
    log=(B/'synthesis_console.log').read_text()
    assert 'CONTROL_SYNTH_DONE' in log and 'ERROR:' not in log
    assert 'TARGET_PART=xc7z020clg400-2' in log
    metrics=dict(re.findall(r'^(\w+)=([-\d.]+)\s*$',(S/'metrics.txt').read_text(),re.M))
    for k,n in [('DSP48',64),('ROOT_RAMB18',16),('DATA_RAMB18',32),('BLACKBOX',0),('LOCAL_RESETS',16),('LOCAL_CONFIGS',16)]:
        assert int(metrics[k])==n,(k,metrics[k])
    assert 'DIRECT_INPUT_TO_CORE_PATHS=0' in (S/'command_barrier.txt').read_text()
    for token in ('FIRST_STAGE_TO_CORE_BYPASS=0','CORE_TO_READ_RESPONSE_BYPASS=0'):
        assert token in (S/'dispatch_barrier.txt').read_text(),token
    r=resource(S/'util.rpt')
    capacity=dict(LUT=53200,FF=106400,DSP=220,RAMB36=140,RAMB18_equivalent=280)
    usage=dict(LUT=100*r['LUT']/capacity['LUT'],FF=100*r['FF']/capacity['FF'],
               DSP=100*r['DSP']/capacity['DSP'],BRAM_equivalent=100*(r['RAMB36']+r['RAMB18']/2)/capacity['RAMB36'])
    validation=json.loads((ROOT/manifest['functional_evidence']['path']).read_text())
    previous=json.loads((ROOT/'study/results/a_cg_cmd_dispatch2.json').read_text())
    result=dict(part=manifest['part'],clock_ns=5,kind='OOC synthesis only, full host/root included',resource=r,
        device_capacity=capacity,device_usage_percent=usage,full_boundary_timing_estimate=prior.summary(S/'timing.rpt'),
        internal_timing_estimate=dict(WNS_ns=float(metrics['REGISTER_TO_REGISTER_WNS_NS']),WHS_ns=float(metrics['REGISTER_TO_REGISTER_WHS_NS'])),
        critical_setup_path=prior.path(S/'internal_setup.rpt'),
        primitives=dict(DSP='DSP48E1',BRAM='RAMB18E1'),
        arithmetic_RTL_changed=False,production_RTL_changed=False,RTL_byte_identical_to='a_cg_cmd_dispatch2',
        functional_evidence_reused_for_identical_RTL=validation,
        reference_other_device=dict(part='xczu7ev-ffvc1156-2-e',resource=previous['synthesis_resource'],kind='synthesis only for this comparison'),
        capacity_source='https://docs.amd.com/api/khub/documents/juMnxca71Tf2gfjmNyjM8A/content',
        LUT_goal=30000,LUT_reduction_needed=max(0,r['LUT']-30000),
        routed=False,board_tested=False,timing_200MHz_confirmed=False,
        notes=['This measurement is on XC7Z020, not a scaled estimate from ZCU106.',
            '5 ns synthesis timing is an estimate; no routed timing result exists for this part.',
            'The external OOC hold limitations persist; pipeline stages do not define a real host/clock interface.',
            'Host adapter and root cache included; PS/AXI subsystem, DMA and board clock/pins are not included.',
            'No precision reduction or cycle change; earlier PQC results apply to identical RTL, not a post-map hardware test.'])
    artifacts=[HERE/'prepare.py',HERE/'manifest.json',HERE/'synth.tcl',HERE/'report.py',B/'synthesis_console.log']
    artifacts += [S/n for n in ('synthesized.dcp','util.rpt','util_hier.rpt','timing.rpt','metrics.txt','internal_setup.rpt','internal_hold.rpt','command_barrier.txt','dispatch_barrier.txt')]
    result['sha256']={p.relative_to(ROOT).as_posix():sha(p) for p in artifacts}
    out=ROOT/'study/results/a_cg_z020_dispatch2'
    out.with_suffix('.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    rows=['# Synth trên XC7Z020-CLG400-2','',
        '**Chỉ synth tại 5 ns; chưa P&R, chưa xác nhận chạy 200 MHz trên chip này.**','',
        '| Tài nguyên | Synth toàn core | Chip có | Tỷ lệ |','|---|---:|---:|---:|']
    for label,k,limit,percent in [('LUT','LUT',53200,'LUT'),('FF','FF',106400,'FF'),('DSP','DSP',220,'DSP')]:
        rows.append(f"| {label} | {r[k]:,} | {limit:,} | {usage[percent]:.1f}% |")
    rows += [f"| BRAM36 quy đổi | {r['RAMB36']+r['RAMB18']/2:g} | 140 | {usage['BRAM_equivalent']:.1f}% |",'',
        f"Thực tế dùng {r['RAMB18']} RAMB18E1 và {r['RAMB36']} RAMB36. DSP được ánh xạ sang DSP48E1.",
        f"Timing nội bộ ước tính sau synth: setup {result['internal_timing_estimate']['WNS_ns']:+.3f} ns; hold {result['internal_timing_estimate']['WHS_ns']:+.3f} ns.",'',
        'Đường setup chậm nhất đi qua cộng/trừ trong tile; pipeline host chưa cắt đường này.',
        '```json',json.dumps(result['critical_setup_path'],indent=2),'```','',
        '## Phạm vi','',
        'RTL là bản sao từng byte của dispatch2 đã kiểm packed16, FFT32/64/128 và NTT đa modulus.',
        'Tái dùng bằng chứng 1.026 vector, 38 ca bốn trạng thái, 12 nhóm reset, 74 lần gọi C và 4 xác minh chữ ký.',
        'Không gọi đây là mô phỏng sau ánh xạ hoặc thử phần cứng Z020.',
        'Có đủ host adapter và root cache. Chưa gồm wrapper AXI, DMA, clock/pin board hoặc chương trình ARM.',
        'Không đổi RTL chính và không dùng checkpoint UltraScale+ để báo số của Z020.','',
        '## Mục tiêu 30k LUT','',
        f"Cần giảm thêm {result['LUT_reduction_needed']:,} LUT so với số synth này để đạt 30.000 LUT.",
        'Đổi chip không tự giảm số phép toán. Cho phép thêm chu kỳ mở ra phương án giảm số engine hoặc',
        'chia thời gian phần cộng/tích lũy, nhưng cần đo lại cả mux, bộ nhớ và điều khiển. Chưa triển khai các phương án đó.','',
        '[Nguồn dung lượng chip: AMD DS190](https://docs.amd.com/api/khub/documents/juMnxca71Tf2gfjmNyjM8A/content).','']
    out.with_suffix('.md').write_text('\n'.join(rows),encoding='utf-8')
    print(json.dumps({k:result[k] for k in ('part','resource','device_usage_percent','internal_timing_estimate','LUT_reduction_needed')},indent=2))

if __name__=='__main__': main()
