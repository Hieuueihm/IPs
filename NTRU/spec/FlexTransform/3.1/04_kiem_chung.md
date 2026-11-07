# 3.1 — bằng chứng và nghiệm thu baseline bốn leaf

Baseline được người dùng nhận ngày 2026-11-04: a_cg_packed4_system160. [Manifest](../../../experiments/BASELINE.json), [báo cáo P&R](../../../study/results/a_cg_packed4_system160.md). Source hệ thống khớp từng byte với a_cg_packed4 đã kiểm.

| Kiểm tra | Phạm vi đã đạt |
|---|---|
| 1.026 ca AXI | Đúng từng bit: 252 packed, 774 nonpacked; FFT32/64/128/native, NTT nhiều modulus, batch |
| Chu kỳ | Nonpacked giữ nguyên; packed không tăng so với mốc trước. Không gọi toàn suite là cycle-equivalent với 3.0 |
| Oracle tile độc lập | 16.800 gói/33.600 butterfly; 7 q gồm biên, 2 slot, CT/GS, halve on/off, pairing, bubbles và enable stall |
| Mức sử dụng leaf | Có chu kỳ cả 4 leaf mang phép hợp lệ; 300 gói trong 448–449 khoảng chu kỳ; steady-state 4 butterfly/3 clock/tile |
| Reset packed | Abort khi cả hai nhóm có phép đang xử lý; không rò response cũ |
| Four-state cấp lõi | 10 ca packed, N=2/N1024, incomplete NTT, batch và CT/GS |
| AXI | AW/W độc lập, B/R stall, WSTRB, địa chỉ/lệnh không hợp lệ, reset AW/W và B/R pending |
| C replay | 74 transform; 14 artifact giống từng byte, 4 chữ ký xác minh độc lập; altered live input bị từ chối |
| IP reset Xilinx | Kế thừa bài test startup/LOCKED/PS reset/lock-loss/aux polarity của wiring IP không đổi |
| Probe latency packed | CT C21/GS C20 sau cạnh nhận, cả hai nhóm; 5.600 gói đầu các run không stall |

38 ca four-state và reset-abort12 của arithmetic 3.0 là bằng chứng lịch sử; không tự chuyển thành coverage RTL mới. Các phần ngoài transform của ứng dụng vẫn ở C, chưa full signer RTL.

## STA toàn hệ thống

Vivado 2018.1, xc7z020clg400-2, 160 MHz/6,250 ns. PS FCLK100 → clock Wizard generated 1:1 → MMCM160; jitter PS/input Wizard 0,300 ns; setup/hold uncertainty 0,100/0,050 ns. Clock contract giống mốc cũ từng byte.

**34.277 LUT, 33.397 FF, 64 DSP48, 48 RAMB18; setup +0,178 ns, hold +0,032 ns, pulse width +1,995 ns**. 0 endpoint vi phạm trên 79.442 endpoint setup/hold; 64.234/64.234 net route, 0 lỗi routing, 0 DRC Error. Còn 64 cảnh báo DPIP-1. Không thiếu clock/constraint, CDC an toàn.

Nguồn/đích setup xấu nhất: e_product_reg[0] → engine8/g_arr32.bsel_reg[0]; data-path 5,892 ns, trong đó routing 5,408 ns. Hold xấu nhất: prev_real_reg[13] → sa5_reg[19] ở tile7. Không suy Fmax cực đại từ một điểm pass.

Phạm vi gồm PS7/OCM-JTAG, AXI interconnect, AXI-Lite host, clock/reset và toàn core/data/root; DDR/ngoại vi tắt. Chưa chạy board hoặc gate-level SDF. Checkpoint: **study/build/a_cg_packed4_system160/route/signoff.dcp**.

## Kiểm và tái tạo

- `python -X utf8 scripts/check_baseline.py`: kiểm read-only source/workflow/raw evidence hiện hành.
- `python -X utf8 experiments/a_cg_packed4_system160/validate.py`: read-only audit log/correctness.
- `experiments/a_cg_packed4/run_sim.ps1`: full rerun harness có ghi lại output. Giữ các file đã pin; chạy bản sao workspace/output khác, không ghi đè evidence baseline.
- `fpga/z020/audit.tcl`: đọc DCP được nhận và xuất báo cáo mới riêng, không route lại/ghi đè mốc.
- Full build theo [fpga/z020](../../../fpga/z020/README.md), chỉ trên bản sao/output riêng. Build giống source vẫn không tự thay baseline.

Raw asset study/build và third_party có thể bị git-ignore: giữ cả DCP, report, log, vector và C reference khi chuyển máy. Manifest nhưng thiếu file không được coi là đã tái kiểm.
