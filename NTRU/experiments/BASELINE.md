# Baseline hiện hành — packed16 dùng cả bốn leaf, 160 MHz

**Được người dùng chấp nhận ngày 2026-11-04: `a_cg_packed4_system160`.** Thay `a_cg_z020_system160` làm mốc mặc định. Tên thư mục `experiments/` giữ để bảo toàn source/evidence, không còn mang nghĩa bản đang chờ phê duyệt.

| Thành phần | Nguồn chuẩn |
|---|---|
| RTL được nhận | [a_cg_packed4_system160/rtl/](a_cg_packed4_system160/rtl/), 4 file |
| Top / bridge / core / tile | system_wrapper / a_cg_axil / a_cg_fast / tile_a2 |
| Planner, vector, C replay và test tile | [a_cg_packed4/](a_cg_packed4/), cùng byte RTL với bản hệ thống |
| Contract hiện hành | [Spec 3.1](../spec/FlexTransform/3.1/README.md) |
| Báo cáo P&R | [a_cg_packed4_system160](../study/results/a_cg_packed4_system160.md) |
| Checkpoint được nhận | study/build/a_cg_packed4_system160/route/signoff.dcp |
| Manifest | [BASELINE.json](BASELINE.json), source/workflow/evidence pin SHA-256 |

**34.277 LUT, 33.397 FF, 64 DSP48, 48 RAMB18**. Toàn hệ thống PS7/OCM-JTAG + AXI + clock/reset + core/data/root trên xc7z020clg400-2 đạt **160 MHz**: setup **+0,178 ns**, hold **+0,032 ns**, pulse width **+1,995 ns**. Không có endpoint vi phạm hoặc thiếu ràng buộc trên 79.442 endpoint setup/hold. Route 64.234/64.234 net, 0 lỗi routing, 0 DRC Error; còn 64 cảnh báo DPIP-1. CDC an toàn. DDR/ngoại vi tắt, chưa chạy board.

## Nội dung được nhận

FFT32/64/128, native NTRUGen64, NTT32 đa modulus, packed16 và batch đồng cấu hình. Packed16 chia leaf0/1 và leaf2/3 thành hai nhóm lệch một chu kỳ, dùng chung T-high/NZ history, reducer cuối, add/sub và side/tag RAM. Mỗi gói vẫn chứa hai butterfly; tổng hai gói mỗi ba chu kỳ, tức bốn butterfly/3 chu kỳ/tile khi đủ việc. Scalar/FFT giữ đường fused 32×32.

Giữ nguyên numerical contract và AXI register map. Tile packed nhận ở pha0/1, lõi đọc bank/root ở pha1/2; phải dùng planner và gap của bản bốn leaf. Spec 3.1 mô tả lịch mới; không lấy lịch một gói/3 clock của spec 3.0 áp vào bản này.

Correctness: 1.026 ca AXI (252 packed, 774 nonpacked); 33.600 butterfly tile; 10 ca four-state packed; reset hai luồng, enable stall, hai slot, pairing và halving; 74 transform C, 14 artifact giống từng byte, 4 chữ ký qua verifier độc lập. 774 ca nonpacked giữ chu kỳ; packed nhanh hơn hoặc bằng mốc trước. Reset IP giữ wiring/cấu hình cũ, dùng bằng chứng IP đã kiểm trước đó; không tự gán coverage 38 ca/12 mode của arithmetic cũ cho arithmetic mới.

Ví dụ kernel NTT q12289/N1024: 531→391 chu kỳ; batch hai job: 987→535. Đây là chu kỳ kernel, không phải thời gian signer hoặc thông lượng AXI end-to-end. IFFT normalize tại host-read: phải đọc hết trước cfg/start/load mới.

## Kiểm và build

- `python -X utf8 scripts/check_baseline.py`: đọc nguồn và raw evidence đã pin, không sửa hash/report.
- `python -X utf8 experiments/a_cg_packed4_system160/validate.py`: kiểm log số học, protocol và C replay; không chạy lại mô phỏng.
- [fpga/z020](../fpga/z020/README.md): build mặc định trỏ nguồn baseline mới; audit chỉ đọc signoff.dcp, ghi kết quả ra thư mục riêng.

Nguồn kiểm chứng ở a_cg_packed4 và nguồn hệ thống ở a_cg_packed4_system160 đều được pin. Mọi sửa/tối ưu sau phải dùng bản riêng. Không ghi đè raw evidence được nhận, không cập nhật hash để che khác biệt. Chỉ nâng mốc khi người dùng nhận kết quả mới. Chưa full signer RTL, chưa kiểm board hoặc chứng nhận side-channel.

## Mốc trước và lịch sử

`a_cg_z020_system160`: baseline trước, 31.242 LUT, 31.186 FF, setup +0,038 ns, hold +0,011 ns. Source và bằng chứng giữ nguyên tại đường dẫn cũ. [Snapshot registry/spec/workflow trước lần nâng mốc này](../docs/plan_history/pre_packed4_baseline_160_2026_11_04/INDEX.md); [spec 3.0 lịch sử](../spec/FlexTransform/3.0/README.md). Các mốc ZCU106, prepare_split và perf160 cũ vẫn là lịch sử.

Các file ở study/build và third_party có thể bị git-ignore. Giữ/copy đủ asset đã pin khi chuyển máy; manifest không thay thế raw DCP/log/vector/C source.
