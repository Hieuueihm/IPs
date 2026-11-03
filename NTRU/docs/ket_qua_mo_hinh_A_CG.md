# Kết quả mô hình A và mạng hình học cố định bốn nguồn

Ngày 02/11/2026. Chỉ thêm mô hình, báo cáo và testbench quan sát trong `study/build`.
Không sửa RTL chính, PLAN, spec hoặc commit. Chưa có số LUT/FF/BRAM/timing cho thiết kế mới.

## 1. Điều chỉnh kết luận trước

Nhận xét trong [tài liệu so sánh](so_sanh_kien_truc_loi.md) là đúng ở điểm quyết định:
A một mình chưa có bằng chứng xuống 35k. Khoản 22k số học/10k điều phối trước đây là
quota thiết kế, không phải ước lượng đã được xác nhận. Cần giảm đồng thời cách giữ
trạng thái của FFT và cách sinh địa chỉ/kết nối; không coi chỉ cắt logic riêng của
FFT64/128 là đủ.

Lượt này thực hiện hai việc:

1. Đo truy cập/lifetime trên RTL hiện có rồi kiểm cách đóng gói và đổi thứ tự input
   của A bằng mô hình bộ nhớ.
2. Tìm một ánh xạ CG có tối đa bốn nguồn đọc/ghi qua tất cả các cấu hình, chạy lại
   bằng RAM vật lý theo chu kỳ với giá trị số học thật.

## 2. A: điều gì đã được kiểm?

Model [tile_a_liveness.py](../model/tile_a_liveness.py) không viết lại tile. Nó tạo
testbench quan sát source hiện tại, lấy trace các lần đọc/ghi, tag và kết quả. Một
bản sao của testbench timing được dùng với thanh ghi input được lái rõ ràng, thay
cho biểu thức `$random` nối thẳng vào cổng. Không dùng timing-only testbench để tự
khẳng định đúng số học.

Mô hình sau đó ánh xạ cùng dữ liệu vào các vòng bộ nhớ mới và kiểm mỗi lần đọc có
đúng owner và giá trị, kể cả khi địa chỉ đã quay vòng. Word cũ được đọc trước khi
ghi word mới cùng cạnh, theo cách dùng LUTRAM hiện tại.

### Kích thước và lifetime

| FFT | Slot BF trong mô hình A | Entry mỗi mảng side/operand | Entry mỗi mảng tổng 3M |
|---|---:|---:|---:|
| 32 bit, BF mỗi 3 chu kỳ | 8 | 16 | 8 |
| 64 bit, BF mỗi 12 chu kỳ | 4 | 16 | 8 |
| 128 bit, BF mỗi 48 chu kỳ | 2 | 16 | 8 |

Đã kiểm 24 BF liên tiếp mỗi ca, hai chiều, đủ quay vòng toàn bộ slot ít nhất hai
lần. Kết quả số học so trực tiếp với 3M, wrap và rounding của reference; GS có
scaling cuối với s=5 trong probe. Tổng 144 BF qua sáu ca FFT.

Riêng NTT đã kiểm 12 cấu hình ×40 request: q3329/12289/8380417/2^31−1 ở 32 bit và
packed16 q3329/12289, hai chiều. Kết quả Montgomery và half modulo khớp; tối đa
**sáu word side cùng sống**, đóng gói vào 16 entry không alias. Tổng 480 request,
tương ứng 640 butterfly khi tính hai làn packed.

Nếu giữ width side 42 bit, dữ liệu khai báo của năm mảng có thể chuyển từ
`32×42 + 4×32×32 = 5.440 bit` sang
`16×42 + 2×16×32 + 2×8×32 = 2.208 bit`, chưa tính `wps`, các thanh ghi và metadata
khác. **Đây là số bit khai báo, không phải dự báo giảm 59% LUTRAM/LUT.**

### Cổng đọc: thay đổi hữu ích hơn chỉ giảm depth

