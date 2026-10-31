# FlexTransform — phân tích related work, vòng 1

Ngày: 21/10/2026. Đã phân tích P1/P2/P3; các bài khác vẫn theo
[reading guide](reading_guide.md). Đây là tài liệu phục vụ chọn kiến trúc,
không phải kết luận đã đủ novelty.

## Kết luận hiện tại

**Hướng đáng khảo sát là thay đổi cách phân bổ mảng số học theo độ rộng, đồng bộ
với reducer, twiddle và memory trên cùng lõi FFT/NTT.** Chỉ đổi q hoặc thêm lựa chọn
FFT/NTT chưa tạo được khác biệt mạnh.

Ba note chi tiết:

1. [P1 — Unified FFT/NTT: chia sẻ tài nguyên và peak throughput](paper_notes/01_unified_fft_ntt.md).
2. [P2 — OpenNTT: synthesis-time, runtime và datapath theo q lớn nhất](paper_notes/02_openntt.md).
3. [P3 — BitFusion: schoolbook, signedness và lịch ghép/tách](paper_notes/03_bitfusion.md).

## Bản đồ bằng chứng

“Không mô tả” chỉ nói về phạm vi tài liệu đã đọc. Dấu “—” là ngoài miền bài toán.
Các kết luận và nguồn cụ thể nằm trong từng note.

| Khả năng | P1: ICASSP | P2: OpenNTT | P3: BitFusion |
|---|---|---|---|
| FFT/NTT cùng lõi runtime | Có | Tool chọn một miền | — |
| FFT nhiều precision runtime | Không mô tả | Không mô tả | — |
| q runtime tổng quát trong cấu hình hỗ trợ | Không mô tả; hai mode PQC | Có | — |
| q nhỏ làm tăng số lane | Mode-specific; chưa tổng quát | Không trong datapath mặc định đã đọc | — |
| Fusion số học theo operand width | Mode-specific | Không thấy trong đường nhân đã đọc | Có, cho DNN |
| Precision thấp và data packing | Có theo mode | Chưa thấy runtime width packing | Có |
| Forward/inverse | Chưa xác minh inverse | Tùy core được tạo | — |
| Bằng chứng kiểm tra của mình | Đọc paper | Paper + generator/RTL | Đọc paper + tự dẫn xuất |

