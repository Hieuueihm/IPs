# Tìm kiến trúc lõi FFT/NTT dưới 35 000 LUT

> Ngày 02/11/2026. Tài liệu làm việc để **chọn** kiến trúc; chưa phải quyết định. Không sửa RTL, PLAN.md hay spec 2.0. Các
> số đo dùng RTL hiện có (và RTL ở commit 267dae9) với vỏ buộc cố định vài đầu vào. Vivado 2018.1,
> `xczu7ev-ffvc1156-2-e`, **chỉ tổng hợp, clock 5,0 ns**. Số ghi "ước tính" chưa đo; số ghi "mô hình" là chu kỳ từ mô hình
> Python, chưa phải RTL.

## 1. Câu hỏi nghiên cứu (đề xuất của anh, 02/11/2026)

> Làm thế nào tổ chức một lõi số học dùng chung cho FFT/IFFT nhiều precision và NTT/INTT nhiều modulus, sao cho giảm chi
> phí hỗ trợ nhiều chế độ mà vẫn giữ đúng số học và đáp ứng tốc độ yêu cầu?

Động lực đo được: thêm FFT 32/64/128 bit vào lõi NTT hiện tại tốn **26 901 LUT**, DSP giữ nguyên 64. Cần biết phần này đến
từ đâu và cơ chế nào giảm được.

Yêu cầu phải giữ:
- FFT 32, 64, 128 bit trên cùng RTL, cùng bitstream, chọn lúc chạy.
- Mỗi độ rộng đúng biểu diễn, quay vòng, làm tròn và chia của tham chiếu.
- NTT chọn modulus và bảng root lúc chạy, kết quả đúng modulo.
- FFT và NTT thực sự dùng chung tài nguyên số học.
- Đo tài nguyên và tốc độ riêng từng chế độ.
- **Ngân sách: LUT < 35 000.**
- Tốc độ: chưa có con số. Đề xuất mặc định (chờ duyệt): mỗi chế độ không chậm hơn lõi hiện tại; NTT tính theo số lời gọi
  thật của sinh khóa FN-DSA N1024 chậm không quá 5 %.

## 2. Chi phí từng chế độ, đo trên RTL hiện có

Cùng một lõi, buộc đầu vào chọn chế độ để Vivado bỏ phần không dùng:

| Bản | LUT | Tile (16) | Logic cấp lõi | Mạng bank → tile | Còn lại: chọn hàng bank, nạp host, địa chỉ ROM root | FF | LUTRAM | WNS |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Chỉ NTT | **24 672** | 13 645 | 2 497 | 1 367 | 7 163 | 17 825 | 1 328 | +2,34 ns |
| NTT + FFT 32 bit (máy FFT hiện tại, độ rộng buộc 32) | **44 873** | 30 245 | 5 070 | 2 161 | 7 397 | 28 924 | 4 448 | +2,17 ns |
| NTT + FFT 32/64/128 bit (lõi hiện tại) | **51 573** | 32 256 | 7 231 | 4 804 | 7 282 | 29 891 | 4 448 | +1,81 ns |
| Commit 267dae9: NTT (profile 0..2) + đường FFT 32 bit gọn | **34 219** | 21 912 | 3 336 | 1 433 | 7 538 | 22 076 | 2 145 | +2,29 ns |

Mọi bản 64 DSP. BRAM: 44 RAMB36 + 64 RAMB18 (267dae9: 12 + 64, chưa có bảng root nạp được của profile 3).

Phần thêm theo từng bước:

| Bước | LUT | Trong tile | Cấp lõi | Mạng | Còn lại |
|---|---:|---:|---:|---:|---:|
| Thêm FFT 32 bit (bằng máy FFT hiện tại) | +20 201 | +16 600 | +2 573 | +794 | +234 |
| Thêm 64/128 bit | +6 700 | +2 011 | +2 161 | +2 643 | −115 |

**Phát hiện chính.**
- **Máy FFT trong tile được làm cho 128 bit, và tile nào cũng trả giá đó kể cả khi chỉ chạy 32 bit.** Tile trong lõi:
  - chỉ NTT: 853 LUT;
  - với máy FFT hiện tại ở 32 bit: 1 890 LUT, kèm 200 LUTRAM giữ các phần của butterfly;
  - với đường FFT 32 bit gọn ở 267dae9: 1 370 LUT.
