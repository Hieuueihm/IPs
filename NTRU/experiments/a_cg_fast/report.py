"""Measured summary of the final isolated prototype, with provenance guards."""
import hashlib
import importlib.util
import json
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
BUILD=ROOT/'study/build/a_cg_fast'
OUT=ROOT/'study/results'


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def text(p):
    b=p.read_bytes();return b.decode('utf-16' if b.startswith((b'\xff\xfe',b'\xfe\xff')) else 'utf-8-sig')


def main():
    def load(name,p):
        sp=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m);return m
    base=load('base_report',ROOT/'experiments/a_cg/report.py')
    resource=base.utilization(BUILD/'synth/util.rpt')
    assert resource['LUT']<35000,resource
    assert 'A_CG_SYNTH_DONE' in text(BUILD/'vivado.log')
    audit=text(BUILD/'synth/audit.txt')
    for item in ('ROOT_RAMB18=16','DATA_RAMB18=32','DSP48=64','BLACKBOX=0'):assert item in audit,item
    assert 'A_CG_AUDIT_DONE' in text(BUILD/'audit.log')
    manifest=json.loads((BUILD/'fixtures.json').read_text());sim=text(BUILD/'sim.log')
    assert f'TOTAL cases={len(manifest)} errors=0 PASS' in sim
    four=text(BUILD/'four_state.log');n4=int(re.search(r'FOUR_STATE TOTAL cases=(\d+) PASS',four)[1])
    cases=[]
    for line in sim.splitlines():
        if not line.startswith('CASE '):continue
        idx=int(line.split()[1]);metric={a:int(b) for a,b in re.findall(r'(\w+)=(\d+)',line)}
        assert metric['errors']==0
        cases.append(dict(case=idx,**manifest[idx],kernel_cycles=metric['cycles'],
                          all_host_cycles=metric['all_host_cycles'],root_writes=metric['root_writes']))
    assert len(cases)==len(manifest)==454
    assert all(c['kernel_cycles']==c['model_cycles'] for c in cases)
    application=json.loads((BUILD/'application/application_results.json').read_text())
    records=json.loads((BUILD/'application/rtl_records.json').read_text())
    assert records['calls']==74
    assert len(application['independent_verification'])==4
    assert all(c['valid']==0 and c['wrong_message']!=0 for c in application['independent_verification'])
    assert len(application['negative_live_input'])==2 and all(c['code']==7 for c in application['negative_live_input'])
    production=json.loads((BUILD/'production_hashes.json').read_text())
    assert all(sha(ROOT/p)==h for p,h in production.items()),'Production HDL changed'
    original=json.loads((OUT/'a_cg_prototype.json').read_text(encoding='utf-8'))
    for f in ('rtl/a_cg_core.sv','rtl/tile_a.sv','rtl/mul_ss.v'):
        p=ROOT/'experiments/a_cg'/f
        assert sha(p)==original['sha256'][p.relative_to(ROOT).as_posix()],'Baseline prototype changed'
    timing=text(BUILD/'synth/timing.rpt')
    wns=float(re.search(r'WNS\(ns\).*?\n\s*-+[^\n]*\n\s*([-\d.]+)',timing,re.S)[1])
    result=dict(date='2026-11-02',kind='isolated RTL simulation, live C application replay and OOC synthesis',
        resource=resource,LUT_margin=35000-resource['LUT'],part='xczu7ev-ffvc1156-2-e',tool='Vivado2018.1',
        report_clock_ns=5,clock_set_after_synthesis=True,post_route=False,synth_WNS_ns=wns,
        numeric_cases=len(cases),native_NTRUGen64_cases=sum(c['native'] for c in cases),four_state_cases=n4,
        cases=cases,application=application,rtl_application_records=records,
        production_sha256=production,
        limitations=['One root context; host software provides valid tables, qinv and stage microcode.',
            'Core transaction ports, not AXI/DMA/DDR. Read responses have no backpressure.',
            'Only FFT/IFFT/NTT/INTT substituted in the R8 application; other kernels and native NTRUGen keygen remain in C.',
            'No full ML-KEM/ML-DSA application KAT or standards/side-channel certification.',
            'No place/route; neither Fmax nor real-time full-application speedup measured.'])
    paths=[p for p in HERE.rglob('*') if p.is_file() and '__pycache__' not in str(p)]
    paths += [BUILD/n for n in ('fixtures.bin','fixtures.json','four_state.bin','sim.log','four_state.log','vivado.log',
              'synth/util.rpt','synth/util_hier.rpt','synth/timing.rpt','synth/audit.txt','synth/synthesized.dcp',
              'application/application_results.json','application/rtl_records.json','application/transform_bridge.c',
              'app_N512_output.bin','app_N1024_output.bin')]
    result['sha256']={p.relative_to(ROOT).as_posix():sha(p) for p in paths}
    (OUT/'a_cg_fast.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    def pick(fft,fmt,q=0,ln=10,hm=0,native=0,inv=0):
        return next(c for c in cases if (c['fft'],c['fmt'],c['q'],c['logn'],c['hmin'],c['native'],c['inverse'])==(fft,fmt,q,ln,hm,native,inv))
    rows=[('NTT q12289 N1024',pick(0,0,12289),1174,5332),('NTT q3329 N256 hmin1',pick(0,0,3329,8,1),319,None),
          ('NTT q8380417 N256',pick(0,0,8380417,8),364,None),('FFT32 N1024',pick(1,0),597,4802),
          ('FFT64 generic N1024',pick(1,1),1920,10317),('FFT128 R8 N1024',pick(1,2),7113,23894)]
    lines=['# A + CG bản nhanh: số đo RTL và correctness ứng dụng','',
        f'**Đạt {resource["LUT"]:,} LUT, dưới 35.000 LUT, còn dư {35000-resource["LUT"]:,} LUT.**',
        'Ngày 02/11/2026. Bản riêng tại `experiments/a_cg_fast`. Không đổi production HDL, PLAN, spec hoặc nguyên mẫu 28.466 LUT; chưa commit.','',
        '## 1. Tài nguyên toàn top','',
        'Vivado2018.1, xczu7ev-ffvc1156-2-e, out-of-context synth, flatten rebuilt. Clock báo cáo 5 ns đặt sau synth giống các baseline. Chưa place/route hoặc đo Fmax.','',
        '| Tài nguyên | A + CG cũ | Bản nhanh + native NTRUGen |','|---|---:|---:|']
    for field,label in [('LUT','LUT tổng'),('FF','FF'),('DSP','DSP48'),('RAMB18','RAMB18'),('RAMB36','RAMB36')]:
        lines.append(f'| {label} | {original["measured"][field]:,} | {resource[field]:,} |')
    lines += ['',f'WNS sau synth **{wns:+.3f} ns** ở clock báo cáo 5 ns; I/O chưa có input/output delay. Đây không phải cam kết chạy 200 MHz sau routing.',
        'Đã mở checkpoint và đếm **32 RAMB18 data, 16 RAMB18 root, 64 DSP, 0 black box**. Cổng host/root/config còn nối vào logic. Dư địa LUT nhỏ, thêm AXI/DMA hoặc tính năng khác phải đo lại.','',
        'Lần đầu thêm đủ tính năng ra 38.700 LUT. Đã giảm bằng tăng A một lần cho cả hai nhánh GS, tái dùng operand register để giữ limb thấp, và chuyển engine nội bộ sang nhận lịch từ core. Không cắt độ chính xác, số engine hoặc khả năng precision.',
        'Mode/q chỉ đổi tại CONFIG_TILE sau reset; bộ đếm idle/admission tổng quát riêng từng engine được bỏ khỏi hardware. Assertion vẫn kiểm buffer sống ≤8/4/2, request không rơi, phase output, host bank conflict và same-edge RAW.','',
        '## 2. Chu kỳ đã đo trên RTL','',
        'Tăng tốc ở cùng clock. Kernel không gồm host/root. Toàn ca gồm config, descriptor, cold root load, input và readback; driver đọc burst. Các số không phải speedup toàn thuật toán PQC.','',
        '| Kernel | A + CG cũ | Bản nhanh | Speedup |','|---|---:|---:|---:|']
    for label,c,old,_ in rows:lines.append(f'| {label} | {old:,} | {c["kernel_cycles"]:,} | {old/c["kernel_cycles"]:.2f}× |')
    nf,ni=pick(1,1,native=1),pick(1,1,native=1,inv=1)
    lines += ['',f'**FFT64 native NTRUGen N1024:** forward {nf["kernel_cycles"]:,}, inverse {ni["kernel_cycles"]:,} chu kỳ. Đây là contract riêng, không dùng FFT64 generic thay thế.',
        'FFT N1024 là 1.024 thành phần scalar =512 điểm phức. Với N nhỏ, chọn lịch rào khi overlap không có lợi; không tự hạ precision.','',
        '| Toàn ca N1024, cold root | A + CG cũ | Bản nhanh | Speedup |','|---|---:|---:|---:|']
    for label,c,_,old in rows:
        if old:lines.append(f'| {label} | {old:,} | {c["all_host_cycles"]:,} | {old/c["all_host_cycles"]:.2f}× |')
    lines += ['',
        'Host load phase0 tại cạnh handshake, read response pipeline qua ranh giới line. Giữ layout natural: FFT32/64/128 dùng 1/2/4 lượt bank mỗi line ở N lớn; có xử lý va chạm N rất nhỏ.',
        'Root multicast chỉ gộp word32 có bit-pattern giống nhau, không nén mất bit. Cache vẫn một context; đổi q/chiều/precision/contract phải nạp đúng root và descriptor. Bảng gap host được sinh bằng model RAM đã kiểm, không phải microcode bất kỳ tự được phần cứng chứng minh an toàn.','',
        '## 3. Correctness đã xác nhận','',
        f'- **454/454 ca Verilator khớp từng word**, bao gồm 138 ca cũ, 40 ca native FFT64 NTRUGen, 176 FFT/IFFT C R8 và 100 NTT/INTT C NTRUGen (năm prime31 bit, N2..1024, hai chiều).',
        f'- **{n4}/{n4} ca Icarus bốn trạng thái** khớp bằng `!==`, gồm cả ba precision, hai chiều và native NTRUGen. Assertion buffer/phase/RAM/host đều qua.',
        '- Số chu kỳ 454 ca khớp model schedule; model không được dùng thay output RTL.',
        '- Root native NTRUGen lấy nguyên bit từ GM_TAB C; nhân floor, signed rounded-half trước nhân mỗi tầng inverse. Bộ 40 vector native đã qua, gồm 35 ca bị lệch trước đây; giữ generic FFT64 như một chế độ khác.',
        '- Không sửa reference hoặc expected vector để hợp RTL; không chuyển FFT128 signing xuống precision thấp.','',
        '## 4. C thực sự tiêu thụ output từ RTL cuối','',
        '**74 lời gọi FFT/IFFT/NTT/INTT** từ workload R8 N512/N1024 được chạy qua simulator của bản cuối, ghi raw output thật. C chạy lại cùng seed, kiểm từng live input rồi lấy output đó; không fallback về C cho bốn transform đã thay.','',
        '- Bốn chữ ký được verifier C gốc độc lập chấp nhận; thông điệp sai bị từ chối. Luồng ứng dụng cũng từ chối chữ ký sửa bit.',
        '- Khóa bí mật/công khai, expanded key, chữ ký và thông điệp giống từng byte với capture C gốc (14 artifact).',
        '- Sửa live input trong replacement bị từ chối với BRIDGE_FAIL ở cả N512/N1024; không tiếp tục bằng C reference.',
        '- Phần còn ở C: CMUL/SPLIT/MERGE, TOMONT/MODMUL, NTRUGen keygen, sampling, SHAKE, codec và các phép khác. Kiểm native FFT64 hiện là kernel với vector C, chưa phải keygen dùng RTL.',
        '- Chưa chạy full ML-KEM/ML-DSA application KAT, chưa kết luận tuân thủ toàn bộ FN-DSA/constant-time/side-channel. Kết quả trên tập kiểm thử không phải formal proof mọi input.','',
        '## 5. Tệp và chạy lại','',
        '- [Source và contract](../../experiments/a_cg_fast/README.md).',
        '- [Top RTL](../../experiments/a_cg_fast/rtl/a_cg_fast.sv), [generator tile/fixture](../../experiments/a_cg_fast/build.py).',
        '- [Utilization](../build/a_cg_fast/synth/util.rpt), [phân cấp](../build/a_cg_fast/synth/util_hier.rpt), [timing](../build/a_cg_fast/synth/timing.rpt), [checkpoint audit](../build/a_cg_fast/synth/audit.txt).',
        '- [Ứng dụng C và verifier](../build/a_cg_fast/application/application_results.json), [74 record output RTL](../build/a_cg_fast/application/rtl_records.json).',
        '- [JSON ca kiểm, số đo và SHA256](a_cg_fast.json).',
        'Chạy các lệnh trong README. Giữ source/hash/log/DCP để phân biệt kết quả đo với model và lần thử 38.700 LUT.','']
    (OUT/'a_cg_fast.md').write_text('\n'.join(lines),encoding='utf-8')
    print(json.dumps({k:result[k] for k in ('resource','LUT_margin','synth_WNS_ns','numeric_cases','four_state_cases')},indent=2))


if __name__=='__main__':main()
