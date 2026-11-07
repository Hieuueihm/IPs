# Timing các nhóm đường trên bản Z020 dưới 30k LUT

Ngày 04/11/2026. Đọc lại checkpoint `a_cg_z020_100mhz/route10/routed.dcp`, clock 10 ns.
Đã khôi phục đúng `HD.CLK_SRC=BUFGCTRL_X0Y16` và tái lập setup +0,032 ns, hold +0,051 ns trước khi truy vấn.
Không đổi RTL, không tối ưu netlist hoặc chạy lại placement/routing, không thêm ngoại lệ timing.

## Kết luận

Rounding host là đường xấu nhất, nhưng các nhóm reset, nạp context/root và cộng-trừ tile cũng còn ít margin.
Bỏ riêng các đích rs_sum khỏi truy vấn thì setup xấu nhất vẫn chỉ +0,206 ns. Vì vậy không thể suy ra rằng chỉ
sửa rounding là lõi sẽ đạt lại 150–178 MHz. Bộ nhân và MAC FFT có nhiều margin hơn các nhóm trên.

## Đường xấu nhất của từng nhóm

Các nhóm chồng lấp nhau, không cộng số lượng giữa các nhóm. Các số dưới đây là setup slack tại 10 ns.
Một nhóm đo đến các thanh ghi có tên toán học vẫn có thể bị giới hạn bởi tín hiệu chọn/địa chỉ/enable của khối đó.

| Nhóm | Slack | Trễ dữ liệu | Logic | Routing | Mức logic |
|---|---:|---:|---:|---:|---:|
| [Đường xấu nhất toàn lõi: rounding host](../study/build/a_cg_z020_100mhz/path_groups/all_internal.rpt) | +0.032 ns | 9.655 ns | 6.680 ns | 2.975 ns | 39 |
| [Reset frontend → các thanh ghi trong lõi](../study/build/a_cg_z020_100mhz/path_groups/reset_from_frontend.rpt) | +0.206 ns | 9.042 ns | 0.348 ns | 8.694 ns | 0 |
| [Nạp q/qprime/format/mode vào tile](../study/build/a_cg_z020_100mhz/path_groups/context_config.rpt) | +0.329 ns | 9.363 ns | 0.379 ns | 8.984 ns | 0 |
| [Đầu vào root BRAM (load/địa chỉ/enable)](../study/build/a_cg_z020_100mhz/path_groups/root_load.rpt) | +0.343 ns | 9.262 ns | 0.433 ns | 8.829 ns | 0 |
| [Tầng toán hạng / cộng-trừ đầu vào tile](../study/build/a_cg_z020_100mhz/path_groups/operand_stage.rpt) | +0.448 ns | 9.277 ns | 3.578 ns | 5.699 ns | 17 |
| [Chốt dữ liệu/tag/valid đầu ra tile](../study/build/a_cg_z020_100mhz/path_groups/tile_response.rpt) | +0.484 ns | 9.283 ns | 3.578 ns | 5.705 ns | 17 |
| [Chương trình FFT → thanh ghi chương trình tile](../study/build/a_cg_z020_100mhz/path_groups/program_broadcast.rpt) | +0.758 ns | 8.841 ns | 0.484 ns | 8.357 ns | 1 |
| [Đầu vào bank dữ liệu (địa chỉ/data/enable)](../study/build/a_cg_z020_100mhz/path_groups/data_bank_write.rpt) | +0.922 ns | 8.394 ns | 0.808 ns | 7.586 ns | 2 |
| [Mọi nguồn → dòng đọc host](../study/build/a_cg_z020_100mhz/path_groups/host_line_capture_all.rpt) | +1.678 ns | 7.596 ns | 0.590 ns | 7.006 ns | 1 |
| [Các thanh ghi u32 / r32r của Montgomery](../study/build/a_cg_z020_100mhz/path_groups/montgomery.rpt) | +1.960 ns | 7.956 ns | 2.837 ns | 5.119 ns | 12 |
| [Ghép tích phức FFT: wps / t5](../study/build/a_cg_z020_100mhz/path_groups/fft_T.rpt) | +2.150 ns | 7.441 ns | 2.303 ns | 5.138 ns | 12 |
| [Tổng hai thành phần FFT / bộ nhớ tổng](../study/build/a_cg_z020_100mhz/path_groups/fft_limb_sums.rpt) | +2.292 ns | 7.531 ns | 3.023 ns | 4.508 ns | 15 |
| [MAC/tích lũy FFT và chốt product limb](../study/build/a_cg_z020_100mhz/path_groups/fft_accumulator.rpt) | +2.367 ns | 7.505 ns | 2.411 ns | 5.094 ns | 14 |
| [Dữ liệu BRAM → dòng đọc host](../study/build/a_cg_z020_100mhz/path_groups/host_read_select.rpt) | +2.664 ns | 7.121 ns | 2.649 ns | 4.472 ns | 3 |
| [Dữ liệu BRAM → req_x/req_y](../study/build/a_cg_z020_100mhz/path_groups/bank_to_tile.rpt) | +3.244 ns | 6.445 ns | 2.512 ns | 3.933 ns | 2 |
| [Mảng nhân, ghép tích và thanh ghi lá](../study/build/a_cg_z020_100mhz/path_groups/multiplier.rpt) | +3.828 ns | 5.932 ns | 0.589 ns | 5.343 ns | 2 |
| [Bộ dịch/đường ra → FF phản hồi host](../study/build/a_cg_z020_100mhz/path_groups/host_shift.rpt) | +5.394 ns | 4.485 ns | 0.874 ns | 3.611 ns | 3 |
| [Dữ liệu root BRAM → các đích trong tile](../study/build/a_cg_z020_100mhz/path_groups/root_to_tile.rpt) | +5.759 ns | 3.873 ns | 0.839 ns | 3.034 ns | 1 |

