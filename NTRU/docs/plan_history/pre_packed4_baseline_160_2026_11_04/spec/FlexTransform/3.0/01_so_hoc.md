# 3.0 — contract số học

Nguồn chuẩn: [tile_a.sv](../../../experiments/a_cg_z020_system160/rtl/tile_a.sv), [a_cg_fast.sv](../../../experiments/a_cg_z020_system160/rtl/a_cg_fast.sv), oracle/vector của baseline. Ràng buộc: tối ưu hiện thực không được tự đổi precision, truncation, dấu, carry hoặc điểm rounding của reference PQC.

## FFT thường

Các giá trị signed two's-complement W=32/64/128, với W/2 bit lẻ, theo mode FFT thường. Cộng/trừ wrap về W bit. Phép nhân thực tương ứng `wrap_W(floor((a*b + 2^(W/2-1))/2^(W/2)))`. Giữ thứ tự phép toán 3M và ranh giới wrap/round ở từng tích/tổng của reference, không thay bằng nhân phức 4M hay làm tròn một tổng vô hạn bit ở cuối. 64/128 bit được chia thành limb 32 bit và tính nhiều lượt trong chính tile.

FFT128 dùng contract R8 Q64.64 đã pin; [numeric contract và reference C](../../../docs/numeric_contract.md) giải thích phép 3M và toolchain LP64. FFT32/64 thường có oracle riêng, không diễn giải chúng thành việc tự giảm precision của signer R8.

Native NTRUGen64 là một mode số học riêng theo C/NTRUGen, không suy toàn bộ quy tắc của nó từ công thức FFT thường. Cấu hình chỉ hợp lệ với FFT64. Vector native và các lời gọi C là bằng chứng; không trộn native với fmt/rounding của mode thường.

## IFFT và đọc kết quả

Phép chia cuối giữ `wrap_W(v + 2^(s-1)) >>> s` khi s>0, identity khi s=0; wrap phải xảy ra trước dịch phải số học. Trong baseline, các tile không chia ở tầng cuối: dữ liệu RAM còn chưa normalize, và core thực hiện scale/round ở đường đọc host.

Phải đọc hết kết quả IFFT trước một cfg/start/load mới có thể xóa trạng thái pending-scale. Không nối trực tiếp kernel mới trên RAM IFFT và giả định dữ liệu đã normalize. Pipeline rounding tách tính carry/addend và cộng theo word; bộ dịch giữ biên từng giá trị 32/64/128 bit.

## NTT

Montgomery thường dùng R=2³², q lẻ dưới 2³¹, qinv tương ứng −q⁻¹ mod R. Packed16 dùng R=2¹⁶ cho mỗi lane, q<2¹⁵; core lấy các phần hằng số cần thiết và không cho carry tràn qua lane. Dữ liệu/root phải ở đúng miền và packing mà planner/reference yêu cầu; không tự thêm/bỏ chuyển miền Montgomery.

CT: nhân nhánh rồi cộng/trừ modulo; GS: cộng/trừ rồi nhân nhánh. INTT và bước chia đôi giữ convention reference/root đã nạp; không thêm một phép normalize theo suy đoán. Với hmin, giữ đúng các tầng bị bỏ. Dừng NTT ở bậc hai không đồng nghĩa đã triển khai kernel basemul ML-KEM.

Các đường cộng FFT và hiệu chỉnh NTT được dùng chung khi mode loại trừ nhau, nhưng phần riêng vẫn phải hoạt động đồng thời theo pipeline. Dùng chung phần cứng không cho phép chia thời gian hoặc đổi latency mà không cập nhật valid/metadata/planner và kiểm lại.
