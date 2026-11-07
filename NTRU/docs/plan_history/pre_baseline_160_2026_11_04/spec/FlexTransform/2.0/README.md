# FlexTransform IP — Đặc tả 2.0

| Thuộc tính | Giá trị |
|---|---|
| Ngày | 2026-10-30 |
| Trạng thái | Đặc tả mục tiêu. Đã có RTL tile và core tối thiểu; chưa triển khai/kiểm hết các yêu cầu |
| Kiến trúc nguồn | [Kiến trúc hiện tại](../../../docs/architecture_v1.md); lịch sử quyết định được dẫn riêng trong trang đó |
| Bản trước | [Đặc tả 1.0](../1.0/README.md), giữ nguyên, không sửa |
| Người viết RTL | Người dùng; bộ spec này không chứa RTL |

Đọc [danh sách source](../../../hdl/README.md) để chọn đúng bản RTL.
[Review ngày 01/11](../../../docs/implementation_review_2026_11_01.md) ghi phạm vi
đã kiểm và lỗi FFT32 đang biết. Tài liệu này mô tả yêu cầu, không tự xác nhận
mọi chức năng đã có hoặc đã PASS trong RTL.

## Vì sao có bản 2.0

Kiến trúc v1 đổi hợp đồng của bản 1.0 ở ba chỗ: trường định dạng thành 3 bit, thêm modulus mới (8380417 và prime 31 bit
nạp lúc chạy), và bảng root NTT 32 bit thành RAM nạp từ host. Theo quy tắc trong
[CHANGELOG của 1.0](../1.0/CHANGELOG.md), các thay đổi này bắt buộc phải lên bản mới.

## Cách đọc

Bộ spec viết bằng tiếng Việt mô tả. Không dùng mã kiểu FT-*, T_*, H1. Tên tín hiệu RTL vẫn viết bằng tiếng Anh
snake_case cho tiện viết code. Mỗi yêu cầu bắt buộc dùng chữ **phải**; điều được phép thay bằng phương án tương đương
dùng chữ **nên**; điều tùy chọn dùng chữ **có thể**.

Khi hai tài liệu mâu thuẫn, dừng lại và ghi yêu cầu thay đổi; không tự chọn một cách hiểu trong RTL.

## Danh mục tài liệu

| Tài liệu | Nội dung | Trạng thái |
|---|---|---|
| [00_pham_vi.md](00_pham_vi.md) | Các phép, định dạng 3 bit, modulus (profile 0–3), số đa thức, tham số, trạng thái prime | Xong |
| [01_so_hoc_kernel.md](01_so_hoc_kernel.md) | FFT 64 bit NTRUGen, NTT q = 8380417, NTT prime 31 bit đã nạp | Xong |
| [02_giao_dien.md](02_giao_dien.md) | Trường lệnh (gồm địa chỉ đầu A/B/C), mã lỗi và thứ tự kiểm, phép nạp prime, cổng bộ nhớ host có pipeline | Xong |
| [03_bo_nho.md](03_bo_nho.md) | Cách đặt hệ số, gom lô FFT, bảng root 4 bank, gói root 32 bit, xen kẽ hai đa thức | Xong |
| [04_kiem_thu_loi.md](04_kiem_thu_loi.md) | Bộ kiểm cấp lõi, thí nghiệm 12 giả thuyết, điều kiện nhận RTL | Xong |
| [10_hop_dong_tile.md](10_hop_dong_tile.md) | Khối tile thử: 4 bộ nhân 16×16 + phần hậu xử lý của tile; mọi chế độ; hai biến thể rút gọn (lai / rút gọn riêng); tốc độ tối thiểu; cách đo Vivado | Xong |
| [11_kiem_thu_tile.md](11_kiem_thu_tile.md) | Các case kiểm thử cấp tile và bộ vector chuẩn | Xong |
| [assets/tile/](assets/tile/) | 22 103 vector cấp tile | Xong |
| [assets/kernel/](assets/kernel/), `assets/*.mem` | 335 ca cấp kernel cho ba kernel mới, gồm lệnh nhiều khe prime; bảng GM_TAB của NTRUGen; ROM root q = 8380417 | Xong |

Phần không nhắc tới trong 00–04 giữ nguyên như bản 1.0 cùng số mục; mỗi tài liệu ghi rõ điều này ở đầu.

**Chưa có trong 2.0:** bản máy đọc của yêu cầu và giao diện (`requirements.json`, `interface.json` của 1.0) và
script kiểm toàn bộ spec. Khi cần, chúng sẽ được làm lại từ các tài liệu ở trên.

## Sinh lại và kiểm vector

```text
python scripts/build_spec2_tile_vectors.py      # vector cấp tile
python scripts/check_spec2_tile_vectors.py      # chạy lại qua mô hình dạng tích 16×16
python scripts/build_spec2_kernel_assets.py     # vector cấp kernel, cần gcc (biên dịch C của NTRUGen)
python scripts/check_spec2_kernel_assets.py     # mã giả của 01 = C; q8380417 = đánh giá đa thức trực tiếp
```

## Cách dùng với RTL hiện tại

1. Bắt đầu ở [tile đang dùng](../../../hdl/tile/MANIFEST.md), rồi đọc
   [core hiện tại](../../../hdl/core_ntt/MANIFEST.md). Không lấy bản nháp `hdl/tile_thu/`
   làm source chính.
2. Đối chiếu từng chức năng RTL với yêu cầu trong 00–04 và hợp đồng tile 10.
   Phần chưa có trong RTL vẫn là yêu cầu mục tiêu.
3. Ưu tiên lỗi và khoảng trống trong [review 01/11](../../../docs/implementation_review_2026_11_01.md),
   sau đó chạy các kiểm tra tương ứng trong [04](04_kiem_thu_loi.md) và [11](11_kiem_thu_tile.md).
