# Source RTL trong hdl/ — nhánh lịch sử

> **Baseline hiện hành từ 2026-11-04:** [a_cg_z020_system160](../experiments/BASELINE.md), source tại `experiments/a_cg_z020_system160/rtl/`, contract [3.0](../spec/FlexTransform/3.0/README.md). Các file trong `hdl/` và mô tả bên dưới thuộc nhánh trước; giữ nguyên RTL làm lịch sử, không ghép chúng vào build baseline.

## Lõi cũ trong thư mục này

Đọc theo thứ tự dưới đây. Chạy lệnh từ root repo `D:\IPs\NTRU` để đường dẫn ROM đúng.

| File | Vai trò |
|---|---|
| [mul_ss.v](mul_ss.v) | Bộ nhân nhỏ, chọn toán hạng có dấu/không dấu |
| [tile/tile_thu.sv](tile/tile_thu.sv) | Tile hiện tại: bốn bộ nhân, FFT butterfly, Montgomery và CT/GS |
| [core/flex_banked_scratch.sv](core/flex_banked_scratch.sv) | RAM chia 64 bank, mỗi bank đọc/ghi độc lập |
| [net/ntt_bank_net_s.sv](net/ntt_bank_net_s.sv) | Chọn dữ liệu từ RAM đưa đến tile và trả kết quả |
| [core_ntt/ntt_core.sv](core_ntt/ntt_core.sv) | Điều khiển đọc, tính, ghi cho toàn transform |
| [core_ntt/ntt_core_gen.sv](core_ntt/ntt_core_gen.sv) | Bảng lịch và chọn nguồn, sinh tự động |
| `core_ntt/root_pack_b0.mem` đến `root_pack_b3.mem` | Bảng hệ số nhân của transform |

`core_ntt/ntt_core_gen.sv` và ROM được tạo bởi
[gen_ntt_core.py](../scripts/gen_ntt_core.py). Sửa generator khi cần đổi bảng;
không sửa thủ công file sinh rồi để generator ghi đè lại.

[Danh sách file biên dịch](../sim/core_ntt/sources.f) là danh sách cho testbench
core hiện tại. Hai wrapper `tile_array16_top.sv` và `tile_thu_top` phục vụ đo
riêng, không phải một signer hoàn chỉnh.

## Bản cũ và bản nháp

| Vị trí | Cách sử dụng |
|---|---|
| `core/flex_kernel_engine.sv`, `proto/flex_stream_array.sv`, `proto/flex_stream_tile.sv` | Baseline cũ có chín kernel; giữ để đối chiếu kết quả ứng dụng |
| `tile_thu/tile_thu.sv` | Bản nháp cũ, khác `tile/tile_thu.sv`; không biên dịch hai bản cùng lúc |
| `tile_l16x4.v`, `tile_l32.v`, các module khác trong `proto/` | Thí nghiệm trước; không tự thêm vào file list core hiện tại |
| Các wrapper `*_top.sv` trong `net/` và `tile/` | Đo riêng từng khối; đọc script tương ứng trước khi dùng |

Giữ các đường dẫn cũ để script và bằng chứng đã lưu không bị hỏng. Danh sách
trên giúp chọn đúng source; không cần xóa hay di chuyển các thí nghiệm cũ.

## Tên đang dùng trong code

| Tên | Nghĩa |
|---|---|
| tile | Một khối tính gồm bốn bộ nhân 16×16 và phần cộng/trừ/xử lý kết quả |
| limb | Một phần 32 bit của số 64/128 bit |
| bank | Một nhánh RAM có cổng đọc/ghi riêng |
| root/twiddle | Hệ số nhân dùng tại từng bước FFT/NTT |
| CT / GS | Hai cách đặt phép nhân trước hoặc sau cộng/trừ trong butterfly |
| commit | Kết quả đã thực sự ghi vào RAM |
| profile | Bộ tham số đã chọn, chẳng hạn modulus q và bảng root |
