# Kiến trúc hiện tại của FlexTransform

Cập nhật cách trình bày ngày 01/11/2026. Trang này mô tả source đang có; yêu cầu
đầy đủ nằm trong [spec 2.0](../spec/FlexTransform/2.0/README.md).
[Lịch sử quyết định và số đo các bản trước](plan_history/cleanup_2026_11_01/docs_architecture_v1.md)
được giữ riêng để không lẫn với mô tả hiện tại.

## 1. Mục tiêu

Dùng cùng một mảng nhân cho hai loại số học:

- FFT: tính trên số có phần lẻ; phải giữ đúng dấu, phép làm tròn và vị trí bit.
- NTT: tính số nguyên modulo q; kết quả phải chính xác theo q đã chọn.

Ứng dụng chính là các kernel số học của Falcon/R8. Thiết kế còn hướng đến
NTT q3329, q8380417 và FFT theo NTRUGen; mức hỗ trợ thực tế xem mục 4.

## 2. Các khối

```text
Lệnh và cổng nạp/đọc dữ liệu
              |
      Bộ điều khiển transform
              |
       RAM + bảng root
              |
      Mạng chọn dữ liệu
              |
           16 tile
              |
       Ghi kết quả vào RAM
```

Mỗi tile có bốn bộ nhân 16×16, ghép thành một phép nhân 32×32.
FFT và NTT dùng lại các bộ nhân và bộ cộng/trừ này.
[Danh sách source](../hdl/README.md).

## 3. Cách tính hiện tại

**NTT:** một tile làm một butterfly mỗi lần nhận dữ liệu. Với biến thể đang
chọn, multiplier được dùng ba lượt cho một phép nhân Montgomery. Tile nhận
phép mới mỗi ba chu kỳ. Các tile nhận lệch nhau để giảm số cổng bộ nhớ/root
cần dùng cùng lúc. Lõi cho các tầng chồng nhau theo bảng lịch đã tính trước.

**FFT:** một tile làm trọn một butterfly phức bằng ba phép nhân thực. Số64/128
bit được tách thành các phần 32 bit; tile tính lần lượt các tích nhỏ và cộng lại.
Đây là ghép theo thời gian trong tile. Không lấy sơ đồ ghép nhiều tile của
baseline cũ để mô tả đường nhân rộng hiện tại.

**Bộ nhớ:** core mới có một vùng A, chia64 bank 16 bit. NTT dùng một từ 32 bit
cho mỗi hệ số, kể cả q nhỏ. FFT dùng 32/64/128 bit cho mỗi thành phần thực.
Bảng root có bốn bank, mỗi bank3072 từ96bit trong source hiện tại.

## 4. Đã có và còn thiếu

| Chức năng | Tình trạng trong core mới |
|---|---|
| NTT/INTT q12289, q3329, q8380417 | Có RTL; lượt kiểm 01/11 đạt 48/48 ca |
| FFT/IFFT32/64/128 | Có RTL; 54/54 ca đạt sau khi chuyển tầng theo số lượt ghi đã xong (01/11) |
| CMUL, SPLIT, MERGE | Chưa nối vào core mới; baseline cũ có |
| FFT64 theo NTRUGen | Có contract/model/vector riêng; chưa nối vào core mới |
| Nạp prime 31 bit và root lúc chạy | Profile 3 có RTL (16 khe, host ghi gói root); 100/100 ca đạt, gồm 4 prime NTRUGen so với C |
| Nhiều đa thức, địa chỉ đầu A/B/C | Chưa có trong core tối thiểu hiện tại |
| Pause/flush và giao diện lệnh đầy đủ | Chưa có trong core tối thiểu hiện tại |

Có code không đồng nghĩa đã kiểm xong. Kết quả 48 ca trên là lượt kiểm chọn lọc,
không là nghiệm thu toàn bộ spec. [Báo cáo đọc code](implementation_review_2026_11_01.md).

## 5. Ưu tiên tiếp theo

1. (Đã làm 01/11) Sửa lịch FFT32 để chỉ đọc tầng sau khi dữ liệu cần dùng đã được ghi.
2. Cho script kiểm thử trả mã lỗi khi có FAIL hoặc không bắt được lỗi cố ý.
3. Chốt cùng một phiên bản cho RTL, mô hình, bảng sinh và báo cáo kết quả.
4. Nếu ưu tiên ký: nối CMUL/SPLIT/MERGE rồi kiểm lại với R8 C.
   Nếu ưu tiên sinh khóa: nối FFT NTRUGen và NTT prime 31 bit.

Các kết quả 5.992 kernel/bốn chữ ký thuộc
[baseline cũ](autonomous_kernel_rtl.md), chưa áp dụng cho core mới.

## 6. Giả thuyết cần chứng minh

Các ngưỡng thí nghiệm và lý do chọn biến thể được giữ nguyên trong
[bản lưu, mục 6](plan_history/cleanup_2026_11_01/docs_architecture_v1.md#6-giả-thuyết-cần-chứng-minh).
Trang này không đặt ngưỡng mới và không sửa quyết định kỹ thuật cũ.
Khi báo cáo hiệu năng, dùng đúng source và cấu hình đã đo; không ghép số liệu
của nhiều bản thành một kết quả.