| Mảng | Trace input cũ | Mô hình input re_k, im_k |
|---|---|---|
| X: phần của o | FFT32 có lúc cần 2R/1W | 1R/1W |
| W: phần root | FFT32 có lúc cần 2R/1W | 1R/1W |
| SX, SW: hai tổng của 3M | 1R/1W | 1R/1W |
| Side và wps | 1R/1W | 1R/1W |

Trong lịch đều của FFT64/128, hai lần đọc X/W hiện không trùng chu kỳ; nhưng cùng
RTL vẫn phải phục vụ trường hợp FFT32 cần 2R. Đổi re_k/im_k bỏ lượt đọc lại real
để tính tổng, để RAM X/W chỉ còn đường đọc của phép nhân.

Ở FFT32 chỉ có re0/im0 nên thứ tự vốn đã xen kẽ; thay đổi quan trọng là dùng giá
trị nhịp trước trong thanh ghi thay cho đọc lại RAM. Với FFT64/128 mới cần đổi
thứ tự các phần để áp dụng cùng cách giữ một cặp giá trị nhịp trước.

Giá trị real/root của nhịp trước phải tồn tại trong thanh ghi: có thể thêm 64 bit
hold, hoặc tính tổng sớm hơn từ thanh ghi pipeline đang có. Cách thứ nhất tăng FF;
cách thứ hai có thể kéo dài đường tổ hợp GS add/sub → tổng 3M. Cần tính cả chi phí
này. GS xen kẽ cũng cần carry/borrow thực và ảo riêng, thêm giải mã beat.

Model giữ lịch các lượt nhân và output của trace, thay thời điểm ghi input/sum và
bỏ PRE read. Tổng 3M được kiểm đủ W bit với carry; không cộng riêng từng phần rồi
bỏ nhớ. Các kiểm cố ý flip giá trị đọc và giảm BF128 còn một slot đều bị bắt.

**Giới hạn:** đây là kiểm trace và retime bộ nhớ, chưa chứng minh pipeline RTL mới
đạt cùng clock. Chỉ cam kết cho cadence đã kiểm, không giữ nguyên quyền nhận burst
bốn BF128 của giao diện tile cũ. Global stall phải dừng nhất quán; chưa kiểm mọi
LEAF_PD, mọi traffic thưa hay trộn hai modulus trong cùng stream.

Kết quả chi tiết: [tile_a_liveness.md](../study/results/tile_a_liveness.md),
[JSON, hash và đường dẫn log](../study/results/tile_a_liveness.json).

## 3. CG: đã tìm được mạng tối đa bốn nguồn

Model [cg_bank4_model.py](../model/cg_bank4_model.py) dùng 32 superbank word32,
tương ứng 64 bank16 hiện tại. Mỗi superbank có một lượt đọc và một lượt ghi mỗi
chu kỳ; hai buffer chia sẻ chính các cổng này.

### Ánh xạ với biến đổi đủ lớn

Với M ≥64 điểm, n=log2(M):

```text
bank(p) = (p & 31) XOR (bit[n−1](p) << 4)
row(p, plane, buffer) = (p >> 5) + plane×(M/32) + buffer×rows_per_buffer
tile(i) = i & 15,     i = 16k + t
```

Tầng xuôi đọc i và i+M/2, ghi 2i và 2i+1. Tầng ngược đảo hai phía.

- NTT hoàn chỉnh: M=N, một plane.
- NTT hmin=m: M=N/2^m, 2^m plane hệ số; hệ số j ở `(position=j>>m, plane=j mod 2^m)`.
- FFT: M=N/2 điểm phức; 2L plane thực/ảo và phần 32 bit.

Ở NTT thiếu tầng, tách các bit không đổi thành plane cho phép dùng cùng topology
CG hoàn chỉnh. Không thêm tầng NTT và không đổi phép biến đổi; từng plane vẫn có
root và số học đúng của transform thiếu tầng.

