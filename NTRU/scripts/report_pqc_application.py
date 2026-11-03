"""Audit and document the actual RTL -> live C application substitution test."""
from collections import Counter
import hashlib
import json
import re
from arith_experiment_common import ROOT,check_hashes,hashes


def main():
    result=json.loads((ROOT/'study/results/pqc_application.json').read_text())
    check_hashes(result['source_sha256']);check_hashes(result['evidence_sha256'])
    assert result['mismatches']==0
    assert len(result['applications'])==len(result['independent_original_C_verifier'])==4
    assert all(x['valid']==0 and x['wrong_message']!=0 for x in result['independent_original_C_verifier'])
    assert all(result['negative_controls'].values())
    # Independently bind every emitted output word to its exact vector file,
    # preserve both input/output digests and the successful TB log.
    build=ROOT/'study/build/pqc_application';batch_evidence=[];total=0
    for marker in sorted((build/'rtl').glob('batch_*_result.json')):
        obj=json.loads(marker.read_text());check_hashes(obj['source_sha256'])
        stem=marker.name.removesuffix('_result.json')
        vectors=marker.parent/(stem+'.txt');actual=marker.parent/(stem+'_actual.txt');log=marker.parent/(stem+'.log')
        assert hashlib.sha256(actual.read_bytes()).hexdigest()==obj['actual_sha256']
        vec=vectors.read_text().splitlines();out=actual.read_text().splitlines()
        assert len(vec)==len(out)==obj['stats']['transactions']
        for i,(v,a) in enumerate(zip(vec,out)):
            fields=v.split();index,value=a.split()
            assert len(fields)==10 and int(index)==i and int(fields[7],16)==int(value,16)
        assert f'PASS transactions={len(vec)} ' in log.read_text()
        vector_hash=hashlib.sha256(vectors.read_bytes()).hexdigest()
        if 'vectors_sha256' in obj:assert obj['vectors_sha256']==vector_hash
        else:
            assert vectors.stat().st_mtime<=marker.stat().st_mtime
            obj['vectors_sha256']=vector_hash
            marker.write_text(json.dumps(obj,indent=2)+'\n')
        batch_evidence.extend(str(p.relative_to(ROOT)) for p in (vectors,actual,log,marker))
        total+=len(vec)
    assert total==result['unique_rtl_transactions']
    manifest=json.loads((build/'c/manifest.json').read_text())
    check_hashes(manifest['harness_sha256'])
    for name,sha in manifest['source_sha256'].items():
        assert hashlib.sha256((ROOT/'third_party/r8'/name).read_bytes()).hexdigest()==sha
    summary={'source_sha256':hashes(['scripts/report_pqc_application.py']),
             'result_sha256':hashes(['study/results/pqc_application.json']),
             'rtl_batch_evidence_sha256':hashes(batch_evidence),
             'c_executable_evidence_sha256':hashes(['study/build/pqc_application/c/'+name for name in ('pqc_bridge','independent_verify','vrfy_instrumented.c')]),
             'transactions_audited':total,
             'all_live_kernel_inputs_checked_by_C':True,'all_supported_kernel_outputs_match_original_C':True,
             'all_application_artifacts_byte_identical':True,'independent_verifier_passes':4}
    recovery=build/'rtl/cache_recovery.json'
    if recovery.exists():summary['cache_recovery_receipt_sha256']=hashes([str(recovery.relative_to(ROOT))])
    (ROOT/'study/results/pqc_application_audit.json').write_text(json.dumps(summary,indent=2)+'\n')
    calls=result['array_frame_uses'];hits=result['exact_cache_hits']
    lines=['# Kiểm chứng ứng dụng PQC: C tiêu thụ kết quả từ RTL','',
           'Ngày 26/10/2026. Đã chạy luồng R8 với các kernel được hỗ trợ nhận kết quả dựng từ RTL,',
           'rồi xác minh chữ ký bằng executable C độc lập không có hook. Đây là functional co-simulation,',
           'không phải toàn bộ thuật toán ký đã được triển khai bằng RTL.',
           '', '## Kết quả ứng dụng', '',
           '| N | Thông điệp | Ký | Verify qua adapter | Verifier C độc lập | Sai thông điệp/chữ ký |',
           '|---|---:|---|---|---|---|']
    for app in result['applications']:
        lines.append(f'| {1<<app["logn"]} | {app["trial"]} | Thành công | Chấp nhận | Chấp nhận | Từ chối / từ chối |')
    lines+=['', f'- **{result["c_kernel_calls"]:,} lời gọi kernel C**, **{result["c_output_words"]:,} word đầu ra** khớp reference.',
            f'- **{result["unique_rtl_transactions"]:,} giao dịch RTL khác nhau**, dùng chung cùng `flex_stream_banked` có FIFO, stall và routing.',
            '- Khóa bí mật/công khai, expanded key và cả bốn chữ ký **giống từng byte** so với luồng C gốc dùng cùng seed.',
            '- NTT dùng bảng `GMb/iGMb` xuất trực tiếp từ C R8; không tự tái tạo root theo một quy ước khác.',
            '', '## Chính xác phần nào chạy bằng RTL?', '',
            '| Phần | RTL đang làm | Host/C đang làm |',
            '|---|---|---|',
            '| FFT/iFFT, CMUL, SPLIT, MERGE | Mọi tích thực Q64.64 của năm kernel này | Cộng/trừ wrap, thứ tự 3M, scaling và điều phối kernel |',
            '| NTT/iNTT q12289 | Butterfly CT/GS qua cụm một/hai tầng, gather/scatter bank | Sinh stage/row/request và chuyển dữ liệu giữa các pass |',
            '| Chuẩn hóa iNTT | Nhân Montgomery với R/N | Chọn hệ số chuẩn hóa |',
            '| TOMONT, MODMUL | Montgomery multiplication trên đường NTT của cùng mảng | Gom/tách các batch hệ số |',
            '| Phần còn lại của ứng dụng | Chưa đưa lên RTL | Sampling, chia, SHAKE, codec, NTRUGen keygen và các phép ngoài nhóm kernel đã thay |',
            '', 'Số giao dịch duy nhất theo phần tính:', '',
            '| Loại frame | Số lượt sử dụng | Input trùng được tái dùng chính xác | Giao dịch RTL duy nhất |',
            '|---|---:|---:|---:|']
    for kind,count in calls.items():lines.append(f'| {kind} | {count:,} | {hits.get(kind,0):,} | {count-hits.get(kind,0):,} |')
    lines+=['', 'Tái dùng chỉ áp dụng cho các input giống hệt; không lượng tử hóa hay xấp xỉ. Các frame duy nhất',
            'được trộn và chạy qua cùng pipeline có backpressure. Số cycle mô phỏng có bubbles/stall kiểm thử,',
            'không dùng làm latency hoặc speedup của thuật toán ký.',
            '', '## Vì sao đây là kiểm chứng ứng dụng mạnh hơn replay vector riêng?', '',
            '1. Capture chạy reference để ghi input/output và các artifact gốc.',
            '2. Host adapter phân rã kernel thành frame của mảng RTL. Đầu ra thực từ simulator được dùng để dựng lại kernel,',
            '   bao gồm việc đưa kết quả RTL tầng NTT trước vào input tầng sau.',
            '3. C chạy lại từ keygen với cùng seed. Tại từng lời gọi, wrapper kiểm toàn bộ input **đang chạy**; khớp mới nhận output từ RTL-backed file.',
            '   Nhánh replay không gọi kernel C đã thay và không có fallback khi thiếu record.',
            '4. Chính luồng C này tạo chữ ký, sau đó verifier gốc độc lập xác minh. Các artifact được so byte với baseline.',
            '', 'Trace được cố định để co-simulation theo hai lượt. Đây là liên kết chức năng qua file, không phải giao tiếp bus',
            'trực tiếp hay hệ thống tăng tốc thời gian thực. Việc kiểm input sống và cấm fallback giúp tránh chỉ kiểm vector',
            'bên ngoài trong khi signer vẫn dùng kết quả kernel C.',
            '', '## Kiểm soát âm và provenance', '',
            '- Thông điệp sửa một byte bị cả đường adapter và verifier độc lập từ chối.',
            '- Chữ ký sửa một bit bị từ chối; trường hợp decoder phát hiện sai format có thể dừng trước NTT.',
            '- Sửa một word input trong file thay thế khiến C dừng với `BRIDGE_FAIL`, không tiếp tục bằng C reference.',
            '- Sửa một bit kết quả nhân RTL bị phát hiện ở ranh giới output kernel.',
            '', f'Reference pin tại `{result["commit"]}`; `FALCON_FPR_MODE=2`, scalar/AVX2=0, GCC Linux LP64.',
            'Checkout reference không đổi. NTT static được nối hook bằng bản TU sinh trong build: chỉ đổi bốn tên định nghĩa,',
            'giữ nguyên lời gọi và thân số học, rồi thêm wrapper capture/replay bên ngoài. Verifier độc lập dùng `vrfy.c` gốc.',
            'SHA256 của source, TU sinh, vector, kết quả RTL, file thay thế và artifact nằm trong các manifest/JSON.',
            '', '## Giới hạn còn lại', '',
            '- Kết quả hiện xác nhận **pinned R8 Falcon, Q64.64/q12289, N512/N1024**, mỗi kích thước một khóa và hai thông điệp.',
            '- FFT32/64 chưa được xác nhận bằng reference PQC precision thấp; q3329 chưa có kiểm chứng ứng dụng Kyber/ML-KEM.',
            '- Chưa có full FFT butterfly/controller/RAM bằng RTL, hardware signer hoặc phép đo toàn ứng dụng trên FPGA.',
            '- Không suy ra tuân thủ toàn bộ chuẩn FN-DSA, constant-time phần cứng hoặc khả năng chống side-channel từ thử nghiệm này.',
            '- Kết quả đúng trên tập kiểm thử không thay thế proof cho mọi input.',
            '', '## Chạy lại và dữ liệu', '',
            '~~~powershell','python -X utf8 scripts/validate_pqc_application.py','python -X utf8 scripts/report_pqc_application.py','~~~',
            '', '`--reuse-capture` tái dùng capture sau khi kiểm hash C/harness. Mô phỏng mặc định tối đa ba process;',
            '`--jobs 1` chạy tuần tự. Batch cache kiểm input/output và hash RTL/testbench trước khi dùng lại.',
            '', '- [Kết quả ứng dụng](../study/results/pqc_application.json).',
            '- [Audit từng batch RTL](../study/results/pqc_application_audit.json).',
            '- [Adapter kernel](../model/pqc_kernel_adapter.py), [driver](../scripts/validate_pqc_application.py), [C bridge](../sim/ref/r8_pqc_cosim.c).']
    (ROOT/'docs/pqc_application_cosim.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    p=ROOT/'ARCHITECTURE.md';content=p.read_text(encoding='utf-8')
    note=('> Kiểm chứng ứng dụng R8: bốn chữ ký N512/N1024 qua kernel RTL-backed, khớp byte C gốc và được verifier C độc lập chấp nhận. '
          '[Phạm vi và bằng chứng](docs/pqc_application_cosim.md).\n')
    content=re.sub(r'^> Kiểm chứng ứng dụng R8:.*\n','',content,flags=re.M)
    content=content.replace('\n\n','\n\n'+note,1)
    heading='## 17. Kiểm chứng ứng dụng PQC qua adapter C/RTL'
    if heading in content:content=content.split(heading)[0].rstrip()+'\n'
    content+='\n'+heading+'\n\n'+f'''[Báo cáo](docs/pqc_application_cosim.md), [kết quả](study/results/pqc_application.json),
[audit RTL](study/results/pqc_application_audit.json).

Đã chạy hai thông điệp cho mỗi N512/N1024. C tiêu thụ kết quả kernel dựng từ RTL,
tạo bốn chữ ký khớp từng byte baseline và được verifier C gốc độc lập chấp nhận.
Thông điệp/chữ ký sửa bị từ chối. Có {result['c_kernel_calls']:,} lời gọi kernel,
{result['unique_rtl_transactions']:,} giao dịch RTL duy nhất; không sai khác output kernel.

FFT128: phép nhân thực Q64.64 ở RTL; 3M/add/sub/scaling và điều phối ở host.
NTT/iNTT q12289: butterfly một/hai tầng và routing ở RTL; stage/row controller ở host.
Chuẩn hóa iNTT, TOMONT và MODMUL cũng dùng Montgomery RTL. Các frame chạy trên
cùng mảng banked có FIFO/stall; input trùng được tái dùng chính xác.

C replay kiểm mọi input sống, không gọi lại kernel đã thay và không fallback.
Trace cố định qua file là co-simulation chức năng, không phải bus accelerator thời gian thực.
Đã có C differential trên NTT q12289 và chứng cứ ứng dụng cho nhóm kernel này;
FFT32/64, ứng dụng q3329, full RTL controller và signoff/side-channel vẫn ngoài kết quả.
'''
    p.write_text(content,encoding='utf-8')
    p=ROOT/'docs/numeric_contract.md';content=p.read_text(encoding='utf-8')
    note='> Cập nhật ứng dụng: [C tiêu thụ kernel RTL-backed và verifier độc lập chấp nhận chữ ký](pqc_application_cosim.md).\n\n'
    content=re.sub(r'^> Cập nhật ứng dụng:.*\n\n','',content,flags=re.M)
    content=content.replace('\n\n','\n\n'+note,1);p.write_text(content,encoding='utf-8')
    print('PASS: application/RTL evidence audited; report and architecture updated')


if __name__=='__main__':main()
