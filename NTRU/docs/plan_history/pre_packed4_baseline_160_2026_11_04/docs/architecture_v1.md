# Kiến trúc baseline 160 MHz của FlexTransform

Cập nhật 2026-11-04. Nguồn chuẩn: [baseline được nhận](../experiments/BASELINE.md), contract: [spec 3.0](../spec/FlexTransform/3.0/README.md). Tên file được giữ để các link cũ vẫn mở đúng trang hiện hành. [Bản mô tả trước đây](plan_history/pre_baseline_160_2026_11_04/docs/architecture_v1.md) là lịch sử.

## 1. Bài toán và ý tưởng

Dùng cùng mảng nhân/cộng cho FFT fixed-point nhiều precision và NTT nhiều modulus. Tăng độ rộng FFT bằng các lượt tính phần 32 bit trong cùng tile; đổi modulus NTT bằng hằng số q/qinv và root nạp từ host. Giữ kết quả đúng contract tham chiếu PQC. Baseline không yêu cầu ghép nhiều tile thành một phép nhân rộng và không tuyên bố cơ chế ghép/tách liên tile đã hoàn thành.

## 2. Hệ thống

```text
PS reference 33.333333 MHz
  PS7 FCLK0 100 MHz → MMCM → 160 MHz cho AXI và lõi
  PS7 M_AXI_GP0 → AXI interconnect/converter → a_cg_axil
      → a_cg_fast (frontend/host + constant-geometry controller)
          ↔ 32 bank dữ liệu
          ↔ 16 tile_a2, mỗi tile 4 leaf nhân 16×16
          ↔ root RAM riêng theo tile
  FCLK_RESET0_N + MMCM LOCKED → proc_sys_reset → reset AXI/lõi
```

Top hệ thống `system_wrapper` sinh từ BD, arithmetic RTL ở [baseline/rtl](../experiments/a_cg_z020_system160/rtl/). Root, modulus, descriptor và mọi hệ số đều truy cập được qua AXI-Lite; không buộc hằng input để bỏ logic. PS dùng OCM/JTAG, DDR và ngoại vi đang tắt.

## 3. Dùng chung số học

16 tile giống nhau, mỗi tile 4 leaf 16×16 ghép thành đường nhân 32×32; toàn mảng dùng 64 DSP48. Mỗi tile xử lý FFT32/64/128, NTT thường và packed16. FFT dùng nhân phức 3M, các tích rộng được tính theo phần và tích lũy trong tile. NTT dùng lại bộ nhân cho ba bước Montgomery T, m, m·q. Các chuỗi cộng hiệu chỉnh NTT được dùng lại cho tổng FFT khi mode cho phép; dữ liệu trung gian giữ tại tile.

Packed16 dùng hai lane 16 bit khi q < 2¹⁵, cắt carry đúng biên và dùng Montgomery R=2¹⁶ mỗi lane. NTT thường dùng R=2³², q lẻ từ 3 tới dưới 2³¹. Hai chiều dùng CT/GS theo contract. Có hai modulus slot ở tile độc lập, nhưng core hiện chỉ chọn slot 0; một lệnh/batch dùng cùng cấu hình.

FFT nhiều precision là yêu cầu đã đạt; hợp tác liên tile là biến thiết kế còn có thể khảo sát. Không gọi việc tính tuần tự theo limb trong tile là ghép PE liên tile.

## 4. Bộ nhớ và điều phối

- 32 bank dữ liệu, mỗi bank `256 × 32` bit, tổng khai báo 32 KiB. Hai vùng ping-pong nằm trong các hàng của chính bank; không phải 64 bank 16 bit của core cũ.
- 16 root RAM, mỗi tile `512 × 32` bit; host nạp bảng theo thứ tự sử dụng và chiều transform.
- Mapping constant-geometry, giao dịch đọc/tính/ghi theo planner của baseline; không dùng generator `hdl/core_ntt/ntt_core_gen.sv` của bản cũ.
- Batch đồng cấu hình dùng các bit địa chỉ/bank còn trống. `jobs_log ≤ 4` không có nghĩa mọi cấu hình đều chạy được 16 job: còn giới hạn planes/rows, do RTL và planner kiểm.
- Frontend lệnh, request, cộng/trừ và rounding IFFT có pipeline; số chu kỳ từng kernel phải khớp planner, không yêu cầu mọi mode cùng latency.
- Tổng P&R: 32 RAMB18 cho dữ liệu, 16 RAMB18 cho root; không suy dung lượng logic bằng cách nhân số BRAM vật lý.

## 5. Contract và kết quả

FFT32/64/128 giữ đúng rounding/carry/wrap. Native NTRUGen64 có mode riêng. IFFT giữ dữ liệu trong RAM chưa normalize và áp scale khi đọc host: phải đọc kết quả trước cfg/start/load tiếp theo. Chưa hỗ trợ chaining IFFT đã normalize trực tiếp trong RAM.

AXI base `0x43C00000`, 4 KiB. Register map và sequencing ở [contract giao tiếp](../spec/FlexTransform/3.0/02_giao_dien.md). Không dùng API 3-bit format/16-prime-slot/A-B-C của spec 2.0 để điều khiển bản này.

Toàn hệ thống ở 160 MHz: **31.242 LUT, 31.186 FF, 64 DSP, 48 RAMB18; setup +0,038 ns, hold +0,011 ns**, 0 vi phạm timing. Đây là STA sau P&R và audit clock PS, chưa đo board. [Báo cáo](../study/results/a_cg_z020_system160.md).

1.026 ca qua AXI khớp số học và chu kỳ, 74 transform C/14 artifact/4 chữ ký đã kiểm. Phần còn lại của ứng dụng vẫn chạy C; không coi đây là full RTL signer hoặc nghiệm thu toàn spec 2.0. CMUL/SPLIT/MERGE, RECIP, basemul riêng, DMA và full keygen không được bổ sung chỉ bằng việc đổi baseline.

## 6. Mốc tiếp theo

Dùng baseline này để đối chiếu PPA/cycle/kernel khi thử nghiệm trên bản riêng. Còn cần nghiên cứu chi phí tính linh hoạt, baseline so sánh công bằng và claim paper; mô phỏng đúng/P&R đạt không tự chứng minh novelty. Chỉ chạy board, thêm DDR/DMA hoặc đổi clock sau khi có mục tiêu tương ứng và kiểm lại phần bị ảnh hưởng.
