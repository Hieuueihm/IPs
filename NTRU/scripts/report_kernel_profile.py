"""Render measured RTL profiling separately from analytical capacity/supply studies."""
from collections import defaultdict
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def number(n):return f'{n:,.0f}'.replace(',','.')
def pct(x):return '—' if x is None else f'{x:.2f}%'


def main():
    result_path=ROOT/'study/results/kernel_profile.json';r=json.loads(result_path.read_text())
    for path,digest in r['source_and_evidence_sha256'].items():assert sha(ROOT/path)==digest,('stale profile',path)
    supply=json.loads((ROOT/'study/results/fft_batch_supply.json').read_text())
    base=r['runs']['no_pause'];stall=r['runs']['random_pause'];a=base['overall'];b=stall['overall']
    def config(op,w,n,q=None):return next(c for c in base['by_config'] if c['op']==op and c['width_bits']==w and c['n']==n and c['q']==q)
    out=['# Profiling mức song song của core FFT/NTT',
        '', '**Kết luận:** giữ 16 tile làm baseline cho ghép FFT128; ưu tiên sửa cấp liệu và',
        'chồng lấp controller trước khi tăng số tile. FFT32/64 chưa biến precision thấp thành',
        'thông lượng cao hơn. NTT nhỏ cần gom nhiều job để lấp các tile đang bỏ trống.',
        'Chưa có phép sweep RTL 4/8/16/32 tile, nên chưa kết luận số tile tối ưu.',
        '', '## Phạm vi và cách đo', '',
        'Mỗi tile là một cụm bốn nhân 16×16. DUT hiện có 16 tile = 64 lá nhân.',
        'Wrapper quan sát chỉ đọc tín hiệu; không đổi arithmetic, RAM, FSM hoặc precision.',
        'Hai lượt chạy cùng 5.992 kernel và 325.492 word/lượt: không pause và pause giả ngẫu nhiên.',
        'Output của cả hai lượt khớp từng byte file RTL đã dùng trong phép thử C/PQC.',
        'Tổng cộng 11.984 lần chạy kernel, 650.984 word được kiểm trong profiling.',
        '', 'Cycle/kernel tính từ sau cạnh nhận START đến cạnh chuyển DONE, gồm pause khi busy;',
        'không gồm nạp dữ liệu, đọc kết quả, giữ DONE hoặc thời gian phần C còn lại.',
        'Không quy cycle thành ns, MHz hoặc tốc độ ký thực tế.',
        '', '**Định nghĩa utilization:** `assigned_leaf_products / (64 × kernel_cycles)`.',
        'Đây là mật độ công việc được giao cho lá nhân theo phân rã hiện tại. Nó không phải',
        'công suất, tỷ lệ transistor chuyển mạch hoặc tỷ lệ bit tích tối thiểu cần giữ.',
        'Một số tích limb cao của FFT bị loại theo contract; metric vẫn đếm slot được giao.',
        'Utilization khi phát frame dùng mẫu số `64 × accepted_frames`; utilization lane FFT',
        'là số real-product lane thực dùng chia cho số lane có thể dùng ở width đó.',
        '', 'Dữ liệu: [JSON](../study/results/kernel_profile.json),',
        '[CSV không pause](../study/build/kernel_profile/no_pause.csv),',
        '[CSV có pause](../study/build/kernel_profile/random_pause.csv).',
        '', '## FFT: precision thấp hiện chưa tăng tốc kernel', '',
        '| Kernel | Precision | N | Cycle/kernel | Lane dùng khi phát frame | Leaf use toàn kernel |',
        '|---|---:|---:|---:|---:|---:|']
    for op,w,n in [('FFT',w,n) for n in (512,1024) for w in (32,64,128)]+[('IFFT',128,1024)]:
        c=config(op,w,n);out.append(f'| {op} | {w} | {n} | {number(c["cycles_min"])} | {pct(c["fft_lane_use_per_fft_frame_pct"])} | {pct(c["leaf_use_over_kernel_pct"])} |')
    fft=config('FFT',128,1024)
    out += ['', 'FFT N1024 có 2.304 butterfly phức; mỗi butterfly mất **23 chu kỳ**:',
        '', '| Pha | Chu kỳ/butterfly | Tỷ trọng |','|---|---:|---:|']
    for title,states in [('Đọc 4 thành phần + chờ RAM',['FREAD','FWAIT']),
        ('Chuẩn bị, ghép 3M và chuyển butterfly',['PREP','COMBINE','ADVANCE']),
        ('Phát ba real product',['ISSUE']),('Chờ/nhận ba product',['WAITP']),('Ghi bốn thành phần',['FWRITE'])]:
        total=sum(fft['state_cycles'].get(s,0) for s in states)/fft['kernels'];per=total/2304
        out.append(f'| {title} | {per:.0f} | {pct(total/(fft["cycles"]/fft["kernels"])*100)} |')
    out += ['', 'Bộ điều khiển đọc một word mỗi lượt và chờ, tính một butterfly rồi mới ghi/chuyển',
        'butterfly tiếp theo. Đổi width vẫn phát đúng ba frame cho một complex product.',
        'FFT32 chỉ dùng 1/16 lane, FFT64 dùng 1/4; FFT128 dùng hết lane trong frame nhưng',
        'cả kernel chỉ phát frame trong 13,04% chu kỳ. Tăng multiplier khi giữ FSM này',
        'không giải quyết việc mảng không được giao việc ở các pha còn lại.',
        '', '## NTT: hai tầng có tái sử dụng, nhưng frame chưa chồng lấp', '',
        '| Kernel | q | N | Cycle/kernel | Tile hoạt động khi phát frame | Leaf use toàn kernel |',
        '|---|---:|---:|---:|---:|---:|']
    for op,q,n in [('NTT',12289,n) for n in (8,16,32,64,256,1024)]+[('NTT',3329,256),('INTT',3329,256),('INTT',12289,1024)]:
        c=config(op,16,n,q);out.append(f'| {op} | {q} | {n} | {number(c["cycles_min"])} | {pct(c["ntt_active_tiles_per_frame_pct"])} | {pct(c["leaf_use_over_kernel_pct"])} |')
    ntt=config('NTT',16,1024,12289)
    out += ['', 'Mỗi frame NTT hiện mất **10 chu kỳ**: READ 1, LATCH 1, ISSUE 1,',
        'NRESULT 5 (4 chu kỳ chưa có output + 1 nhận output), WRITE 1, ADVANCE 1.',
        'N8 chỉ kích hoạt 2/16 tile; N16 dùng 4/16, N32 dùng 8/16, từ N64 mới lấp hết',
        'tile của frame paired. Frame tail một tầng chỉ dùng nửa số nhân trong tile.',
        'Hai modulus đều dùng lane 16 bit; q nhỏ hơn chưa tự tạo thêm lane.',
        '', f'NTT q12289 N1024: {number(ntt["frames"]//ntt["kernels"])} frame, '
        f'{number(ntt["data_read_bank_beats"]//ntt["kernels"])} read và '
        f'{number(ntt["data_write_bank_beats"]//ntt["kernels"])} write word 16 bit.',
        'Đây là 5 lượt qua dữ liệu cho 10 tầng: tái sử dụng hai tầng đã hiện diện.',
        'So đếm số word với 10 lượt một tầng cho thấy giảm một nửa traffic transform;',
        'chưa phải so cycle với một RTL một tầng riêng. q3329 N256 có 7 tầng, vẫn cần',
        '4 lượt như q12289 N256 có 8 tầng; lượt tail có ít công việc hơn nhưng cùng latency.',
        '', '## Stall và FIFO', '',
        '| Metric, tổng 5.992 kernel | Không pause | Có pause |', '|---|---:|---:|']
    for name,key in [('Cycle busy','cycles'),('Pause bên ngoài','pause_cycles'),
        ('Input valid nhưng chưa ready','input_ready_blocked_cycles'),
        ('WAIT nhưng chưa có output, không pause','waiting_result_empty_cycles'),
        ('Output valid nhưng controller chưa nhận','output_backpressure_cycles'),
        ('Array bị giữ CE','array_advance_blocked_cycles'),('FIFO occupancy cực đại','fifo_peak')]:
        out.append(f'| {name} | {number(a[key])} | {number(b[key])} |')
    out += ['', f'Pause làm tổng cycle tăng {pct((b["cycles"]/a["cycles"]-1)*100)}.',
        'Các bộ đếm wait/backpressure/CE có thể chồng nhau; không cộng chúng như các',
        'nhóm stall độc lập. Pause có thể cho pipeline đã phát chạy tiếp, nên không',
        'lấy `cycle có pause − số pause` làm cycle của lượt không pause.',
        'Không pause không có input-ready stall hay output backpressure, FIFO chỉ đạt',
        'một entry. Chưa có bằng chứng tăng FIFO hoặc tăng PE giải quyết nút thắt hiện tại.',
        'FSM không có arbiter đợi bank nên không có bộ đếm bank-conflict stall riêng;',
        'không diễn giải thời gian FWAIT/NWAIT cố định thành xung đột bank.',
        '', '## Kiểm tra khả năng cấp dữ liệu cho packing FFT', '',
        'Phần này là **phân tích địa chỉ**, không phải kết quả RTL của controller mới.',
        'Duyệt toàn bộ butterfly FFT/IFFT N4..1024, ba width; batch phục vụ độc lập,',
        'mỗi bank 1R/1W, không cache root giữa các batch. Đếm đúng số row khác nhau',
        'trong từng bank và số twiddle khác nhau trong batch.',
        '[Kết quả](../study/results/fft_batch_supply.json). FFT N1024:',
        '', '| Width | Butterfly/batch đề xuất | Lượt đọc data/batch tùy tầng | Root khác nhau/batch tối đa |',
        '|---|---:|---:|---:|']
    for width in (32,64,128):
        c=next(c for c in supply['cases'] if c['n']==1024 and c['width_bits']==width and c['op']=='FFT')
        lo=min(s['data_read_rounds_min'] for s in c['stages']);hi=max(s['data_read_rounds_max'] for s in c['stages']);roots=max(s['distinct_twiddles_max'] for s in c['stages'])
        out.append(f'| {width} | {c["proposed_butterflies_per_batch"]} | {lo}–{hi} | {roots} |')
    out += ['', 'Ngay FFT128 một butterfly cũng cần 2–4 lượt đọc theo map bank hiện tại,',
        'dù tổng số word của butterfly nhỏ hơn 64: real/imag hoặc hai nhánh có thể trùng',
        'bank ở row khác nhau. FFT32 batch16 có thể cần 16 root ở tầng cuối, trong khi',
        'ROM FFT hiện chỉ đọc một complex root/cycle. Vì vậy packing không mặc nhiên',
        'cho 16×/4× speedup. Cần khảo sát lại map/gather và prefetch/cache/banking twiddle.',
        'Các số phục vụ từng batch chưa tính interleave giữa batch, dependency, buffer',
        'hoặc normalization; không dùng chúng làm dự báo cycle/kernel mới.',
        '', '## Quyết định về số tile và bước tối ưu', '',
        '| Tile ×4 lá | Slot lá 16×16 | Beat tối thiểu phát một FFT128 real product | Hệ số NTT paired/frame, chặn bởi 64 bank đọc |',
        '|---|---:|---:|---:|']
    for c in r['capacity_bounds_not_rtl_sweep']:
        out.append(f'| {c["tiles"]} | {c["leaves16x16"]} | {c["fft128_real_product_min_issue_beats"]} | {c["ntt_pair_coefficients_single_read_bound_64banks"]} |')
    out += ['', '**Bảng này chỉ là capacity theo phân rã slot hiện tại**, không phải số cycle đã',
        'mô phỏng cho các mảng nhỏ hơn/lớn hơn, không phải cận số phép nhân toán học tối thiểu.',
        'Giảm xuống 8 tile đòi hỏi thiết kế temporal fusion FFT128 và kiểm lại accumulation,',
        'rounding, latency. Tăng lên 32 tile cần controller tận dụng thêm lane và cấp dữ liệu',
        'NTT vượt giới hạn một lượt đọc 64 bank, hoặc buffering nhiều lượt; hiện chưa có.',
        '', 'Quyết định hiện tại:',
        '', '1. **Giữ 16 tile làm baseline**, chưa gắn nhãn tối ưu. Nó khớp cấu trúc ghép',
        '   một FFT128 product từ 16 tích 32×32 đã kiểm chứng.',
        '2. **Ưu tiên controller/bộ nhớ:** tách các pha đọc, tính, ghi để chồng lấp nhiều',
        '   butterfly độc lập trong tầng; cần context/tag và xử lý dependency ở ranh giới tầng.',
        '3. **FFT hẹp:** batch theo số lane thực có thể nuôi, cùng kế hoạch twiddle và map bank;',
        '   mục tiêu là chuyển việc giảm width thành tăng công việc/frame, giữ nguyên contract.',
        '4. **NTT nhỏ:** khảo sát ghép nhiều polynomial/job cùng N, profile vào frame. Cần',
        '   phân bank theo job và sửa active-mask/context, chưa thể nhân thẳng 8× từ N8.',
        '', 'Chốt được nút thắt và thứ tự tối ưu từ mô phỏng này; chưa chốt được số tile tối ưu',
        'về diện tích/năng lượng, throughput của controller mới hay độ chính xác PQC cho W32/64.',
        'Không triển khai ZCU106 trong phép thử này.',
        '', '## Tái chạy', '', '```text',
        'python -X utf8 scripts/profile_kernel_engine.py',
        'python -X utf8 model/fft_batch_supply.py',
        'python -X utf8 scripts/report_kernel_profile.py',
        '```', '']
    path=ROOT/'docs/kernel_parallelism_profile.md';path.write_text('\n'.join(out),encoding='utf8')
    summary={'profile_result_sha256':sha(result_path),'supply_result_sha256':sha(ROOT/'study/results/fft_batch_supply.json'),
        'report_sha256':sha(path),'report_script_sha256':sha(Path(__file__)),
        'supply_model_sha256':sha(ROOT/'model/fft_batch_supply.py'),
        'outputs_identical_to_validated_baseline':True,'measured_tile_count':16,
        'alternative_tile_counts_are_bounds_only':True,'no_pause_cycles':a['cycles'],
        'random_pause_cycles':b['cycles'],'next_priority':'controller overlap, narrow FFT feed, small NTT multi-job occupancy'}
    (ROOT/'study/results/kernel_profile_summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(f'Wrote {path}',flush=True)


if __name__=='__main__':main()
