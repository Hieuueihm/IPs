# Lịch sử thay đổi

## 2.0 — đang viết (bắt đầu 2026-10-30)

Nguồn: [kiến trúc v1](../../../docs/architecture_v1.md). Bản 1.0 giữ nguyên.

### 2026-11-01, lần 11: FFT 64/128 bit, máy chế độ 5 dùng chung, profile 3 trên lõi

- Hợp đồng tile (10, lần 9 và 10): chế độ 5 ở 64 / 128 bit (`cfg_q[5:4]`), tính theo từng phần 32 bit trên chính bộ nhân,
  bộ cộng/trừ và bộ dịch của tile; từ lần 10 FFT 32 bit là trường hợp L = 1 của cùng máy (bỏ đường 32 bit riêng), tile giữ
  8 butterfly ở 32 bit, 4 ở 64 / 128 bit; độ trễ 32 bit 15 / 16. Kiểm thử (11, lần 7): `fftwbf.txt`, `+KIND=4`,
  `FAULT_NO_CARRY`; 5 cấu hình, mỗi cấu hình 82 lần chạy đạt, 22/22 lỗi bị bắt (`EN_REG`: 50, 16/16).
- Lõi: FFT định dạng 1, 2 bằng ánh xạ "phần 32 bit = phần tử định dạng 0 ảo": khối L tile chung một butterfly, không thêm
  nguồn mạng ([model/fft_wide_sched.py](../../../model/fft_wide_sched.py)); FFT chuyển tầng theo số lượt ghi đã xong (sửa lỗi
  FFT32 chuyển tầng sớm). N1024: 644 / 2 031 / 7 510 chu kỳ (ngưỡng giả thuyết 3: 700 / 2 300 / 8 500).
- Lõi: profile 3, prime lẻ < 2³¹ nạp lúc chạy, 16 khe, N2..1024, bỏ 0..2 tầng cuối; host ghi khe và gói root (đơn giản hóa so
  với phép nạp prime của 02). 100 ca vàng đạt (80 so với C NTRUGen, 20 theo định nghĩa); N1024 984 / 985 chu kỳ.
- Vivado lõi trước profile 3: 53 722 LUT / 29 435 FF / 64 DSP / 64 BRAM tile, WNS −0,672 ns; đường găng do rào chắn mới,
  đã sửa, chưa đo lại.

### 2026-11-01, lần 10: chế độ 5 của tile, FFT 32 bit trên lõi

- Hợp đồng tile (10, lần 8): chế độ 5, một butterfly FFT 32 bit trong hai nhịp request, chạy trên đường butterfly NTT
  (cộng/trừ với q = 0, bộ nhân ghép làm 3 tích, làm tròn chế độ 1); `cfg_q[3:0]` = độ dịch div2e, `req_sign[0]` = chia;
  độ trễ 9, một butterfly mỗi 3 chu kỳ; chỉ với `EN_REG` = 0. Kiểm thử (11, lần 6): `fft32bf.txt`, `+KIND=3`.
- Lõi tối thiểu chạy FFT / FFT ngược định dạng 0 qua chế độ 5: 18/18 ca vàng 1.0; N1024 539 chu kỳ (ngưỡng giả thuyết 3:
  700 / 770). Mạng: nguồn cho cặp ảo; đường root 64 bit có nạp/giữ; ROM gói hai cổng, mỗi từ FFT một root.
- Vivado lõi: 33 423 LUT / 64 DSP / 44 BRAM tile, WNS −0,061 ns (chỉ NTT: 17 748 LUT, +0,098 ns).
- Bản trước: [docs/plan_history/before_tile_mode5_2026-11-01/](../../../docs/plan_history/before_tile_mode5_2026-11-01/).

### 2026-11-01, lần 9: tile lệch pha, 4 bank gói root

- v1 trên mảng chỉ cần 16 butterfly mỗi 3 chu kỳ. Tile t bắt đầu ở pha t / 6 (tham số `PHASE` của tile, lịch phát do
  người triển khai chọn, hợp đồng tile mục 9), nên mỗi chu kỳ chỉ 4–6 tile được cấp, và 4 bank gói root đủ: mô hình
  [model/staggered_net.py](../../../model/staggered_net.py) cho 99,4% của 16/3, bằng 8 bank.
- 03 mục 4: số bank gói P = 4 cho v1, 8 cho bản đối chứng rút gọn riêng; địa chỉ bank theo P. Định dạng gói, dung lượng và
  phép nạp prime không đổi.
- Tile lệch pha (`PHASE` = t / 6) và 4 bank gói root: mạng 5 216 LUT / 6 001 FF, WNS +0,487 ns (root 1 536 LUT, trước 2 560); 16 tile 12 495 LUT / 14 872 FF / 64 DSP, WNS +0,063 ns; phần tính + mạng 17 711 LUT, 64 DSP. Bản 8 bank sinh lại được bằng `python scripts/gen_structured_net.py --pbanks 8`
  (`hdl/net/ntt_bank_net_s_p8.sv`).
