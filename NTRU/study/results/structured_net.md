# Mạng bank → tile có cấu trúc: gán tile theo bank

Mô hình: [model/structured_net.py](../../model/structured_net.py). Tile của một butterfly là hàm cố định của superbank hai toán hạng. Một lane 32 bit: mọi NTT, kể cả q nhỏ, lưu dạng 4 (mỗi hệ số một từ 32 bit trên hai bank). Mọi trường hợp N 2..1024 (dưới 64: 1 hoặc min(8, 64/N) đa thức; từ 64: 1 hoặc 2), xuôi và ngược. Vị trí gói đầu của mỗi khe là bội của 8.

| Cổng | Số nguồn lớn nhất | Trung bình | Crossbar |
|---|---:|---:|---:|
| Đọc, nửa thấp mỗi toán hạng | 16 | 8.8 | 64 |
| Đọc, nửa cao mỗi toán hạng | 16 | | 32 |
| Ghi, mỗi bank | 14 | 8.8 | 32 |

Tốc độ: 55634 butterfly trong 3532 chu kỳ = 15.75 mỗi chu kỳ; chu kỳ thêm do xung đột bank gói root: 40; số tầng chậm hơn lý tưởng: 20. Không có xung đột bank dữ liệu (do cách gán).

Số modulus một tile phải phục vụ trong một lệnh nhiều prime: tối đa 2 (N = 8, 16, 32), nên tile cần bảng hằng số 2 ô chọn theo request.
