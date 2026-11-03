# Ngưỡng giả thuyết đã khóa — 01/11/2026, lần 7

Khóa lại sau khi người dùng chọn cách đặt FFT lên tile một làn (mỗi tile làm trọn một butterfly phức, tích độ rộng W gồm
1 / 4 / 15 tích con chạy lần lượt) và duyệt giả thuyết 3 viết lại cho cách đó: các ngưỡng số giữ nguyên; bỏ câu "chỉ có
pipeline"; điều kiện độ trễ ≤ 24 đổi thành báo độ trễ từng độ rộng; bác bỏ khi tỉ lệ 128/32 bit < 4. Duyệt sau khi thấy
dự báo của mô hình ([study/results/fft_core_plan.md](../../study/results/fft_core_plan.md)), chưa có RTL FFT. Các giả
thuyết khác không đổi so với lần 6.

Lý do và trạng thái ở bảng "Sửa sau khi khóa", mục 6 của [kiến trúc v1](../architecture_v1.md). Các bản khóa trước:
[lần 6](nguong_khoa_2026-11-01_lan6.md), [lần 5](nguong_khoa_2026-11-01_lan5.md), [lần 4](nguong_khoa_2026-10-31_lan4.md),
[lần 3](nguong_khoa_2026-10-31_lan3.md), [lần 2](nguong_khoa_2026-10-31_lan2.md), [lần đầu](nguong_khoa_2026-10-31.md).

Cách kiểm lại:
1. Lấy dòng tiêu đề và 12 dòng giả thuyết của bảng ở mục 6 (bỏ dòng kẻ).
2. Nối các dòng bằng ký tự xuống dòng, thêm một xuống dòng ở cuối.
3. Tính SHA-256 trên UTF-8. Kết quả phải bằng giá trị dưới đây.

Bảng được chép nguyên văn để mã kiểm khớp, nên các liên kết trong bảng tính từ thư mục `docs/` chứ không phải từ thư
mục này.

SHA-256: `feffe4a53538a73cc79cb8a3a7c6074087dd332aa8b6248767f8b8000d2ab35c`

