# FlexTransform — thiết kế lại từ đầu

**Trạng thái: microarchitecture0.2 đã khóa ngày2026-11-05. Chưa có RTL mới hoặc PPA mới.**

Đây là bộ hồ sơ để tự viết một project **FFT/IFFT đa precision và NTT/INTT đa modulus** cho kernel PQC, ưu tiên Falcon/FN-DSA. RTL mới được viết theo ranh giới module rõ ràng; baseline đã nhận chỉ làm mốc số học, vector và PPA. Thư mục này không thay `PLAN.md`, spec 3.1 hay registry baseline ở gốc repository.

## Quyết định xuất phát

| Hạng mục | Chọn cho lần dựng đầu |
|---|---|
| Mảng tính | 16 tile giống nhau, mỗi tile 4 leaf 16×16; tổng 64 DSP |
| FFT thường | Fixed-point 32/64/128 bit mỗi thành phần; 1/2/4 limb 32 bit |
| Native NTRUGen | Q32.32 riêng, chỉ FFT64; giữ cả hai chiều |
| NTT | Montgomery R=2³², q lẻ 3≤q<2³¹ |
| Packed16 | Montgomery R=2¹⁶, q<2¹⁵, hai nhóm dùng đủ 4 leaf |
| Đa precision | Tăng số lượt nhân trong tile; không bắt buộc ghép tile |
| Đa modulus | q/qinv/root thay theo command; không thêm multiplier theo từng q |
| Bộ nhớ | CG, 32 data bank, 16 root bank; mux đọc tối đa 4 nguồn/input |
| Đồng thời | Một context; batch các job cùng cấu hình |
| FPGA mục tiêu | xc7z020clg400-2, 160 MHz, khoảng ≤35k LUT toàn hệ thống |
| Giao tiếp đầu tiên | Giữ register map AXI-Lite 3.1; bên trong dùng command/token rõ ràng |

Mục tiêu DSP là 64, RAMB18 là 48. Đây là **mục tiêu nghiệm thu RTL mới**, không phải kết quả đã đạt. Không tự chuyển số 34.277 LUT/160 MHz của baseline sang project viết lại.

## Microarchitecture đã khóa

- [08: port chính xác](spec/08_locked_ports.md), [09: từng clock](spec/09_locked_cycles.md), [10: FSM](spec/10_locked_fsm.md), [11: liveness và điều kiện khóa](spec/11_liveness_and_lock.md).
- JSON authoritative trong `microarchitecture/`; CSV mọi cạnh trong `microarchitecture/cycles/`.
- [Báo cáo khóa và số đo model](docs/MICROARCH_REVIEW.md) là điểm đọc nhanh trước khi viết RTL.
- Model chạy được: `verification/model/liveness.py`; full report730 case có hash. Spec08..11 thay các lựa chọn còn mở trong draft0.1.

## Thứ tự đọc

1. [Yêu cầu và phạm vi](spec/01_requirements.md).
2. [Kiến trúc tổng thể và các quyết định](docs/ARCHITECTURE.md).
3. [Contract số học](spec/02_arithmetic.md).
4. [Bộ nhớ, root và lịch](spec/03_memory_schedule.md).
5. [Giao tiếp và vòng đời command](spec/04_interfaces.md).
6. [Thiết kế RTL từng khối](spec/05_rtl_blocks.md) và [port/bundle giữa các khối](spec/07_block_interfaces.md).
7. [Kế hoạch kiểm chứng](spec/06_verification.md).
8. [Lộ trình triển khai](PLAN.md).

[design.json](design.json) là bản cấu hình máy đọc. [reference_lock.json](reference_lock.json) khóa các nguồn tham chiếu hiện có; nó không biến RTL cũ thành RTL mới.

## Bố cục project

```text
rebuild/flextransform/
  README.md, PLAN.md, design.json, reference_lock.json
  docs/ARCHITECTURE.md
  spec/01..06_*.md
  rtl/                    # nơi người thiết kế sẽ viết RTL
    README.md
    filelist.planned      # danh sách dự kiến, chưa phải filelist build
  verification/README.md
  fpga/README.md
  tools/check_design.py   # kiểm tính nhất quán tài liệu và nguồn tham chiếu
```

Output mới phải nằm ở `study/build/flextransform_rebuild/`, không ghi vào thư mục evidence baseline. Tên module dùng tiền tố `ft_` để không bị compile lẫn với source nghiên cứu cũ.

## Bằng chứng dùng để chọn hướng

Theo [ablation cùng chip/contract](../../docs/paper_notes/05_resource_ablation_baseline31.md), đường FFT/NTT dùng chung tiết kiệm 4.860 LUT và 64 DSP so với tách hai đường số học vẫn chung host/memory. Chia sẻ T_hi giảm 1.208 LUT; tile mạnh nhưng cấp dữ liệu thưa không giữ được tốc độ packed16. Vì vậy giữ số học tại tile, chia sẻ điều khiển và lịch sử khi không tranh chấp, đồng thời thiết kế bộ nhớ cùng datapath.

Reduction NTT32 riêng chỉ tăng 823 LUT nhưng cần thêm 112 DSP. Nó được giữ làm đối chứng nghiên cứu, không đưa vào cấu hình 64 DSP đầu tiên. 16 tile được chọn để có mốc so; chưa chứng minh đây là số tile tối ưu toàn cục.

## Giữ gì và viết mới gì?

- **Giữ nguyên ý nghĩa:** số học, tập mode, thứ tự host, root convention, packing, hmin, kết quả ứng dụng C.
- **Viết mới:** phân cấp RTL, tên/kiểu tín hiệu, FSM, quản lý command, đếm in-flight, context ghi và tổ chức verification/build.
- **Tương thích ngoài:** register map và cách phần mềm poll ready. Không cam kết cùng số clock cho từng lệnh MMIO.
- **Đo lại:** latency tile, gap giữa tầng, chu kỳ kernel, tài nguyên, setup/hold toàn hệ thống.

Không sao chép một monolithic module rồi đổi tên và gọi đó là dựng từ đầu. Có thể đọc RTL tham chiếu để hiểu contract; implementation và kiểm chứng mới phải có filelist, hash và báo cáo riêng.

Chạy `python -X utf8 rebuild/flextransform/tools/check_design.py` để kiểm hồ sơ. Lệnh này kiểm cả full model report khớp source; **không mô phỏng RTL và không xác nhận PPA**.
