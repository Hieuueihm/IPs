"""Collect measured packed/batch results; reject incomplete validation."""
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import struct

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
B=ROOT/'study/build/a_cg_batch'

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):
    b=p.read_bytes()
    return b.decode('utf-16' if b.startswith(b'\xff\xfe') else 'utf-8-sig')

def payload(path,new):
    b=path.read_bytes();w=struct.unpack('<'+'I'*(len(b)//4),b);pos=2;out=[]
    assert w[0]==(0x43474233 if new else 0x43474632)
    for _ in range(w[1]):
        h=w[pos:pos+(13 if new else 11)];pos+=len(h)
        ns,nr,nw=h[-3:];d=w[pos:pos+4*ns];pos+=4*ns
        values=w[pos:pos+16*nr+2*nw];pos+=len(values)
        old_header=h[:8]+h[10:] if new else h
        out.append((old_header,tuple(v for i,v in enumerate(d) if i%4!=3),values))
    assert pos==len(w)
    return out

def main():
    baseline=json.loads((ROOT/'study/results/a_cg_tune.json').read_text(encoding='utf-8'))
    for p,h in baseline['sha256'].items():
        if p.startswith('experiments/a_cg_tune/'):assert sha(ROOT/p)==h,('Baseline changed',p)
    production=json.loads((B/'production_hashes.json').read_text())
    for p,h in production.items():assert sha(ROOT/p)==h,('Production changed',p)
    for p in ('a_cg_fast.sv','tile_a.sv','mul_ss.v'):
        assert sha(HERE/'rtl'/p)==sha(B/'attempt1/rtl'/p),('Retained synth source changed',p)
    assert payload(B/'fixtures.bin',True)[:454]==payload(ROOT/'study/build/a_cg_tune/fixtures.bin',False)
    manifest=json.loads((B/'fixtures.json').read_text())
    sim=read(B/'sim.log');assert f'TOTAL cases={len(manifest)} errors=0 PASS' in sim
    four=read(B/'four_state.log');nf=int(re.search(r'FOUR_STATE TOTAL cases=(\d+) PASS',four)[1])
    assert 'A_CG_SYNTH_DONE' in read(B/'vivado.log')
    assert 'A_CG_AUDIT_DONE' in read(B/'audit.log')
    audit=read(B/'synth/audit.txt')
    for s in ('ROOT_RAMB18=16','DATA_RAMB18=32','DSP48=64','BLACKBOX=0'):assert s in audit
    sp=importlib.util.spec_from_file_location('util',ROOT/'experiments/a_cg/report.py')
    util=importlib.util.module_from_spec(sp);sp.loader.exec_module(util)
    resource=util.utilization(B/'synth/util.rpt')
    ablation=None
    if (B/'batch_only_synth/util.rpt').exists():
        assert 'A_CG_SYNTH_DONE' in read(B/'batch_only_vivado.log')
        assert 'A_CG_AUDIT_DONE' in read(B/'batch_only_audit.log')
        ablation=util.utilization(B/'batch_only_synth/util.rpt')
    timing=read(B/'synth/timing.rpt')
    wns=float(re.search(r'WNS\(ns\).*?\n\s*-+[^\n]*\n\s*([-\d.]+)',timing,re.S)[1])
    cases=[]
    for line in sim.splitlines():
        if not line.startswith('CASE '):continue
        idx=int(line.split()[1]);v={a:int(b) for a,b in re.findall(r'(\w+)=(\d+)',line)}
        c=dict(manifest[idx],case=idx,kernel_cycles=v['cycles'],all_host_cycles=v['all_host_cycles'])
        assert v['errors']==0 and c['kernel_cycles']==c['model_cycles']
        cases.append(c)
    assert len(cases)==len(manifest)
    ablation_cases=[]
    if ablation:
        ids=json.loads((B/'batch_only_indices.json').read_text())
        log=read(B/'batch_only_sim.log')
        assert f'TOTAL cases={len(ids)} errors=0 PASS' in log
        for line in log.splitlines():
            if not line.startswith('CASE '):continue
            j=int(line.split()[1]);v={a:int(b) for a,b in re.findall(r'(\w+)=(\d+)',line)}
            c=cases[ids[j]]
            assert not c['packed'] and v['errors']==0
            assert v['cycles']==c['kernel_cycles'] and v['all_host_cycles']==c['all_host_cycles']
            ablation_cases.append(ids[j])
        assert len(ablation_cases)==len(ids)
    app=json.loads((B/'application/application_results.json').read_text())
    calls=json.loads((B/'application/rtl_records.json').read_text())
    assert calls['calls']==74 and len(app['artifacts_sha256'])==14
    assert len(app['independent_verification'])==4 and all(x['valid']==0 and x['wrong_message']!=0 for x in app['independent_verification'])
    assert all(x['code']==7 for x in app['negative_live_input'])
    def pick(fft=0,fmt=0,ln=10,hm=0,q=12289,packed=0,jl=0,native=0,inv=0):
        return next(c for c in cases if (c['fft'],c['fmt'],c['logn'],c['hmin'],c['q'],c['packed'],c['jobs_log'],c['native'],c['inverse'])==(fft,fmt,ln,hm,q,packed,jl,native,inv))
    comparisons=[]
    for args in [dict(packed=1),dict(ln=8,hm=1,q=3329,packed=1),
                 dict(ln=3,jl=4),dict(ln=3,packed=1,jl=4),dict(packed=1,jl=1),
                 dict(ln=8,q=8380417,jl=1),dict(fft=1,fmt=2,ln=3,q=0,jl=3),
                 dict(fft=1,fmt=2,ln=10,q=0)]:
        c=pick(**args);single=pick(**dict(args,packed=0,jl=0))
        comparisons.append(dict(case=c['case'],name=c['name'],jobs=c['jobs'],
            baseline_single_cycles=single['kernel_cycles'],kernel_cycles=c['kernel_cycles'],
            cycles_per_job=c['kernel_cycles']/c['jobs'],
            throughput_ratio=single['kernel_cycles']*c['jobs']/c['kernel_cycles'],
            all_host_cycles=c['all_host_cycles'],baseline_single_all_host=single['all_host_cycles']))
    result=dict(resource=resource,baseline_resource=baseline['resource'],
        budget_margin=35000-resource['LUT'],synth_WNS_ns=wns,clock_ns=5,
        clock_set_after_synthesis=True,post_route=False,numeric_cases=len(cases),
        four_state_cases=nf,unchanged_first_454_payload=True,comparisons=comparisons,
        batch_only_static_resource=ablation,
        batch_only_verified_cases=len(ablation_cases),
        cases=cases,application=app,application_records=calls,production_sha256=production,
        limitations=['Kernel cycles exclude host/root loading; cold transaction cycles are also reported.',
            'Batch jobs share N, q, direction, precision, tables and arithmetic contract; no mixed-context execution.',
            'Packed16 requires canonical inputs and odd q < 32768, with roots in Montgomery R16 domain.',
            'No additional DSP/BRAM; combined packed and batch increase LUT versus the 33,669-LUT baseline.',
            'Application replay substitutes only FFT/IFFT/NTT/INTT; other PQC kernels remain C.',
            'Application replay uses single jobs; batch correctness uses independent transform vectors.',
            'Synth-only timing is not measured post-route Fmax; no full-algorithm speedup claim.'])
    paths=[p for p in HERE.rglob('*') if p.is_file() and '__pycache__' not in str(p)]
    paths += [B/p for p in ('fixtures.bin','fixtures.json','sim.log','four_state.log',
              'synth/util.rpt','synth/util_hier.rpt','synth/timing.rpt','synth/audit.txt','synth/synthesized.dcp',
              'application/application_results.json','application/rtl_records.json','app_N512_output.bin','app_N1024_output.bin')]
    if ablation:
        paths += [B/'batch_only_synth'/p for p in ('util.rpt','util_hier.rpt','timing.rpt','audit.txt','synthesized.dcp')]
        paths += [B/p for p in ('batch_only_sim.log','batch_only.bin','batch_only_indices.json','batch_only_main.cpp')]
    result['sha256']={p.relative_to(ROOT).as_posix():sha(p) for p in paths}
    out=ROOT/'study/results';(out/'a_cg_batch.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    lines=['# Packed16 NTT và batch transform: số đo RTL','',
        f'Bản riêng: **{resource["LUT"]:,} LUT, {resource["FF"]:,} FF, {resource["DSP"]} DSP, {resource["RAMB18"]} RAMB18**; chênh ngân sách 35k: {result["budget_margin"]:+,} LUT.',
        'Toàn core gồm host, root, descriptor, bộ nhớ và 16 engine. Không thay production, PLAN, spec hay các bản thử trước. Chưa commit.','',
        '## Hiệu năng','',
        'Chu kỳ đo từ start đến done. Tỷ lệ throughput so với chạy tuần tự cùng số job bằng scalar NTT hoặc FFT một job, cùng clock; không phải tăng tốc toàn ứng dụng.','',
        '| Cấu hình | Job/lệnh | Baseline/job | Chu kỳ cả lô | Chu kỳ/job | Throughput | Cold cả lô |',
        '|---|---:|---:|---:|---:|---:|---:|']
    for r in comparisons:
        lines.append(f'| {r["name"]} | {r["jobs"]} | {r["baseline_single_cycles"]} | {r["kernel_cycles"]} | {r["cycles_per_job"]:.2f} | {r["throughput_ratio"]:.2f}× | {r["all_host_cycles"]} |')
    lines += ['', 'Cold bao gồm cấu hình, root/descriptor, nạp dữ liệu và đọc kết quả theo driver hiện tại. Batch N=8 là trường hợp nhỏ minh họa mức lấp đầy; không suy ra throughput tương tự cho N lớn.',
        '', '## Tính đúng', '',
        f'- {len(cases)} ca Verilator: khớp model chu kỳ và mọi word kết quả; 454 ca cũ giữ nguyên input/root/expected.',
        f'- {nf} ca Icarus bốn trạng thái, gồm packed tầng thường/tầng trong word, bank jobs và row jobs.',
        '- NTT mới dùng oracle đánh giá đa thức Horner độc lập. FFT giữ nguyên contract 32/64/128 và native NTRUGen64.',
        '- 74 lần gọi transform trong C thực tế, dùng packed cho NTT/INTT, FFT128 như trước; 4 chữ ký verify và 14 artifact khớp từng byte. Đầu vào bị sửa bị từ chối.',
        '- Không phải chứng minh hình thức mọi đầu vào hay chứng nhận an toàn toàn bộ ứng dụng PQC.',
        '', '## Diện tích và giới hạn', '',
        f'Baseline {baseline["resource"]["LUT"]:,} LUT; bản này tăng {resource["LUT"]-baseline["resource"]["LUT"]:,} LUT. DSP và BRAM không tăng.',
        f'WNS sau synth ở clock 5 ns: {wns:+.3f} ns. Clock đặt sau synth như baseline; chưa place/route.',
        *['- '+s for s in result['limitations']],
        '', 'Chi tiết cơ chế, cấu hình và lệnh tái lập: `experiments/a_cg_batch/README.md`. JSON kèm hash nguồn, báo cáo và từng ca đo.']
    if ablation:
        lines += ['', '## Đo tách chức năng packed', '',
            f'Bản compile-time tắt packed, giữ batch và FFT32/64/128: **{ablation["LUT"]:,} LUT, {ablation["FF"]:,} FF, {ablation["DSP"]} DSP, {ablation["RAMB18"]} RAMB18**.',
            f'Chênh ngân sách 35k: {35000-ablation["LUT"]:+,} LUT. Chênh so với baseline 33.669 LUT: {ablation["LUT"]-baseline["resource"]["LUT"]:+,} LUT.',
            f'Đây là cấu hình chuyên biệt tĩnh của cùng source, với packed=0; **{len(ablation_cases)} ca mô phỏng riêng đều qua**, chu kỳ kernel và cold trùng core đầy đủ ở cùng chế độ. Chưa mô phỏng netlist sau synth.',
            'Không được gán số chu kỳ packed16 cho bản này. Tính năng batch không tự tạo ra các job độc lập trong ứng dụng.',
            'Thử đưa phép nhân bản q vào engine thay vì cổng cấu hình làm tăng từ 36.231 lên 36.499 LUT, nên đã bỏ. Báo cáo lần thử được giữ trong attempt2.']
    (out/'a_cg_batch.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps(dict(resource=resource,budget_margin=result['budget_margin'],comparisons=comparisons),indent=2))

if __name__=='__main__':main()