### Vì sao bốn nguồn là đủ?

Qua cả hai chiều, cổng x của tile t chỉ cần các bank:

```text
{ t, t+16, (2t) mod 32, ((2t) mod 32) XOR 16 }
```

Cổng y thay 2t bằng 2t+1. Mỗi bank b nhận ghi từ tối đa bốn cặp `(tile, nhánh)`:

```text
{ (b>>1, b&1), ((b>>1) XOR 8, b&1), (b&15, 0), (b&15, 1) }
```

Các phần tử có thể trùng, nên nhiều cổng thực tế ít hơn bốn. Đây là giới hạn qua
mọi mode, N và hmin đã xét, không phải chỉ một tầng hoặc một chiều.

Giới hạn này áp dụng cho mạng **tính toán** bank↔tile. Nguồn ghi từ host và đường
root không được lén tính là miễn phí hoặc đã nằm trong bốn nguồn đó. Nếu host
dùng chung mux ghi ở bank, đó có thể là nguồn thứ năm hoặc cần tổ chức inject riêng;
cả hai cách đều phải tính tài nguyên và kiểm lịch của adapter.

Với M≤32, model nhúng transform nhỏ vào đồ thị shuffle 32 bank, thay mask tile
hoạt động theo tầng. Ánh xạ stage được sinh sẵn; không yêu cầu bộ quay bit biến
thiên ở từng tile. Cách này tránh làm số nguồn tăng ở N nhỏ. Code kiểm tính đơn
ánh của mọi layout, không chỉ đếm nguồn.

### Địa chỉ chung có thực chất không?

Với i=16k+t, M≥64:

- Phía far: row x=k>>1, row y=(k>>1)+M/64.
- Phía near: row cả hai nhánh = k.
- Bank swap chỉ phụ thuộc một bit của k và chiều; plane/buffer thêm các trường
  địa chỉ chung. NTT cần các bộ đếm theo nhóm pha; FFT cùng nhịp.

N nhỏ dùng descriptor/mask theo tầng và row bằng 0 trong mỗi plane. Địa chỉ ghi
vẫn phải đi đúng pipeline và buffer parity; không tự kết luận xóa được mọi metadata
hoặc mọi lựa chọn row. Root, host và logic mask cũng chưa có số LUT.

## 4. Kiểm chứng CG và kết quả chu kỳ

- 154 cấu hình cổng/phụ thuộc: NTT N2..1024, hmin0..2 khi hợp lệ; FFT N2..1024,
  ba precision, hai chiều, cả thứ tự input cũ và input xen kẽ ở FFT64/128.
- Replay đọc/ghi theo **địa chỉ RAM vật lý và chu kỳ**, kiểm version từng word;
  không lấy kết quả Python của tầng trước làm dữ liệu luôn sẵn.
- 48 vector NTT thuộc 30 cấu hình khớp golden.
- 11 cấu hình khảo sát (9 modulus khác nhau) khớp định nghĩa forward và inverse
  quay về đầu vào.
- 60 vector FFT N2..1024 khớp từng bit; thêm sáu ca N1 identity. FFT64/128 được
  chạy lại 40 ca với thứ tự input xen kẽ, vẫn khớp.
- Kiểm cố ý bỏ XOR bank bị bắt vì x/y trùng cổng.

Root FFT dùng base `M/h`, khác root NTT base `M/(2h)`; model không tái dùng nhầm
chỉ số root NTT cho FFT. Cả hai đều đối chiếu đúng bảng reference theo chiều và width.

| Mode | Kernel cycle | So với baseline hiện tại |
|---|---:|---|
| NTT N1024 | 983 | 984/985 |
| NTT N256 đủ tầng | 309 | 255/249, vẫn chậm hơn |
| NTT N256 hmin1 | 272 | 231/225, vẫn chậm hơn |
| FFT32 N1024 | 451 | 644 |
| FFT64 N1024 | 1.750 | 2.031 |
| FFT128 N1024 | 6.935 | 7.510 |

