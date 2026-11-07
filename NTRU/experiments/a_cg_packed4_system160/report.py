"""Audit private full-system P&R evidence without changing either RTL baseline."""
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
BUILD=ROOT/'study/build/a_cg_packed4_system160'
ROUTE=BUILD/'route'
def read(p):return p.read_text(encoding='utf-8-sig',errors='replace')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def timing_table(text):
    lines=text.splitlines()
    for i,line in enumerate(lines):
        if 'WNS(ns)' in line and 'TNS Failing Endpoints' in line:
            for row in lines[i+1:i+5]:
                p=row.split()
                if len(p)==12 and re.fullmatch(r'-?\d+\.\d+',p[0]):
                    return p
    raise AssertionError('Full-system timing summary missing')

def main():
    subprocess.run([sys.executable,'-X','utf8',str(ROOT/'scripts/check_baseline.py')],check=True)
    frozen=json.loads(read(BUILD/'input_manifest.json'))
    for name,h in frozen['source_sha256'].items():
        assert sha(HERE/'rtl'/name)==h
        assert (HERE/'rtl'/name).read_bytes()==(ROOT/'experiments/a_cg_packed4/rtl'/name).read_bytes()
    assert sha(ROOT/'study/build/a_cg_packed4/results.json')==frozen['validated_results_sha256']
    for name,h in frozen['workflow_sha256'].items():assert sha(HERE/name)==h,name
    assert (HERE/'signoff.tcl').read_bytes()==(ROOT/'experiments/a_cg_z020_system160/signoff.tcl').read_bytes()
    timing=read(ROUTE/'timing.rpt')
    p=timing_table(timing)
    wns,tns,ns,ts,whs,ths,nh,th,pw,tpw,npw,total_pw=p
    assert int(ts)>0 and int(th)>0 and int(total_pw)>0
    check=read(ROUTE/'check_timing.rpt')
    descriptions=['register/latch pins with no clock','register/latch pins with constant_clock',
        'input ports with no input delay specified','ports with no output delay specified',
        'register/latch pins with multiple clocks','generated clocks that are not connected to a clock source',
        'combinational loops in the design','input ports with partial input delay specified',
        'ports with partial output delay specified']
    for description in descriptions:assert f'There are 0 {description}' in check,description
    assert 'There are 0 pins that are not constrained for maximum delay.' in check
    cdc_safe='All paths are Safely Timed.' in read(ROUTE/'cdc.rpt')
    drc=read(ROUTE/'drc.rpt')
    errors=re.findall(r'^\S+#\d+\s+Error\s*$',drc,re.M)
    warnings=re.findall(r'^\S+#\d+\s+Warning\s*$',drc,re.M)
    m=dict(line.split('=',1) for line in read(ROUTE/'metrics.txt').splitlines())
    assert m['PS7']=='1' and m['MMCM']=='1' and m['BLACKBOX']=='0'
    assert m['DSP48']=='64' and m['RAMB18']=='48'
    util=read(ROUTE/'util.rpt');resources={}
    for key,label in [('lut','Slice LUTs'),('ff','Slice Registers'),('dsp','DSPs'),('ramb18','RAMB18')]:
        match=re.search(r'\|\s*'+re.escape(label)+r'\*?\s*\|\s*([\d,]+)',util)
        assert match,label
        resources[key]=int(match[1].replace(',',''))
    status=read(ROUTE/'route_status.rpt')
    def number(label):return int(re.search(re.escape(label)+r'\.+\s*:\s*(\d+)',status)[1])
    routed=number('# of fully routed nets');routable=number('# of routable nets')
    routing_errors=number('# of nets with routing errors')
    complete=(routed==routable and routing_errors==0 and not errors)
    timing_pass=(float(wns)>=0 and float(whs)>=0 and float(pw)>=0 and
                 int(ns)==int(nh)==int(npw)==int(m['SETUP_FAILING'])==int(m['HOLD_FAILING'])==0)
    clocks=read(ROUTE/'clocks.rpt')
    assert '6.250' in clocks and '10.000' in clocks
    path=read(ROUTE/'setup.rpt')
    source=re.search(r'^\s*Source:\s*(.+)',path,re.M)
    dest=re.search(r'^\s*Destination:\s*(.+)',path,re.M)
    result=dict(target_mhz=160,full_timing_pass=timing_pass,implementation_clean=complete,
        signoff_pass=timing_pass and complete and cdc_safe,
        setup_wns_ns=float(wns),hold_whs_ns=float(whs),pulse_width_slack_ns=float(pw),
        setup_failing=int(ns),setup_endpoints=int(ts),hold_failing=int(nh),hold_endpoints=int(th),
        pulse_width_failing=int(npw),resources=resources,within_35k_lut=resources['lut']<=35000,
        routed_nets=routed,routable_nets=routable,routing_errors=routing_errors,
        drc_errors=len(errors),drc_warnings=len(warnings),cdc_safe=cdc_safe,
        unconstrained_endpoints=0,critical_source=source[1].strip() if source else None,
        critical_destination=dest[1].strip() if dest else None,
        baseline_unchanged=True,rtl_unchanged_from_validated_candidate=True,hardware_tested=False,
        scope='PS7 OCM/JTAG + AXI interconnect + AXI-Lite host + MMCM/reset + core/data/root; DDR/peripherals disabled')
    (BUILD/'signoff_results.json').write_text(json.dumps(result,indent=2)+'\n')
    evidence={str(f.relative_to(ROOT)).replace('\\','/'):sha(f) for f in ROUTE.iterdir() if f.is_file() and f.suffix in ['.rpt','.txt','.dcp']}
    (BUILD/'evidence_sha256.json').write_text(json.dumps(evidence,indent=2)+'\n')
    base=json.loads(read(ROOT/'study/build/a_cg_z020_system160/signoff_results.json'))
    registry=json.loads(read(ROOT/'experiments/BASELINE.json'))
    accepted=registry['id']=='a_cg_packed4_system160' and registry['status']=='accepted'
    status=('Baseline được người dùng nhận ngày 2026-11-04, contract 3.1. Mốc trước `a_cg_z020_system160` giữ làm lịch sử.'
            if accepted else 'Bản thử riêng `a_cg_packed4_system160`; baseline `a_cg_z020_system160` không đổi.')
    rows=['# Packed16 bốn leaf — P&R toàn hệ thống 160 MHz','',
        '**'+('ĐẠT' if result['signoff_pass'] else 'CHƯA ĐẠT')+' timing 160 MHz theo báo cáo routed toàn hệ thống.**',
        status+' Chưa commit/chạy board.','',
        '| Chỉ tiêu | Baseline cũ | Packed16 bốn leaf |','|---|---:|---:|',
        f"| Setup WNS (ns) | {base['setup_wns_ns']:+.3f} | {float(wns):+.3f} |",
        f"| Hold WHS (ns) | {base['hold_whs_ns']:+.3f} | {float(whs):+.3f} |",
        f"| Pulse-width slack (ns) | {base['pulse_width_slack_ns']:+.3f} | {float(pw):+.3f} |"]
    for key,label in [('lut','LUT'),('ff','FF'),('dsp','DSP48'),('ramb18','RAMB18')]:
        rows.append(f"| {label} | {base['resources'][key]:,} | {resources[key]:,} |")
    rows+=['',f"Setup vi phạm {ns}/{ts} endpoint; hold vi phạm {nh}/{th}; pulse width vi phạm {npw}.",
        f"Routing: {routed}/{routable} net; {routing_errors} lỗi. DRC: {len(errors)} Error, {len(warnings)} Warning.",
        f"CDC an toàn: {cdc_safe}. Endpoint chưa ràng buộc: 0. Ngân sách ≤35k LUT: {result['within_35k_lut']}.",
        '', '## Phạm vi và ràng buộc','',
        'Part xc7z020clg400-2; Vivado 2018.1. PS7 reference 33,333333 MHz, FCLK100 → MMCM160; AXI và lõi chung miền 160 MHz. DDR/ngoại vi tắt, dùng cấu hình OCM/JTAG như baseline.',
        'Ràng buộc `signoff.tcl` giống baseline từng byte: PS clock jitter 0,300 ns, setup uncertainty 0,100 ns, hold uncertainty 0,050 ns; clock Wizard dẫn từ FCLK thật. Không dùng I/O OOC hoặc giả định chân clock ảo.',
        'P&R mặc định: opt_design → place_design → phys_opt_design → route_design. Không thay RTL, precision, modulus hay thêm timing exception để làm đẹp kết quả.',
        '', '## Đường setup xấu nhất','',f"Nguồn: `{result['critical_source']}`.",f"Đích: `{result['critical_destination']}`.",
        '', '## Correctness và bằng chứng','',
        'Bốn file RTL giống từng byte với ứng viên `a_cg_packed4` đã kiểm: 1.026 ca AXI, 33.600 butterfly tại tile, 10 ca four-state, 74 transform C, 14 artifact giống từng byte và 4 chữ ký xác minh độc lập. Đây là kiểm chứng chức năng RTL; chưa chạy gate-level SDF hoặc board.',
        'Checkpoint cuối: `study/build/a_cg_packed4_system160/route/signoff.dcp`. Các báo cáo setup/hold, timing summary, clocks, CDC, exceptions, check_timing, route_status và DRC ở cùng thư mục.',
        'Kết quả máy đọc: `study/build/a_cg_packed4_system160/signoff_results.json`. Hash RTL/workflow trong `input_manifest.json`; hash bằng chứng trong `evidence_sha256.json`.',
        'Kiểm lại: `python -X utf8 experiments/a_cg_packed4_system160/report.py`. Trạng thái baseline xem `experiments/BASELINE.json`; không tự nâng baseline khi chạy report.']
    (ROOT/'study/results/a_cg_packed4_system160.md').write_text('\n'.join(rows)+'\n',encoding='utf-8')
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