- Regression: 5 cấu hình, thêm `PHASE = 2`; mỗi cấu hình 50 lần chạy đạt, 16/16 lỗi bị bắt.
- Bản trước: [docs/plan_history/before_on_array_v1_2026-11-01/](../../../docs/plan_history/before_on_array_v1_2026-11-01/)
  (gồm mạng và generator 8 bank).

### 2026-11-01, lần 8: thiết kế v1 rút gọn trên mảng

- Người dùng duyệt và khóa lại giả thuyết 2 và 4 (lần 5): với chữ bản đối chứng cho một lane, giả thuyết 2 đạt ở cấp tile
  (trên mảng 781 LUT / 4 DSP so với riêng 777 LUT / 11 DSP).
- Theo 10 mục 8, người dùng chọn biến thể trên mảng làm thiết kế v1: RTL mặc định `TREN_MANG = 1`; không DSP nào ngoài 64
  bộ nhân; NTT mọi q 1/3 request/chu kỳ mỗi tile, độ trễ 19. 16 tile v1 trên mảng sau một thanh ghi `en`: 12 494 LUT / 14 872 FF / 64 DSP / 0 BRAM, WNS +0,073 ns; phần tính + mạng 18 733 LUT, 64 DSP. Bộ Montgomery riêng (`TREN_MANG = 3`) là bản đối chứng.
- Giao diện, vector, testbench không đổi. Mạng bank → tile làm cho 16 butterfly/chu kỳ, nay dư (03 mục 1).
- Giả thuyết 4 viết lại theo tốc độ phát 1/3 (số chu kỳ phát × 3, độ trễ 19; dự báo q12289 N1024 ≤ 1 466, N256 ≤ 450, xen
  kẽ ≤ 240, NTT 32 bit N256 ≤ 450); người dùng duyệt, khóa lại lần 6.
- Bản trước: [docs/plan_history/before_on_array_v1_2026-11-01/](../../../docs/plan_history/before_on_array_v1_2026-11-01/).

### 2026-10-31, lần 7: một lane 32 bit cho mọi NTT

- Hợp đồng tile (10, lần 6): bỏ lane 16 bit và cổng `cfg_lane32`; mọi q lẻ 3 ≤ q < 2³¹, kể cả 3329 và 12289, dùng bộ
  Montgomery R = 2³²; `req_slot` áp dụng cho mọi request NTT; NTT trễ 15 chu kỳ với mọi q (trước: 13 cho q < 2¹⁶).
- Định dạng: profile 0, 1 dùng định dạng 4; định dạng 3 không còn phép nào nhận (00, 02, 03). Kết quả mọi phép vẫn như
  1.0: bảng root của 12289 / 3329 nhân thêm 2¹⁶ mod q; 0x7 dùng hằng 2⁴⁸ mod q; 0x8 tốn hai lượt (01 mục 3.0).
- Mạng bank → tile sinh lại chỉ cho dạng 4: tối đa 6 nguồn mỗi cổng đọc, 7 mỗi cổng ghi, 6 239 LUT (trước 8 371), 15,75
  butterfly/chu kỳ.
- Tile (Vivado 2018.1, 3,0 ns): v1 777 LUT / 1 004 FF / 11 DSP (trước 913 / 1 155 / 11). Biến thể trên mảng 781 LUT /
  4 DSP: nay đạt các ngưỡng số của giả thuyết 2 ở cấp tile (LUT +0,5%, DSP −7; NTT N256 chậm 1,8 lần một đa thức, 1,9 lần hai đa thức).
  Người dùng duyệt chữ bản đối chứng cho một lane và dự báo mới của giả thuyết 4 (khóa lại lần 5, 01/11/2026, sau khi đã có
  số đo), nên giả thuyết 2 **đạt ở cấp tile**. Theo quy tắc đặt trước (10 mục 8),
  kết quả này nghiêng về biến thể trên mảng; RTL vẫn mặc định bộ riêng cho tới khi người dùng chọn.
- Kiểm thử (11, lần 5): vector NTT gộp thành `ntt.txt` (8 055 ca); testbench bỏ `cfg_lane32`; `+MIX` và
  `FAULT_IGNORE_SLOT` kiểm cả q nhỏ; `run.sh` mặc định chạy RTL nghiệm thu.
- Bản trước: [docs/plan_history/before_one_lane_2026-10-31/](../../../docs/plan_history/before_one_lane_2026-10-31/).

### 2026-10-31, lần 6: hai ô modulus mỗi tile, mạng bank → tile có cấu trúc

