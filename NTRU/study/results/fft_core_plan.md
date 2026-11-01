# FFT trên tile một làn: hai cách đặt (mô hình trước RTL)

Mô hình: [model/fft_core_plan.py](../../model/fft_core_plan.py). Số học butterfly 3 tích kiểm lại với 66 ca vàng FFT / FFT ngược của 1.0 (định dạng 0, 1, 2, logn 0..10): khớp hết.

## Chu kỳ, N = 1024 (giả thuyết 3, khóa lần 6)

| W | (A) xuôi | (A) ngược | (A) độ trễ đọc → ghi | (B) xuôi (kiến trúc mục 4) | Ngưỡng xuôi / ngược |
|---:|---:|---:|---:|---:|---:|
| 32 | 531 | 531 | 14 | 552 | 700 / 770 |
| 64 | 1827 | 1827 | 23 | 1864 | 2300 / 2530 |
| 128 | 6579 | 6579 | 56 | 7496 | 8500 / 9350 |

(A): tỉ lệ 128 / 32 bit = 12.4 (ngưỡng ≥ 10; N512 10.6, ngưỡng ≥ 8), 128 / 64 bit = 3.6 (ngưỡng ≥ 3). Độ trễ đọc → ghi của một butterfly: 14 / 23 / 56 chu kỳ (điều kiện của giả thuyết 3: ≤ 24).

## Mạng: số siêu bank mỗi cổng tile phải tới (A), tile = tile của cặp phần thực

| Định dạng | Lớn nhất | Trung bình | NTT hiện tại (mỗi nửa) |
|---|---:|---:|---:|
| W = 32 | 16 | 8.8 | 6 / 4,5 |
| W = 64 | 22 | 7.1 | 6 / 4,5 |
| W = 128 | 28 | 5.5 | 6 / 4,5 |
| Hợp ba độ rộng | 28 | 14.3 | |

### Chọn tile cho butterfly FFT (hợp ba độ rộng; cột sau gộp thêm nguồn NTT)

| Cách gán tile | Lớn nhất | Trung bình | Lớn nhất / trung bình khi gộp NTT |
|---|---:|---:|---:|
| Theo cặp phần thực (A.re, B.re) | 28 | 14,3 | 28 / 14,3 |
| **Theo cặp thực–ảo của A (A.re, A.im)** | 28 | 9,0 | 28 / 10,1 |
| 4 bit thấp siêu bank của A.re | 32 | 10,7 | 32 / 11,7 |
| j mod 16 | 32 | 24,6 | 32 / 24,7 |

Ước lượng giá: phần đọc của mạng hiện 2 176 LUT cho trung bình 4,5 nguồn mỗi cổng (khoảng 0,47 LUT mỗi bit-nguồn). Với
trung bình 10,1 nguồn: khoảng 4 900 LUT phần đọc (+2 700), phần ghi tăng tương tự; tổng mạng khoảng +4 đến +5 nghìn LUT.
Chưa tối ưu cách gán; chưa tính cấp root FFT (4 bank, spec 03 mục 3).

## Kết luận tạm (chờ người dùng chọn)

- (A) đạt mọi ngưỡng số của giả thuyết 3 theo dự báo, không cần cây cộng giữa các tile, nhưng: độ trễ đọc → ghi ở 128 bit
  là 56 chu kỳ (điều kiện của giả thuyết 3 là ≤ 24); cơ chế tạo chiều precision là thời gian trong tile, không phải gom lô
  16 / 4 / 1 như chữ của giả thuyết 3; mạng cần nhiều nguồn hơn khoảng 2,2 lần.
- (B) giữ đúng chữ của giả thuyết 3, nhưng cần cây cộng giữa 4 / 16 tile và đưa limb tới nhiều tile cùng lúc; số chu kỳ ở
  trên là dự báo cũ cho tile 4 làn, chưa mô hình lại cho tile một làn.
