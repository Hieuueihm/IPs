# Core FFT/NTT hiện tại

Lõi: [ntt_core.sv](ntt_core.sv). Tile: [tile_thu.sv](../tile/tile_thu.sv).
Danh sách đầy đủ: [hdl/README.md](../README.md).

## Phạm vi

- Một đa thức mỗi lệnh, một vùng RAM A.
- NTT/INTT các profile cố định: q12289, N8..1024; q3329, N8..256 với 7 tầng tại N256; q8380417, N256.
- **NTT/INTT profile 3 (từ 01/11/2026):** mọi q lẻ < 2³¹ nạp lúc chạy, N2..1024, bỏ 0..2 tầng cuối (NTT thiếu tầng
  như ML-KEM). 16 khe; mỗi khe giữ q, q′ = −q⁻¹ mod 2³², root 1 hai chiều, vị trí gói root đầu (bội của 4), logn của bảng.
  Gói root [GM[g], GM[2g], GM[2g+1]] nằm ở hàng 3072..3327 của 4 bank gói root, host ghi khi lõi rảnh. Bảng root theo
  quy ước `mp_mkgmigm` của NTRUGen (dạng Montgomery R = 2³², bảng ngược đã nhân 1/2), nên NTT ngược chia đôi mỗi tầng
  như `mp_iNTT`. Lệnh trên khe chưa nạp, hoặc logn lớn hơn logn của khe, kết thúc ngay với lỗi.
- FFT/IFFT 32/64/128 bit, N tối đa 1024; N1/N2 là trường hợp đồng nhất. FFT chuyển tầng theo **số lượt ghi đã xong**
  của tầng (không theo khoảng cách cố định trong bảng), nên không phụ thuộc độ trễ của tile.
- Chưa có CMUL/SPLIT/MERGE, FFT NTRUGen, nhiều đa thức trong một lệnh, pause/flush hoặc giao diện lệnh đầy đủ của spec 2.0.
- **Đơn giản hóa so với spec 2.0 (02, phép nạp prime):** host ghi thẳng các gói 96 bit và các hằng số của khe, không ghi
  bảng gm/igm tuyến tính để lõi tự đóng gói, cũng không kiểm R² mod p.

## Các file sinh tự động

[gen_ntt_core.py](../../scripts/gen_ntt_core.py) tạo `ntt_core_gen.sv`, `root_pack_b0.mem` đến `root_pack_b3.mem` và vector
kiểm core. Bảng tầng NTT khóa theo (số tầng bỏ, chiều, logn, tầng): kế hoạch chồng tầng không phụ thuộc q, nên các profile
cố định và profile 3 dùng chung một bảng ([model/ntt_core_overlap.py](../../model/ntt_core_overlap.py),
[model/ntt_prime_core.py](../../model/ntt_prime_core.py); bộ sinh kiểm hai nguồn cho cùng kế hoạch).

## Tile dùng trong lõi

Từ 02/11/2026 tile có ba chế độ, `req_mode` 2 bit: lõi gửi 0 (NTT) và 1 (FFT); chế độ 2 (NTT hai hệ số 16 bit mỗi từ)
có ở tile nhưng lõi chưa dùng. Kết quả tile 64 bit. Độ trễ NTT và FFT của tile không đổi, nên bảng tầng và lịch FFT
giữ nguyên. Tile tổng hợp riêng 1 759 LUT (trước 2 045), xem [hdl/tile/MANIFEST.md](../tile/MANIFEST.md).

## Kiểm tra gần nhất

01/11/2026, nguồn sau khi thêm profile 3 (`sh sim/core_ntt/run.sh`, trả mã lỗi khi thiếu ca hoặc có ca sai):

| File vector | Ca | Kết quả |
|---|---:|---|
| `vectors.txt` (NTT profile 0, 1, 2) | 48 | đạt |
| `vectors_fft.txt` (FFT định dạng 0, 1, 2, hai chiều, N4..1024) | 54 | đạt; chu kỳ trùng [mô hình](../../model/fft_wide_sched.py) ở cả 54 ca |
| `vectors_p3.txt` (profile 3) | 100 | đạt: 80 ca so với C NTRUGen (4 prime, gồm hai prime của HAWK, logn 1..10, hai chiều) và 20 ca theo định nghĩa cho 3329 (thiếu 1 tầng), 8380417, 12289, 18433, 64513, 7681, 10753, 25166081 (thiếu 1 tầng), 20972417 (thiếu 2 tầng) |
| Lệnh profile 3 trên khe chưa nạp | 1 | kết thúc với lỗi |

Chu kỳ (lần đọc RAM đầu → lần ghi cuối + 1), N1024:

| Lệnh | Chu kỳ |
|---|---:|
| NTT / INTT q12289 (profile 0) | 984 / 985 |
| NTT / INTT prime nạp (profile 3), mọi q | 984 / 985 |
| FFT 32 / 64 / 128 bit, hai chiều | 644 / 2 031 / 7 510 |

Lỗi chuyển tầng FFT32 mà [báo cáo review](../../docs/implementation_review_2026_11_01.md) tìm thấy đã sửa bằng rào chắn
theo lượt ghi.

## Biên dịch và chạy

Từ root repo:

```text
sh sim/core_ntt/run.sh
```

Script sinh lại bảng, chạy ba file vector và trả mã 1 nếu số dòng CASE khác số dòng vector hoặc có ca sai.

## Số đo Vivado

Từ 02/11/2026 mục tiêu là 5,0 ns (200 MHz); lần đo dưới đây còn ở 3,0 ns, trước khi rút gọn tile. **Chưa đo lõi ở 5,0 ns.**
Vivado 2018.1, `xczu7ev-ffvc1156-2-e`, 3,0 ns, sau route, mặc định opt/place/route. Bản chụp nguồn ở
`study/build/step1_snapshot/` (hash trong `hashes.txt`).

| Nguồn | LUT | FF | DSP | BRAM tile | URAM | WNS |
|---|---:|---:|---:|---:|---:|---:|
| Bước 1: FFT 32/64/128 trên máy chung của tile, rào chắn theo lượt ghi, chưa có profile 3 | 53 722 | 29 435 | 64 | 64 | 0 | −0,672 ns |

Đường găng của lần đo này do RTL: số lượt ghi vừa xong (cộng 16 cờ) → cộng dồn → so sánh → chuyển tầng → cho phép nạp
bảng tầng. Đã sửa sau lần đo: so sánh trên bộ đếm đã đăng ký, FFT chuyển tầng muộn 1 chu kỳ. **Chưa đo lại.** Phân bổ
LUT: 16 tile 34 526, top 7 079, mạng 4 797, logic gắn RAM 4 170, logic gắn ROM root 2 752.

## Số đo và các phiên bản trước

[Lịch sử triển khai, chu kỳ, timing và cấu hình từng lần đo](../../docs/plan_history/cleanup_2026_11_01/core_ntt_MANIFEST.md)
được lưu nguyên nội dung, chỉ chỉnh đường dẫn. Không gán số LUT/DSP/WNS của một bản cũ cho source hiện tại chưa đo lại.
