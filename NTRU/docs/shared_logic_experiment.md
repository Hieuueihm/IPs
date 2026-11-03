# Thử gộp mạng 32 bit và tính sẵn tổng root

Ngày 01/11/2026. Biến thể thử nằm trong `study/build/shared_logic_experiment/`.
RTL chính không bị sửa. Script tạo lại thử nghiệm:
[experiment_shared_logic.py](../scripts/experiment_shared_logic.py).

**Kết luận: chưa chọn bản kết hợp này để giảm tài nguyên.** Toàn core chỉ giảm
0,19% LUT, trong khi FF tăng 6,85% và BRAM tăng 18,75%. Kết quả số học PASS trong
bộ kiểm đã chạy, nhưng lợi ích tài nguyên riêng tile không chuyển thành lợi
ích đáng kể ở cấp core.

## Các bản thử

| Bản | Thay đổi |
|---|---|
| baseline | Bản đối chiếu, thêm điều kiện chờ ghi xong trước khi chuyển tầng FFT |
| word32 | Như baseline; gộp lựa chọn dữ liệu/ghi theo từ 32 bit |
| root_sum | Như word32; tổng `wr+wi` tính sẵn trong ROM và đưa tới tile |

Điều kiện chờ ghi xong được áp dụng cho cả ba bản để không so với FFT32 đang
sai của RTL chính. Không tăng delay tùy ý để che lỗi: có bộ đếm kết quả theo
tầng và chỉ chuyển khi số write đã hoàn tất. Lịch các tầng NTT giữ nguyên.
Đây là sửa chức năng trong bản thử, không là kết quả giảm tài nguyên.

## Những gì đã thay

- Hai nửa 16 bit đi cùng địa chỉ dùng một selector 32 bit. Điều này chỉ hợp lệ với
  những cổng luôn đọc/ghi theo cặp trong core hiện tại; không thay bằng mạng
  này cho interface cho phép hai nửa chọn độc lập.
- Từ ROM FFT vẫn rộng 96 bit; phần 32 bit trước đây bằng zero chứa limb của tổng root.
  Tổng tính sau quantize/conjugate, wrap đúng W rồi mới tách limb.
- Mạng có thêm đường chuyển tổng; tile có thêm input 32 bit. Bỏ bộ cộng tổng
  root và lần đọc root phục vụ phép cộng đó. Giữ bộ đệm tổng vì tích thứ ba
  vẫn cần dùng giá trị này đúng lúc.
- Các phép nhân, carry, rounding, format và vector expected giữ nguyên.

Lượt này mới thay mạng chọn dữ liệu và đường cấp tổng root. Chưa đổi RAM thành
32 bank vật lý, chưa gom bộ điều khiển/buffer của bốn tile thành một cụm, và
chưa thay topology kết nối. Vì vậy đây là phép đo hai bước đầu, chưa là toàn
bộ phương án chia sẻ tài nguyên trong [kế hoạch](shared_logic_plan.md).

## Kiểm chứng đã chạy

| Kiểm tra | Kết quả |
|---|---|
| Mạng word32/root_sum so mạng cũ | 5.000 chu kỳ PASS, gồm enable/hold, root, đọc và ghi |
| Tile root_sum: FFT32 | 2.940 ca không stall và 2.940 ca có stall PASS |
| Tile root_sum: FFT64/128 | 11.520 ca không stall và 11.520 ca có stall PASS |
| Tile root_sum: NTT | 8.055 ca không stall và 8.055 ca có stall PASS |
| Core baseline | 48 NTT và 54 FFT PASS bằng Icarus |
| Core word32 | 48 NTT và 54 FFT PASS bằng Verilator |
| Core root_sum | 48 NTT và 54 FFT PASS bằng Verilator |
| Core root_sum: các ca nhỏ FFT32/64/128 | Chạy thêm bằng Icarus, PASS |
| Driver Verilator khi đổi expected một bit | Trả lỗi và FAIL đúng như yêu cầu |

Hai core dùng Verilator chạy [driver C++](../sim/experiments/shared_core_main.cpp) chỉ để
nạp RAM/chạy/đọc và so expected; không tính butterfly ở host. Verilator là mô
phỏng hai trạng thái; các kiểm tile và ca core nhỏ bằng Icarus bổ sung kiểm bốn trạng thái.
Đây chưa là live replay của toàn signer hoặc nghiệm thu toàn spec 2.0.

Lượt FFT word32 bằng Icarus đã dừng vì chậm; kết quả đầy đủ của bản này lấy từ
Verilator. Log lưu trong từng thư mục biến thể, phân biệt bằng hậu tố `_fast`.

## Tài nguyên riêng tile

Cùng Vivado 2018.1, chip xczu7ev-ffvc1156-2-e, clock 3 ns, wrapper đăng ký I/O,
`TREN_MANG=1`; số bên dưới sau place/route:

| Tile | LUT | FF | DSP | BRAM | WNS |
|---|---:|---:|---:|---:|---:|
| baseline | 1.995 | 1.436 | 4 | 0 | +0,210ns |
| root_sum | 1.932 | 1.496 | 4 | 0 | +0,198ns |

Giảm 63 LUT (~3,2%), tăng 60 FF (~4,2%). Input tổng root mới và các thanh ghi giữ
nó được tính vào bản thử; không giấu chi phí giao tiếp khỏi bảng tài nguyên.
WNS cả hai dương ở mục tiêu 3 ns, không là timing của toàn core.

## Tài nguyên toàn core

Cùng Vivado, chip và source đã đóng băng; số sau `synth_design` và `opt_design`,
chưa place/route. Cả hai bản đều có điều kiện chờ ghi xong FFT.

| Toàn core | LUT | FF | DSP | BRAM36 tương đương |
|---|---:|---:|---:|---:|
| baseline | 54.677 | 29.413 | 64 | 64 |
| word32 + root_sum | 54.573 | 31.428 | 64 | 76 |
| Chênh lệch | −104 (−0,19%) | +2.015 (+6,85%) | 0 | +12 (+18,75%) |

BRAM36 tương đương = RAMB36 + RAMB18/2; không phải số block chỉ có loại RAMB36.
Không so các số synthesis này với baseline cũ sau route khoảng 56 nghìn LUT.
Chưa chạy place/route toàn core của bản thử, nên chưa kết luận timing hệ thống.

Phân cấp LUT giải thích vì sao giảm ở tile nhưng gần như không giảm toàn core:

| Phần | baseline | Bản kết hợp | Chênh lệch |
|---|---:|---:|---:|
| 16 tile | 35.423 | 34.564 | −859 |
| Mạng `u_net` | 4.617 | 5.545 | +928 |
| Bốn ROM root, phần logic | 2.745 | 2.439 | −306 |
| Logic gắn RAM dữ liệu | 4.607 | 4.724 | +117 |
| Logic trực tiếp ở core | 6.950 | 6.966 | +16 |

Mạng thêm đường tổng 32 bit tới mỗi tile làm tăng mux và thanh ghi. Mặc dù
từ ROM vẫn khai báo 96 bit, 32 bit bằng zero trước đây có thể bị tool loại;
điền tổng vào đó làm tăng bộ nhớ thực. Bốn ROM tăng tổng cộng 12 BRAM36.
Vì vậy không thể coi phần zero trong khai báo là dung lượng vật lý miễn phí.
Thay đổi phân cấp sau tối ưu cũng không phải phép đo cô lập từng thay đổi RTL.

Đã mô phỏng riêng word32, nhưng chưa đo PPA toàn core của bản word32 riêng;
không quy toàn bộ chênh lệch trên cho một thay đổi. Kết quả đầy đủ và hash:
[shared_logic_experiment.json](../study/results/shared_logic_experiment.json).

## Quyết định sau thử nghiệm

Giữ bản thử và log để tra cứu, không đưa bản kết hợp vào RTL chính. Việc cấp
sẵn tổng root theo cách này không đáp ứng mục tiêu giảm tài nguyên toàn core.
Gộp từ 32 bit vẫn giúp đơn giản hóa interface, nhưng chưa có bằng chứng rằng
chỉ thay cách viết mux sẽ giảm mạnh tài nguyên mà Vivado đã tối ưu.

Ưu tiên khảo sát tiếp là gom lịch limb, cấu hình và metadata cho các tile
cùng tiến độ; sau đó giảm buffer lặp theo cụm có đủ cổng. Nếu thử tổng root
lần nữa, cần chọn/broadcast trong cụm hoặc tái sử dụng đường root hiện có,
thay vì kéo thêm đường 32 bit tới cả 16 tile. Các hướng này chưa được triển khai
hoặc đo trong lượt hiện tại.

## Chạy lại

```text
python -X utf8 scripts/experiment_shared_logic.py --net-test
python -X utf8 scripts/experiment_shared_logic.py --tile-test
python -X utf8 scripts/experiment_shared_logic.py --fast-test --variants root_sum
python -X utf8 scripts/experiment_shared_logic.py --fast-test --variants word32
python -X utf8 scripts/experiment_shared_logic.py --synth
python -X utf8 scripts/experiment_shared_logic.py --synth-core
python -X utf8 scripts/experiment_shared_logic.py --report
```

Vivado và MSYS2/Verilator dùng đường dẫn cài trên máy hiện tại. Các input RTL
được ghi hash; script từ chối dùng lại thư mục thử nếu source đầu vào đổi.
Lệnh `--test --variants baseline` dùng Icarus và kiểm cả số dòng CASE lẫn TOTAL,
không coi exit 0 hoặc dòng TOTAL có 54 record là đủ khi chỉ chạy một case.
