# Bản thử RTL 160 MHz trên XC7Z020-CLG400-2

> **Mốc đối chiếu, không phải baseline hiện hành.** Từ 2026-11-04 baseline được nhận là [a_cg_z020_system160](../BASELINE.md). Số đo dưới đây chỉ thuộc cấu hình/source của thư mục này; không thay cho STA toàn hệ thống 160 MHz.


Đã qua P&R tại chu kỳ 6,250 ns và các kiểm tra chức năng bên dưới. Bản riêng, chưa thay RTL chính, chưa commit. Không coi 160 MHz là Fmax cực đại đã tìm được.

## Kết quả đo

| Chỉ tiêu | Điểm 100 MHz hiện có | Bản thử 160 MHz |
|---|---:|---:|
| LUT, sau routing, gồm LUTRAM | 29.837 | **30.215** |
| FF | 24.115 | 29.900 |
| DSP48 | 64 | 64 |
| RAMB18 | 48 | 48 |
| Setup nội bộ | +0,032 ns | **+0,231 ns** |
| Hold nội bộ | +0,051 ns | **+0,052 ns** |

Tính đủ frontend/host, điều phối, tile, bộ nhớ dữ liệu và root. Root dùng 16 RAMB18, dữ liệu dùng 32 RAMB18. Tăng 378 LUT, còn 4.785 LUT so với ngân sách 35.000. Toàn bộ 57.119 net cần routing đã được route, 0 lỗi routing. Không thêm false-path, multicycle hay case-analysis.

Phạm vi đạt timing là các đường nội bộ giữa phần tử tuần tự, kể cả host và điều khiển. Đây là implementation OOC: hold toàn giao diện vẫn −1,237 ns, 357 endpoint, đường xấu nhất từ cổng `desc_mask[10]` đến thanh ghi frontend. Cổng chưa có vị trí vật lý, input min-delay đang bằng 0; chưa xác nhận timing I/O khi ghép PS/AXI hoặc board. Không loại bỏ các vi phạm này bằng ngoại lệ.

## Thay đổi RTL

Dùng `a_cg_z020_share` làm nguồn cho các tầng pipeline và đường số học dùng chung, ghép bộ dịch đúng biên giá trị từ `a_cg_z020_100mhz`. So với bản 100 MHz:

1. Khôi phục hai tầng nhận lệnh frontend, một tầng request tile và cấu hình `IN_REG=1`.
2. Khôi phục bộ cộng/trừ butterfly hai tầng. Giữ dùng chung các chuỗi cộng của FFT/NTT và lựa chọn toán hạng đã đăng ký.
3. Làm tròn khi đọc IFFT qua hai bước: tính carry/addend, rồi cộng các từ 32 bit độc lập. Không còn chuỗi carry xuyên 128 bit trong một chu kỳ.
4. Giữ bộ dịch số học gọn theo biên 32/64/128 bit của bản 100 MHz. Giữ wrap trước shift, làm tròn, dấu và thứ tự kết quả.

Không đổi số tile, số bộ nhân, precision, modulus, packed16 hay phép toán native NTRUGen64. Planner được lấy cùng phiên bản pipeline của `share`; số chu kỳ mới phải khớp chính xác với planner.

P&R dùng `opt_design`, `place_design`, `phys_opt_design`, `route_design` mặc định, Vivado 2018.1, 4 luồng. Clock 6,250 ns, setup uncertainty 0,100 ns, hold uncertainty 0,050 ns; giữ cùng giả định I/O như baseline. Không chạy quét directive.

## Thời gian kernel

Đây là số chu kỳ mô phỏng nhân với chu kỳ clock đã đạt P&R; không phải đo trên board. Với FFT, N1024 ở đây là 1.024 phần tử thực trong biểu diễn phần mềm, tức 512 điểm phức.