## Các truy vấn bao quát

- Toàn lõi, bỏ nhóm rs_sum: **+0.206 ns**, `p_rst_reg/C` → `u_exec/qi_reg[8]/R`.
- Mọi đường đến tile, gồm nạp cấu hình: **+0.329 ns**, `u_exec/qi_reg[7]/C` → `u_exec/engine[15].u_tile/qi0_reg[7]/D`.
- Giữa các thanh ghi trong mảng tile: **+0.464 ns**, `u_exec/engine[3].u_tile/wbi_reg[1]/C` → `u_exec/engine[3].u_tile/s1_reg[23]/D`.

## Phải đọc kết quả thế nào?

1. **Rounding:** chuỗi carry dài là một nguyên nhân thật ở RTL. Khối này có phần lớn trễ nằm ở logic.
2. **Reset, hằng số, root và phát chương trình:** nhiều đường có rất ít logic nhưng routing dài. Đó là độ trễ
   của bố trí/nối dây hiện tại; không có nghĩa các phép toán này tự cần 9 ns. Chúng vẫn phải đóng timing, dù chỉ
   hoạt động lúc cấu hình hoặc khởi động.
3. **Trong tile:** còn các đường cộng/trừ và chọn dữ liệu sát ngưỡng. Mảng DSP không phải đại diện cho toàn bộ
   thời gian của butterfly; các khối chuẩn bị và ghép kết quả cũng phải tính.
4. **Fmax:** công cụ đã thực hiện implementation với mục tiêu 10 ns. Nhiều đường chỉ được rút ngắn đủ để đạt
   mục tiêu này. Không quy trực tiếp slack trong bản route này thành giới hạn tần số tối đa của kiến trúc.
5. **Hold:** toàn bộ đường nội bộ vẫn có hold tối thiểu +0,051 ns theo checkpoint gốc. Bảng ở trên là setup,
   không dùng nó để kết luận về hold ở một clock khác. Các cổng I/O OOC vẫn cần timing tích hợp riêng.

