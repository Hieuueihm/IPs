# Baseline được nhận — packed16 bốn leaf, 160 MHz

**Người dùng nhận ngày 2026-11-04**, thay `a_cg_z020_system160`. Contract [3.1](../../spec/FlexTransform/3.1/README.md), [registry/nguồn chuẩn](../BASELINE.md). Bốn file RTL ở đây là nguồn build mặc định; planner/test/C replay tại `a_cg_packed4/` được pin cùng baseline và có RTL giống từng byte.

Dùng cùng PS7/OCM-JTAG, AXI interconnect, clock/reset và part
`xc7z020clg400-2` như baseline. `signoff.tcl` giống baseline từng byte:
FCLK100 → MMCM160, jitter 0,300 ns, setup/hold uncertainty 0,100/0,050 ns.
Không đưa constraint OOC của phép đo synth trước vào top hệ thống.

Chạy: `./experiments/a_cg_packed4_system160/run_pnr.ps1`.
Script giữ các đầu ra dưới `study/build/a_cg_packed4_system160/`, từ chối
ghi đè project/checkpoint sign-off đã có. Không tạo bitstream hoặc nạp board.

Sau khi hoàn tất: `python -X utf8 experiments/a_cg_packed4_system160/report.py`.
Report kiểm input hash, setup/hold/pulse width toàn thiết kế, ràng buộc,
CDC, routing, DRC và tài nguyên; timing pass và ngân sách LUT là hai cờ riêng.
Kết quả ở `study/results/a_cg_packed4_system160.md` và
`study/build/a_cg_packed4_system160/signoff_results.json`.

**Đã hoàn tất P&R và audit ngày 2026-11-04: đạt 160 MHz.** Setup
+0,178 ns, hold +0,032 ns, pulse width +1,995 ns. Không có endpoint vi
phạm trên 79.442 endpoint setup/hold; không có endpoint chưa ràng buộc.

Toàn hệ thống: **34.277 LUT, 33.397 FF, 64 DSP48, 48 RAMB18**. Routing
64.234/64.234 net, 0 lỗi routing, 0 DRC Error. Còn 64 cảnh báo DPIP-1 về
pipeline DSP, cùng loại khuyến nghị với baseline. CDC được báo an toàn.

Đường setup xấu nhất từ `e_product_reg[0]` tới
`engine[8].u_tile/g_arr32.bsel_reg[0]`, phần lớn độ trễ nằm ở routing
(5,408/5,892 ns data-path delay). RTL giống ứng viên đã kiểm từng byte.

[Báo cáo cuối](../../study/results/a_cg_packed4_system160.md).
Checkpoint: `study/build/a_cg_packed4_system160/route/signoff.dcp`.
Nguồn và bằng chứng mốc trước giữ nguyên làm lịch sử; registry mặc định đã chuyển sang bản này. Chưa nạp board hoặc mô phỏng SDF.


## Kiểm và bảo toàn baseline

`python -X utf8 scripts/check_baseline.py` kiểm read-only nguồn/workflow/raw evidence. `python -X utf8 experiments/a_cg_packed4_system160/validate.py` kiểm log chức năng. Điểm vào build/audit mặc định xem [fpga/z020](../../fpga/z020/README.md); không chạy full rerun lên các output đã pin.

Planner chuẩn: [a_cg_packed4/planner.py](../a_cg_packed4/planner.py). Packed16 tile nhận pha0/1, core đọc pha1/2; mỗi gói hai butterfly, tổng bốn butterfly/3 clock khi đủ việc. Không thay descriptor/gap bằng lịch 3.0. [Register map và sequencing](../../spec/FlexTransform/3.1/02_giao_dien.md), [cấu hình board](board_sources.md).

`manifest.json` và `study/build/.../input_manifest.json` lưu nguồn gốc lần thử trước khi nhận; trường baseline/accepted_baseline_changed ở đó là metadata của thời điểm đo, không phải con trỏ baseline hiện hành. Registry chuẩn là `experiments/BASELINE.json`.