- Riêng phần "làm sẵn cho 128 bit" vì thế tốn khoảng 520 LUT mỗi tile, **~8 300 LUT** cho 16 tile.
- Phần riêng của 64/128 bit ngoài tile tốn **4 800 LUT**: cấp lõi 2 161 và mạng 2 643. Đây là chi phí chọn nguồn theo khối
  tile khi một butterfly rộng lấy toán hạng qua cổng của nhiều tile, cộng phần chuyển tiếp kết quả.
- Ngay bản chỉ NTT đã tốn 11 027 LUT cho điều phối (cấp lõi, mạng, chọn hàng bank, nạp host, địa chỉ ROM root), gần bằng
  13 645 LUT tính toán trong tile.
- **Đường FFT 32 bit gọn đã đo được và đúng hợp đồng:**
  - 3 tích (3M), làm tròn nửa-lên với `cfg_floor`, chia ở tầng cuối FFT ngược;
  - kiểm tile 5 cấu hình, lõi 18/18 ca FFT định dạng 0;
  - mỗi tile thêm ~520 LUT;
  - tile lúc đó còn chế độ tích thô 32×32, đúng cổng "tích từng phần" mà khối rộng dùng chung cần.

### Kiểm lại trên một tile đứng riêng (`tile_thu_top`, IN_REG = 1)

Buộc độ rộng ở cổng lõi chưa đủ chắc chắn: tile đọc độ rộng từ `cfg_q[5:4]`, mà ở NTT các bit này là q lúc chạy
([phân tích butterfly](phan_tich_tai_nguyen_butterfly.md) mục 2). Đo lại trên bản sao chỉ dùng để đo, buộc ngay trong vỏ
`tile_thu_top` (`study/build/tile_split/`):

| Tile (RTL hiện tại) | LUT | FF | LUTRAM | DSP | WNS ở 5 ns |
|---|---:|---:|---:|---:|---:|
| Chỉ NTT (bỏ cả NTT hai hệ số) | 625 | 1 040 | 63 | 4 | +2,52 ns |
| NTT + FFT, độ rộng buộc 32 bit, không NTT hai hệ số | 1 555 | 1 441 | 246 | 4 | +2,19 ns |
| NTT + FFT, độ rộng buộc 32 bit | 1 592 | 1 463 | 247 | 4 | +1,81 ns |
| Đầy đủ, không NTT hai hệ số | 1 654 | 1 498 | 250 | 4 | +2,06 ns |
| Đầy đủ | 1 759 | 1 521 | 251 | 4 | +2,01 ns |

- Logic riêng của 64/128 bit trong tile chỉ 99 .. 167 LUT, khớp số đo ở cấp lõi (126 mỗi tile).
- Máy FFT hiện tại ở 32 bit tốn 930 LUT và 183 LUTRAM trên nền NTT. Đường FFT 32 bit gọn ở 267dae9 tốn 538 LUT trên nền
  NTT cũ. So hai commit khác nhau nên chỉ là ước tính: tổ chức "máy nào cũng làm mọi độ rộng" tốn khoảng 400 .. 500 LUT
  mỗi tile hơn đường 32 bit gọn, chủ yếu ở trạng thái và tuần tự các phần, không ở phép toán riêng của 64/128 bit.
- Vậy khoản có thể lấy lại từ việc tổ chức lại FFT trong tile nhiều nhất khoảng 6 400 .. 8 000 LUT cho 16 tile, trước khi
  trừ chi phí của cách tổ chức mới (trạng thái đóng gói, hoặc khối rộng dùng chung).

## 3. Cơ chế giảm chi phí

