# Ngưỡng giả thuyết đã khóa — 31/10/2026, lần 3

Khóa lại sau khi người dùng duyệt bản đối chứng mới của giả thuyết 2: cả hai biến thể rút gọn lane 16 bit trên mảng nhân,
chỉ khác ở lane 32 bit (thiết kế v1 chuyển sang rút gọn mọi modulus trên mảng). Ngưỡng của giả thuyết 2 không đổi. Duyệt
**sau** khi đã thấy số đo bản nháp với bản đối chứng này (LUT +16,2%, chạm điều kiện bác bỏ). Lý do và trạng thái ở bảng
"Sửa sau khi khóa", mục 6 của [kiến trúc v1](../architecture_v1.md). Đề xuất sửa giả thuyết 4 trong bảng đó **chưa**
duyệt nên không có trong bản khóa này. Các bản khóa trước: [lần 2](nguong_khoa_2026-10-31_lan2.md),
[lần đầu](nguong_khoa_2026-10-31.md).

Cách kiểm lại:
1. Lấy dòng tiêu đề và 12 dòng giả thuyết của bảng ở mục 6 (bỏ dòng kẻ).
2. Nối các dòng bằng ký tự xuống dòng, thêm một xuống dòng ở cuối.
3. Tính SHA-256 trên UTF-8. Kết quả phải bằng giá trị dưới đây.

Bảng được chép nguyên văn để mã kiểm khớp, nên các liên kết trong bảng tính từ thư mục `docs/` chứ không phải từ thư
mục này.

SHA-256: `12d91d2e069944b90b6a60c753fdcaff058cb0415954a6395f4ac6948b1d4c04`

| # | Giả thuyết | Đạt khi | Bác bỏ khi |
| 1 | **Dùng chung FFT/NTT có lợi về tài nguyên** | Với từng loại LUT, DSP và BRAM/URAM: lõi chung ≤ lõi chỉ-FFT + lõi chỉ-NTT, mỗi lõi riêng có cùng tốc độ với lõi chung ở chế độ của nó; LUT nhỏ hơn rõ rệt | LUT hoặc DSP của lõi chung ≥ tổng hai lõi riêng |
| 2 | **Rút gọn 32 bit trên mảng nhân rẻ hơn bộ Montgomery 32 bit riêng** | So với cùng tile dùng bộ Montgomery 32 bit riêng (cả hai rút gọn lane 16 bit trên mảng nhân; định nghĩa ở mục 5 của [hợp đồng cấp tile](../spec/FlexTransform/2.0/10_hop_dong_tile.md)): DSP ít hơn ít nhất 4 mỗi tile; LUT tăng ≤ 5%; Fmax giảm ≤ 10%; NTT 32 bit chậm ≤ 3,5 lần ở N256, một hoặc hai đa thức (dự báo 2,4–2,8) | DSP giảm < 2, hoặc LUT tăng > 10%, hoặc chậm > 4 lần |
| 3 | **Gom lô tạo ra chiều precision cho FFT** | N1024: FFT xuôi ≤ 700 / 2 300 / 8 500 chu kỳ cho 32 / 64 / 128 bit; FFT ngược ≤ 770 / 2 530 / 9 350. Tỉ lệ 128 bit so với 32 bit ≥ 10, so với 64 bit ≥ 3 (N512: ≥ 8). Khi chỉ có pipeline, tỉ lệ 128/32 bit ≤ 2. Ngưỡng đúng khi độ trễ đo được của đường FFT (đọc RAM tới ghi) ≤ 24 chu kỳ | Có gom lô mà tỉ lệ 128/32 bit < 4 |
| 4 | **Pipeline đưa NTT tới gần mô hình** | Thời gian ≤ 1,25 × mô hình, với mô hình = tổng các lượt × (số nhịp / (16 × tốc độ nhịp mỗi tile) + độ trễ nhịp đo được). Dự báo: q12289 (bộ rút gọn hằng, độ trễ nhịp 16) N1024 ≤ 200, N256 ≤ 100, hai đa thức xen kẽ ≤ 50 mỗi đa thức; NTT 32 bit (trên mảng, độ trễ nhịp 30) N256 ≤ 400 | Vượt 2 × mô hình |
| 5 | **Chiều độ rộng FFT không đắt so với lõi chỉ làm FFT 128 bit** | LUT ≤ 1,35 lần và DSP bằng lõi chỉ-128-bit; tốc độ trên LUT ở 32 bit ≥ 7 lần, ở 128 bit ≥ 0,75 lần | Không đạt cả hai ngưỡng 32 bit |
| 6 | **Mọi kết quả khớp từng bit với phần mềm chuẩn** | 0 sai khác; chữ ký khớp từng byte | Một sai khác (**đã đạt** với lõi hiện tại) |
| 7 | **NTT hai tầng gộp giảm một nửa lượng dữ liệu, tốn ít tài nguyên** | N1024 cần 5 lượt thay vì 10; thêm ≤ 3% LUT so với chỉ chạy một tầng | Thêm > 10% LUT. (Đã đo trên thiết kế cũ có bộ rút gọn riêng: 5 lượt, +1,10%; **phải đo lại** trên lõi v1) |
| 8 | **Một lõi phục vụ cả ký (128 bit) và sinh khóa (64 bit)** | FFT 64 bit khớp NTRUGen; sinh khóa dùng lõi cho khóa khớp từng byte (≥ 2 seed mỗi N512/N1024) | Một sai khác |
| 9 | **NTT 32 bit chạy đúng, không xung đột bank** | Khớp NTT của bản chuẩn ML-DSA (Dilithium, pq-crystals) sau khi đổi cách biểu diễn; bộ đếm xung đột = 0 | Một sai khác hoặc có xung đột |
| 10 | **Đổi sang prime 31 bit bất kỳ của NTRUGen không tốn thêm phép tính, chỉ tốn ít tài nguyên** | Khớp từng bit `mp_NTT`/`mp_iNTT` trên cả 323 prime, logn = 1..10; LUT thêm cho chế độ này ≤ 3% lõi; BRAM thêm không quá RAM gói root hai chiều (khoảng 12 KiB, [spec 2.0 mục 03.4](../spec/FlexTransform/2.0/03_bo_nho.md)); thời gian ≤ 1,25 × mô hình (N1024 ≤ 1 400 chu kỳ, chưa gồm nạp root) | Một sai khác, hoặc LUT thêm > 10% |
| 11 | **Mỗi tile một modulus làm sinh khóa nhanh lên mà gần như không tốn tài nguyên** | Mỗi đa thức của lệnh nhiều khe khớp từng bit với chạy riêng; LUT thêm ≤ 2% lõi; thời gian NTT của sinh khóa (đếm như [study/results/fn_dsa_workload.md](../study/results/fn_dsa_workload.md), với chu kỳ đo trên RTL) giảm ≥ 1,5 lần so với một đa thức mỗi lệnh (dự báo 1,8–2,0) | Giảm < 1,2 lần, hoặc LUT thêm > 5% |
| 12 | **Cổng host có pipeline và địa chỉ trong lệnh làm giảm thời gian chép** | Cổng host đạt ≥ 0,9 dòng/chu kỳ khi đọc và ghi liên tục; trình điều khiển giữ dữ liệu trong lõi làm số dòng chép của phép ký N = 1024 ≤ 0,85 lần so với không giữ (dự báo 0,82 khi chỉ giữ đầu vào); LUT thêm cho hai thay đổi ≤ 2% lõi | Cổng host < 0,5 dòng/chu kỳ, hoặc giữ dữ liệu giảm < 5% số dòng |
