# FlexTransform v1 — ý tưởng, kiến trúc và giả thuyết

> Ngày 30/10/2026. **Bản chốt để triển khai RTL.** Ưu tiên thiết kế: **diện tích nhỏ**, NTT 16 bit (3329, 12289) chạy hết
> tốc độ, chấp nhận NTT 32 bit chậm hơn. Thay đổi sau ngày này cần ghi lý do và cập nhật lại tài liệu.
>
> **Thay đổi 31/10/2026, lần 6** (người dùng xác nhận): **lane 32 bit dùng một bộ Montgomery 32 bit riêng mỗi tile.**
> Giả thuyết 2 bị bác bỏ ở cấp tile trên RTL nghiệm thu ([hdl/tile/tile_thu.sv](../hdl/tile/tile_thu.sv); trên mảng
> 1 022 LUT / 4 DSP so với riêng 906 LUT / 11 DSP, LUT +12,8% > 10%), nên theo quy tắc đặt trước (hợp đồng tile mục 8)
> lane 32 bit dùng bộ riêng. Lane 16 bit giữ rút gọn trên mảng (lần 5). Hệ quả: khẳng định "không tốn DSP cho rút gọn"
> **không còn đúng** (thêm 7 DSP mỗi tile, khoảng 112 DSP cả lõi); đổi modulus 32 bit vẫn chỉ là đổi hằng số; NTT 32 bit
> nhanh gấp khoảng 3 lần ở cấp tile. Các mục 1, 3, 4, 5.3, 6 và 10 **chưa cập nhật**. Cấp lõi chưa đo: mạng bank → tile và
> cấp root nay phải nuôi 16 butterfly 32 bit mỗi chu kỳ. Bản trước:
> [trước khi chuyển lane 32 bit sang bộ riêng](plan_history/architecture_v1_before_dedicated32_2026-10-31.md).
>
> **Thay đổi 31/10/2026, lần 5** (người dùng chọn): **mọi modulus rút gọn trên mảng nhân**, kể cả 3329/12289. Với một
> làn NTT mỗi tile, ba lượt Montgomery 16 bit chạy trên ba bộ nhân khác nhau nên vẫn 1 butterfly/chu kỳ mỗi tile, và bản
> nháp cho ít LUT hơn bộ rút gọn hằng 6,7% (1 193 so với 1 279, cùng 4 DSP). Thay thế lựa chọn "rút gọn lai" của lần 3.
> Bản đối chứng của giả thuyết 2 đổi theo (bảng "Sửa sau khi khóa", chờ duyệt). Các mục 1, 3, 4, 5.3 và 6 **chưa cập
> nhật**. Bản trước: [trước khi chuyển sang mọi modulus trên mảng](plan_history/architecture_v1_before_all_on_array_2026-10-31.md).
>
> **Thay đổi 31/10/2026, lần 4** (người dùng duyệt): **một làn NTT mỗi tile**. Mỗi tile chỉ còn một bộ rút gọn hằng
> và một làn butterfly; mỗi request của tile là một butterfly, toán hạng ở ô cố định; bỏ nhịp hai tầng; ghép cặp hệ số
> chuyển ra mạng bank → tile. Lý do: tách LUT bản nháp cho thấy 4 làn NTT 16 bit tốn khoảng 1 700 / 4 000 LUT mỗi tile,
> trong khi NTT 16 bit chiếm dưới 0,1% chu kỳ của FN-DSA. Hệ quả: NTT 16 bit của lõi còn 16 butterfly/chu kỳ, **bỏ ưu
> tiên "NTT 16 bit chạy hết tốc độ"** ở đầu tài liệu. Hợp đồng tile và kiểm thử đã cập nhật
> ([spec 2.0, 10 và 11](../spec/FlexTransform/2.0/10_hop_dong_tile.md)); **các mục 1, 3, 4, 5.3 và 6 của tài liệu này
> chưa cập nhật** (vẫn mô tả 64 bộ rút gọn hằng và nhịp hai tầng). Bản trước:
> [trước khi chuyển sang một làn](plan_history/architecture_v1_before_single_lane_2026-10-31.md).
>
> **Thay đổi 31/10/2026, lần 3** (người dùng chọn): **rút gọn lai**. Hai modulus 16 bit 3329 và 12289 dùng bộ rút gọn
> hằng (cộng và dịch, không tốn DSP); lane 32 bit (8380417 và mọi prime 31 bit) giữ rút gọn trên mảng nhân. Lý do: bản
> nháp khối tile thử ([study/results/tile_thu_draft.md](../study/results/tile_thu_draft.md)) cho thấy rút gọn trên mảng
> cho mọi modulus chỉ giảm 6,5% LUT, trong khi NTT 16 bit chậm khoảng 3 lần; phần đắt nhất của bộ rút gọn riêng là bộ
> Montgomery 32 bit (7 DSP mỗi tile). Giả thuyết 2 và 4 được viết lại (mục 6). Bản trước:
> [trước khi chuyển sang rút gọn lai](plan_history/architecture_v1_before_hybrid_reduction_2026-10-31.md).
> Bản trước: [trước khi thêm NTT prime 31 bit](plan_history/architecture_v1_before_prime31_2026-10-30.md),
> [trước khi dùng chung hậu xử lý](plan_history/architecture_v1_before_shared_postproc_2026-10-30.md),
> [trước khi làm gọn](plan_history/architecture_v1_before_cleanup_2026-10-30.md).
>
> **Thay đổi phạm vi 31/10/2026, lần 2** (người dùng duyệt): thêm **cổng host có pipeline** và **địa chỉ trong lệnh**
> (thay đổi 10, 11). Lý do: đo trên bản chuẩn cho thấy chép dữ liệu host ↔ lõi chiếm 45–65% tổng thời gian với giao
> diện của spec 1.0. Bản trước: [trước khi sửa giao diện host](plan_history/architecture_v1_before_host_io_2026-10-31.md).
>
> **Thay đổi phạm vi 31/10/2026** (người dùng duyệt): thêm **mỗi tile một modulus** (thay đổi 9). Lý do: đo trên bản
> chuẩn cho thấy sinh khóa gọi hàng nghìn NTT nhỏ, mỗi lần một prime mới; chạy nhiều prime cùng lúc trên các tile
> khác nhau gỡ lại khoản chậm của rút gọn trên mảng. Bản trước:
> [trước khi thêm khe prime](plan_history/architecture_v1_before_prime_slots_2026-10-31.md).
>
> **Thay đổi phạm vi 30/10/2026** (người dùng duyệt): thêm **NTT modulo các prime 31 bit của NTRUGen** (thay đổi 8).
> Lý do: biến chiều modulus thành "mọi prime 31 bit lấy từ workload thật, đổi lúc chạy, không thêm phép tính"; xem
> [điểm mạnh của kiến trúc](diem_manh_kien_truc.md).

## 1. Ý tưởng

Lõi FlexTransform dùng **một mảng 64 bộ nhân 16×16** và **một khối hậu xử lý dùng chung** cho cả hai loại
phép biến đổi mà FN-DSA (Falcon) cần:

- **FFT số phức fixed-point** ở ba độ rộng: 32, 64 và 128 bit mỗi phần thực/ảo.
- **NTT modulo** ở hai độ rộng hệ số: 16 bit (q = 12289 của FN-DSA, q = 3329 của ML-KEM) và 32 bit
  (q = 8380417 của ML-DSA, và **mọi prime 31 bit** mà phần sinh khóa FN-DSA dùng, nạp lúc chạy).

Ba điểm chính:

1. **Luật độ rộng.** Một phép nhân w bit cần (w/16)² bộ nhân 16×16, nên mảng làm được 64 / (w/16)² phép nhân
   mỗi chu kỳ. Toán hạng càng hẹp, càng nhiều phép nhân song song, ở cả FFT lẫn NTT.
2. **Gom lô theo độ rộng.** Bộ điều khiển gom nhiều butterfly vào một lượt theo độ rộng đang chạy, để
   "hẹp hơn" thật sự thành "nhanh hơn" trong giới hạn bộ nhớ và bảng twiddle cấp được.
3. **Dùng chung cả phần sau phép nhân.** Làm tròn của FFT và rút gọn modulo của NTT đều có dạng
   "phần cao của tích + một hạng bù + một bit nhớ". Vì vậy dùng chung một bộ cộng cho bước này và một
   ngân hàng cộng/trừ chia làn cho mọi phép cộng sau đó. Ở lane 32 bit, các phép nhân phụ của rút gọn
   Montgomery **chạy luôn trên mảng nhân**, nên đổi modulus (8380417, mọi prime 31 bit) chỉ là đổi hằng số và không
   tốn DSP. Hai modulus 16 bit phổ biến (3329, 12289) dùng **bộ rút gọn hằng** nhỏ để NTT 16 bit chạy hết tốc độ.

Ba độ rộng FFT ứng với workload thật:

