"""Require complete, comparable synthesis and numeric validation."""
import hashlib
import json
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
B=ROOT/'study/build/a_cg_timing'
VARIANTS=('base','host','local','raw','all')

def read(p):
    b=p.read_bytes();return b.decode('utf-16' if b.startswith(b'\xff\xfe') else 'utf-8-sig')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def resource(p):
    s=read(p)
    def get(label):
        m=re.search(r'^\|\s*'+re.escape(label)+r'\*?\s*\|\s*(\d+)\s*\|',s,re.M)
        assert m,(p,label)
        return int(m[1])
    return dict(LUT=get('CLB LUTs'),FF=get('CLB Registers'),DSP=get('DSPs'),RAMB18=get('RAMB18'),RAMB36=get('RAMB36/FIFO'))

def summary(p):
    s=read(p);m=re.search(r'WNS\(ns\).*?\n\s*-+[^\n]*\n\s*([-\d.]+[^\n]*)',s,re.S)
    assert m,p
    w=m[1].split()
    return dict(WNS_ns=float(w[0]),TNS_ns=float(w[1]),setup_failing_endpoints=int(w[2]),WHS_ns=float(w[4]),THS_ns=float(w[5]))

def path(p):
    s=read(p)
    def field(label):
        m=re.search(r'^\s*'+re.escape(label)+r':\s*(.+)$',s,re.M)
        return m[1].strip() if m else None
    return dict(source=field('Source'),destination=field('Destination'),data_path=field('Data Path Delay'),levels=field('Logic Levels'))

def parse_sim(p):
    s=read(p);assert 'TOTAL cases=1026 errors=0 PASS' in s,p
    rows=[]
    for line in s.splitlines():
        if line.startswith('CASE '):
            v={k:int(x) for k,x in re.findall(r'(\w+)=(\d+)',line)}
            assert v['errors']==0;rows.append(v)
    assert len(rows)==1026
    return rows

