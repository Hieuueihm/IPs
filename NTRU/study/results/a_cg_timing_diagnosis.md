# Chẩn đoán timing: giữ packed16, ưu tiên đường điều khiển và bank

36k LUT được chấp nhận theo trao đổi hiện tại. Vấn đề cần tối ưu tiếp là timing; chưa có phiên bản RTL sửa timing mới và chưa thay RTL chính.

## Bằng chứng đang có

- Sau synth, đường chậm nhất: state_reg[0] → data_bank[14].mem_reg/ENARDEN. Có 14 mức LUT, 3,918 ns data path; phần dây 3,183 ns là ước tính (81,2%).
- Sau placement, đường chậm nhất chuyển sang engine[11].u_tile/dir_reg → engine[2].u_tile/wy0l_reg[31]. Fanout đầu đường 1.046; 18 mức logic, gồm 11 CARRY8 thuộc nhiều chuỗi cộng. Data path 4,943 ns, trong đó dây ước tính 3,457 ns (69,9%).
- Route phát hiện tắc nghẽn mức 5. Lượt route đã dừng theo yêu cầu; slack -11,006 ns chỉ là số trung gian, không có báo cáo đường tới hạn sau route hoàn chỉnh.
- Không đủ dữ liệu để quy mức -11 ns cho riêng packed16.

## Kiểm tra mode trên checkpoint synth

Cố định mode, hướng tính, precision FFT và native cùng TẤT CẢ bản sao các thanh ghi tương ứng (104 pin, xác định bằng ORIG_CELL_NAME). Không synth lại, không bỏ logic và không đổi diện tích 36.231 LUT. q, kích thước, scheduler và dữ liệu vẫn không bị cố định bởi case analysis.

| Cấu hình trong phép STA | WNS toàn core | WNS tập đường giữa các register trong tile |
|---|---:|---:|
| unconstrained_modes | +0.705 ns | +1.523 ns |
| ntt32_forward | +0.705 ns | +2.062 ns |
| ntt16_forward | +0.705 ns | +2.734 ns |
| fft128_forward | +0.705 ns | +2.062 ns |
| fft128_inverse | +0.705 ns | +2.229 ns |
| native64_inverse | +0.705 ns | +1.672 ns |

Toàn core vẫn bị giới hạn bởi state → enable RAM bank trong các trường hợp kiểm tra. Các số trong cột tile chỉ là chẩn đoán: có thể bao gồm register không dùng ở mode đó, không đại diện Fmax riêng của bộ nhân NTT. Phân tích mode tĩnh không kiểm chứng chuyển cấu hình và không thay thế timing sau route.

## Hướng sửa nên đo, theo thứ tự

1. Dùng cùng ràng buộc clock NGAY TRƯỚC synth; báo cáo rõ đường nội bộ và giao diện. Hiện clock 5 ns được tạo sau synth, còn 342 input và 167 output chưa có I/O delay.
2. Tách nhận yêu cầu host khỏi truy cập bank. Hiện load_accept/read_accept đi vào host_read/write và mux địa chỉ/dữ liệu ngay trong chu kỳ nhận; đường state → chọn host/compute → giải mã bank → RAM enable quá dài. Chụp request rồi mới giải mã/truy cập RAM. Đổi lại thêm độ trễ host; cần đo cả kernel và cold transaction, không hứa tăng tốc từ sơ đồ.
3. Phân phối mode/hướng tính bằng register cục bộ gần từng tile/cụm. Tool đã có replica nhưng tải chưa cân bằng. Nhắm vào các bit điều khiển cụ thể, tránh DONT_TOUCH toàn datapath. Chưa đo chi phí FF/LUT của bản sửa này.
4. Xét đưa tổng/hiệu thô của bộ cộng ra đường FFT, tránh bắt FFT đi qua logic hiệu chỉnh q dùng cho NTT. Giữ nguyên carry/borrow, wrap, rounding, 3M và số bit. Cần kiểm chứng bit-exact; chưa triển khai.
5. Chỉ thêm tầng pipeline số học sau khi kiểm tra lại carry giữa limb, valid/tag, feedback và lịch đọc/ghi. Không thể chèn register tùy ý rồi giữ nguyên lịch cũ.

Giữ packed16 và toàn bộ FFT32/64/128, NTT đa modulus. Không đánh đổi độ chính xác PQC để lấy timing. Không đặt false path hoặc multicycle hàng loạt để che vi phạm.

## Kiểm chứng khi có bản sửa RTL

Đo riêng từng thay đổi bằng synth với cùng ràng buộc, nguồn và workload. Nếu đổi hành vi/lịch, chạy lại vector số học, bốn trạng thái, model hazard/cycle và replay ứng dụng C. Không chạy lại P&R nếu chưa được yêu cầu.

File tái lập chẩn đoán: experiments/a_cg_batch/profile_timing.tcl. Báo cáo gốc: study/build/a_cg_batch/profile_timing/. JSON kèm hash và phạm vi giả định.
