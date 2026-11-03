# Ước tính tăng tốc A + CG, giữ contract số học PQC

Ngày 02/11/2026. Đây là **model chu kỳ và replay số học**, chưa phải RTL đã tăng tốc.
Không thay nguyên mẫu 28.466 LUT hoặc RTL chính. Mọi speedup dưới đây giả định cùng clock; chưa có LUT hoặc post-route Fmax cho bản tối ưu.

## 1. Tăng tốc kernel bằng chồng lấp tầng

| Kernel | RTL nguyên mẫu | Model chồng lấp | Speedup | Giảm chu kỳ |
|---|---:|---:|---:|---:|
| NTT q12289 N1024 | 1,174 | 985 | 1.19× | 16.1% |
| NTT q3329 N256 hmin1 | 319 | 265 | 1.20× | 16.9% |
| NTT q8380417 N256 | 364 | 301 | 1.21× | 17.3% |
| FFT32 N1024 | 597 | 453 | 1.32× | 24.1% |
| FFT64 N1024 (generic) | 1,920 | 1,752 | 1.10× | 8.8% |
| FFT128 N1024 (R8) | 7,113 | 6,937 | 1.03× | 2.5% |

NTT N1024 đạt khoảng 985 chu kỳ, gần baseline cũ 984. FFT128 chỉ còn khoảng 2,5% chu kỳ lấy lại từ overlap; không nên kỳ vọng tăng vài lần chỉ từ bỏ rào tầng.
N1024 FFT ở đây là 1.024 thành phần scalar = 512 điểm phức, đúng reference của repo.
Với 16 engine và lịch 45 tích32×32/BF, FFT128 N1024 cần 103.680 tích, cận dưới số học là 6.480 chu kỳ. Model 6.937 đã gần cận này; đây là cận có điều kiện giữ thuật toán/lịch tích hiện tại, không phải cận mọi kiến trúc.

Model giữ từng stream input của một tầng liền nhau, nhưng cho đọc tầng kế trong khi kết quả tầng trước còn ghi về. Có kiểm cổng 1R/1W, RAW/WAR/WAW, pha chung FFT theo II 3/12/48 và tài nguyên engine.
RTL tương lai cần tách context tầng đọc và tầng ghi; pipeline nhãn, active mask, root và cờ scale cuối tầng. Không được chỉ bỏ điều kiện chờ trong FSM hiện tại.
**N nhỏ:** ép FFT64/128 về pha liên tục có thể chậm hơn rào hiện tại. Lịch này chỉ chọn khi có lợi; các cấu hình nhỏ nên giữ rào, hoặc khảo sát ghép batch độc lập sau. Không tự giảm precision theo N.

## 2. Host và root mới là khoản lớn của toàn giao dịch

Bảng sau là **cận thời gian phục vụ bank có điều kiện**, không phải latency RTL đã đo của host mới. Giả định host có burst/buffer, nhận line chồng với phục vụ bank và pipeline read response; giữ nguyên bố cục, một cổng đọc/ghi mỗi bank.
Giữ chi phí cố định đã đo, chưa tính stall phía host/DDR. Cột root multicast thêm giao thức gửi một giá trị32 bit tới mask các lane cùng địa chỉ, chỉ gom các bit-pattern giống hệt.

| N1024 | Toàn ca hiện tại | Chỉ overlap | + host burst, root nối tiếp | + multicast root |
|---|---:|---:|---:|---:|
| NTT q12289 N1024 | 5,332 | 5,143 | 2,583 | 2,534 |
| FFT32 N1024 | 4,802 | 4,658 | 2,098 | 2,000 |
| FFT64 N1024 (generic) | 10,317 | 10,149 | 6,053 | 4,939 |
| FFT128 N1024 (R8) | 23,894 | 23,718 | 19,622 | 17,394 |

Các cột toàn ca đều nạp root mới, nạp input và đọc output; không trộn với trường hợp cache đã có root. Đây chưa phải thời gian ký/sinh khóa/encapsulate.
Với line tự nhiên 128 bit: NTT hmin0/FFT32 cần ít nhất một nhịp bank; FFT64 hai nhịp; FFT128 bốn nhịp. Ở FFT128, bốn limb của một phần tử nằm cùng bank, khác row. Không thể mặc định cả ba precision đạt một line/nhịp nếu giữ layout.
Ví dụ FFT128: overlap chỉ 23.894 → 23.718 toàn ca; cải thiện host mới mở ra cận 19.622, thêm multicast root còn 17.394, khoảng 1,37× so với hiện tại. Đây là khả năng từ mô hình, không phải cam kết.
Root multicast FFT128 N1024 giảm 4.480 lượt ghi xuống 2.252; NTT N1024 chỉ 1.072 xuống 1.023. Vì vậy không nên ưu tiên multicast nếu workload chủ yếu là NTT.
Nếu root còn đúng context thì bỏ được cold-load, nhưng không gọi phần lợi do tái dùng cache là speedup số học. Đổi q/chiều/precision/root contract phải vô hiệu hoặc thay đúng context.