| Kernel, tiến, một job | Chu kỳ 100 MHz | Chu kỳ 160 MHz | Thời gian cũ | Thời gian mới |
|---|---:|---:|---:|---:|
| FFT32, N1024 | 451 | 454 | 4,510 µs | 2,838 µs |
| FFT64, N1024 | 1.749 | 1.752 | 17,490 µs | 10,950 µs |
| FFT128, N1024 | 6.505 | 6.508 | 65,050 µs | 40,675 µs |
| NTT q=12289, N1024, unpacked | 984 | 987 | 9,840 µs | 6,169 µs |
| NTT q=12289, N1024, packed16 | 504 | 531 | 5,040 µs | 3,319 µs |
| NTT q=3329, N256, packed16 | 216 | 237 | 2,160 µs | 1,481 µs |

Tổng trên 1.026 ca: 550.644 → 559.565 chu kỳ, tăng 1,62%. Tính theo clock đạt P&R, tổng thời gian kernel giảm 36,49%, tương đương tăng tốc 1,574 lần. Tính cả các giao dịch host của test driver, gồm nạp root/cấu hình/đọc ghi, tăng tốc 1,430 lần. Đây không phải số tăng tốc toàn bộ signer.

## Correctness

- 1.026 ca khớp vector từng bit, đồng thời khớp chu kỳ planner; gồm 252 ca packed và 78 ca native.
- FFT32/64/128 và NTT với 15 modulus trong vector suite; giữ giới hạn hợp lệ của từng chế độ, đặc biệt packed16 chỉ dùng q phù hợp.
- 38 ca mô phỏng bốn trạng thái; reset-abort 12 chế độ; kiểm reset ở hai tầng lệnh và flush response.
- Tile độc lập: 300 request mỗi chiều CT/GS, hai modulus slot luân phiên. Core hiện vẫn dùng slot 0.
- 74 lời gọi transform từ ứng dụng C được thay bằng kết quả RTL; 14 artifact giống từng byte với reference, 4 chữ ký qua bộ kiểm độc lập. Phần ngoài transform vẫn chạy C; chưa phải toàn signer RTL.
- Hash xác nhận `hdl/` và RTL của hai bản `share`/`100mhz` được bảo vệ không đổi.

Giữ nguyên contract IFFT đã có: kết quả trong RAM chưa scale, scale được áp dụng ở đường đọc host. Phải đọc kết quả trước khi cấu hình/start/load mới làm mất trạng thái scale; bản này không thêm khả năng nối kernel trực tiếp với dữ liệu IFFT đã chuẩn hóa trong RAM.

## Đường chậm còn lại

Sau routing, worst setup là `u_exec/inverse_reg` → `engine[1].u_tile/dir_reg_rep__1`: data delay 5,708 ns, gồm logic 0,379 ns và route 5,329 ns. Khoảng 93,4% delay nằm ở dây phân phối điều khiển. Đây là điểm cần xét nếu muốn tăng clock tiếp; chưa có phép đo cho một thiết kế nhanh hơn 160 MHz.

## Tái kiểm và bằng chứng

Chạy từ gốc repo:

```powershell
./experiments/a_cg_z020_perf160/run_sim.ps1
python -X utf8 experiments/a_cg_z020_perf160/compare.py
C:/Xilinx/Vivado/2018.1/bin/vivado.bat -mode batch -source experiments/a_cg_z020_perf160/synth.tcl
C:/Xilinx/Vivado/2018.1/bin/vivado.bat -mode batch -source experiments/a_cg_z020_perf160/implement.tcl
python -X utf8 experiments/a_cg_z020_perf160/report.py
```

Script mô phỏng giữ snapshot RTL; nếu source khác snapshot thì dừng thay vì ghi đè. Khi đọc lại routed DCP trong Vivado, khôi phục `HD.CLK_SRC` theo `route/run_config.txt` rồi cập nhật timing; không dùng clock source khác để so slack.

Bằng chứng ở `study/build/a_cg_z020_perf160/`: `performance.json`, `source_manifest.json`, `protected_source_manifest.json`, `sim.log`, `four_state.log`, `pipeline_reset.log`, `tile_slots.log`, `application/application_results.json`, `synth/` và `route/`. `performance.json` có chu kỳ và thời gian của từng ca.