| Độ rộng FFT | Dùng cho | Phép tính phải khớp từng bit với |
|---|---|---|
| 128 bit (Q64.64) | Ký FN-DSA | Bản FN-DSA fixed-point đã chọn làm chuẩn (mục 5.1) |
| 64 bit (Q32.32) | Sinh khóa FN-DSA | Thư viện NTRUGen đi kèm chính bản chuẩn đó |
| 32 bit (Q16.16) | Xử lý tín hiệu | Quy tắc số học tự định nghĩa; không dùng cho ký |

## 2. Vấn đề hiện tại

Lõi đã chạy đúng hoàn toàn: 5 992 lời gọi kernel khớp, và bốn chữ ký (N = 512 và 1024) khớp từng byte với
phần mềm. Nhưng hai chiều linh hoạt mới có về chức năng, chưa có về tốc độ:

- **FFT 32, 64 và 128 bit đều mất 52 992 chu kỳ** (N = 1024). Bộ điều khiển xử lý tuần tự,
  23 chu kỳ cho mỗi butterfly.
- **NTT mất 10 chu kỳ cho mỗi lượt dữ liệu**; với N nhỏ, phần lớn mảng nhân để trống.
- **NTT chỉ có hai modulus cùng độ rộng 16 bit**, mỗi modulus một mạng nhân hằng riêng.
- Mỗi làn NTT có một bộ rút gọn riêng (64 làn), chỉ dùng cho NTT. Ước lượng thô từ các lần tổng hợp trước:
  khoảng 20% logic. Trên FPGA, phần này nằm ở LUT (nhân hằng bằng cộng/dịch), còn mảng nhân nằm ở DSP;
  con số thật sẽ đo lại bằng Vivado.

## 3. Kiến trúc

~~~text
              Lệnh + nạp/đọc dữ liệu (giao diện của spec 1.0)
                                |
   +------------- Khối lệnh: gom lô, 2 context, xen kẽ đa thức -------------+
                  |                                       |
     Bộ nhớ: 3 vùng × 64 bank × 16 bit         Bảng twiddle
     (hệ số 32 bit = 2 bank liền kề)            FFT: 4 bank, mỗi bank 1 root/chu kỳ
                  |                             NTT: gói 3 root cho hai tầng liên tiếp
                  |                                       |
     Chuẩn bị toán hạng: cộng trước cho nhân phức 3 tích; trừ (và chia đôi nếu là
     FFT 64 bit NTRUGen) cho butterfly ngược; giữ toán hạng chờ kết quả
                  |                       ^
                  |                       |  NTT 32 bit: đưa T_thấp·q' và m·q quay lại mảng
     Mảng 16 tile × 4 bộ nhân 16×16, nhóm theo độ rộng đang chạy
                                |
     Cây cộng ghép tích, lượng dịch cố định; lấy kết quả ở mức 1, 4, 16 hoặc 64 bộ nhân
                                |
   +------------------- HẬU XỬ LÝ DÙNG CHUNG --------------------+
   | Trích cửa sổ bit của tích (chọn vị trí, hằng số làm tròn)    |
   | Bộ cộng: phần cao + hạng bù + bit nhớ                         |
   |   FFT: P_cao + bit làm tròn (hoặc 0 nếu cắt bớt)              |
   |   NTT 32 bit: T_cao + (m·q)_cao + [T_thấp ≠ 0]                |
   |   (NTT 16 bit: bước này nằm trong 64 bộ rút gọn hằng)         |
   | Ngân hàng cộng/trừ chia làn (khoảng 5 730 bit cộng, mục 3.1b): |
   |   FFT: ghép số phức 3 tích, cộng/trừ butterfly (quay vòng)    |
   |   NTT: trừ q có điều kiện, cộng/trừ modulo                    |
   +---------------------------------------------------------------+
                                |
     Bộ điều khiển: đọc, tính, ghi chạy song song; chỉ sang tầng mới
     khi mọi kết quả của tầng cũ đã ghi xong
~~~

**Phần còn riêng cho từng miền** (nhỏ):
- NTT 32 bit: mux đưa T_thấp, q′, m, q quay lại mảng nhân; thanh ghi giữ T trong lúc chờ; cổng OR phát hiện
  T_thấp ≠ 0; hằng số q, q′, N⁻¹ của từng modulus.
- NTT 16 bit: 64 bộ rút gọn hằng (mỗi tile 4), mỗi bộ chọn giữa 3329 và 12289: nhân hằng q′ và q bằng cộng/dịch, cộng
  phần cao, trừ q có điều kiện. Không dùng DSP.
- FFT: dây nối ghép số phức 3 tích (phần cộng nằm trong ngân hàng chung); hằng số làm tròn; bảng twiddle.

### 3.1 Cách nhóm bộ nhân theo chế độ

| Chế độ | Bộ nhân cho một phép nhân | Phép nhân/chu kỳ | Đơn vị công việc/chu kỳ |
|---|---:|---:|---|
| FFT 32 bit | 4 | 16 | 5,33 butterfly (3 tích/butterfly) |
| FFT 64 bit (cả bản NTRUGen) | 16 | 4 | 1,33 butterfly |
| FFT 128 bit | 64 (58 cần dùng) | 1 | 0,333 butterfly |
| NTT 16 bit (3329, 12289) | 1 (T); rút gọn ở bộ hằng | — | 64 phép nhân modulo |
| NTT 32 bit | 11 (4 + 3 + 4), chạy 3 lượt trong một tile | — | 5,33 phép nhân modulo |

FFT dùng **ba tích thực cho mỗi phép nhân phức**, đúng như phần mềm chuẩn. Ở 128 bit, 6 trong 64 tích con
không ảnh hưởng kết quả nên được bỏ, vẫn chính xác từng bit. Lô FFT: 16 / 4 / 1 butterfly cho 32 / 64 / 128 bit.

### 3.1b Định cỡ ngân hàng cộng/trừ dùng chung

Tính bằng [model/postproc_adders.py](../model/postproc_adders.py): số bit cộng cần mỗi chu kỳ ở từng tầng sau
phép nhân, tại tốc độ đỉnh của mỗi chế độ.

| Bố trí | Tổng bit cộng |
|---|---:|
| Cần cho FFT (lớn nhất là FFT 32 bit) | 2 064 |
| Cần cho NTT (lớn nhất là NTT 16 bit, 64 butterfly/chu kỳ; phần cộng trong bộ rút gọn hằng không tính) | 4 704 |
| Hai ngân hàng riêng | 6 768 |
| **Một ngân hàng dùng chung** | **5 733** |

Dùng chung tiết kiệm khoảng **15%** bit cộng (chưa tính mux chọn làn và cắt chuỗi nhớ). Trước khi chuyển sang rút gọn
lai, khi NTT 16 bit chỉ chạy 21,3 butterfly/chu kỳ, con số là 2 832 bit và 33%
([study/results/postproc_adders_tren_mang.md](../study/results/postproc_adders_tren_mang.md)). Đây là **cái giá ở cấp
lõi** của rút gọn lai: NTT 16 bit chạy nhanh gấp 3 nên cần gấp 3 bộ cộng butterfly. Bản nháp khối tile thử không
thấy khoản này, vì ở đó mỗi biến thể đều có đủ phần butterfly cho tốc độ tối đa.

### 3.2 Mười một thay đổi so với lõi hiện tại

| # | Thay đổi | Mục đích |
|---|---|---|
| 1 | **Bộ điều khiển pipeline**: đọc, tính, ghi chạy chồng lên nhau | Bỏ 23 chu kỳ tuần tự mỗi butterfly |
| 2 | **Gom lô theo độ rộng**: 16 / 4 / 1 butterfly cho FFT 32 / 64 / 128 bit | Biến độ rộng hẹp thành tốc độ |
| 3 | **Bảng twiddle FFT chia 4 bank** (root số k ở bank k mod 4) | FFT 32 bit cần nhiều root mỗi chu kỳ |
| 4 | **Hậu xử lý dùng chung + rút gọn lai**: lane 32 bit rút gọn Montgomery trên mảng nhân; 3329/12289 dùng 64 bộ rút gọn hằng (không DSP) | Không tốn DSP cho rút gọn 32 bit; đổi modulus 32 bit chỉ là đổi hằng số; NTT 16 bit chạy hết tốc độ |
| 5 | **NTT 32 bit cho q = 8380417** (ML-DSA, N = 256) | Thêm chiều độ rộng cho NTT |
| 6 | **Chạy xen kẽ hai đa thức NTT** trên hai context sẵn có | Che thời gian chờ giữa các tầng |
| 7 | **FFT 64 bit theo đúng NTRUGen** | Sinh khóa FN-DSA dùng được lõi, khớp từng bit |
| 8 | **NTT modulo prime 31 bit của NTRUGen**: p và p0i nạp theo lệnh, bảng root là RAM nạp từ host, chia đôi modulo trong ngân hàng cộng, N = 2..1024 | Đổi modulus lúc chạy với prime bất kỳ của workload thật; sinh khóa dùng lõi cho cả NTT |
| 9 | **Mỗi tile một modulus**: 16 khe prime (p, p0i, R² mod p, vị trí bảng trong RAM gói root); với N < 64, một lệnh chạy tới 8 đa thức, mỗi đa thức một khe, trên các tile riêng | Song song RNS thật trên cùng mảng; gỡ khoản chậm của sinh khóa (nhiều NTT nhỏ, mỗi lần một prime) |
| 10 | **Giao diện bộ nhớ host có pipeline**: tới 8 giao dịch đang chờ, 1 dòng 128 bit mỗi chu kỳ | Phần chép dữ liệu của phép ký từ 65% xuống 49% tổng thời gian |
| 11 | **Địa chỉ đầu của vùng A/B/C trong mỗi lệnh** | Giữ dữ liệu trong lõi giữa các kernel; phép ký còn khoảng 36% là chép (cận dưới) |

