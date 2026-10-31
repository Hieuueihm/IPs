# Lịch sử thay đổi

## 2.0 — đang viết (bắt đầu 2026-10-30)

Nguồn: [kiến trúc v1](../../../docs/architecture_v1.md). Bản 1.0 giữ nguyên.

### 2026-10-31, lần 2: một làn NTT mỗi tile

Người dùng duyệt sau khi tách LUT của bản nháp khối tile thử (ghi chú bản nháp mục 8):
- Mỗi tile chỉ còn **một làn NTT** (một bộ rút gọn hằng 3329/12289). Mỗi request là một butterfly (chế độ 4) hoặc một
  phép nhân modulo (chế độ 2), toán hạng ở ô cố định: x = d0, y = d1, w = r0. **Chế độ 3 (nhịp hai tầng) bị bỏ.**
- Cổng `req_data` / `req_root` / `rsp_data` còn 64 / 32 / 65 bit. Ghép cặp CT/GS và đặt kết quả chuyển ra tầng bộ nhớ.
- Tốc độ tối thiểu: lane 16 bit 1 request/chu kỳ; lane 32 bit 1/3 (lai), 1 (rút gọn riêng).
- Vector NTT, testbench, lỗi cài vào (`FAULT_SWAP_XY` thay `FAULT_SWAP_R1R2`) làm lại; testbench tự kiểm tốc độ.
- Thêm điểm đo "mọi modulus trên mảng" (10 mục 5.3): nay không làm chậm NTT 16 bit nữa.
- **Chưa cập nhật** theo thay đổi này: 03 (gói root ba phần tử, xung đột bank kiểm cho nhịp hai tầng, cách xếp N nhỏ
  vào tile), dự báo chu kỳ của kiến trúc, mô hình workload, mô hình ngân hàng cộng, giả thuyết 4 (đang khóa). Bằng
  chứng khớp NTRUGen của 10 mục 4.6 phải chạy lại với lịch một tầng.
- Bản trước: [docs/plan_history/spec2_before_single_lane_2026-10-31/](../../../docs/plan_history/spec2_before_single_lane_2026-10-31/).

### 2026-10-31: rút gọn lai

Theo thay đổi 4 mới của kiến trúc (người dùng chọn sau bản nháp khối tile thử):
- Thiết kế dùng **rút gọn lai**: lane 16 bit chỉ nhận q = 3329 và 12289, rút gọn bằng 4 bộ hằng mỗi tile, tốc độ đầy
  đủ; lane 32 bit rút gọn trên mảng nhân như trước.
- Hai biến thể của khối tile thử nay là **lai** (thiết kế) và **rút gọn riêng** (đối chứng). Chúng chỉ khác ở rút gọn
  lane 32 bit. Biến thể "rút gọn trên mảng cho mọi modulus" của bản trước chỉ còn là số đo tham khảo của bản nháp.
- Bảng tốc độ tối thiểu của tile đổi theo; `ntt16_q_khac.txt` không còn áp dụng cho biến thể nào của v1.
- Bản trước của các tài liệu 2.0: [docs/plan_history/spec2_before_hybrid_reduction_2026-10-31/](../../../docs/plan_history/spec2_before_hybrid_reduction_2026-10-31/).

### Đã có trong bản này

- **Hợp đồng cấp tile** (mới, 1.0 không có): khối tile thử với năm chế độ, thanh ghi hằng số chỉ ghi khi tile rảnh,
  dừng bằng tín hiệu cho phép chung, kết quả ra đúng thứ tự, tốc độ tối thiểu theo từng chế độ.
- Hai biến thể rút gọn có cùng giao diện và cùng kết quả:
  - **rút gọn trên mảng nhân**;
  - **rút gọn riêng**: 4 bộ rút gọn hằng cho 3329/12289 và 1 bộ Montgomery 32 bit tổng quát mỗi tile.

  Bản đối chứng này làm đủ cùng tập modulus với biến thể trên mảng. Nó thay cho bản đối chứng "64 bộ rút gọn của lõi
  cũ", vì lõi cũ không chạy được 8380417 hay prime nạp lúc chạy.
- Phép chia đôi modulo ở nhánh tổng của butterfly GS (NTT ngược của NTRUGen).
- Vector chuẩn cấp tile, sinh từ phép toán modulo và phép nhân số nguyên thuần túy. Bộ vector này **thay cho**
  16 102 vector của cụm NTT cũ khi kiểm khối tile thử, vì cụm cũ chỉ có lane 16 bit và cách đóng gói khác.

### Cấp lõi (00–04)

- Trường định dạng 3 bit: 4 = hệ số 32 bit, 5 = FFT 64 bit theo NTRUGen. Trường dự trữ còn 7 bit.
- Profile 2 = q 8380417 (chỉ N = 256); profile 3 = prime 31 bit đã nạp (N = 2..1024, NTT ngược chia đôi mỗi tầng).
- Opcode 0x9 nạp prime: đọc p, p0i, R² mod p, gm, igm từ vùng C; lõi xếp thành RAM gói root.
- Mã lỗi mới 0x07 (chưa nạp prime) và 0x08 (dữ liệu prime sai); profile, kích thước, số đa thức mở rộng theo bảng mới.
- Gom lô FFT bắt buộc 16 / 4 / 1 butterfly; bảng root FFT 4 bank; bảng root Q32.32 của NTRUGen.
- Gói root NTT 32 bit 96 bit, 4 bank. Xen kẽ hai đa thức ở N ≥ 64.
- Vector cấp kernel cho ba kernel mới, lấy từ C của NTRUGen hoặc từ phép toán modulo có kiểm độc lập.
- **2026-10-31, mỗi tile một modulus** (thay đổi 9 của kiến trúc):
  - 16 khe prime; trường lệnh `cmd_slot_i` (4 bit) và `cmd_same_slot_i` (1 bit) lấy từ trường dự trữ, dự trữ còn 2 bit;
  - phép nạp prime chọn khe và vị trí gói (byte 14–15 của phần đầu), xóa cờ các khe có vùng chồng lên;
  - profile 3 với N < 64 chạy tới min(8, 64/N) đa thức, mỗi đa thức một khe; N ≥ 64 với 2 đa thức phải cùng khe;
  - 10 lệnh nhiều khe trong vector cấp kernel.
- **2026-10-31, chép dữ liệu host** (thay đổi 10, 11 của kiến trúc):
  - cổng bộ nhớ host có pipeline: tới 8 giao dịch đang chờ, trả lời đúng thứ tự, ≥ 0,9 dòng mỗi chu kỳ;
  - ba trường `cmd_base_a_i`, `cmd_base_b_i`, `cmd_base_c_i` (13 bit) trong lệnh, căn theo kích thước vùng làm tròn lên
    lũy thừa của 2; payload lệnh từ 55 thành 94 bit;
  - mã lỗi mới 0x09 (sai địa chỉ), kiểm sau 0x06 và trước 0x07;
  - dữ liệu của phép nạp prime đọc từ địa chỉ đầu của vùng C.

### Chưa có

- Bản máy đọc của yêu cầu và giao diện; script kiểm toàn bộ spec.

### Quy tắc thay đổi

Giữ như bản 1.0. Đổi hợp đồng, nội dung vector hay bố cục bit thì phải tăng phiên bản và sinh lại vector cùng
manifest. Sửa câu chữ không đổi nghĩa thì không cần.