| Phần chi phí | Đo | Cơ chế | Sau khi đổi | Cơ sở |
|---|---:|---|---:|---|
| Máy FFT 128 bit chép vào 16 tile | ~8 300 + 2 011 | Tile chỉ giữ đường FFT 32 bit gọn và cổng tích từng phần 32×32; FFT 64/128 làm ở **khối rộng dùng chung, mỗi nhóm 4 tile một khối** | 4 khối × X | 267dae9 đo; X chưa biết |
| Chọn nguồn theo khối cho FFT rộng | 4 804 | Tile gửi tích từng phần tới khối rộng của nhóm qua dây cố định; khối rộng ghi kết quả của chính nó | ~0 .. 1 000 | ước tính |
| Địa chỉ riêng từng tile, chọn hàng bank, địa chỉ ROM root (NTT và FFT 32 bit) | ~6 000 .. 8 000 trong 12 307 điều phối của 267dae9 | **Lịch hình học cố định**: tầng nào cũng đọc i, i + M/2 và ghi 2i, 2i + 1 sang bộ đệm kia; bộ đếm chung; mỗi tile một bảng root đọc ở địa chỉ chung | ~2 000 .. 3 000 | ước tính; lịch đã mô hình (mục 5) |
| Mạng bank → tile | 1 433 (267dae9) | Hình học cố định cần tới 8 nguồn mỗi cổng 32 bit với cách đặt bank đã thử; cần cách đặt ≤ 4 nguồn | 2 000 .. 4 000 | mô hình số nguồn; LUT ước tính |
| Nạp host vào 64 bank | ~2 000 | Không đổi | ~2 000 | ước tính từ số bit |

Hai cơ chế tách được: bỏ chọn nguồn theo khối của FFT rộng không cần đổi lịch bộ nhớ, và ngược lại. Không cộng một khoản
hai lần.

## 4. Kiến trúc đề xuất

1. **Tile (16):** NTT như hiện tại (Montgomery trên mảng, mọi q, NTT hai hệ số mỗi từ) + đường FFT 32 bit gọn (3M trên
   bộ nhân ghép, dùng chung bộ cộng/trừ) + cổng tích từng phần 32×32 có dấu cho FFT rộng. Số học dùng chung thật: 4 lá
   16×16, bộ cộng/trừ, đường rút gọn.
2. **Khối FFT rộng (4, mỗi nhóm 4 tile một khối):** nhận 4 tích từng phần mỗi chu kỳ từ 4 tile của nhóm, cộng dồn theo
   cột, làm tròn ở W/2, cộng/trừ phức có nhớ giữa các phần, chia ở tầng cuối FFT ngược. Tốc độ bằng hiện tại vì FFT rộng bị
   giới hạn bởi bộ nhân: 128 bit cần 45 tích từng phần mỗi butterfly. 16 tile × 1 tích mỗi chu kỳ cho 0,36 butterfly mỗi
   chu kỳ, như 16 tile × 1/45 hiện nay.
3. **Bộ nhớ:** lịch hình học cố định, hai bộ đệm trong cùng BRAM (đang dùng 128 / 1 024 hàng), bộ đếm hàng chung, bảng
   root riêng mỗi tile.

### Con số mỗi khối phải đạt để dưới 35 000 LUT

| Khối | Phải đạt | Đã biết | Trạng thái |
|---|---:|---|---|
| 16 tile: NTT + FFT 32 bit gọn + cổng tích từng phần | ≤ 23 000 | 21 912 đo ở 267dae9 (có tích thô, chưa có NTT hai hệ số, ~+50 .. 200 mỗi tile) | gần chắc |
| Điều phối (cấp lõi, mạng, chọn hàng bank, nạp host, root) | ≤ 8 000 | 12 307 hiện có ở 267dae9; ước tính sau hình học cố định 6 000 .. 9 000 | cần mạng ≤ 4 nguồn mỗi cổng |
| 4 khối FFT rộng | ≤ 4 000 (≤ 1 000 mỗi khối) | chưa biết; máy FFT trong tile hiện nay ~1 037 LUT + 200 LUTRAM nhưng chỉ nhận 1 tích mỗi chu kỳ, khối rộng nhận 4 | **rủi ro lớn nhất** |
| **Tổng** | **< 35 000** | | |

Nhận định về khối rộng: bộ cộng dồn 4 đầu vào, bộ chọn cột cho tích, và chỗ giữ phần của các butterfly đang chạy (độ
trễ ~66 chu kỳ, một butterfly mỗi ~11 chu kỳ: ~6 butterfly) có lẽ vượt 1 000 LUT mỗi khối. Nếu tốc độ FFT rộng được phép
giảm, khối nhỏ đi:
- **Một khối cho cả mảng, nhận 4 tích mỗi chu kỳ:** FFT 64/128 bit chậm khoảng 4 lần, chỉ một khối X.
- **Hai khối:** chậm khoảng 2 lần.

Vì vậy tốc độ yêu cầu cho FFT rộng quyết định X.

## 5. Tốc độ