Nguồn chính:
[P1](https://arxiv.org/html/2504.11124v1),
[P2](https://flokrieger.github.io/papers/tcad25_opennttext.pdf),
[P3](https://arxiv.org/html/1712.01507v2).

Không xếp P1 vào ô “không flex width”: số lane theo mode của bài là đối chiếu
trực tiếp cần xử lý. Khác biệt của mình phải cụ thể hơn việc có nhiều mode.

## Các giả thuyết cần phân biệt

| Phương án | Ví dụ tự đặt | Lợi ích có thể có | Điều chưa được bảo đảm |
|---|---|---|---|
| Đổi q cùng width | Hai prime trong container 32 bit | Dùng chung nhiều context | Không tự tăng số butterfly |
| Đổi container width | 16/32/64 bit cho NTT | Giảm traffic, có thể giảm switching | Không tự tăng multiplier slot |
| Đổi grouping theo width | Nhiều nhóm hẹp, ít nhóm rộng | Tăng mức song song khi hẹp | Cần reducer và memory theo kịp |
| Đổi precision FFT | 64/128 bit mỗi real/imag | Cân bằng sai số và thời gian | Cần numeric contract và workload |
| Chia sẻ FFT/NTT | Cùng mảng integer product | Giảm tài nguyên trùng lặp | Mux/routing có thể giảm Fmax |

“Precision” FFT liên quan sai số; NTT phải chính xác theo modulus.
Container 16 bit cho q=12289 không có nghĩa q có 16 bit có nghĩa: q cần 14 bit.
Nếu prime nhỏ và lớn đều vừa một uPE 32×32, schoolbook ở granularity này
không tạo thêm lane nhân. Cần chọn width từ workload thực tế trước khi
quảng bá lợi ích NTT ghép/tách.

## Mô hình chung để không đếm thiếu tài nguyên

Đây là dẫn xuất của mình, không phải benchmark của ba paper:

~~~text
R_BF <= min(
    integer-product capacity,
    partial-product assembly capacity,
    complex-add hoặc modular-reduction capacity,
    data-read capacity,
    data-write capacity,
    twiddle capacity,
    scheduler/hazard capacity
)
~~~

Mỗi thành phần phải quy về butterfly/cycle.
Khi reducer dùng chung mảng nhân, integer-product budget phải gồm công việc reduction;
không cộng lại cùng tài nguyên hai lần.

Ví dụ K=32 multiplier slot 32×32, schoolbook; read/write mỗi hướng 512 bit/cycle:

| Mode giả định | Partial products/BF | Trần integer compute | Trần data read/write | Trần hai yếu tố |
|---|---:|---:|---:|---:|
| FFT64, twiddle64 | 16 | 2 BF/cycle | 2 | 2 |
| FFT128, twiddle128 | 64 | 0.5 | 1 | 0.5 |
| NTT container16 | 1 | 32 | 16 | 16 |
| NTT container32 | 1 | 32 | 8 | 8 |
| NTT container64 | 4 | 8 | 4 | 4 |

Ba dòng NTT chỉ khảo sát capacity, **chưa trừ chi phí reduction**.
Một product 16×16 vẫn dùng một slot 32×32; chưa có subword packing.
Không dùng bảng này làm cam kết throughput. Nó minh họa rằng thêm lane tính toán
có thể không tạo thêm tốc độ khi memory đã chạm trần.

## Đối chứng cần có trước khi khẳng định lợi ích

| Đối chứng đề xuất | Câu hỏi được trả lời |
|---|---|
| Lõi rộng cố định; mode hẹp dùng padding | Fusion có tăng utilization thực tế không? |
| Cùng chức năng nhưng tách FFT/NTT | Tài nguyên chung tiết kiệm bao nhiêu, mất gì về Fmax? |
| Runtime q, lane cố định kiểu OpenNTT | Width-aware allocation thêm lợi ích ngoài đổi modulus không? |
| Tắt memory packing, giữ arithmetic fusion | Speedup đến từ arithmetic hay memory? |
| FFT64-only so với FFT64/128 trong cùng lõi | Giá của precision linh hoạt là bao nhiêu? |

So cùng primitive count và so cùng tổng area là hai thí nghiệm khác nhau.
Cần nêu ngân sách DSP/LUT/BRAM, clock đạt được, N, quy ước transform và numeric
semantics. Không so floating-point với fixed-point chỉ bằng số bit lưu trữ.

## Phần cần đọc tiếp trước khi khóa novelty

Ưu tiên **Maestro** cho FFT đa precision, **CoHA-NTT** cho modular arithmetic
linh hoạt và **Aloha-HE** cho chia sẻ hai miền.
Nguồn và câu hỏi đọc có trong [reading guide](reading_guide.md).

Cần toàn văn **R-BMM**, bài **configurable 2-D NTT** và bài **fused FP64/NTT tại ICTA**
trước khi claim kiến trúc mới. Abstract/metadata chưa đủ kết luận mức overlap.

Câu hỏi nghiên cứu có thể giữ ở dạng:

> Liệu một mảng số học ghép/tách, với cấp dữ liệu và xử lý kết quả phù hợp từng
> width, có cải thiện hiệu quả toàn lõi cho FFT đa precision và NTT đổi modulus
> so với các cách phân bổ cố định tương đương?

Đây là câu hỏi, chưa phải kết quả hay claim “đầu tiên”.

## Kiểm tra có thể tái chạy

Từ thư mục dự án:

~~~powershell
python scripts/check_research_models.py
~~~

[Script](../scripts/check_research_models.py) kiểm tra signed schoolbook với boundary/random,
prime/root của ví dụ NTT, phép đếm cycle P1 và các cận compute/bandwidth.
Không chạy RTL, không đo timing FPGA, không kiểm chứng numerical accuracy của FFT.

Kết quả chạy ngày 21/10/2026: 298 cặp signed 64/128 bit qua kiểm tra;
hai q của ví dụ đều prime, có root bậc 2048 tại N=1024.
Root minh họa tìm được: 1945 cho q=12289, 709697997 cho q=2013265921.
Các phép đếm trong bảng khớp output của script.

PLAN giữ tập mode xuất phát FFT64/FFT128/NTT12289; NTT đa modulus ở tài liệu
này là hướng khảo sát để ra quyết định phạm vi tiếp theo.
