"""Collect physical implementation separately from the frozen synthesis study."""
import hashlib
import json
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
B=ROOT/'study/build/a_cg_batch'

def read(p):
    b=p.read_bytes()
    return b.decode('utf-16' if b.startswith(b'\xff\xfe') else 'utf-8-sig')

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def utilization(p):
    text=read(p)
    def get(label):
        m=re.search(r'^\|\s*'+re.escape(label)+r'\*?\s*\|\s*(\d+)\s*\|',text,re.M)
        assert m,(p,label)
        return int(m[1])
    return dict(LUT=get('CLB LUTs'),FF=get('CLB Registers'),DSP=get('DSPs'),
        RAMB18=get('RAMB18'),RAMB36=get('RAMB36/FIFO'),BRAM36_equivalent=get('Block RAM Tile'),
        BUFGCE=get('BUFGCE'))

def timing(p):
    text=read(p)
    m=re.search(r'WNS\(ns\).*?\n\s*-+[^\n]*\n\s*([-\d.]+[^\n]*)',text,re.S)
    assert m,('Timing summary missing',p)
    v=m[1].split();assert len(v)>=12,(p,v)
    return dict(WNS_ns=float(v[0]),TNS_ns=float(v[1]),setup_failing_endpoints=int(v[2]),
        WHS_ns=float(v[4]),THS_ns=float(v[5]),hold_failing_endpoints=int(v[6]),
        WPWS_ns=float(v[8]),TPWS_ns=float(v[9]),pulse_failing_endpoints=int(v[10]))

def critical_path(p):
    text=read(p)
    def field(name):
        m=re.search(r'^\s*'+re.escape(name)+r':\s*(.+)$',text,re.M)
        return m[1].strip() if m else None
    return dict(source=field('Source'),destination=field('Destination'),
        data_path_delay=field('Data Path Delay'),logic_levels=field('Logic Levels'))