## 3. Correctness PQC: những gì đã và chưa được kiểm

- Model rào khớp **138/138** số chu kỳ RTL đã đo, bao gồm N, hmin và ba precision.
- Model overlap replay đúng dữ liệu RAM theo chu kỳ: **126 ca transform + 12 ca identity**, dùng đúng root bit-pattern từ fixture, không tự thay primitive root.
- Kiểm thêm trực tiếp với capture C R8 Q64.64: **154 synthetic + 22 FFT/IFFT thật từ workload N512/N1024**, khớp từng bit; root so nguyên bit với C.
- NTT/INTT theo C NTRUGen: **100 ca**, năm prime31 bit, N2..1024, hai chiều. Đây là model, không phải kết quả RTL mới.
- Multicast tái tạo đúng toàn bộ root đã nạp ở 138 ca. Thử cho đọc trước khi dữ liệu tồn tại đã bị checker bắt.
- Các thay đổi đề xuất giữ precision, phép wrap/carry, 3M, vị trí rounding, root, Montgomery domain và normalization. Chỉ thay thời điểm truyền/tính những phép độc lập.

**Khoảng trống quan trọng: FFT64 generic không phải FFT64 NTRUGen.**
Model contract hiện tại không khớp **35/40 vector C FFT64 NTRUGen**; 5 ca còn lại trùng ngẫu nhiên hoặc là đồng nhất.
NTRUGen yêu cầu nhân cắt bớt, bảng GM_TAB riêng, signed rounded-half ở mọi tầng inverse trước phép nhân. Nguyên mẫu dùng round-nearest, root thu hẹp từ R8 và scale ở tầng cuối. Cờ floor hiện cũng không điều khiển tích64 bit trong tile.
Vì vậy **không gán hàng FFT64 1.752 chu kỳ cho keygen NTRUGen**, không tuyên bố core hiện hỗ trợ đầy đủ keygen FN-DSA. Phải bổ sung một contract số học riêng, chạy đúng vector C, rồi đo lại cadence/cycle/LUT. Không được sửa expected vector để hợp với RTL.
FFT32/64 vẫn là chế độ số học hợp lệ của accelerator, nhưng chưa phải quyền thay FFT128 trong signer R8. Muốn dùng precision thấp cho một ứng dụng khác cần reference và phân tích sai số của chính ứng dụng đó.
NTT q3329/q8380417 khớp kernel không tự xác nhận toàn ML-KEM/ML-DSA. Cần adapter đúng residue/domain/order/root/scaling và các phép ngoài transform, đặc biệt incomplete NTT/base multiplication ở q3329.
Co-simulation ký/verify đã có trong repo dùng một RTL cũ; **không chuyển kết luận đó sang A + CG hoặc model overlap**. Sau khi có RTL tối ưu, phải replay các lời gọi C bằng output của chính RTL đó, rồi ký/verify (hoặc encapsulate/decapsulate) bằng reference độc lập trước khi chốt ứng dụng.

## 4. Hướng thực hiện đề nghị

1. Khóa contract ứng dụng trước: giữ FFT128 R8 cho signing; bổ sung profile FFT64 NTRUGen nếu keygen nằm trong mục tiêu. Không đổi độ chính xác để đạt latency.
2. Tối ưu burst host vì lợi toàn giao dịch lớn nhất; kiểm lưu/đọc đủ word, thứ tự và backpressure, kể cả N nhỏ.
3. Thêm read/write stage context để chồng lấp, ưu tiên NTT; giữ lựa chọn rào ở N nhỏ.
4. Thêm multicast/reuse root nếu trace cho thấy đáng làm; context phải gắn đúng contract và tham số.
5. Mỗi bản chỉ được ghi nhận speedup sau simulation RTL với vector C; sau đó synth đủ host/root và xác nhận vẫn dưới 35k. Chưa dự toán số LUT tăng bằng dư địa 6.534 LUT.

Muốn tính tăng tốc toàn ứng dụng cần trace số lời gọi từng N/format/chiều, cache miss và thời gian phần C còn lại. Không suy từ speedup một kernel ra speedup toàn PQC.

## Dữ liệu và chạy lại

- [Model](../../model/a_cg_speed_estimate.py), chạy `python -X utf8 model/a_cg_speed_estimate.py`.
- [JSON mọi cấu hình, giả định và SHA256](a_cg_speed_estimate.json).
- [RTL và số đo hiện tại](a_cg_prototype.md).
- [Contract R8](../../docs/numeric_contract.md), [contract NTRUGen](../../spec/FlexTransform/2.0/01_so_hoc_kernel.md).
