"""Collect the tuning result against the frozen, functionally matched baseline."""
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import struct

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
B=ROOT/'study/build/a_cg_tune'


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def read(p):
    b=p.read_bytes();return b.decode('utf-16' if b.startswith((b'\xff\xfe',b'\xfe\xff')) else 'utf-8-sig')


def payload(path):
    raw=path.read_bytes();w=struct.unpack('<'+'I'*(len(raw)//4),raw);i=2;out=[]
    assert w[0]==0x43474632
    for _ in range(w[1]):
        header=w[i:i+11];i+=11;ns,nr,nw=header[-3:]
        desc=w[i:i+4*ns];i+=4*ns
        stable_desc=tuple(x for j,x in enumerate(desc) if j%4!=3)
        values=w[i:i+16*nr+2*nw];i+=16*nr+2*nw
        out.append((header,stable_desc,values))
    assert i==len(w)
    return out


def main():
    baseline=json.loads((ROOT/'study/results/a_cg_fast.json').read_text(encoding='utf-8'))
    for p,h in baseline['sha256'].items():
        if p.startswith('experiments/a_cg_fast/'):assert sha(ROOT/p)==h,('Baseline changed',p)
    for p,h in baseline['production_sha256'].items():assert sha(ROOT/p)==h
    assert payload(B/'fixtures.bin')==payload(ROOT/'study/build/a_cg_fast/fixtures.bin'),'Input, expected, root or non-timing descriptor changed'
    manifest=json.loads((B/'fixtures.json').read_text())
    sim=read(B/'sim.log');assert 'TOTAL cases=454 errors=0 PASS' in sim
    four=read(B/'four_state.log');assert 'FOUR_STATE TOTAL cases=16 PASS' in four
    assert 'A_CG_SYNTH_DONE' in read(B/'vivado.log')
    assert 'A_CG_AUDIT_DONE' in read(B/'audit.log')
    audit=read(B/'synth/audit.txt')
    for value in ('ROOT_RAMB18=16','DATA_RAMB18=32','DSP48=64','BLACKBOX=0'):assert value in audit
    sp=importlib.util.spec_from_file_location('oldreport',ROOT/'experiments/a_cg/report.py')
    old=importlib.util.module_from_spec(sp);sp.loader.exec_module(old)
    resource=old.utilization(B/'synth/util.rpt')
    timing=read(B/'synth/timing.rpt')
    wns=float(re.search(r'WNS\(ns\).*?\n\s*-+[^\n]*\n\s*([-\d.]+)',timing,re.S)[1])
    cases=[]
    for line in sim.splitlines():
        if not line.startswith('CASE '):continue
        idx=int(line.split()[1]);metric={a:int(b) for a,b in re.findall(r'(\w+)=(\d+)',line)}
        c=dict(manifest[idx],case=idx,kernel_cycles=metric['cycles'],all_host_cycles=metric['all_host_cycles'])
        assert c['kernel_cycles']==c['model_cycles']
        assert metric['errors']==0
        cases.append(c)
    assert len(cases)==454
    app=json.loads((B/'application/application_results.json').read_text());calls=json.loads((B/'application/rtl_records.json').read_text())
    assert calls['calls']==74
    assert len(app['independent_verification'])==4 and all(x['valid']==0 and x['wrong_message']!=0 for x in app['independent_verification'])
    assert all(x['code']==7 for x in app['negative_live_input'])
    mapping=json.loads((B/'host_map_equivalence.json').read_text());assert mapping['result']=='PASS'
    result=dict(date='2026-11-02',kind='isolated tuning RTL, simulation and full OOC synthesis',resource=resource,
        baseline_resource=baseline['resource'],LUT_saved=baseline['resource']['LUT']-resource['LUT'],
        budget_margin=35000-resource['LUT'],synth_WNS_ns=wns,clock_ns=5,clock_set_after_synthesis=True,
        post_route=False,cases=cases,numeric_cases=454,four_state_cases=16,
        identical_input_root_expected_payload=True,host_mapping_equivalence=mapping,
        application=app,application_records=calls,
        changes=['FFT128 BF issue interval 48 -> 45, same products/rounding/precision.',
                 'One shared base host map plus two GF(2) basis vectors instead of four word maps.'],
        limitations=['Both changes measured together; no isolated area ablation.',
                     'Same one-context root cache and transaction-level host interface as baseline.',
                     'Only four transform kernels substituted in C; other PQC kernels remain C.',
                     'No place/route, measured Fmax or full-algorithm speedup.'])
    paths=[p for p in HERE.rglob('*') if p.is_file() and '__pycache__' not in str(p)]
    paths += [B/p for p in ('fixtures.bin','fixtures.json','sim.log','four_state.log','host_map_equivalence.json',
              'synth/util.rpt','synth/util_hier.rpt','synth/timing.rpt','synth/audit.txt','synth/synthesized.dcp',
              'application/application_results.json','application/rtl_records.json','app_N512_output.bin','app_N1024_output.bin')]
    result['sha256']={p.relative_to(ROOT).as_posix():sha(p) for p in paths}
    out=ROOT/'study/results';(out/'a_cg_tune.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    def pick(cs,fft,fmt,q=0,native=0,inv=0):
        return next(c for c in cs if (c['fft'],c['fmt'],c['q'],c['logn'],c['hmin'],c['native'],c['inverse'])==(fft,fmt,q,10,0,native,inv))
    lines=['# Tuning sau bản 34.062 LUT','',
        f'**Đo mới: {resource["LUT"]:,} LUT, giảm {result["LUT_saved"]:,} LUT, còn {result["budget_margin"]:,} LUT dưới ngân sách 35k.**',
        'Ngày 02/11/2026. Chỉ thêm bản riêng `experiments/a_cg_tune`; không thay production, spec, PLAN hoặc bản 34.062 LUT.','',
        '## Hai thay đổi','',
        '1. FFT128 cấp BF mỗi 45 thay vì 48 chu kỳ. Ba tích thật ×15 tích con =45 lượt trên bộ nhân32×32; bỏ ba nhịp trống. Giữ nguyên 3M, thứ tự tích, bit giữ lại, carry, rounding và precision.',
        '2. Host map word0 một lần, tạo word1/2/3 bằng XOR hai vector cơ sở. Giữ nguyên layout, giao thức, cổng RAM, bank grouping và xử lý N nhỏ.','',
        'Số LUT là của bản kết hợp hai thay đổi; chưa đo ablation riêng để gán toàn bộ mức giảm cho host mapping.','',
        '## Tài nguyên toàn core','',
        '| Tài nguyên | Bản trước | Bản thử mới |','|---|---:|---:|']
    for k in ('LUT','FF','DSP','RAMB18','RAMB36'):lines.append(f'| {k} | {baseline["resource"][k]:,} | {resource[k]:,} |')
    lines += ['',f'Vivado2018.1, xczu7ev-ffvc1156-2-e, OOC synthesis, cùng setting baseline. WNS sau synth {wns:+.3f} ns tại clock báo cáo 5 ns; clock vẫn được đặt sau synth, chưa place/route hoặc xác nhận Fmax. Root/host/data/16 engine đều được tính.',
        'Checkpoint: 16 root RAMB18 +32 data RAMB18, 64 DSP, 0 black box.','',
        '## Chu kỳ RTL N1024','',
        '| Kernel | Bản trước | Bản thử mới |','|---|---:|---:|']
    for fft,fmt,q,native,inv,label in [(0,0,12289,0,0,'NTT q12289'),(1,0,0,0,0,'FFT32'),(1,1,0,0,0,'FFT64 generic'),
            (1,1,0,1,0,'FFT64 NTRUGen'),(1,1,0,1,1,'IFFT64 NTRUGen'),(1,2,0,0,0,'FFT128 R8'),(1,2,0,0,1,'IFFT128 R8')]:
        a=pick(baseline['cases'],fft,fmt,q,native,inv);b=pick(cases,fft,fmt,q,native,inv)
        lines.append(f'| {label} | {a["kernel_cycles"]:,} | {b["kernel_cycles"]:,} |')
    a=pick(baseline['cases'],1,2);b=pick(cases,1,2)
    lines += ['',f'FFT128 giảm {a["kernel_cycles"]-b["kernel_cycles"]} chu kỳ ({100*(1-b["kernel_cycles"]/a["kernel_cycles"]):.2f}%), speedup {a["kernel_cycles"]/b["kernel_cycles"]:.3f}× ở cùng clock.',
        f'Toàn giao dịch FFT128, gồm cold root/input/readback: {a["all_host_cycles"]:,} → {b["all_host_cycles"]:,} chu kỳ. Không phải tăng tốc toàn thuật toán ký.',
        'FFT N1024 ở đây là 1.024 thành phần scalar =512 điểm phức. Các chế độ ngoài FFT128 giữ chu kỳ như baseline.','',
        '## Correctness và kiểm chứng','',
        '- 454/454 ca Verilator, 16/16 ca Icarus khớp; có assertion số BF sống, request/phase, host bank conflict và same-edge RAW.',
        '- Root, input và expected payload của cả 454 ca giống nguyên bit với bản 34.062 LUT; chỉ descriptor timing được đổi. C/vector reference không sửa.',
        '- Ánh xạ affine bank/row/phase khớp ánh xạ full-index cũ trên 240 cấu hình, 81.836 word hợp lệ.',
        '- 74 output transform từ RTL mới được C R8 tiêu thụ qua live-input checking; bốn chữ ký N512/N1024 được verifier độc lập chấp nhận; 14 artifact khớp byte với C gốc. Sửa live input bị BRIDGE_FAIL ở cả hai kích thước.',
        '- Chỉ FFT/IFFT/NTT/INTT được thay trong co-sim; các kernel khác, sampler và NTRUGen keygen còn C. Chưa phải full-PQC hardware, formal proof hoặc chuẩn hóa bảo mật.','',
        '## Dư địa còn lại','',
        'Với 16 engine, lịch hiện tại cần 103.680 tích con cho FFT128 N1024, cận dưới tính toán 6.480 chu kỳ. Kết quả 6.508 chỉ còn cao hơn 28 chu kỳ. NTT32 N1024 có cận ba lượt nhân/BF là 960, hiện 985. Các cận này có điều kiện giữ số engine và cách tính hiện tại.',
        'Tăng tốc lớn hơn cần thay năng lực tính hoặc cách phục vụ workload: ví dụ packed16 NTT cho q nhỏ, batch các transform nhỏ độc lập, hoặc thay cấu trúc số học có chứng minh tương đương. Chưa đo các hướng đó, chưa hứa mức LUT/speedup.',
        'Giảm LUT tiếp nên nhắm mapper/operand mux, metadata và buffer còn lặp; không thể lấy các số sau flatten/rebuild của riêng một tile làm chi phí thật độc lập của tile ấy.','',
        '## Tệp','',
        '- [Source và chạy lại](../../experiments/a_cg_tune/README.md).',
        '- [Utilization](../build/a_cg_tune/synth/util.rpt), [timing](../build/a_cg_tune/synth/timing.rpt), [audit](../build/a_cg_tune/synth/audit.txt).',
        '- [JSON số đo, mọi ca kiểm và SHA256](a_cg_tune.json).','']
    (out/'a_cg_tune.md').write_text('\n'.join(lines),encoding='utf-8')
    print(json.dumps(dict(resource=resource,LUT_saved=result['LUT_saved'],margin=result['budget_margin'],WNS=wns,
                         FFT128_cycles=b['kernel_cycles'],cold_cycles=b['all_host_cycles']),indent=2))


if __name__=='__main__':main()