def main():
    frozen=json.loads((B/'baseline_hashes.json').read_text())
    for group in frozen.values():
        for p,h in group.items():assert sha(ROOT/p)==h,('Frozen input changed',p)
    old=json.loads((ROOT/'study/results/a_cg_batch.json').read_text(encoding='utf-8'))
    for f in ('a_cg_fast.sv','tile_a.sv','mul_ss.v'):
        assert (HERE/'base/rtl'/f).read_bytes()==(ROOT/'experiments/a_cg_batch/rtl'/f).read_bytes()
    golden=json.loads((ROOT/'study/build/a_cg_batch/fixtures.json').read_text())
    assert sha(ROOT/'study/build/a_cg_batch/fixtures.bin')==old['sha256']['study/build/a_cg_batch/fixtures.bin']
    baseline_sim=parse_sim(ROOT/'study/build/a_cg_batch/sim.log')
    results=[];hashes={}
    for v in VARIANTS:
        d=B/v;s=d/'synth'
        assert f'TIMING_SYNTH_DONE variant={v}' in read(d/'vivado.log'),('Synthesis incomplete',v)
        r=resource(s/'util.rpt');assert r['DSP']==64 and r['RAMB18']==48 and r['RAMB36']==0
        metrics=read(s/'metrics.txt')
        timing_text=read(s/'timing.rpt')
        assert 'There are 0 input ports with no input delay specified.' in timing_text
        assert 'There are 0 ports with no output delay specified.' in timing_text
        assert re.search(r'User Uncertainty\s+\(UU\):\s+0\.100ns',timing_text)
        for x in ('ROOT_RAMB18=16','DATA_RAMB18=32','DSP48=64','BLACKBOX=0'):assert x in metrics,(v,x)
        internal={k:float(re.search(label+r'=([-\d.]+)',metrics)[1]) for k,label in
            [('WNS_ns','REGISTER_TO_REGISTER_WNS_NS'),('WHS_ns','REGISTER_TO_REGISTER_WHS_NS')]}
        sim=baseline_sim if v=='base' else parse_sim(d/'sim.log')
        for i,c in enumerate(sim):
            assert c['cycles']==baseline_sim[i]['cycles']==golden[i]['model_cycles'],(v,i,'kernel cycle change')
            expected=2*((golden[i]['words']+3)//4) if v in ('host','all') else 0
            assert c['all_host_cycles']-baseline_sim[i]['all_host_cycles']==expected,(v,i,'unexpected host latency')
        fanout=[]
        for line in read(s/'control_fanout.txt').splitlines():
            m=re.match(r'(\S+) fanout=(\d+) dont_touch=(.*)',line);assert m,line
            fanout.append(dict(cell=m[1],fanout=int(m[2]),dont_touch=m[3]))
        if v in ('local','all'):
            for kind,count in [('dir',16),('mf',16),('native_r',16),('fmt_r',32),('shift_r',64),('halve_r',16),('md',32)]:
                cells=[x for x in fanout if re.search('/'+kind+r'_reg(?:\[|$)',x['cell'])]
                assert len(cells)==count,(v,kind,len(cells),count)
                assert all(x['dont_touch']=='1' for x in cells),(v,kind,'preservation missing')
        def max_fanout(kind):
            rows=[c for c in fanout if re.search('/'+kind+r'_reg',c['cell'])]
            return max((c['fanout'] for c in rows),default=0)
        results.append(dict(variant=v,resource=r,full_timing=summary(s/'timing.rpt'),internal_timing=internal,
            critical_internal_path=path(s/'internal_paths.rpt'),mode_max_fanout={k:max_fanout(k) for k in ('dir','mf','fmt_r','shift_r','native_r')},
            control_registers=fanout,numeric_cases=1026,kernel_cycles_identical=True,
            host_added_cycles_per_line=2 if v in ('host','all') else 0,
            host_delta_note='One extra load cycle plus one extra read cycle per line for host/all.',
            cases=[dict(case=i,**c) for i,c in enumerate(sim)]))
        paths=[p for p in (HERE/v/'rtl').glob('*') if p.is_file()]
        paths += [s/f for f in ('util.rpt','util_hier.rpt','timing.rpt','metrics.txt','internal_paths.rpt','control_fanout.txt','synthesized.dcp')]
        paths += [d/'vivado.log']
        if v!='base':paths+=[d/'sim.log']
        hashes.update({p.relative_to(ROOT).as_posix():sha(p) for p in paths})
    assert 'ADDSUB_EQUIVALENCE cases=100256 PASS' in read(B/'addsub/result.log')
    assert 'FOUR_STATE TOTAL cases=38 PASS' in read(B/'all/four_state.log')
    assert 'FOUR_STATE TOTAL cases=38 PASS' in read(B/'host/four_state.log')
    app=json.loads((B/'all/application/application_results.json').read_text())
    calls=json.loads((B/'all/application/rtl_records.json').read_text())
    assert calls['calls']==74 and len(app['artifacts_sha256'])==14
    assert len(app['independent_verification'])==4 and all(x['valid']==0 and x['wrong_message']!=0 for x in app['independent_verification'])
    assert all(x['code']==7 for x in app['negative_live_input'])
    host_app=json.loads((B/'host/application/application_results.json').read_text())
    host_calls=json.loads((B/'host/application/rtl_records.json').read_text())
    assert host_calls['calls']==74 and len(host_app['artifacts_sha256'])==14
    assert len(host_app['independent_verification'])==4 and all(x['valid']==0 and x['wrong_message']!=0 for x in host_app['independent_verification'])
    assert all(x['code']==7 for x in host_app['negative_live_input'])
    base=results[0]
    for r in results:
        r['delta_LUT']=r['resource']['LUT']-base['resource']['LUT']
        r['delta_internal_WNS_ns']=round(r['internal_timing']['WNS_ns']-base['internal_timing']['WNS_ns'],3)
    selected=next(r for r in results if r['variant']=='host')
    assert selected['resource']['LUT']==min(r['resource']['LUT'] for r in results)
    assert selected['internal_timing']['WNS_ns']==max(r['internal_timing']['WNS_ns'] for r in results)
    assert selected['full_timing']['WNS_ns']==max(r['full_timing']['WNS_ns'] for r in results)
    more=[p for p in HERE.glob('*') if p.is_file()]+[B/'addsub/result.log']
    for v in ('host','all'):
        more += [B/v/p for p in ('four_state.log','application/application_results.json','application/rtl_records.json','app_N512_output.bin','app_N1024_output.bin')]
    hashes.update({p.relative_to(ROOT).as_posix():sha(p) for p in more})
    result=dict(kind='synthesis-only comparison',clock_ns=5,clock_read_before_synthesis=True,place_route=False,
        all_modes_runtime=True,packed16_retained=True,results=results,arithmetic_equivalence_cases=100256,
        combined_four_state_cases=38,application=app,application_records=calls,frozen=frozen,sha256=hashes,
        recommended_variant='host',recommended_four_state_cases=38,recommended_application=host_app,recommended_application_records=host_calls,
        limitations=['Unplaced net delay estimates; not physical Fmax or timing closure.',
            'XDC identical for all variants; Vivado may classify uncertainty as implementation-only. Inspect actual timing reports.',
            'Local DONT_TOUCH applies only to configuration flops and does not guarantee physical placement locality.',
            'Host/all trade one load and one read cycle per host line for a registered request path.',
            'Application replay substitutes only FFT/IFFT/NTT/INTT; remaining application code runs in C.'])
    out=ROOT/'study/results';(out/'a_cg_timing.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    lines=['# Thử ba hướng cải thiện timing, giữ packed16','',
        '**Đề xuất giữ bản host:** LUT thấp nhất và WNS ước tính toàn core bằng bản kết hợp. Bản kết hợp thêm 767 LUT nhưng chưa tăng margin timing synth. Đây chưa phải kết luận sau route.','',
        'Chỉ synth, cùng part xczu7ev-ffvc1156-2-e và cùng XDC clock 5 ns đọc trước synth. Không P&R, không sửa RTL chính. Các input mode vẫn runtime; không buộc mode để làm nhỏ mạch.','',
        '| Bản | LUT | Δ LUT | FF | WNS nội bộ | Δ WNS nội bộ | WNS gồm I/O |',
        '|---|---:|---:|---:|---:|---:|---:|']
    for r in results:
        lines.append(f'| {r["variant"]} | {r["resource"]["LUT"]:,} | {r["delta_LUT"]:+,} | {r["resource"]["FF"]:,} | {r["internal_timing"]["WNS_ns"]:+.3f} ns | {r["delta_internal_WNS_ns"]:+.3f} ns | {r["full_timing"]["WNS_ns"]:+.3f} ns |')
    lines += ['', 'Mọi bản đều 64 DSP, 48 RAMB18 (32 data + 16 root), không blackbox. WNS càng lớn càng tốt dưới CÙNG ràng buộc. Không quy đổi WNS này thành Fmax sau route. Baseline so sánh là bản base mới, không phải lượt 36.231 LUT tạo clock sau synth.','',
        '## Ý nghĩa các bản','',
        '- host: chụp request/line/data, phục vụ bank từ chu kỳ sau; bỏ đường xuyên từ ready/accept đến RAM trong cùng chu kỳ.',
        '- local: giữ các register cấu hình trong mỗi tile; không DONT_TOUCH mảng nhân, bộ nhớ hay toàn datapath.',
        '- raw: FFT dùng tổng/hiệu thô, NTT dùng hiệu chỉnh q cũ; cùng carry/borrow, wrap, rounding và số bit.',
        '- all: kết hợp cả ba.','',
        '## Kiểm chứng','',
        '- Mỗi bản sửa qua 1.026 ca dùng lại input/root/expected đã đóng băng. Tất cả chu kỳ kernel trùng baseline.',
        '- Bộ cộng mới khớp bản cũ trong 100.256 phép thử, gồm signed-bit patterns, wrap, carry/borrow, NTT32 và packed16.',
        '- Bản kết hợp qua 38 ca Icarus bốn trạng thái; 74 lần gọi transform từ C, 4 chữ ký verify và 14 artifact khớp từng byte; đầu vào live bị sửa bị từ chối.',
        '- Bản host được đề xuất cũng qua riêng 38 ca bốn trạng thái, 74 lần gọi C, 4 chữ ký verify và 14 artifact khớp từng byte; đầu vào live bị sửa bị từ chối.',
        '- Bản host/all thêm đúng 2 × ceil(số word/4) chu kỳ cho tổng nạp + đọc của mỗi ca. Chi phí nằm ở host, không ẩn vào số kernel.','',
        '## Fanout điều khiển sau synth','',
        '| Bản | dir max | mf max | fmt_r max | shift_r max | native_r max |',
        '|---|---:|---:|---:|---:|---:|']
    for r in results:
        f=r['mode_max_fanout'];lines.append('| '+r['variant']+' | '+' | '.join(str(f[k]) for k in ('dir','mf','fmt_r','shift_r','native_r'))+' |')
    lines += ['', '## Chu kỳ kernel và giao dịch host ở bản đề xuất','',
        '| Trường hợp | Kernel trước/sau | Cold baseline | Cold host |',
        '|---|---:|---:|---:|']
    for fft,fmt,ln,hm,q,packed,jobs in [(0,0,10,0,12289,1,0),(0,0,8,1,3329,1,0),(1,2,10,0,0,0,0)]:
        i=next(i for i,c in enumerate(golden) if (c['fft'],c['fmt'],c['logn'],c['hmin'],c['q'],c['packed'],c['jobs_log'],c['inverse'],c['native'])==(fft,fmt,ln,hm,q,packed,jobs,0,0))
        a=baseline_sim[i];z=selected['cases'][i]
        label='FFT128 N1024' if fft else f'Packed16 NTT q={q} N={1<<ln}'
        lines.append(f'| {label} | {a["cycles"]} / {z["cycles"]} | {a["all_host_cycles"]} | {z["all_host_cycles"]} |')
    lines += ['', 'Cold gồm cấu hình, root, nạp, kernel và đọc theo cùng driver. Chi phí host tăng đã được tính, không suy ra tăng tốc toàn ứng dụng từ WNS synth.','',
        '## Đường tới hạn nội bộ','']
    for r in results:
        p=r['critical_internal_path'];lines.append(f'- {r["variant"]}: `{p["source"]}` → `{p["destination"]}`; {p["data_path"]}; {p["levels"]}.')
    lines += ['', '## Giới hạn','',*['- '+x for x in result['limitations']],
        '- WNS setup dương không có nghĩa đã khép timing. Mô hình I/O tạm còn hold -0,110 ns sau synth; hold register→register được ghi riêng trong JSON. Chưa có timing sau layout.',
        '', 'README và lệnh tái lập: experiments/a_cg_timing/README.md. JSON lưu từng ca, hash nguồn/checkpoint và dữ liệu ứng dụng.']
    (out/'a_cg_timing.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps([dict(variant=r['variant'],resource=r['resource'],internal=r['internal_timing'],full=r['full_timing']) for r in results],indent=2))

if __name__=='__main__':main()