Lịch hình học cố định đã mô hình ([model/cg_core_model.py](../model/cg_core_model.py),
[kết quả](../study/results/cg_core_model.md)):
- Mọi butterfly là đúng butterfly của phép biến đổi tại chỗ, kết quả NTT khớp ca vàng và profile 3 (hmin 0..2), thứ tự cuối
  tự nhiên.
- Không trùng cổng bank, mọi phụ thuộc đọc/ghi được giữ.
- Mô hình FFT trong đó cho mỗi tile tự làm butterfly rộng (như hiện tại). Lịch của khối rộng dùng chung **chưa mô hình**.

| Phép | Hiện tại | Đề xuất | Cơ sở |
|---|---:|---:|---|
| NTT N1024 | 984 | 983 | mô hình |
| NTT N256 | 255 | 309 (+21 %) | mô hình |
| NTT theo lời gọi sinh khóa FN-DSA N1024 (N2..1024) | 878 903 | 905 848 (**+3,1 %**) | mô hình × số lời gọi |
| FFT 32 bit N1024 | 644 | 451 (mô hình hình học cố định); 539 đo ở 267dae9 với lõi tại chỗ | mô hình / đo |
| FFT 64 bit N1024 (khóa: NTRUGen) | 2 031 | ~1 750 nếu đủ 4 khối nhận 4 tích mỗi chu kỳ | ước tính |
| FFT 128 bit N1024 (ký: Falcon R8) | 7 510 | ~6 900 nếu đủ 4 khối nhận 4 tích mỗi chu kỳ | ước tính |

Phần FFT nhanh hơn chủ yếu do tầng sau bắt đầu trước khi tầng trước ghi xong; lõi tại chỗ cũng làm được nếu thêm, không
phải lợi thế riêng của hình học cố định. NTT N64..256 chậm hơn vì tầng ngắn không che được độ trễ tile; theo tải sinh khóa
thật chỉ +3,1 %.

## 6. Các phương án đã loại, và vì sao

| Phương án | Lý do loại |
|---|---|
| Giữ máy FFT hiện tại, chỉ cho FFT rộng ở 4 tile | Đo bản buộc 32 bit: tile vẫn 1 890 LUT, phần riêng 64/128 trong tile chỉ 126 LUT mỗi tile. Chỉ tiết kiệm ~1 500 trong tile cộng một phần của 4 800 điều phối. Bản trước của tài liệu dựa vào ước tính 1 400 LUT mỗi tile, đã sai. |
| Chỉ đổi lịch bộ nhớ sang hình học cố định | Ước tính lõi 36 000 .. 42 000; khoản lớn nhất (máy FFT 128 bit trong 16 tile) vẫn còn. |
| Tile NTT + khối FFT riêng (tài nguyên cố định) | Cùng tốc độ FFT cần gấp đôi DSP (ước tính); không đạt yêu cầu "dùng chung tài nguyên số học". Giữ làm mốc so sánh cho bài báo. |
| Dòng chảy (mỗi tile một tầng) | 16 tile cho 10 tầng N1024: có tầng chỉ 1 tile → ≥ 1 536 chu kỳ (hiện tại 984); thêm đường vòng cho N, hmin, chiều ngược, nhịp FFT rộng. Ước tính, chưa mô hình. |

## 7. Việc phải làm để chốt (chưa làm; đều là mô hình hoặc ước tính, không RTL)

1. Chốt tốc độ yêu cầu cho FFT 64/128 bit (quyết định số khối rộng và X).
2. Thiết kế giấy khối FFT rộng: lịch cấp tích từng phần cho 4 tile, bộ cộng dồn, chỗ giữ, đúng làm tròn/quay vòng của
   tham chiếu; mô hình bit-exact với vector `fftwbf.txt`, đếm phép cộng và thanh ghi để ước tính LUT.
3. Tìm cách đặt bank cho hình học cố định để mỗi cổng mạng ≤ 4 nguồn; mô hình lại.
4. Mô hình lịch FFT rộng qua khối dùng chung trên hình học cố định (cổng, phụ thuộc, chu kỳ).
5. Xen hai đa thức để bù NTT N64..256 (nếu tốc độ yêu cầu cần).

Số đo: `study/build/core_area/` (lõi đầy đủ), `study/build/core_split/{nofft,fft32,keephier}/` (vỏ
`ntt_core_nofft.sv`, `ntt_core_fft32.sv`), `study/build/at267_core/` (RTL commit 267dae9). Thư mục này không vào git; trước
khi commit phải chép báo cáo sang `study/results/`.