## Startpoint và endpoint cụ thể

### Đường xấu nhất toàn lõi: rounding host

`u_exec/scale_r_reg[3]/C` → `u_exec/rs_sum_reg[125]/D`.
Slack +0.032 ns; 39 mức logic. [Ba đường chậm nhất của nhóm](../study/build/a_cg_z020_100mhz/path_groups/all_internal.rpt).

### Toàn lõi, bỏ nhóm rs_sum

`p_rst_reg/C` → `u_exec/qi_reg[8]/R`.
Slack +0.206 ns; 0 mức logic. [Ba đường chậm nhất của nhóm](../study/build/a_cg_z020_100mhz/path_groups/except_rounding.rpt).

### Reset frontend → các thanh ghi trong lõi

`p_rst_reg/C` → `u_exec/qi_reg[8]/R`.
Slack +0.206 ns; 0 mức logic. [Ba đường chậm nhất của nhóm](../study/build/a_cg_z020_100mhz/path_groups/reset_from_frontend.rpt).

### Mọi đường đến tile, gồm nạp cấu hình

`u_exec/qi_reg[7]/C` → `u_exec/engine[15].u_tile/qi0_reg[7]/D`.
Slack +0.329 ns; 0 mức logic. [Ba đường chậm nhất của nhóm](../study/build/a_cg_z020_100mhz/path_groups/tile_all.rpt).

### Nạp q/qprime/format/mode vào tile

`u_exec/qi_reg[7]/C` → `u_exec/engine[15].u_tile/qi0_reg[7]/D`.
Slack +0.329 ns; 0 mức logic. [Ba đường chậm nhất của nhóm](../study/build/a_cg_z020_100mhz/path_groups/context_config.rpt).

### Đầu vào root BRAM (load/địa chỉ/enable)

`p_root_data_reg[12]/C` → `u_exec/engine[13].root_mem_reg/DIADI[12]`.
Slack +0.343 ns; 0 mức logic. [Ba đường chậm nhất của nhóm](../study/build/a_cg_z020_100mhz/path_groups/root_load.rpt).

### Tầng toán hạng / cộng-trừ đầu vào tile

`u_exec/engine[3].req_x_reg[3][0]/C` → `u_exec/engine[3].u_tile/s1_reg[23]/D`.
Slack +0.448 ns; 17 mức logic. [Ba đường chậm nhất của nhóm](../study/build/a_cg_z020_100mhz/path_groups/operand_stage.rpt).

### Giữa các thanh ghi trong mảng tile

`u_exec/engine[3].u_tile/wbi_reg[1]/C` → `u_exec/engine[3].u_tile/s1_reg[23]/D`.
Slack +0.464 ns; 17 mức logic. [Ba đường chậm nhất của nhóm](../study/build/a_cg_z020_100mhz/path_groups/tile_to_tile.rpt).

### Chốt dữ liệu/tag/valid đầu ra tile

`u_exec/engine[3].req_x_reg[3][0]/C` → `u_exec/engine[3].u_tile/rd_reg[27]/D`.
Slack +0.484 ns; 17 mức logic. [Ba đường chậm nhất của nhóm](../study/build/a_cg_z020_100mhz/path_groups/tile_response.rpt).

### Chương trình FFT → thanh ghi chương trình tile

`u_exec/e_product_reg[0]/C` → `u_exec/engine[11].u_tile/mxa_reg[0]/D`.
Slack +0.758 ns; 1 mức logic. [Ba đường chậm nhất của nhóm](../study/build/a_cg_z020_100mhz/path_groups/program_broadcast.rpt).

### Đầu vào bank dữ liệu (địa chỉ/data/enable)

`u_exec/write_far_reg/C` → `u_exec/data_bank[27].mem_reg/DIBDI[5]`.
Slack +0.922 ns; 2 mức logic. [Ba đường chậm nhất của nhóm](../study/build/a_cg_z020_100mhz/path_groups/data_bank_write.rpt).