Không đổi: cây cộng ghép tích, cách làm tròn FFT 128 bit, NTT hai tầng gộp.

## 4. Dự báo tốc độ

Tính bằng [model/flex_v1_projection.py](../model/flex_v1_projection.py). Đây là **dự báo**, chưa phải số đo:
giả định mỗi lượt phát được một chu kỳ một lần, đọc và ghi song song, chờ L chu kỳ giữa hai tầng.
Số lượt đọc bộ nhớ và số root lấy từ phân tích địa chỉ thật của lõi hiện tại.

**FFT, N = 1024** (hiện tại 52 992 chu kỳ cho cả ba độ rộng; L = 8):

| Áp dụng | 32 bit | 64 bit | 128 bit |
|---|---:|---:|---:|
| Chỉ thay đổi 1 (pipeline) | 4 680 | 5 192 | 7 496 |
| Thay đổi 1 + 2 + 3 | 552 | 1 864 | 7 496 |
| Giới hạn tính toán (không thể nhanh hơn) | 432 | 1 728 | 6 912 |

- Chỉ pipeline thì ba độ rộng gần như chạy ngang nhau: chưa có chiều precision.
- Thêm gom lô thì tỉ lệ thời gian 32 : 64 : 128 bit là 1 : 3,4 : 13,6, gần mức lý tưởng 1 : 4 : 16.
- FFT ngược cho cùng số chu kỳ, cộng thêm một lượt chia cuối (khoảng 32 / 64 / 128 chu kỳ). Với N = 512:
  264 / 832 / 3 264 chu kỳ.

**NTT với rút gọn lai** (thay đổi 4): NTT 16 bit dùng bộ rút gọn hằng, NTT 32 bit rút gọn trên mảng. Có tính độ trễ
thật của một nhịp hai tầng: tầng 2 phải chờ tầng 1; ở lane 32 bit mỗi phép nhân modulo còn đi qua bộ nhân ba lượt nối
tiếp. Tốc độ nhịp và độ trễ nhịp lấy từ mô hình tile ([model/mont_on_array_tile.py](../model/mont_on_array_tile.py));
độ trễ bộ nhân DSP 4 chu kỳ:

| Trường hợp | v1 (lai), một đa thức | v1, hai đa thức xen kẽ (mỗi đa thức) | Nếu rút gọn trên mảng (bản trước), một / hai | Nếu rút gọn riêng cả 32 bit, một / hai | Đo hiện tại |
|---|---:|---:|---:|---:|---:|
| q12289, N1024 | 160 | 80 | 390 / 240 | 160 / 80 | 800 |
| q12289, N256 | 80 | 40 | 168 / 84 | 80 / 40 | 160 |
| q8380417, N256 (32 bit) | 320 | 192 | 320 / 192 | 136 / 68 | — |

- Độ trễ một nhịp: 16 chu kỳ với bộ rút gọn hằng, 30 (16 bit) và 32 (32 bit) khi rút gọn trên mảng; gồm 2 chu kỳ
  đọc/ghi RAM.
- NTT 16 bit: nhanh hơn lõi hiện tại 5 lần (N1024) và 2 lần (N256), một đa thức.
- NTT 32 bit chậm **2,4–2,8 lần** so với khi có bộ Montgomery 32 bit riêng. Chấp nhận, đổi lấy 7 DSP mỗi tile.
- Với độ trễ bộ nhân 3: NTT 32 bit N256 khoảng 296 chu kỳ. FFT không bị ảnh hưởng.

**NTT modulo prime 31 bit của NTRUGen** (thay đổi 8; lane 32 bit, rút gọn trên mảng, độ trễ bộ nhân 4, một đa thức).
Nạp prime theo [spec 2.0 mục 02.3](../spec/FlexTransform/2.0/02_giao_dien.md): host ghi bảng vào vùng nhớ C, rồi
phép nạp prime xếp bảng thành gói root.

| N | 64 | 128 | 256 | 512 | 1024 |
|---|---:|---:|---:|---:|---:|
| NTT xuôi hoặc ngược (chu kỳ) | 132 | 212 | 320 | 592 | 1 120 |
| Host ghi vùng C, một bảng (dòng 128 bit) | 17 | 33 | 65 | 129 | 257 |
| Phép nạp, một bảng (chu kỳ, ước lượng thấp nhất) | 8 | 16 | 32 | 64 | 128 |

- N256 cho 320 chu kỳ, bằng NTT q = 8380417 cùng kích thước: cùng đường dữ liệu, chỉ khác hằng số.
- Logn lẻ có thêm một lượt một tầng cuối; con số trên lấy độ trễ lượt đó bằng một nhịp hai tầng (cận trên).
- Nạp cả hai bảng thì gấp đôi hai dòng dưới. Bảng nạp ở N lớn dùng được cho mọi N nhỏ hơn (đã kiểm trên cả 323 prime),
  nên mỗi prime chỉ cần nạp một lần. NTRUSolve biến đổi nhiều đa thức với cùng prime, nên chi phí nạp được chia đều.
  Thời gian nạp vẫn **phải tính vào** khi báo kết quả cho sinh khóa.

## 5. Quy tắc số học

### 5.1 Bản chuẩn