| # | Giả thuyết | Đạt khi | Bác bỏ khi |
| 1 | **Dùng chung FFT/NTT có lợi về tài nguyên** | Với từng loại LUT, DSP và BRAM/URAM: lõi chung ≤ lõi chỉ-FFT + lõi chỉ-NTT, mỗi lõi riêng có cùng tốc độ với lõi chung ở chế độ của nó; LUT nhỏ hơn rõ rệt | LUT hoặc DSP của lõi chung ≥ tổng hai lõi riêng |
| 2 | **Rút gọn 32 bit trên mảng nhân rẻ hơn bộ Montgomery 32 bit riêng** | So với cùng tile dùng bộ Montgomery 32 bit riêng (cả hai một lane 32 bit cho mọi q; định nghĩa ở mục 5 của [hợp đồng cấp tile](../spec/FlexTransform/2.0/10_hop_dong_tile.md)): DSP ít hơn ít nhất 4 mỗi tile; LUT tăng ≤ 5%; Fmax giảm ≤ 10%; NTT (mọi q) chậm ≤ 3,5 lần ở N256, một hoặc hai đa thức (dự báo 2,4–2,8) | DSP giảm < 2, hoặc LUT tăng > 10%, hoặc chậm > 4 lần |
| 3 | **Số tích con theo độ rộng tạo ra chiều precision cho FFT** | Mỗi tile làm trọn một butterfly phức; một tích độ rộng W gồm 1 / 4 / 15 tích con 32 bit chạy lần lượt (W = 32 / 64 / 128), nên độ rộng hẹp cho nhiều butterfly mỗi chu kỳ hơn. N1024: FFT xuôi ≤ 700 / 2 300 / 8 500 chu kỳ cho 32 / 64 / 128 bit; FFT ngược ≤ 770 / 2 530 / 9 350. Tỉ lệ 128 bit so với 32 bit ≥ 10, so với 64 bit ≥ 3 (N512: ≥ 8). Báo độ trễ đọc RAM tới ghi của một butterfly ở từng độ rộng (dự báo 14 / 23 / 56 chu kỳ) | Tỉ lệ 128/32 bit < 4 |
| 4 | **Pipeline đưa NTT tới gần mô hình** | Thời gian ≤ 1,25 × mô hình, với mô hình = tổng các lượt (mỗi tầng một lượt) × (3 × số chu kỳ phát của lượt theo [model/single_lane_feed.py](../model/single_lane_feed.py) + độ trễ butterfly đo được + 2 chu kỳ RAM); hệ số 3 vì tile rút gọn trên mảng nhận một butterfly mỗi 3 chu kỳ. Dự báo: q12289 N1024 ≤ 1 466, N256 ≤ 450, hai đa thức xen kẽ ≤ 240 mỗi đa thức; NTT 32 bit N256 ≤ 450 | Vượt 2 × mô hình |
| 5 | **Chiều độ rộng FFT không đắt so với lõi chỉ làm FFT 128 bit** | LUT ≤ 1,35 lần và DSP bằng lõi chỉ-128-bit; tốc độ trên LUT ở 32 bit ≥ 7 lần, ở 128 bit ≥ 0,75 lần | Không đạt cả hai ngưỡng 32 bit |
| 6 | **Mọi kết quả khớp từng bit với phần mềm chuẩn** | 0 sai khác; chữ ký khớp từng byte | Một sai khác (**đã đạt** với lõi hiện tại) |
| 7 | **NTT hai tầng gộp giảm một nửa lượng dữ liệu, tốn ít tài nguyên** | N1024 cần 5 lượt thay vì 10; thêm ≤ 3% LUT so với chỉ chạy một tầng | Thêm > 10% LUT. (Đã đo trên thiết kế cũ có bộ rút gọn riêng: 5 lượt, +1,10%; **phải đo lại** trên lõi v1) |
| 8 | **Một lõi phục vụ cả ký (128 bit) và sinh khóa (64 bit)** | FFT 64 bit khớp NTRUGen; sinh khóa dùng lõi cho khóa khớp từng byte (≥ 2 seed mỗi N512/N1024) | Một sai khác |
| 9 | **NTT 32 bit chạy đúng, không xung đột bank** | Khớp NTT của bản chuẩn ML-DSA (Dilithium, pq-crystals) sau khi đổi cách biểu diễn; bộ đếm xung đột = 0 | Một sai khác hoặc có xung đột |
| 10 | **Đổi sang prime 31 bit bất kỳ của NTRUGen không tốn thêm phép tính, chỉ tốn ít tài nguyên** | Khớp từng bit `mp_NTT`/`mp_iNTT` trên cả 323 prime, logn = 1..10; LUT thêm cho chế độ này ≤ 3% lõi; BRAM thêm không quá RAM gói root hai chiều (khoảng 12 KiB, [spec 2.0 mục 03.4](../spec/FlexTransform/2.0/03_bo_nho.md)); thời gian ≤ 1,25 × mô hình (N1024 ≤ 1 400 chu kỳ, chưa gồm nạp root) | Một sai khác, hoặc LUT thêm > 10% |
| 11 | **Mỗi tile một modulus làm sinh khóa nhanh lên mà gần như không tốn tài nguyên** | Mỗi đa thức của lệnh nhiều khe khớp từng bit với chạy riêng; LUT thêm ≤ 2% lõi; thời gian NTT của sinh khóa (đếm như [study/results/fn_dsa_workload.md](../study/results/fn_dsa_workload.md), với chu kỳ đo trên RTL) giảm ≥ 1,5 lần so với một đa thức mỗi lệnh (dự báo 1,8–2,0) | Giảm < 1,2 lần, hoặc LUT thêm > 5% |
| 12 | **Cổng host có pipeline và địa chỉ trong lệnh làm giảm thời gian chép** | Cổng host đạt ≥ 0,9 dòng/chu kỳ khi đọc và ghi liên tục; trình điều khiển giữ dữ liệu trong lõi làm số dòng chép của phép ký N = 1024 ≤ 0,85 lần so với không giữ (dự báo 0,82 khi chỉ giữ đầu vào); LUT thêm cho hai thay đổi ≤ 2% lõi | Cổng host < 0,5 dòng/chu kỳ, hoặc giữ dữ liệu giảm < 5% số dòng |