### Mọi nguồn → dòng đọc host

`p_rst_reg/C` → `u_exec/line_data_reg[21]/R`.
Slack +1.678 ns; 1 mức logic. [Ba đường chậm nhất của nhóm](../study/build/a_cg_z020_100mhz/path_groups/host_line_capture_all.rpt).

### Các thanh ghi u32 / r32r của Montgomery

`u_exec/engine[10].u_tile/md_reg[1]/C` → `u_exec/engine[10].u_tile/g_arr32.u32_reg[32]/D`.
Slack +1.960 ns; 12 mức logic. [Ba đường chậm nhất của nhóm](../study/build/a_cg_z020_100mhz/path_groups/montgomery.rpt).

### Ghép tích phức FFT: wps / t5

`u_exec/engine[3].u_tile/wpe_reg[0]__0/C` → `u_exec/engine[3].u_tile/wps_reg_0_3_31_31/SP/I`.
Slack +2.150 ns; 12 mức logic. [Ba đường chậm nhất của nhóm](../study/build/a_cg_z020_100mhz/path_groups/fft_T.rpt).

### Tổng hai thành phần FFT / bộ nhớ tổng

`u_exec/engine[3].req_x_reg[3][0]/C` → `u_exec/engine[3].u_tile/sw5_reg[31]/D`.
Slack +2.292 ns; 15 mức logic. [Ba đường chậm nhất của nhóm](../study/build/a_cg_z020_100mhz/path_groups/fft_limb_sums.rpt).

### MAC/tích lũy FFT và chốt product limb

`u_exec/engine[3].u_tile/d_mcw/r_reg[5][0]__0/C` → `u_exec/engine[3].u_tile/wpl_reg[28]/D`.
Slack +2.367 ns; 14 mức logic. [Ba đường chậm nhất của nhóm](../study/build/a_cg_z020_100mhz/path_groups/fft_accumulator.rpt).

### Dữ liệu BRAM → dòng đọc host

`u_exec/data_bank[14].mem_reg/CLKARDCLK` → `u_exec/line_data_reg[124]/D`.
Slack +2.664 ns; 3 mức logic. [Ba đường chậm nhất của nhóm](../study/build/a_cg_z020_100mhz/path_groups/host_read_select.rpt).

### Dữ liệu BRAM → req_x/req_y

`u_exec/data_bank[29].mem_reg/CLKARDCLK` → `u_exec/engine[13].req_y_reg[13][16]/D`.
Slack +3.244 ns; 2 mức logic. [Ba đường chậm nhất của nhóm](../study/build/a_cg_z020_100mhz/path_groups/bank_to_tile.rpt).

### Mảng nhân, ghép tích và thanh ghi lá

`u_exec/engine[3].u_tile/md_reg[1]/C` → `u_exec/engine[3].u_tile/leaves/g_leaf[3].ar_reg[8]/D`.
Slack +3.828 ns; 2 mức logic. [Ba đường chậm nhất của nhóm](../study/build/a_cg_z020_100mhz/path_groups/multiplier.rpt).

### Bộ dịch/đường ra → FF phản hồi host

`u_exec/rs_s_reg[1]/C` → `rsp_data_q_reg[59]/D`.
Slack +5.394 ns; 3 mức logic. [Ba đường chậm nhất của nhóm](../study/build/a_cg_z020_100mhz/path_groups/host_shift.rpt).

### Dữ liệu root BRAM → các đích trong tile

`u_exec/engine[3].root_mem_reg/CLKARDCLK` → `u_exec/engine[3].u_tile/wmw_reg_0_15_30_31/RAMA/I`.
Slack +5.759 ns; 1 mức logic. [Ba đường chậm nhất của nhóm](../study/build/a_cg_z020_100mhz/path_groups/root_to_tile.rpt).

[JSON kết quả và hash đầu vào](../study/results/z020_100mhz_timing_groups.json).
