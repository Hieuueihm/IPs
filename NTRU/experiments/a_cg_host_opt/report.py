"""Collect verified synthesis-only studies from the newly accepted baseline."""
from pathlib import Path
import hashlib
import importlib.util
import json
import re

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
B=ROOT/'study/build/a_cg_host_opt'
V=('direction','fields','prepare','prepare_local','select','prepare_split','select_split')

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
sp=importlib.util.spec_from_file_location('accepted_report',ROOT/'experiments/a_cg_timing/report.py')
old=importlib.util.module_from_spec(sp);sp.loader.exec_module(old)
read=old.read

def main():
    manifest=json.loads((ROOT/'experiments/a_cg_host_baseline/manifest.json').read_text())
    evidence=ROOT/manifest['evidence'];assert sha(evidence)==manifest['evidence_sha256']
    accepted=json.loads(evidence.read_text(encoding='utf-8'))
    for p,h in manifest['source_sha256'].items():assert sha(ROOT/p)==h,('Baseline changed',p)
    for p,h in manifest['production_sha256'].items():assert sha(ROOT/p)==h,('Production changed',p)
    assert sha(HERE/'clock.xdc')==manifest['clock_xdc_sha256']
    proof=json.loads((B/'geometry_proof.json').read_text())
    assert proof['result']=='PASS' and proof['geometry_count']==328 and proof['one_valid_word_per_bank_phase']
    assert 'FFT_SPLIT_EQUIVALENCE cases=100256 PASS' in read(B/'split_check/result.log')
    ref_sim=old.parse_sim(ROOT/'study/build/a_cg_timing/host/sim.log')
    gold=json.loads((ROOT/'study/build/a_cg_batch/fixtures.json').read_text())
    packed_evidence=json.loads((ROOT/'study/results/a_cg_batch.json').read_text(encoding='utf-8'))
    assert sha(ROOT/'study/build/a_cg_batch/fixtures.bin')==packed_evidence['sha256']['study/build/a_cg_batch/fixtures.bin']
    baseline=next(r for r in accepted['results'] if r['variant']=='host')
    rows=[];hashes={}
    for v in V:
        d=B/v;s=d/'synth'
        assert f'TIMING_SYNTH_DONE variant={v}' in read(d/'vivado.log'),('Incomplete synthesis',v)
        r=old.resource(s/'util.rpt');t=old.summary(s/'timing.rpt')
        assert r['DSP']==64 and r['RAMB18']==48 and r['RAMB36']==0
        metrics=read(s/'metrics.txt')
        for q in ('ROOT_RAMB18=16','DATA_RAMB18=32','DSP48=64','BLACKBOX=0'):assert q in metrics,(v,q)
        internal={k:float(re.search(label+r'=([-\d.]+)',metrics)[1]) for k,label in
            [('WNS_ns','REGISTER_TO_REGISTER_WNS_NS'),('WHS_ns','REGISTER_TO_REGISTER_WHS_NS')]}
        text=read(s/'timing.rpt')
        assert 'There are 0 input ports with no input delay specified.' in text
        assert 'There are 0 ports with no output delay specified.' in text
        assert re.search(r'User Uncertainty\s+\(UU\):\s+0\.100ns',text)
        sim=old.parse_sim(d/'sim.log');prepared=v in ('prepare','prepare_local','prepare_split')
        for i,c in enumerate(sim):
            assert c['cycles']==ref_sim[i]['cycles']==gold[i]['model_cycles'],(v,i,'kernel change')
            delta=2*((gold[i]['words']+3)//4) if prepared else 0
            assert c['all_host_cycles']-ref_sim[i]['all_host_cycles']==delta,(v,i,'host delta')
        four=0
        if v!='prepare_local':
            assert 'FOUR_STATE TOTAL cases=38 PASS' in read(d/'four_state.log'),('Four-state incomplete',v)
            four=38
        else:
            assert (HERE/'prepare/rtl/a_cg_fast.sv').read_bytes()==(HERE/'prepare_local/rtl/a_cg_fast.sv').read_bytes()
            spec=importlib.util.spec_from_file_location('baseline_builder',ROOT/'experiments/a_cg_timing/build.py')
            builder=importlib.util.module_from_spec(spec);spec.loader.exec_module(builder)
            assert (HERE/'prepare_local/rtl/tile_a.sv').read_text()==builder.local((HERE/'prepare/rtl/tile_a.sv').read_text())
        app=json.loads((d/'application/application_results.json').read_text())
        calls=json.loads((d/'application/rtl_records.json').read_text())
        assert calls['calls']==74 and len(app['artifacts_sha256'])==14
        assert len(app['independent_verification'])==4 and all(x['valid']==0 and x['wrong_message']!=0 for x in app['independent_verification'])
        assert all(x['code']==7 for x in app['negative_live_input'])
        if v in ('prepare_split','select_split'):
            assert len(re.findall(r'^\|\s*u_fft_ct\s*\|',read(s/'util_hier.rpt'),re.M))==16,'Dedicated FFT stage not preserved'
        row=dict(variant=v,resource=r,full_timing=t,internal_timing=internal,
            delta_LUT=r['LUT']-baseline['resource']['LUT'],
            delta_internal_WNS_ns=round(internal['WNS_ns']-baseline['internal_timing']['WNS_ns'],3),
            critical_internal_path=old.path(s/'internal_paths.rpt'),numeric_cases=1026,
            four_state_cases=four,four_state_note='Same prepared core; tile differs only in configuration attributes' if not four else 'Direct run',
            added_host_roundtrip_cycles_per_line=2 if prepared else 0,kernel_cycles_identical=True,
            application=app,application_records=calls,cases=[dict(case=i,**c) for i,c in enumerate(sim)])
        rows.append(row)
        paths=list((HERE/v/'rtl').glob('*'))+[d/'sim.log',d/'vivado.log',d/'application/application_results.json',d/'application/rtl_records.json',d/'app_N512_output.bin',d/'app_N1024_output.bin']
        paths += [s/f for f in ('util.rpt','util_hier.rpt','timing.rpt','metrics.txt','internal_paths.rpt','control_fanout.txt','synthesized.dcp')]
        if four:paths.append(d/'four_state.log')
        hashes.update({p.relative_to(ROOT).as_posix():sha(p) for p in paths})
    more=[p for p in HERE.glob('*') if p.is_file()]+[B/'geometry_proof.json',B/'split_check/result.log',ROOT/'experiments/a_cg_host_baseline/manifest.json',ROOT/'experiments/BASELINE.md',evidence,ROOT/'experiments/a_cg_timing/report.py']
    hashes.update({p.relative_to(ROOT).as_posix():sha(p) for p in more})
    result=dict(kind='synthesis-only follow-up',accepted_baseline=manifest,baseline_resource=baseline['resource'],
        baseline_internal_timing=baseline['internal_timing'],baseline_full_timing=baseline['full_timing'],
        baseline_not_overwritten=True,production_RTL_changed=False,place_route=False,clock_ns=5,
        results=rows,geometry_proof=proof,FFT_adder_equivalence_cases=100256,sha256=hashes,
        limitations=['All timing is unplaced synthesis estimation; no measured Fmax or physical timing closure.',
            'I/O max/min 1/0 ns and clock uncertainty 0.100/0.050 ns are common assumptions, not board constraints.',
            'The 0.006 ns changes of several variants are too small to claim a material timing improvement.',
            'Prepared host variants add one load and one read cycle per line relative to the accepted registered-host baseline.',
            'Application replay substitutes FFT/IFFT/NTT/INTT only; other PQC kernels remain in C.',
            'Static address proof covers all accepted geometries, not arbitrary invalid internal register states.'])
    out=ROOT/'study/results';(out/'a_cg_host_opt.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    lines=['# Tối ưu timing tiếp từ baseline host đã chấp nhận','',
        'Baseline đã được chốt tại `experiments/a_cg_host_baseline/rtl/`, có manifest và sổ `experiments/BASELINE.md`. Các thử nghiệm sau không tự thay baseline hay RTL chính. Giữ packed16, FFT32/64/128, native64 và NTT đa modulus. Chỉ synth.','',
        '| Bản | LUT | Δ LUT | FF | WNS nội bộ | Δ WNS | WNS gồm I/O | Host thêm so baseline |',
        '|---|---:|---:|---:|---:|---:|---:|---|',
        f'| Baseline host | {baseline["resource"]["LUT"]:,} | 0 | {baseline["resource"]["FF"]:,} | {baseline["internal_timing"]["WNS_ns"]:+.3f} ns | 0 | {baseline["full_timing"]["WNS_ns"]:+.3f} ns | 0 |']
    for r in rows:
        lines.append(f'| {r["variant"]} | {r["resource"]["LUT"]:,} | {r["delta_LUT"]:+,} | {r["resource"]["FF"]:,} | {r["internal_timing"]["WNS_ns"]:+.3f} ns | {r["delta_internal_WNS_ns"]:+.3f} ns | {r["full_timing"]["WNS_ns"]:+.3f} ns | {r["added_host_roundtrip_cycles_per_line"]} chu kỳ/dòng nạp+đọc |')
    lines += ['', 'Tất cả: 64 DSP, 48 RAMB18 (32 data + 16 root), không blackbox. Cùng XDC 5 ns đọc trước synth, cùng part và flow. Baseline dùng lại số đo đã đóng băng; RTL sao chép byte-identical và hash được kiểm tra. Không so với flow cũ tạo clock sau synth.','',
        '## Các thay đổi','',
        '- direction: chốt hướng đọc/ghi lúc nhận yêu cầu; geometry không cần đợi giải mã trạng thái FSM.',
        '- fields: ghép các trường row, plane, buffer và far-half không chồng bit bằng OR.',
        '- prepare: chốt bank/row/phase/OOB cho bốn word trong HPREP rồi mới phục vụ RAM. Không thêm chu kỳ kernel; thêm một chu kỳ cho mỗi lệnh nạp hoặc đọc host.',
        '- prepare_local: host có bước chuẩn bị cộng thuộc tính giữ register cấu hình cục bộ đã thử trước.',
        '- select: chốt hướng, giải mã hit bank một lần cho cả đọc/ghi; chọn word bằng OR song song dưới điều kiện một hit. Không lưu one-hot bank trong pipeline.',
        '- prepare_split: thêm bộ cộng/trừ wrap32 riêng cho FFT forward ở đầu ra; GS/NTT vẫn dùng khối chung, FFT GS có raw bypass. Không thêm tầng pipeline hay bộ nhân. Carry/borrow forward lấy từ đúng bộ cộng mới; inverse rounding và thứ tự tích giữ nguyên.','',
        '- select_split: cùng bộ cộng FFT tách riêng, ghép với chọn word host song song, không có HPREP và không tăng host cycles.','',
        '## Vì sao thử tách bộ cộng FFT','',
        'Sau các thay đổi địa chỉ, đường chậm chuyển sang input register của tile → kết quả FFT, có 19 mức logic và 12 CARRY8. Chỉ tiếp tục thêm bước host không giải quyết được giới hạn đó. Bản split nhắm vào đường này, đổi thêm LUT để giảm chuỗi dùng chung; không dùng false path hoặc giảm precision.','',
        '## Tính đúng và chu kỳ','',
        '- Mỗi biến thể qua 1.026 ca cùng input/root/expected đóng băng. Mọi chu kỳ kernel trùng baseline.',
        '- direction, fields, prepare, select và prepare_split qua trực tiếp 38 ca bốn trạng thái. prepare_local có cùng core byte-identical với prepare, tile chỉ khác thuộc tính; cũng qua riêng 1.026 ca và replay C.',
        '- Mỗi biến thể qua 74 lần gọi transform từ C, 4 chữ ký verify, 14 artifact khớp từng byte và ca sửa đầu vào bị từ chối.',
        f'- Chứng minh vét hết {proof["geometry_count"]} geometry: {proof["row_compositions"]} tổ hợp trường hàng, {proof["far_compositions"]} far-offset và {proof["host_word_mappings"]} ánh xạ word. Không có hai word hợp lệ trùng bank trong một pha.',
        '- Hai bộ cộng FFT của bản split khớp bộ cũ q=0 trong 100.256 phép thử biên/ngẫu nhiên, gồm carry/borrow và bit dấu. Shared raw module byte-identical với bản đã kiểm trước.',
        '- Kernel ví dụ vẫn: packed q12289 N1024 =505, packed q3329 N256 hmin1 =217, FFT128 N1024 =6508.','',
        '## Chi phí host (cùng driver)','',
        '| Trường hợp | Kernel | Cold baseline | Cold prepare/prepare_split |',
        '|---|---:|---:|---:|']
    prep=next(r for r in rows if r['variant']=='prepare')
    for fft,fmt,ln,hm,q,packed in [(0,0,10,0,12289,1),(0,0,8,1,3329,1),(1,2,10,0,0,0)]:
        i=next(i for i,c in enumerate(gold) if (c['fft'],c['fmt'],c['logn'],c['hmin'],c['q'],c['packed'],c['jobs_log'],c['inverse'],c['native'])==(fft,fmt,ln,hm,q,packed,0,0,0))
        c=ref_sim[i];z=prep['cases'][i];label='FFT128 N1024' if fft else f'Packed NTT q={q} N={1<<ln}'
        lines.append(f'| {label} | {c["cycles"]} | {c["all_host_cycles"]} | {z["all_host_cycles"]} |')
    lines += ['', 'direction, fields và select giữ nguyên cả cold cycles. Chưa suy ra tăng tốc toàn ứng dụng từ WNS synth.','', '## Đường chậm từng bản','']
    for r in rows:
        p=r['critical_internal_path'];lines.append(f'- {r["variant"]}: `{p["source"]}` → `{p["destination"]}`; {p["data_path"]}; {p["levels"]}.')
    lines += ['', '## Giới hạn','',*['- '+x for x in result['limitations']],
        '- Hold I/O của mô hình tạm còn âm; setup/hold nội bộ ghi riêng. Không coi slack setup dương là xác nhận clock vật lý.',
        '', 'Lệnh tái lập và phạm vi biến thể: `experiments/a_cg_host_opt/README.md`. JSON kèm hash nguồn/checkpoint và từng ca đo.']
    (out/'a_cg_host_opt.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps([dict(variant=r['variant'],resource=r['resource'],internal=r['internal_timing'],full=r['full_timing']) for r in rows],indent=2))

if __name__=='__main__':main()