- Mạng bank → tile gán butterfly vào tile theo bank của hai toán hạng (03 mục 1): không xung đột bank dữ liệu, 15,9
  butterfly/chu kỳ, 9 397 LUT thay vì 35 623 của crossbar.
- Hợp đồng tile: thanh ghi hằng số có hai ô (q, q′), cổng mới `cfg_slot` (ô được ghi) và `req_slot` (ô của request, đổi
  được ở mọi request). Ở lệnh nhiều prime N = 8..32 một tile nhận butterfly của tối đa hai prime.
- Kiểm thử: `+MIX=1` trộn request của hai prime ở hai ô; lỗi cài vào mới `FAULT_IGNORE_SLOT`.
- Sau đó (tối ưu trong tile): lane 16 bit chỉ dùng ô 0, nên `+MIX` và `FAULT_IGNORE_SLOT` chỉ chạy trên vector lane 32 bit.
- Bản trước: [docs/plan_history/spec2_before_two_slots_2026-10-31/](../../../docs/plan_history/spec2_before_two_slots_2026-10-31/).

### 2026-10-31, lần 5: tín hiệu dừng chung `en` qua một thanh ghi

- RTL nghiệm thu cho thấy `en` (fanout khoảng 800 trong một tile) là đường dài nhất; trong lõi nó phải tới 16 tile.
- Hợp đồng tile mục 2 và 6: điều kiện dừng chung nay nói theo những gì thấy ở cổng (không nhận request, `rsp_valid = 0`,
  cổng ra giữ nguyên, cùng chuỗi kết quả). Trạng thái bên trong được chạy thêm tối đa một chu kỳ sau khi `en` xuống; mỗi
  đợt dừng mất thêm một chu kỳ. Testbench không đổi và vẫn kiểm đúng các điều kiện này.
- Đo 16 tile sau một thanh ghi `en` chung: đạt 3,0 ns mà không cần thanh ghi `en` trong tile (Vivado tự chèn bộ đệm
  toàn cục). RTL giữ mặc định `EN_REG = 0`; thêm yêu cầu: trong lõi `en` lấy trực tiếp từ một thanh ghi.
- Bản trước: [docs/plan_history/spec2_before_en_reg_2026-10-31/](../../../docs/plan_history/spec2_before_en_reg_2026-10-31/).

### 2026-10-31, lần 4: lane 32 bit dùng bộ Montgomery riêng

- RTL nghiệm thu ([hdl/tile/tile_thu.sv](../../../hdl/tile/tile_thu.sv), trợ lý viết theo yêu cầu người dùng): 64 lần chạy
  đạt, 24/24 lỗi bị bắt. Vivado: trên mảng 1 022 LUT / 4 DSP, rút gọn riêng lane 32 bit 906 LUT / 11 DSP, cả hai ≥ 333 MHz.
- Giả thuyết 2 **bị bác bỏ ở cấp tile** (LUT +12,8% > 10%). Theo 10 mục 8, người dùng xác nhận: lane 32 bit của v1 dùng bộ
  Montgomery riêng. Lane 16 bit giữ rút gọn trên mảng.
- Tốc độ tối thiểu của v1: 1 request/chu kỳ ở cả hai lane.
- 03 viết lại mục 1, 4, 6 theo mô hình cấp dữ liệu (model/single_lane_feed.py): 8 bank gói root (trước 4), đọc lệch
  một chu kỳ khi hai toán hạng cùng bank, cách xếp đa thức vào tile. Định dạng gói, dung lượng RAM root và giao diện nạp
  prime không đổi.
- Bản trước: [docs/plan_history/spec2_before_dedicated32_2026-10-31/](../../../docs/plan_history/spec2_before_dedicated32_2026-10-31/).

### 2026-10-31, lần 3: mọi modulus trên mảng nhân

Người dùng chọn sau số đo tile một làn (ghi chú bản nháp mục 9: trên mảng 1 193 LUT so với lai 1 279, cùng 4 DSP):
- Thiết kế v1 rút gọn **cả lane 16 bit** trên mảng nhân: ba lượt Montgomery chạy trên ba bộ nhân khác nhau, 1
  request/chu kỳ, mọi q lẻ < 2¹⁶. Không còn bộ rút gọn hằng 3329/12289.
- Bản đối chứng của giả thuyết 2: lane 16 bit giống thiết kế, lane 32 bit dùng bộ Montgomery riêng (tham số 3).
- `ntt16_q_khac.txt` áp dụng cho cả hai biến thể. Thiết kế lai và rút gọn riêng cả hai lane chỉ còn là điểm đo.
- Bản trước: [docs/plan_history/spec2_before_all_on_array_2026-10-31/](../../../docs/plan_history/spec2_before_all_on_array_2026-10-31/).

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
