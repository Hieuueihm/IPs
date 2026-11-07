# Baseline hiện hành — a_cg_z020_system160

**Được người dùng chấp nhận ngày 2026-11-04.** Thay thế `a_cg_prepare_split_baseline` và các ứng viên cũ làm điểm xuất phát mặc định. Tên thư mục `experiments/` được giữ để không phá source/evidence; bản này đã là baseline được nhận, không còn là ứng viên chờ phê duyệt.

## Nguồn chuẩn và phạm vi

| Thành phần | Nguồn |
|---|---|
| RTL baseline | [a_cg_z020_system160/rtl/](a_cg_z020_system160/rtl/) |
| AXI slave / core / tile | `a_cg_axil` / `a_cg_fast` / `tile_a2` |
| Top hệ thống | `system_wrapper`, sinh từ `create_project.tcl` |
| Clock cuối | `signoff.tcl`: PS FCLK100 → input Wizard 1:1 → MMCM160 |
| Contract hiện hành | [Spec 3.0](../spec/FlexTransform/3.0/README.md) |
| Checkpoint được nhận | `study/build/a_cg_z020_system160/route/signoff.dcp` |
| Bằng chứng | [Sign-off](../study/results/a_cg_z020_system160.md), [chi tiết baseline](a_cg_z020_system160/README.md) |
| Manifest | [BASELINE.json](BASELINE.json), kiểm bằng `python -X utf8 scripts/check_baseline.py` |

Hệ thống PS7/OCM-JTAG + AXI + MMCM/reset + toàn bộ lõi/data/root, target `xc7z020clg400-2`, clock 160 MHz (6,250 ns). DDR/ngoại vi đang tắt, chưa chạy board. Không sao chép đè RTL ở `hdl/`; danh mục nguồn nay trỏ rõ tới thư mục baseline này.

## Kết quả được nhận

**31.242 LUT, 31.186 FF, 64 DSP48, 48 RAMB18.** Setup **+0,038 ns**, hold **+0,011 ns**, pulse-width **+1,995 ns**; 0 endpoint vi phạm trên báo cáo toàn hệ thống, không lọc riêng core. 59.641/59.641 net đã route, 0 lỗi routing và 0 DRC Error. Có 64 khuyến nghị DPIP-1; không gọi đây là 0 warning.

Clock/jitter đã audit từ PS: 100/160 MHz, input jitter 0,300 ns, setup uncertainty 0,100 ns, hold uncertainty 0,050 ns. Không dùng timing OOC 30.215 LUT/+0,231/+0,052 ns để thay cho số toàn hệ thống ở trên.

1.026 ca qua AXI, reset/protocol, 74 transform C, 14 artifact và 4 chữ ký đã qua kiểm. Ba file arithmetic/core giống bản `a_cg_z020_perf160`; đây là nguồn reference/evidence phụ cần giữ khi chạy lại test. Không thay precision hoặc contract PQC. IFFT normalize khi đọc host; phải đọc trước cấu hình/start/load mới.

## Sử dụng và thay đổi

Kiểm đã pin: `python -X utf8 scripts/check_baseline.py`. Build/audit mới xem [fpga/z020](../fpga/z020/README.md). Mỗi thử nghiệm sau phải tách source/output riêng; baseline JSON là mốc đối chiếu, không tự cập nhật hash để hợp thức hóa thay đổi source. Chỉ người dùng nhận một kết quả mới thì mới thay mốc.

Manifest cũ của từng thí nghiệm được giữ nguyên. Một số generator báo cáo lịch sử còn kiểm cả hash tài liệu ở `hdl/`; sau lần cập nhật tài liệu này, dùng checker baseline ở trên cho mốc được nhận, và `validate.py` để kiểm log chức năng. Không diễn giải khác biệt Markdown là thay đổi RTL.

## Lịch sử mốc

| Mốc | Vai trò hiện nay |
|---|---|
| `a_cg_z020_system160` | **Baseline hiện hành**, STA toàn hệ thống 160 MHz |
| `a_cg_z020_perf160` | Core/host OOC đã kiểm, 30.215 LUT; nguồn arithmetic/reference phụ |
| `a_cg_z020_100mhz` | Điểm lịch sử 100 MHz, 29.837 LUT; không phải mặc định |
| `a_cg_prepare_split_baseline`, `a_cg_prepare_route` | Mốc nhận trước; P&R 200 MHz chưa đạt; đã được thay thế |
| `a_cg_host_baseline`, các nhánh ZCU106 | Đối chiếu lịch sử, không phải target/current source |

[Snapshot tài liệu trước lần nhận này](../docs/plan_history/pre_baseline_160_2026_11_04/INDEX.md).