Bản chuẩn là mã FN-DSA fixed-point
[fixed-point-fndsa/fixed-point-c](https://github.com/fixed-point-fndsa/fixed-point-c), commit
`ad1e5bf7714d53230ad457364db8a46a1b459c94`, cấu hình mặc định (fixed-point, không AVX2).
- Phần **ký** dùng FFT 128 bit (Q64.64); lõi hiện tại đã khớp từng bit.
- Phần **sinh khóa** gọi thư viện **NTRUGen** đi kèm, dùng FFT 64 bit (Q32.32).

Các quy tắc FFT 32/64/128 bit hiện có giữ nguyên như [spec 1.0](../spec/FlexTransform/1.0/01_numeric_kernels.md).

### 5.2 FFT 64 bit theo NTRUGen (thay đổi 7)

Đã đọc trong mã nguồn và kiểm bằng [model/arch_checks.py](../model/arch_checks.py). Mọi phép cộng/trừ quay vòng ở 64 bit (có dấu).

```text
nhân(x, y)  = floor(x·y / 2^32)            // cắt bớt, KHÔNG làm tròn
nửa(v)      = floor((v + 1) / 2)           // cộng 1 rồi dịch phải
nhân phức 3 tích(s, y):
    z0 = nhân(s_re, y_re);  z1 = nhân(s_im, y_im)
    z2 = nhân(s_re + s_im, y_re + y_im)
    phần thực = z0 − z1;  phần ảo = z2 − (z0 + z1)

FFT xuôi:  y ← s·y;  (x, y) ← (x + y, x − y)                 // cùng lịch chỉ số với FFT 128 bit
FFT ngược: (x, y) ← (nửa(x + y), liên_hợp(s) · nửa(x − y))   // chia đôi ở MỌI tầng, không chia cuối
```

Khác FFT 64 bit hiện có của spec ở ba điểm:
1. Nhân cắt bớt: hằng số làm tròn ở bộ trích cửa sổ bằng 0.
2. Chia đôi ở cả hai nhánh của butterfly ngược, mỗi tầng.
3. Bảng twiddle riêng: 1 024 số phức, chép nguyên bit từ `GM_TAB` của NTRUGen (16 KiB).

Phải build NTRUGen **không AVX2** làm chuẩn so sánh. Mô hình đã kiểm: phép nhân và chia đôi đúng công thức,
lịch FFT/FFT ngược trùng với lịch của FFT 128 bit; chưa chạy với bảng `GM_TAB` thật và chương trình C.

### 5.3 Rút gọn Montgomery: bộ hằng cho 16 bit, trên mảng cho 32 bit (thay đổi 4, 5)

Một công thức cho tất cả, chỉ đổi hằng số. Với 3329 và 12289, bước m và m·q là nhân hằng, làm trong bộ rút gọn hằng
bằng cộng/dịch (như lõi hiện tại). Với lane 32 bit, cả ba lượt chạy trên mảng nhân:

```text
Hệ số nằm trong [0, q); root lưu dạng w·R mod q; q' = −q^(−1) mod R
T = a·b                                   // lượt 1 trên mảng nhân
m = phần thấp (log2 R bit) của T_thấp·q'  // lượt 2: chỉ cần nửa thấp
u = T_cao + (m·q)_cao + [T_thấp ≠ 0]      // lượt 3 tính m·q; cộng ở bộ cộng chung
kết quả = u − q nếu u ≥ q, ngược lại u      // = a·b·R^(−1) mod q, trong [0, q)
```

| q | R | q' | Bộ nhân dùng/phép nhân modulo | Phép nhân modulo/chu kỳ (16 tile) |
|---:|---|---:|---:|---:|
| 3329 | 2^16 | 3327 | 1 (T); m, m·q ở bộ rút gọn hằng | 64 |
| 12289 | 2^16 | 12287 | 1 (T); m, m·q ở bộ rút gọn hằng | 64 |
| 8380417 | 2^32 | 4236238847 | 11 (chiếm 3 lượt × 4 bộ nhân của một tile; 1 vị trí bỏ trống) | 5,33 |

Đã kiểm bằng code ([model/arch_checks.py](../model/arch_checks.py)): dựng T, m, m·q từ tích 16×16 rồi qua bộ cộng
chung cho đúng a·b·R⁻¹ mod q và u < 2q, với các q trên và hai prime 32 bit khác. Kết quả giống hệt cách rút gọn
hiện tại; chỉ đổi nơi tính.

**NTT 32 bit (q = 8380417):**
- NTT xuôi 8 tầng, root ζ = 1753 (bậc 512); NTT ngược nhân thêm 256⁻¹ mod q = 8 347 681 ở cuối.
- **Cách đặt trong bộ nhớ**: hệ số thứ c chiếm hai ô 16 bit liền nhau (địa chỉ 2c và 2c + 1), giống cách FFT
  đặt số nhiều phần. Với cách đánh bank sẵn có của lõi, hai nửa luôn nằm ở hai bank cạnh nhau cùng hàng.
- **Không xung đột bank**: đã kiểm toàn bộ 4 lượt xuôi và ngược của N = 256, cả dữ liệu lẫn bảng root
  ([model/res32_bank_map.py](../model/res32_bank_map.py)). v1 chỉ hỗ trợ N = 256. Kiểm thêm cùng bố cục cho mọi N:
  N ≤ 512 không xung đột; N = 1024 có 20% chu kỳ phải đọc hai lượt.

Lane 32 bit chạy được modulus lẻ bất kỳ < 2^31 chỉ bằng hằng số, kể cả 3329 và 12289 (chậm hơn bộ hằng). Lane 16 bit
chỉ nhận 3329 và 12289. v1 kiểm chứng ba modulus trên và các prime 31 bit của NTRUGen (mục 5.4).

### 5.4 NTT modulo prime 31 bit của NTRUGen (thay đổi 8)

Đã đọc trong mã nguồn `ng_mp31.c` của NTRUGen đi kèm bản chuẩn. Hàm `mp_mkgm7` chỉ dùng cho BAT, không thuộc FN-DSA.

```text
Prime p < 2^31, R = 2^32, p0i = −p^(−1) mod 2^32 (đúng là q' của mục 5.3), hệ số trong [0, p)
Bảng root (host nạp; dạng Montgomery):
    g_n  = căn nguyên thủy bậc 2n (g của bảng PRIMES bình phương 10 − logn lần)
    gm[đảo_bit(u)]  = g_n^u · R mod p
    igm[đảo_bit(u)] = (1/2) · g_n^(−u) · R mod p      // đã gộp sẵn hệ số 1/2
NTT xuôi (CT, giống NTT q12289):  t = mont(y, gm[k]);  (x, y) ← (x + t, x − t)
NTT ngược (GS):  (x, y) ← (nửa(x + y), mont(x − y, igm[k]))   // chia đôi MỌI tầng, không nhân 1/n ở cuối
nửa(v) = (v + p nếu v lẻ) / 2                                  // cộng có điều kiện rồi dịch, trong ngân hàng cộng
```

- Cách xếp hệ số và nhịp hai tầng giống NTT 32 bit của q = 8380417 (hệ số c ở ô 2c, 2c + 1). N = 2..1024; logn lẻ có
  một lượt một tầng cuối.
- Bố cục không xung đột bank ở mọi N ≤ 512. Ở N = 1024 có 20% chu kỳ phải đọc hai lượt, nhưng không làm chậm, vì phần
  tính chỉ dùng 1,33 trong 4 nhịp mỗi chu kỳ mà bộ nhớ cấp được
  ([model/res32_bank_map.py](../model/res32_bank_map.py)).
- Một nhịp cần 3 root (gm[k], gm[2k], gm[2k + 1]); ở 1,33 nhịp/chu kỳ là khoảng 4 root mỗi chu kỳ. Đã chốt trong
  [spec 2.0 mục 03.4](../spec/FlexTransform/2.0/03_bo_nho.md): phép nạp prime xếp bảng thành gói 96 bit, 4 bank,
  tới 511 gói mỗi chiều.
- **Đã kiểm khớp từng bit với C** ([model/ntrugen_mp31.py](../model/ntrugen_mp31.py), kết quả
  [study/results/ntrugen_mp31.md](../study/results/ntrugen_mp31.md)), trên cả 323 prime của bảng `PRIMES` và
  logn = 1..10:
  - 21 641 phép Montgomery dựng từ tích 16×16 cộng bộ cộng chung khớp `mp_montymul`, gồm các giá trị 0, 1, p − 1;
  - 3 230 bảng root tính theo công thức khớp `mp_mkgmigm`;
  - 3 230 NTT xuôi khớp `mp_NTT`, chạy theo nhịp hai tầng như phần cứng;
  - 3 230 NTT ngược khớp `mp_iNTT`.

### 5.5 Mỗi tile một modulus (thay đổi 9)

- Lõi giữ **16 khe prime**. Mỗi khe có p, p0i, R² mod p, logn của bảng, mặt nạ bảng có mặt, vị trí gói đầu trong RAM
  gói root và một cờ hợp lệ. Phép nạp prime ghi một khe; host chọn khe và vị trí. Bảng N = 16 chỉ có 7 gói, nên RAM
  511 gói mỗi chiều chứa đủ 16 khe ở N nhỏ.
- **N < 64:** một lệnh profile 3 chạy tới min(8, 64/N) đa thức. Đa thức j dùng khe (khe đầu + j) mod 16. Mỗi đa thức
  nằm trên các tile riêng, nên bộ điều khiển ghi q, q′ của khe tương ứng vào thanh ghi hằng số của từng tile lúc mảng rảnh,
  đúng như hợp đồng tile đã cho phép. Phần số học không thêm gì.
- **N ≥ 64:** mọi tile phục vụ cả lệnh, nên một lệnh chỉ dùng một khe. Hai đa thức xen kẽ phải cùng khe.
- Chi phí thêm: 16 khe × khoảng 110 bit thanh ghi; cộng địa chỉ gói với vị trí của khe; bộ điều khiển ghi hằng số theo
  từng tile.
- Host phải tổ chức lại vòng lặp theo prime của NTRUSolve, để các NTT cùng loại của nhiều prime đứng liền nhau. Các làn
  RNS độc lập nên làm được. Riêng một vòng trong `ng_poly.c` dùng chung mảng `k` giữa các prime, cần chép riêng cho từng
  prime.
- Dự báo trên workload thật (cận trên theo cách gom, [study/results/fn_dsa_workload.md](../study/results/fn_dsa_workload.md)):
  - thời gian NTT của sinh khóa giảm 1,8 lần (N = 512) và 2,0 lần (N = 1024);
  - tổng chu kỳ kernel của sinh khóa N = 1024 còn 943 632, so với 1 395 007 khi mỗi lệnh một đa thức.

### 5.6 Chép dữ liệu host ↔ lõi (thay đổi 10, 11)

Đo trên bản chuẩn ([study/results/fn_dsa_workload.md](../study/results/fn_dsa_workload.md), mục "Chép dữ liệu"): các
kernel của FN-DSA nhỏ, và giữa chúng host còn làm việc khác (bộ lấy mẫu khi ký, nhân từng điểm khi sinh khóa), nên dữ
liệu phải qua lại liên tục.

| N = 1024, một lần … | Chu kỳ tính | Tổng, giao diện 1.0 | Tổng, burst 128 bit (thay đổi 10) | Tổng, burst + giữ dữ liệu (thay đổi 10 + 11, cận dưới) |
|---|---:|---:|---:|---:|
| Ký | 129 952 | 375 712 (65% là chép) | 252 832 (49%) | 203 648 (36%) |
| Sinh khóa | 943 632 | 1 719 297 (45%) | 1 331 464 (29%) | 1 281 513 (26%) |

- **Thay đổi 10: giao diện bộ nhớ host có pipeline.**
  - Cho tới 8 giao dịch đang chờ, nhận một dòng 128 bit mỗi chu kỳ, trả lời đúng thứ tự.
  - Khớp cổng AXI HP 128 bit của Zynq UltraScale+ qua một bộ chuyển đổi bên ngoài lõi.
  - Mảng nhân không đổi.
- **Thay đổi 11: mỗi lệnh mang địa chỉ đầu của vùng A, B, C.** Lệnh của 1.0 luôn làm việc ở địa chỉ 0, nên host phải
  chép lại mọi đầu vào. Với địa chỉ trong lệnh, host giữ được nhiều bộ đệm trong 48 KiB và chỉ chép phần thật sự thay đổi.
  - Điều kiện: địa chỉ là bội của kích thước vùng dữ liệu làm tròn lên lũy thừa của 2 (ít nhất 8 ô).
  - Khi đó hàm đánh bank chỉ bị xor với một hằng, nên số xung đột bank giữ nguyên như ở địa chỉ 0. Đã kiểm 4 084
    trường hợp NTT 16 và 32 bit ([model/res32_bank_map.py](../model/res32_bank_map.py)); lập luận xor đúng cho mọi
    cách đặt.
  - Không có trạng thái ẩn giữa các lệnh.
- Giữ dữ liệu chỉ giảm số dòng của phép ký khoảng 18% (giữ đầu vào) tới 40% (cận dưới), vì phần lớn đầu ra được host
  dùng ngay. Phần còn lại phụ thuộc băng thông cổng host, không phụ thuộc mảng nhân.
- **Để sau v1:** cho host chép vào vùng nhớ mà lệnh đang chạy không dùng, để chồng phần chép lên phần tính.

## 6. Giả thuyết cần chứng minh

Đo trên RTL v1 bằng công cụ profiling hiện có, tính chu kỳ từ lúc bắt đầu đến lúc xong lệnh.
Ngưỡng được đặt **trước khi đo**; không sửa sau khi có kết quả.

**Đã khóa ngày 31/10/2026, khóa lại cùng ngày sau khi chuyển sang rút gọn lai, sau khi đổi bản đối chứng của giả
thuyết 2, và sau khi viết lại giả thuyết 4 cho tile một làn.** Bản sao và mã SHA-256 của bảng hiện hành nằm ở
[plan_history/nguong_khoa_2026-10-31_lan4.md](plan_history/nguong_khoa_2026-10-31_lan4.md); các bản khóa trước ở
[lần 3](plan_history/nguong_khoa_2026-10-31_lan3.md), [lần 2](plan_history/nguong_khoa_2026-10-31_lan2.md) và
[lần đầu](plan_history/nguong_khoa_2026-10-31.md). Từ đây:
- mọi sửa đổi ngưỡng phải thêm một dòng vào bảng lịch sử bên dưới, ghi ngưỡng cũ, ngưỡng mới, lý do, và đã có số đo
  nào chưa;
- bài báo báo cả ngưỡng đã khóa, kể cả khi kết quả không đạt.

Lịch sử sửa trước khi khóa (chưa có số đo nào):

| Ngày | Giả thuyết | Thay đổi | Lý do |
|---|---|---|---|
| 30/10 | 2 | Bản đối chứng từ "64 bộ rút gọn của lõi cũ" thành "rút gọn riêng đủ cùng tập modulus"; chậm cho phép từ ≤ 2,5 lần thành ≤ 3,5 lần | Lõi cũ không chạy được modulus mới; mô hình độ trễ nhịp cho chậm 2,1–3,0 lần |
| 30/10 | 3, 4 | Thêm điều kiện độ trễ đường FFT ≤ 24; mô hình NTT tính theo độ trễ nhịp | Mô hình tile hai tầng |
| 30/10 | 10 | Thêm mới; BRAM cho phép từ 8 KiB thành khoảng 12 KiB | NTT prime 31 bit; bảng root lưu dạng gói 96 bit |
| 31/10 | 11 | Thêm mới | Mỗi tile một modulus |
| 31/10 | 12 | Thêm mới | Cổng host có pipeline, địa chỉ trong lệnh |

Sửa sau khi khóa:

| Ngày | Giả thuyết | Ngưỡng cũ | Ngưỡng mới | Lý do | Đã có số đo? |
|---|---|---|---|---|---|
| 31/10 | 2 | Rút gọn trên mảng cho mọi modulus so với rút gọn riêng: LUT giảm ≥ 10% (bác bỏ khi < 5%), DSP không tăng, Fmax giảm ≤ 10%, NTT chậm ≤ 3,5 lần | Chỉ lane 32 bit rút gọn trên mảng, so với bộ Montgomery 32 bit riêng: DSP ít hơn ≥ 4 mỗi tile, LUT tăng ≤ 5%, Fmax giảm ≤ 10%, NTT 32 bit chậm ≤ 3,5 lần (bác bỏ khi DSP giảm < 2, LUT tăng > 10% hoặc chậm > 4 lần) | Người dùng chọn cấu hình lai (mục 5.3): 3329/12289 dùng bộ rút gọn hằng để NTT 16 bit chạy hết tốc độ; lane 32 bit giữ rút gọn trên mảng | Có số đo **bản nháp** của hai biến thể cũ ([study/results/tile_thu_draft.md](../study/results/tile_thu_draft.md): LUT 0,935, DSP 4 so với 11). Ngưỡng mới đặt **trước** khi đo biến thể lai, nhưng điều kiện DSP đặt khi đã biết bản riêng tốn 7 DSP. Chưa có RTL nghiệm thu. Ngưỡng do trợ lý đề xuất; **người dùng duyệt 31/10/2026**, sau khi đã thấy số đo bản nháp của biến thể lai |
| 31/10 | 4 | q12289 theo độ trễ nhịp 30: N1024 ≤ 488, N256 ≤ 210, xen kẽ ≤ 105 | Theo độ trễ nhịp 16 của bộ rút gọn hằng: N1024 ≤ 200, N256 ≤ 100, xen kẽ ≤ 50 mỗi đa thức; NTT 32 bit giữ ≤ 400 | Cùng lý do; vẫn là 1,25 × mô hình | Chưa |
| 31/10 | 7 | Ghi chú "phải đo lại với rút gọn trên mảng" | "Phải đo lại trên lõi v1" | NTT 16 bit không còn rút gọn trên mảng | Không đổi ngưỡng |
| 31/10 (lần 4, sửa ở lần 5 và 6) | 4 | N1024 ≤ 200, N256 ≤ 100, xen kẽ ≤ 50 mỗi đa thức; NTT 32 bit N256 ≤ 400 | **Người dùng duyệt 31/10/2026, đã ghi vào bảng và khóa lại (lần 4).** Viết lại cột "Đạt khi": "Thời gian ≤ 1,25 × mô hình, với mô hình = tổng các lượt (mỗi tầng một lượt) × (số chu kỳ phát của lượt theo [model/single_lane_feed.py](../model/single_lane_feed.py) + độ trễ butterfly đo được + 2 chu kỳ RAM). Dự báo: q12289 N1024 ≤ 590, N256 ≤ 230, hai đa thức xen kẽ ≤ 115 mỗi đa thức; NTT 32 bit (bộ Montgomery riêng) N256 ≤ 250". Ngưỡng bác bỏ giữ "Vượt 2 × mô hình". Mô hình (8 bank gói root, đọc lệch một chu kỳ) cho 16 butterfly/chu kỳ ở N256 và N1024, cả hai lane: 470 / 184 / 92 / 200 chu kỳ với độ trễ RTL nghiệm thu 13 và 15 | Ngưỡng cũ **hỏng do thay đổi đã duyệt** (một làn NTT mỗi tile, bỏ nhịp hai tầng), không phải do số đo; công thức cũ nói theo "nhịp" nên phải viết lại | Chỉ độ trễ của tile; chưa có lõi |
| 31/10 (lần 5) | 2 | "So với cùng tile dùng bộ Montgomery 32 bit riêng (cả hai có cùng 4 bộ rút gọn hằng cho 3329/12289; …)" | "So với cùng tile dùng bộ Montgomery 32 bit riêng (cả hai rút gọn lane 16 bit trên mảng nhân; …)". **Người dùng duyệt 31/10/2026**, đã ghi vào bảng và khóa lại (lần 3). Các ngưỡng giữ nguyên: DSP ít hơn ≥ 4 mỗi tile, LUT tăng ≤ 5%, Fmax giảm ≤ 10%, NTT 32 bit chậm ≤ 3,5 lần | Người dùng chọn rút gọn mọi modulus trên mảng; bản đối chứng phải chỉ khác thiết kế ở lane 32 bit (hợp đồng tile mục 5) | Có, bản nháp, đo **sau** khi viết đề xuất này: so với bản đối chứng mới, DSP ít hơn 7 nhưng LUT tăng 16,2%, tức **chạm điều kiện bác bỏ** ([study/results/tile_thu_draft.md](../study/results/tile_thu_draft.md) mục 10). Không đổi ngưỡng vì kết quả này. Người dùng giữ lane 32 bit trên mảng và chờ RTL thật để quyết định |

| # | Giả thuyết | Đạt khi | Bác bỏ khi |
|---|---|---|---|
| 1 | **Dùng chung FFT/NTT có lợi về tài nguyên** | Với từng loại LUT, DSP và BRAM/URAM: lõi chung ≤ lõi chỉ-FFT + lõi chỉ-NTT, mỗi lõi riêng có cùng tốc độ với lõi chung ở chế độ của nó; LUT nhỏ hơn rõ rệt | LUT hoặc DSP của lõi chung ≥ tổng hai lõi riêng |
| 2 | **Rút gọn 32 bit trên mảng nhân rẻ hơn bộ Montgomery 32 bit riêng** | So với cùng tile dùng bộ Montgomery 32 bit riêng (cả hai rút gọn lane 16 bit trên mảng nhân; định nghĩa ở mục 5 của [hợp đồng cấp tile](../spec/FlexTransform/2.0/10_hop_dong_tile.md)): DSP ít hơn ít nhất 4 mỗi tile; LUT tăng ≤ 5%; Fmax giảm ≤ 10%; NTT 32 bit chậm ≤ 3,5 lần ở N256, một hoặc hai đa thức (dự báo 2,4–2,8) | DSP giảm < 2, hoặc LUT tăng > 10%, hoặc chậm > 4 lần |
| 3 | **Gom lô tạo ra chiều precision cho FFT** | N1024: FFT xuôi ≤ 700 / 2 300 / 8 500 chu kỳ cho 32 / 64 / 128 bit; FFT ngược ≤ 770 / 2 530 / 9 350. Tỉ lệ 128 bit so với 32 bit ≥ 10, so với 64 bit ≥ 3 (N512: ≥ 8). Khi chỉ có pipeline, tỉ lệ 128/32 bit ≤ 2. Ngưỡng đúng khi độ trễ đo được của đường FFT (đọc RAM tới ghi) ≤ 24 chu kỳ | Có gom lô mà tỉ lệ 128/32 bit < 4 |
| 4 | **Pipeline đưa NTT tới gần mô hình** | Thời gian ≤ 1,25 × mô hình, với mô hình = tổng các lượt (mỗi tầng một lượt) × (số chu kỳ phát của lượt theo [model/single_lane_feed.py](../model/single_lane_feed.py) + độ trễ butterfly đo được + 2 chu kỳ RAM). Dự báo: q12289 N1024 ≤ 590, N256 ≤ 230, hai đa thức xen kẽ ≤ 115 mỗi đa thức; NTT 32 bit (bộ Montgomery riêng) N256 ≤ 250 | Vượt 2 × mô hình |
| 5 | **Chiều độ rộng FFT không đắt so với lõi chỉ làm FFT 128 bit** | LUT ≤ 1,35 lần và DSP bằng lõi chỉ-128-bit; tốc độ trên LUT ở 32 bit ≥ 7 lần, ở 128 bit ≥ 0,75 lần | Không đạt cả hai ngưỡng 32 bit |
| 6 | **Mọi kết quả khớp từng bit với phần mềm chuẩn** | 0 sai khác; chữ ký khớp từng byte | Một sai khác (**đã đạt** với lõi hiện tại) |
| 7 | **NTT hai tầng gộp giảm một nửa lượng dữ liệu, tốn ít tài nguyên** | N1024 cần 5 lượt thay vì 10; thêm ≤ 3% LUT so với chỉ chạy một tầng | Thêm > 10% LUT. (Đã đo trên thiết kế cũ có bộ rút gọn riêng: 5 lượt, +1,10%; **phải đo lại** trên lõi v1) |
| 8 | **Một lõi phục vụ cả ký (128 bit) và sinh khóa (64 bit)** | FFT 64 bit khớp NTRUGen; sinh khóa dùng lõi cho khóa khớp từng byte (≥ 2 seed mỗi N512/N1024) | Một sai khác |
| 9 | **NTT 32 bit chạy đúng, không xung đột bank** | Khớp NTT của bản chuẩn ML-DSA (Dilithium, pq-crystals) sau khi đổi cách biểu diễn; bộ đếm xung đột = 0 | Một sai khác hoặc có xung đột |
| 10 | **Đổi sang prime 31 bit bất kỳ của NTRUGen không tốn thêm phép tính, chỉ tốn ít tài nguyên** | Khớp từng bit `mp_NTT`/`mp_iNTT` trên cả 323 prime, logn = 1..10; LUT thêm cho chế độ này ≤ 3% lõi; BRAM thêm không quá RAM gói root hai chiều (khoảng 12 KiB, [spec 2.0 mục 03.4](../spec/FlexTransform/2.0/03_bo_nho.md)); thời gian ≤ 1,25 × mô hình (N1024 ≤ 1 400 chu kỳ, chưa gồm nạp root) | Một sai khác, hoặc LUT thêm > 10% |
| 11 | **Mỗi tile một modulus làm sinh khóa nhanh lên mà gần như không tốn tài nguyên** | Mỗi đa thức của lệnh nhiều khe khớp từng bit với chạy riêng; LUT thêm ≤ 2% lõi; thời gian NTT của sinh khóa (đếm như [study/results/fn_dsa_workload.md](../study/results/fn_dsa_workload.md), với chu kỳ đo trên RTL) giảm ≥ 1,5 lần so với một đa thức mỗi lệnh (dự báo 1,8–2,0) | Giảm < 1,2 lần, hoặc LUT thêm > 5% |
| 12 | **Cổng host có pipeline và địa chỉ trong lệnh làm giảm thời gian chép** | Cổng host đạt ≥ 0,9 dòng/chu kỳ khi đọc và ghi liên tục; trình điều khiển giữ dữ liệu trong lõi làm số dòng chép của phép ký N = 1024 ≤ 0,85 lần so với không giữ (dự báo 0,82 khi chỉ giữ đầu vào); LUT thêm cho hai thay đổi ≤ 2% lõi | Cổng host < 0,5 dòng/chu kỳ, hoặc giữ dữ liệu giảm < 5% số dòng |

**Cách đo tài nguyên** (giả thuyết 1, 2, 5): trên FPGA, bằng Vivado.
- Linh kiện **xczu7ev-ffvc1156-2-e** (board ZCU106, đã dùng trong `fpga/zcu106/`); cùng phiên bản Vivado và cùng
  cài đặt cho mọi thiết kế; tổng hợp và place-and-route out-of-context.
- Báo riêng từng loại: **LUT, FF, DSP, BRAM/URAM**, và **Fmax** (WNS sau route ở cùng một clock mục tiêu).
  Không cộng các loại thành một con số "diện tích".
- RTL vẫn viết chung, không gọi primitive của Xilinx; Vivado tự suy ra DSP và BRAM.
- Lõi chỉ-NTT riêng chỉ cần RAM đủ cho NTT, nên phần tiết kiệm BRAM của lõi chung bằng RAM của lõi NTT,
  không phải cả 48 KiB.
- "Tốc độ 32 bit" của lõi chỉ-128-bit nghĩa là chạy cùng phép biến đổi ở 128 bit (kết quả không giống hệt,
  chỉ để so thời gian).

**Hình chính của bài báo:** tốc độ theo độ rộng toán hạng (FFT 32/64/128, NTT 16/32) trên cùng lõi, kèm LUT/DSP/BRAM
so với lõi chỉ-FFT + lõi chỉ-NTT và lõi chỉ-128-bit.

## 7. Thay đổi so với spec 1.0

| Thay đổi | Mục spec bị thay | Nội dung mới |
|---|---|---|
| 5, 7 | 00.2 bảng định dạng | Trường định dạng 3 bit: thêm **4 = NTT 32 bit**, **5 = FFT 64 bit NTRUGen** (chỉ FFT/FFT ngược, logn 1..10); 6–7 dự trữ |
| 5 | 00.3 bảng modulus | Thêm modulus số 2 = 8380417, chỉ định dạng 4, chỉ N = 256 |
| 6 | 00.4 số đa thức mỗi lệnh | N ≥ 64: cho phép 1 hoặc 2 đa thức; đa thức thứ hai bắt đầu ở ô N (16 bit) hoặc 2N (32 bit) |
| 3 | 00.5 và 03.5 "một root mỗi chu kỳ" | 4 bank root; thêm bảng NTRUGen |
| 2 | 03.5 "nên gom butterfly" | Thành **bắt buộc**: 16 / 4 / 1 butterfly theo độ rộng |
| 5 | 03.4 cách đặt hệ số; 03.6 gói root | NTT 32 bit: hệ số c ở ô 2c, 2c + 1; gói 3 root 96 bit ở 4 bank, bank = số gói mod 4 |
| 5, 7 | 02 giao diện lệnh | `cmd_fmt_i` thành 3 bit, `cmd_reserved_i` còn 7 bit (vẫn phải bằng 0) |
| 4 | Không đổi hợp đồng | Rút gọn lai (bộ hằng cho 16 bit, trên mảng nhân cho 32 bit) là lựa chọn vi kiến trúc; kết quả số học giống hệt |
| 8 | 00.3 bảng modulus | Thêm modulus số 3 = **prime 31 bit nạp được**: chỉ định dạng 4, N = 2..1024; NTT, NTT ngược theo NTRUGen (chia đôi mỗi tầng) và nhân từng điểm |
| 8 | 02 giao diện; 03.6 bảng root | Lệnh nạp p, p0i và bảng gm/igm (1 024 word 32 bit mỗi bảng) từ host; bảng root NTT 32 bit thành RAM |
| 8 | 01 số học | Thêm phép chia đôi modulo trong ngân hàng cộng |
| 9 | 00, 02, 03 | 16 khe prime; trường lệnh "khe đầu" 4 bit lấy từ trường dự trữ; phép nạp prime chọn khe và vị trí gói; profile 3 với N < 64 cho tới min(8, 64/N) đa thức, mỗi đa thức một khe |
| 10 | 02.3 bộ nhớ host | Tới 8 giao dịch đang chờ, 1 dòng mỗi chu kỳ, trả lời đúng thứ tự |
| 11 | 02 trường lệnh; 03.4 cách đặt | Ba trường địa chỉ đầu 13 bit (ô 16 bit) cho vùng A, B, C; căn theo kích thước vùng làm tròn lên lũy thừa của 2; lỗi mới khi sai địa chỉ |

Lỗi lệnh mới (giữ thứ tự kiểm như spec):

| Lỗi | Khi nào |
|---|---|
| Sai định dạng | Định dạng 6–7; NTT 32 bit cho lệnh FFT; FFT NTRUGen cho lệnh khác FFT/FFT ngược |
| Sai modulus | Modulus 2 hoặc 3 với định dạng khác 4; định dạng 4 với modulus 0 hoặc 1 |
| Sai kích thước | Modulus 2 với N khác 256; modulus 3 với N = 1; FFT NTRUGen với N = 1 |
| Chưa nạp prime | Modulus 3 khi chưa nạp p, p0i, hoặc bảng root đã nạp cho N khác N của lệnh |
| Sai số đa thức | N ≥ 64 với hơn 2 đa thức |

## 8. Kiểm chứng và thứ tự triển khai

Mọi bước phải giữ: 5 992 kernel khớp như hiện tại, chữ ký khớp từng byte và được verifier chấp nhận.

| Bước | Làm | Kiểm và báo cáo |
|---|---|---|
| 1 | Bộ điều khiển pipeline | Chu kỳ FFT ba độ rộng và NTT khi **chỉ** có bước này; độ trễ L thật |
| 2 | Gom lô + twiddle 4 bank | Giả thuyết 3; thử 1, 2, 4 bank twiddle |
| 3 | Hậu xử lý dùng chung + rút gọn lai | Giả thuyết 2: trước hết làm **khối tile thử** theo [hợp đồng cấp tile](../spec/FlexTransform/2.0/10_hop_dong_tile.md) (hai biến thể: lai / rút gọn riêng), chạy [kiểm thử cấp tile](../spec/FlexTransform/2.0/11_kiem_thu_tile.md), đo LUT/FF/DSP/Fmax bằng Vivado; sau đó mới đưa vào lõi |
| 4 | Xen kẽ hai đa thức | Giả thuyết 4 |
| 5 | NTT 32 bit | Giả thuyết 9; so với Dilithium, giá trị biên 0, 1, q − 1 |
| 6 | FFT 64 bit NTRUGen | Giả thuyết 8 |
| 6b | NTT prime 31 bit NTRUGen | Giả thuyết 10; vector từ `mp_NTT`/`mp_iNTT` cho cả 323 prime; sau đó sinh khóa dùng lõi cho cả FFT 64 bit lẫn NTT, khóa khớp từng byte |
| 6c | Mỗi tile một modulus | Giả thuyết 11; lệnh nhiều khe; đếm lại workload sinh khóa với chu kỳ đo trên RTL |
| 6d | Cổng host có pipeline, địa chỉ trong lệnh | Giả thuyết 12; đo tốc độ cổng host; trình điều khiển giữ dữ liệu cho luồng ký |
| 7 | Vivado cho lõi chung, lõi chỉ-FFT, lõi chỉ-NTT, lõi chỉ-128-bit | Giả thuyết 1, 5; LUT/FF/DSP/BRAM thêm của từng bước |

Báo cáo thêm: sai số FFT 32/64 bit theo độ rộng (cho xử lý tín hiệu). Nếu chu kỳ đo lệch dự báo quá 30%,
cập nhật mô hình theo độ trễ thật trước khi kết luận.

### 8.1 Chia giai đoạn (đề xuất, 31/10/2026)

v1 có 11 thay đổi cho một người viết RTL. Chia thành các giai đoạn. Mỗi giai đoạn kết thúc bằng một bộ kết quả đủ để
viết bài, và giai đoạn sau chỉ làm mạnh thêm.

| Giai đoạn | Bước ở bảng trên | Thay đổi | Giả thuyết đo được | Kết quả có được |
|---|---|---|---|---|
| **0. Thí nghiệm quyết định** | Phần đầu bước 3: khối tile thử hai biến thể | 4 (một tile) | 2 ở cấp tile | Có giữ rút gọn 32 bit trên mảng hay không. Nếu bác bỏ: lane 32 bit dùng bộ Montgomery riêng, phần còn lại không đổi |
| **1. Lõi tối thiểu cho bài** | 1, 2, phần còn lại của 3, cổng host của 6d, 7 | 1, 2, 3, 4, 10 | 1, 2, 3, 5, 6, cổng host của 12 | Precision FFT thành tốc độ; một phép hậu xử lý; chi phí linh hoạt; ký và kiểm FN-DSA khớp từng byte. **Đủ để viết bài** |
| **2. Chiều modulus** | 4, 5, 6b, 6c, địa chỉ trong lệnh của 6d | 5, 6, 8, 9, 11 | 4, 7, 9, 10, 11, phần còn lại của 12 | NTT 32 bit và prime 31 bit; nhiều modulus cùng lúc; giảm chép dữ liệu |
| **3. Sinh khóa trọn vẹn** | 6 | 7 | 8 | Một lõi phục vụ cả ký lẫn sinh khóa FN-DSA, khóa khớp từng byte |

- Thứ tự này đặt rủi ro lớn nhất (LUT của mux vào DSP) lên đầu, và đưa phần đáng tin nhất của bài (chiều precision FFT,
  ký FN-DSA đã có bản chạy) vào giai đoạn 1.
- Cổng host có pipeline (thay đổi 10) nằm ở giai đoạn 1 vì rẻ và cần cho mọi số liệu ứng dụng.
- Spec 2.0 vẫn mô tả đủ v1. Một giai đoạn chưa làm thì các bộ kiểm của nó ghi "chưa chạy".

## 9. So với các công trình gần nhất

| Công trình | Đã làm | Điểm FlexTransform khác |
|---|---|---|
| *A Unified Hardware Accelerator for FFT and NTT* (ICASSP 2025) | Bộ nhân 32 bit ghép từ 16 bit; FFT 32 bit; NTT ML-KEM/ML-DSA với 4/2 butterfly mỗi chu kỳ | FFT ba độ rộng tới 128 bit, khớp bit phần mềm thật; gom lô theo độ rộng; hậu xử lý và rút gọn dùng chung; NTT hai tầng gộp |
| *OpenNTT* | Chọn FFT/NTT và modulus khi tạo lõi; rút gọn theo modulus lớn nhất | Đổi lúc chạy trên cùng lõi; modulus chỉ là hằng số |
| *BitFusion* (ISCA 2018) | Ghép/tách bộ nhân theo độ rộng cho mạng nơ-ron | Có làm tròn và rút gọn modulo đúng chuẩn |
| *A Lightweight Fused Floating-Point & Modular Arithmetic Unit for FALCON FFT/NTT* (ICTA 2026) | Ghép bộ nhân 14 bit thành nhân dấu phẩy động 64 bit; tách thành 8 làn NTT, rút gọn bằng bảng tra | Fixed-point ba độ rộng khớp phần mềm; rút gọn 32 bit chạy trên chính mảng nhân; mới đọc tóm tắt, **cần đọc toàn văn** |

Phần "NTT hẹp hơn thì nhiều làn hơn" **không phải điểm mới**: bài ICASSP 2025 đã làm. Điểm mới nằm ở chiều
FFT, cơ chế gom lô, việc dùng chung cả phần sau phép nhân, và NTT hai tầng gộp.

## 10. Ngoài phạm vi v1 và rủi ro

- **Chưa làm trong v1:** phép nhân cơ sở của ML-KEM; q = 8380417 với N khác 256; FFT NTRUGen cho các phép khác
  ngoài FFT/FFT ngược; ghép CRT và các phần khác của NTRUSolve (vẫn ở host).
- **NTT prime 31 bit:** mới kiểm số học và lịch nhịp bằng mô hình. Chỉ khẳng định ở mức kernel.
- **Giá của rút gọn lai theo workload thật** (đếm lời gọi trên bản chuẩn × dự báo chu kỳ,
  [study/results/fn_dsa_workload_lai.md](../study/results/fn_dsa_workload_lai.md); bản "trên mảng cho mọi modulus" trước
  đó ở [study/results/fn_dsa_workload.md](../study/results/fn_dsa_workload.md)):
  - ký không tốn thêm (không có NTT);
  - kiểm chữ ký và mở rộng khóa không chậm (NTT 16 bit dùng bộ rút gọn hằng; bản trước chậm 103–126%);
  - sinh khóa tăng 37–45% thời gian kernel, vì NTRUSolve gọi hàng nghìn NTT 32 bit nhỏ (chủ yếu N = 16) với prime mới
    mỗi lần. Khoản này không đổi so với bản trước.

  Trong phần mềm, kernel chỉ chiếm 22–26% thời gian sinh khóa.
  - Ghép đa thức cùng prime gần như không giúp (vẫn +36–44%), vì mỗi prime chỉ có một chuỗi phụ thuộc ngắn.
  - Vì vậy v1 thêm **thay đổi 9: mỗi tile một modulus** (mục 5.5). Ghép khác prime ở N < 64 giảm thời gian NTT của
    sinh khóa 1,8–2,0 lần (dự báo, cần tách vòng lặp theo prime ở host). So cùng điều kiện (cả hai biến thể đều ghép),
    bản trên mảng vẫn chậm hơn 31–44% thời gian kernel khi sinh khóa. So với bản rút gọn riêng không ghép, kết quả đổi
    từ chậm hơn 4–12% tới nhanh hơn 19–22% tùy chi phí mỗi lệnh (0–64 chu kỳ), nên không dùng làm khẳng định.
- **Giả định của mô hình chu kỳ** (mọi dự báo ở mục 4, 5.5, 5.6 dựa trên chúng; phải thay bằng số đo khi có RTL):
  - Độ trễ bộ nhân DSP 4 chu kỳ. Với 3 chu kỳ, NTT nhanh hơn khoảng 8–14% (mục 4).
  - Chi phí cố định 16 chu kỳ mỗi lệnh, gồm ghi hằng số cho các tile ở lệnh nhiều khe. Kết quả sinh khóa nhạy với con
    số này: tỉ lệ chậm của rút gọn trên mảng (một đa thức mỗi lệnh) đổi từ +66% / +49% (0 chu kỳ) tới +23% / +21%
    (64 chu kỳ) cho N = 512 / 1024.
  - Cách gom khác prime giả định tách được vòng lặp theo prime ở host (cận trên).
  - Công thức thời gian cho NTT nhỏ là xấp xỉ: mỗi lượt = số nhịp / tốc độ + độ trễ nhịp.
- **Chép dữ liệu host ↔ lõi** ([study/results/fn_dsa_workload.md](../study/results/fn_dsa_workload.md), mục "Chép dữ
  liệu"): với giao diện host của spec 1.0 (một giao dịch đang chờ, không burst), chép chiếm 45–65% tổng thời gian của
  ký, kiểm và sinh khóa; khi ký N = 1024, 375 712 chu kỳ tổng so với 129 952 chu kỳ tính. Giao diện burst 128 bit đưa
  phần chép của phép ký xuống 49%; thêm giữ dữ liệu trong lõi thì còn khoảng 36% (cận dưới). Đã đưa vào v1 thành thay
  đổi 10 và 11 (mục 5.6). Chép trong lúc lõi chạy để sau v1.
- **Thanh ghi giữ T và ba lượt phụ thuộc khi stall — đã kiểm bằng mô hình chu kỳ một tile** (các số lane 16 bit dưới
  đây thuộc bản "trên mảng cho mọi modulus"; trong v1 chỉ lane 32 bit còn rút gọn trên mảng)
  ([model/mont_on_array_tile.py](../model/mont_on_array_tile.py), kết quả
  [study/results/mont_on_array_tile.md](../study/results/mont_on_array_tile.md); 722 787 phép nhân modulo, 0 sai khác):
  - Với độ trễ bộ nhân 4 chu kỳ, mỗi tile 16 bit có tối đa 20 phép đang chạy, giữ 752 bit, so với 576 bit khi
    dùng bộ rút gọn riêng: **thêm khoảng 180 bit/tile, khoảng 2 800 FF cho cả lõi**, rất nhỏ so với FF của ZCU106.
    Không cần giới hạn số phép đang chạy.
  - Với nhịp NTT hai tầng (tầng 2 chờ tầng 1): tối đa 11 nhịp đang chạy, giữ 1 124 bit/tile so với 1 008 bit khi
    rút gọn riêng; 23 092 nhịp khớp NTT số nguyên; stall 10% / 30% còn 90% / 70% tốc độ, kết quả đúng thứ tự.
  - Lịch phát: **ưu tiên lượt của phép cũ hơn, phép mới chỉ lấp bộ nhân còn trống; stall dừng toàn tile.**
    Với lịch này kết quả luôn ra đúng thứ tự (không cần bộ sắp xếp lại), và stall chỉ làm mất đúng tỉ lệ chu kỳ bị
    dừng (stall 10% → còn 90% tốc độ), không mất thêm vì ba lượt phụ thuộc nhau. RTL phải giữ đúng hai quy tắc này.
    (Sửa 31/10/2026: khi `en` tới đường dữ liệu qua một thanh ghi, hợp đồng tile mục 6, mỗi đợt dừng mất thêm một chu
    kỳ.)
  - NTT 32 bit lập lịch trong một tile chỉ đạt 5,33 phép/chu kỳ (không phải 5,82), vì ở lượt tính m, bộ nhân thứ
    tư bị bỏ trống; các con số ở mục 4 đã dùng 5,33.
- **NTT 32 bit nhỏ chậm vì độ trễ nhịp** (lane 32 bit rút gọn trên mảng). Đã chấp nhận, đổi lấy 7 DSP mỗi tile; nếu
  sau này cần nhanh hơn, cách rẻ nhất là xen kẽ nhiều đa thức hơn (thêm context).
- **Ngân hàng cộng dùng chung lớn gấp đôi** so với bản trước (khoảng 5 730 so với 2 830 bit cộng, mục 3.1b), vì NTT 16
  bit chạy 64 butterfly mỗi chu kỳ. Thêm 64 bộ rút gọn hằng (LUT). Hai khoản này là cái giá ở cấp lõi của rút gọn lai,
  khối tile thử không đo được; phải đo khi có lõi (giả thuyết 1).
- Rủi ro còn lại là **LUT cho mux** đưa T_thấp, q′, m, q quay lại đầu vào DSP ở lane 32 bit; đo bằng Vivado trên tile
  thử (bản nháp: [study/results/tile_thu_draft.md](../study/results/tile_thu_draft.md)).
- **Bản nháp khối tile thử, biến thể lai so với rút gọn riêng** (cùng tài liệu, mục 6; chưa phải RTL nghiệm thu): DSP
  4 so với 11, LUT +2,0%, Fmax 256 so với 310 MHz. Đường tới hạn của cả hai nằm ở phần chọn request và butterfly dùng
  chung, không ở phép rút gọn; chưa giải thích được vì sao C chậm hơn. Giả thuyết 2 trên bản nháp: DSP và LUT đạt,
  Fmax chưa đạt, nên chưa kết luận.
- Phép "phần cao + hạng bù" có thể được Vivado gộp vào bộ cộng sau nhân của DSP nếu viết RTL dạng nhân-cộng;
  không ép bằng primitive, chỉ ghi nhận nếu xảy ra.
- **Thứ tự kết quả NTT 32 bit so với Dilithium** chưa đối chiếu; bước kiểm phải ghi rõ phép đổi thứ tự nếu có.
- **FFT 64 bit NTRUGen** mới kiểm bằng mô hình, chưa chạy với bảng twiddle thật và chương trình C.
- **Diện tích các thay đổi** chưa đo; nếu không đạt ngưỡng, báo cáo như kết quả âm.

## Phụ lục: kiểm tra có thể chạy lại

| Script | Kiểm gì |
|---|---|
| [model/arch_checks.py](../model/arch_checks.py) | Số học FFT 128 bit và 64 bit NTRUGen, cây cộng, Montgomery chạy trên mảng nhân, root |
| [model/flex_v1_projection.py](../model/flex_v1_projection.py) | Mọi dự báo chu kỳ ở mục 4 |
| [model/res32_bank_map.py](../model/res32_bank_map.py) | NTT 32 bit và xen kẽ hai đa thức không xung đột bank |
| [model/mont_on_array_tile.py](../model/mont_on_array_tile.py) | Một tile rút gọn trên mảng nhân: tốc độ, bit giữ, stall, thứ tự kết quả, nhịp NTT hai tầng |
| [model/postproc_adders.py](../model/postproc_adders.py) | Định cỡ ngân hàng cộng/trừ dùng chung (`--tren-mang`: bản trước rút gọn lai) |
| [model/ntrugen_mp31.py](../model/ntrugen_mp31.py) | NTT prime 31 bit khớp từng bit với C của NTRUGen (cả 323 prime, logn 1..10) |
| [scripts/profile_fn_dsa_workload.py](../scripts/profile_fn_dsa_workload.py) | Đếm lời gọi kernel của ký / kiểm / sinh khóa trên bản chuẩn, nhân với dự báo chu kỳ của các biến thể rút gọn (cần WSL; `--lai` cho v1) |
| [sim/tile_thu/run.sh](../sim/tile_thu/run.sh), [fpga/zcu106/tile_thu.tcl](../fpga/zcu106/tile_thu.tcl) | Bản nháp khối tile thử ba biến thể: kiểm toàn bộ vector, đo Vivado |