def main():
    baseline=json.loads((ROOT/'study/results/a_cg_batch.json').read_text(encoding='utf-8'))
    for p,h in baseline['sha256'].items():
        if p.endswith(('.sv','.v','synthesized.dcp')):
            assert sha(ROOT/p)==h,('Frozen input changed',p)
    for p,h in baseline['production_sha256'].items():assert sha(ROOT/p)==h
    runs=[];paths=[HERE/'route.tcl',HERE/'route_audit.tcl',HERE/'route_report.py',HERE/'README.md',ROOT/'study/results/a_cg_batch.json']
    for variant in ('packed','batch_only'):
        d=B/f'route_{variant}_5.000'
        log=B/f'route_{variant}.log'
        if not log.exists():log=B/f'route_{variant}_console.log'
        assert f'A_CG_IMPLEMENT_DONE variant={variant} period=5.000' in read(log),(variant,'Implementation incomplete')
        assert (d/'routed.dcp').exists()
        config=read(d/'run_config.txt')
        assert 'period_ns=5.000' in config and 'HD.CLK_SRC=' in config
        audit=read(d/'audit.txt')
        for v in ('ROOT_RAMB18=16','DATA_RAMB18=32','DSP48=64','BLACKBOX=0'):assert v in audit
        internal={k:float(re.search(label+r'=([-\d.]+)',audit)[1]) for k,label in
            [('WNS_ns','REGISTER_TO_REGISTER_WNS_NS'),('WHS_ns','REGISTER_TO_REGISTER_WHS_NS')]}
        route=read(d/'route_status.rpt')
        t=timing(d/'timing.rpt');r=utilization(d/'util.rpt')
        synth=baseline['resource'] if variant=='packed' else baseline['batch_only_static_resource']
        assert r['DSP']==64 and r['RAMB18']==48 and r['RAMB36']==0
        run=dict(variant=variant,resource=r,synth_resource=synth,LUT_change=r['LUT']-synth['LUT'],
            budget_margin=35000-r['LUT'],timing=t,target_MHz=200,config=config,
            route_status=route,internal_timing=internal,
            internal_critical_path=critical_path(d/'internal_setup_paths.rpt'),
            internal_setup_hold_pass=all(x>=0 for x in internal.values()),
            boundary_partial_route_warnings=read(log).count('[Route 35-198]'),
            all_reported_timing_nonnegative=all(t[x]>=0 for x in ('WNS_ns','WHS_ns','WPWS_ns')))
        runs.append(run)
        paths += [d/f for f in ('run_config.txt','constraints.xdc','util.rpt','util_hier.rpt','timing.rpt',
            'placed_timing.rpt','placed_util.rpt','route_status.rpt','setup_paths.rpt','hold_paths.rpt','drc.rpt','routed.dcp',
            'audit.txt','internal_setup_paths.rpt','internal_hold_paths.rpt')]
        paths.append(log)
    result=dict(kind='out-of-context core place and route',runs=runs,
        numeric_validation=dict(full_cases=baseline['numeric_cases'],four_state_cases=baseline['four_state_cases'],
            batch_only_cases=baseline['batch_only_verified_cases'],application_calls=baseline['application_records']['calls']),
        source_checkpoint_sha256={p:h for p,h in baseline['sha256'].items() if p.endswith(('.sv','.v','synthesized.dcp'))},
        production_sha256=baseline['production_sha256'],
        limitations=['Core OOC implementation; no board I/O placement, clock input pin, board project or bitstream.',
            '5 ns clock, 1 ns max and 0 ns min synchronous I/O delays, setup/hold uncertainty 0.100/0.050 ns.',
            'HD.CLK_SRC reference site is identical for both variants; real system clock integration can change timing.',
            'OOC ports without HD.PARTPIN_LOCS have incomplete boundary routes; their I/O timing is not board/system timing closure.',
            'No post-route functional timing simulation or full algorithm benchmark.',
            'Power report, if present, is vectorless and is not a measured power claim.',
            'Passing RTL vectors does not guarantee hardware correctness at a clock that fails physical timing; do not claim 200 MHz latency without closure.'])
    result['sha256']={p.relative_to(ROOT).as_posix():sha(p) for p in paths}
    out=ROOT/'study/results'
    (out/'a_cg_batch_route.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    lines=['# Place/route: packed16 + batch và bản chỉ batch','',
        'Toàn core gồm host/config, root/descriptor, dữ liệu và 16 engine. RTL chính và các checkpoint synth đầu vào giữ nguyên.','',
        '| Bản | LUT synth | LUT sau route | Dư ngân sách 35k | FF | DSP | RAMB18 | WNS @200 MHz | WHS |',
        '|---|---:|---:|---:|---:|---:|---:|---:|---:|']
    for x in runs:
        r=x['resource'];t=x['timing']
        lines.append(f'| {x["variant"]} | {x["synth_resource"]["LUT"]:,} | {r["LUT"]:,} | {x["budget_margin"]:+,} | {r["FF"]:,} | {r["DSP"]} | {r["RAMB18"]} | {t["WNS_ns"]:+.3f} ns | {t["WHS_ns"]:+.3f} ns |')
    lines += ['', '## Điều kiện đo', '',
        '- xczu7ev-ffvc1156-2-e, Vivado 2018.1; opt_design → place_design → phys_opt_design → route_design.',
        '- Clock 5 ns, I/O delay max 1 ns và min 0 ns; uncertainty setup 0,100 ns / hold 0,050 ns.',
        '- Không dùng false path cho host, config hoặc reset. Đây là ràng buộc tích hợp core giả định, không phải timing board ZCU106.',
        '- Clock OOC có HD.CLK_SRC; vị trí cụ thể, route status và đường tới hạn được lưu cùng báo cáo.',
        '- Các cổng OOC chưa có HD.PARTPIN_LOCS không có route biên đầy đủ: số timing I/O chưa xác nhận giao diện hệ thống. Báo cáo giữ cả số toàn design và số register-to-register.',
        '', '## Hiệu năng và tính đúng', '',
        'Số chu kỳ không đổi so với bản đã mô phỏng: NTT q=12289 N=1024 scalar 985, packed 505; FFT128 N=1024 6.508.',
        'Tại 200 MHz, 985/505 chu kỳ tương ứng 4,925/2,525 µs **chỉ là quy đổi nội bộ khi setup/hold register→register đạt**; không gồm nạp/đọc host và không xác nhận timing I/O.',
        'Đã có 1.026 ca số học, 38 ca bốn trạng thái, 774 ca riêng cho bản chỉ batch; 74 lần gọi transform trong C, bốn chữ ký verify và 14 artifact khớp. Không chạy lại bộ mô phỏng này vì không đổi RTL.',
        'Chưa mô phỏng chức năng sau route; các kiểm tra C chỉ thay FFT/IFFT/NTT/INTT bằng RTL, phần còn lại vẫn C.',
        '', '## Giới hạn', '',*['- '+s for s in result['limitations']]]
    lines += ['', '## Timing nội bộ (register → register)', '',
        '| Bản | Setup WNS | Hold WHS | Setup và hold không âm |',
        '|---|---:|---:|---|']
    for x in runs:
        t=x['internal_timing']
        lines.append(f'| {x["variant"]} | {t["WNS_ns"]:+.3f} ns | {t["WHS_ns"]:+.3f} ns | {"Đạt" if x["internal_setup_hold_pass"] else "Chưa đạt"} |')
    lines += ['', '## Đường tới hạn nội bộ', '']
    for x in runs:
        p=x['internal_critical_path']
        lines.append(f'- {x["variant"]}: `{p["source"]}` → `{p["destination"]}`; {p["data_path_delay"]}; {p["logic_levels"]}.')
    (out/'a_cg_batch_route.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps(runs,indent=2))

if __name__=='__main__':main()