Input xen kẽ cho cùng các mốc FFT trên **nếu** tile giữ latency output đang giả
định. FFT nhanh hơn có phần do chồng tầng; không gán toàn bộ cho cách đặt bank.

Root cũng có cấu trúc dùng một chỉ số k chung vào bảng của các tile; đã kiểm chu
kỳ lặp. Với một lệnh N1024, một chiều: NTT cần 67 word32/tile; FFT32/64/128 cần
35 root phức/tile, tương ứng 70/140/280 word32. Chưa mô hình cổng/nạp và ánh xạ
BRAM cho toàn bộ profile/slot. Không coi root decoder hay lưu root là miễn phí.

Kết quả: [cg_bank4_model.md](../study/results/cg_bank4_model.md),
[topology đầy đủ, case, hash](../study/results/cg_bank4_model.json).

## 5. Chi phí mới phải tính trước khi khẳng định 35k

**Giao diện host đổi layout.** Nếu host vẫn gửi line 128 bit theo thứ tự hệ số cũ,
nhiều word của line có thể vào cùng bank nhưng khác row:

| Mode | Tối đa nhịp con để nạp/đọc một line |
|---|---:|
| NTT đủ tầng / FFT32 lớn | 1 |
| NTT hmin1 / FFT64 | 2 |
| NTT hmin2 / FFT128 | 4 |

Đây không phải giao diện load_valid một line mỗi chu kỳ tương thích nguyên trạng.
Cần adapter có backpressure/buffer, hoặc host sắp dữ liệu theo layout mới. Model
đếm nhịp tối thiểu trong từng line; chưa thiết kế adapter hoặc che chi phí bằng DMA.
Các kernel cycle trong bảng **không gồm** nạp/đọc dữ liệu, cấu hình và nạp root.

FFT128 N1024 cần 128 row mỗi buffer, 256 row tổng: phải mở địa chỉ RTL từ 7 lên
ít nhất 8 bit. RAM vật lý FPGA có thể có dung lượng dư, nhưng chưa tổng hợp lại để
cam kết không tăng block. Root vẫn có thể là khoản tăng BRAM đáng kể. Quy đổi đúng:
44 RAMB36+64 RAMB18=76 BRAM36 tương đương; 80+64/2=112, vượt ngân sách 80 nếu giữ mốc đó.

Mạng bốn nguồn là kết quả cấu trúc, chưa là số LUT. Selector, valid, row, forwarding,
root, host, FF và dây nối vẫn phải đo đủ. Buffer 1R/1W cũng cần tổng hợp theo đúng
mã truy cập để biết tool đã bỏ RAM nhân bản chưa.

## 6. Quyết định sau hai mô hình

**A + CG bốn nguồn đã có cơ sở chức năng/lịch cụ thể để làm nguyên mẫu đo.** A giảm
nhu cầu trạng thái/cổng đọc; CG giảm độ phức tạp tạo địa chỉ và giới hạn fan-in mạng.
Không lấy A một mình hoặc số bit giảm làm bằng chứng đạt 35k LUT.

Trước khi chốt ngân sách còn cần số đo cho engine A, mạng bốn nguồn, row/valid và
host/root adapter. Lượt hiện tại hoàn tất ở mô hình; chưa viết lại RTL hoặc thay
ngân sách trong PLAN/spec.

## Chạy lại

```text
python -X utf8 model/tile_a_liveness.py
python -X utf8 model/cg_bank4_model.py
```

Lượt đầu cần Icarus/vvp; dùng PATH hoặc đường dẫn C:/iverilog/bin trên máy hiện tại.
Mô hình CG dùng Python và bảng/vector có trong repo. Báo cáo được sinh vào study/results;
source RTL được kiểm hash trong lượt liveness.
