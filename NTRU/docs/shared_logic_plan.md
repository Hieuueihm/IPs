# Giảm tài nguyên bằng cách dùng chung logic

Ngày 01/11/2026. Đây là hướng chỉnh kiến trúc để khảo sát, chưa đổi RTL hoặc
contract số học. Giữ 16 bộ tính làm điểm đối chiếu trước khi xét giảm số tile.

Đã có [thử nghiệm riêng cho mạng word32 và tổng root](shared_logic_experiment.md).
Các phần dưới đây là kế hoạch đầy đủ; thử nghiệm mới thực hiện hai bước đầu,
không sửa RTL chính.

## 1. Phần nào đang tốn tài nguyên?

Theo [báo cáo phân cấp](../study/build/ntt_core/util_route_hier.rpt):

| Phần | LUT |
|---|---:|
| 16 tile | 36.689 |
| Logic ở cấp core, gồm điều khiển, địa chỉ và giao tiếp | 6.993 |
| Logic gắn với RAM dữ liệu `u_mem` | 4.720 |
| Mạng dữ liệu `u_net` | 4.562 |
| Logic gắn với bốn ROM root | 2.665 |
| Chọn địa chỉ/đường ghi `u_route` | 278 |

Phân cấp sau tổng hợp không hoàn toàn bằng ranh giới source; các số là để chọn
nơi khảo sát, không suy số LUT tiết kiệm bằng cách xóa tên module.
Khoản 16.605 LUT đã nói trước là phần ngoài tile/root; không phải riêng mạng nối.

## 2. Gộp dữ liệu theo từ 32 bit từ đầu

Core hiện luôn cấp NTT hoặc limb FFT theo 32 bit nhưng RAM và mạng vẫn tách
low 16/high 16. Đã kiểm từ map và `structured_net.json`:

- Toàn bộ 4.096 cặp word16 `(2e,2e+1)` nằm cùng row, ở hai bank kế nhau.
- Cả 32 cổng đọc x/y của 16 tile có danh sách nguồn high đúng bằng nguồn low+1.
- Có thể dùng chung lựa chọn nguồn cho cả từ 32 bit; không cần truyền hai bộ
  tín hiệu chọn low/high độc lập trong interface nội bộ.

Hướng đầu tiên: gom thành 32 bank logic 32 bit; mỗi bank có một bộ địa chỉ/enable
và một lựa chọn nguồn cho từ 32 bit. Host 128 bit tách thành bốn từ 32 bit.
Đầu ra vẫn theo đúng byte/limb order cũ. Nếu cần byte-enable thì giữ 4 bit/từ.

Điều chắc chắn ở mức cấu trúc là có thể gộp thông tin điều khiển trùng nhau.
Vivado có thể đã gộp một phần mạch giống nhau, nên chưa bảo đảm LUT giảm bao
nhiêu. Số BRAM phụ thuộc chế độ cổng và cách tool ánh xạ; phải đo lại, không
khẳng định tự giảm một nửa BRAM.

## 3. Root tính một lần, các tile chỉ dùng

Mỗi tile đang có `sw5`, `wmsw`, carry và adder để tính/lưu `wr+wi` cho 3M.
Root là hằng, nên tính tổng này lúc tạo ROM thay vì mỗi butterfly.

`gen_ntt_core.py` hiện lưu mỗi limb FFT trong từ 96 bit:
`[wi_limb,wr_limb,0]`. Có thể khảo sát thay phần 0 bằng limb của tổng root,
không tăng độ rộng logic của một từROM. Mạng hiện chỉ chuyển hai phần 32 bit;
phải tính chi phí chuyển thêm tổng hoặc chọn tổng tại cổng đọc.

Tổng đúng phải tính `wrap_W(wr_W+wi_W)` sau khi root đã quantize/conjugate theo
contract, rồi mới tách thành limb. Không cộng riêng từng limb mà bỏ carry.
Root có cùng index/width/direction có thể broadcast; root khác nhau vẫn cần
đủ cổng hoặc lịch đọc riêng. Tích CMUL dữ liệu bất kỳ không dùng được ROM sum này.

Đã thử bỏ tính lại hằng số theo cách cấp thêm đường tổng tới tile. Kết quả
[đo toàn core](shared_logic_experiment.md) chỉ giảm 0,19% LUT, tăng FF và BRAM;
chưa chọn cách cấp dữ liệu này cho RTL chính.

## 4. Điều khiển dùng chung, dữ liệu vẫn có chủ riêng

Những phần cần khảo sát gom ra khỏi từng tile:

- Mode, width, direction, scaling được giải mã một lần từ command.
- q/qprime lưu theo context hoặc cụm; cấp bản sao có thanh ghi gần multiplier.
- Lịch ba lượt Montgomery dùng một bộ đếm pha, phát các mask tương ứng 6/6/4 tile.
- Lịch chỉ số limb/product (`wtab`, `mpr`, `mst`) dùng chung cho các lane được
  phát và dừng cùng nhịp; lane chưa đủ operand phải có valid/mask riêng.
- FIFO địa chỉ/tag ghi RAM giữ trong bộ điều khiển cụm; không cần đưa đầy đủ
  command metadata qua mọi thanh ghi dữ liệu nếu destination suy được từ token.

Không gom carry, accumulator hoặc operand của nhiều phép độc lập vào một state
duy nhất. Nếu các tile không cùng tiến độ, vẫn cần context/state riêng hoặc
đồng bộ cả nhóm bằng lịch có chứng minh. Cấu hình khác prime trong cùng batch
sau này cần q/qprime theo context, không dùng một q toàn cục cho mọi phép.

Không chỉ nối một control combinational tới 16 tile: dùng cây broadcast có
register và bản sao cục bộ để tránh tăng fanout/đường tới hạn.

## 5. Tile nhẹ và cụm xử lý chung

Hướng khảo sát: chia 16 tile thành bốn cụm, mỗi cụm bốn bộ nhân 32×32 và phần
cộng/reduction cục bộ. Cụm giữ cấu hình, bảng lịch limb, metadata và bộ đệm có
chia bank. Mạng trong cụm ngắn; kết nối giữa cụm chỉ cho các trao đổi mà
FFT/NTT thật sự cần, không thêm một crossbar lớn ở giữa.

Tile hiện có năm mảng 32 entry và `wps`: khai báo 5.536 bit/tile, tổng 88.576 bit
cho 16 tile. Đây là dung lượng source, không là số FF/BRAM sau tổng hợp. Cần tách:
operand cần cho nhiều tích; root có thể dùng chung; nhánh A phải giữ; metadata
có thể suy từ lịch. Chỉ giữ số context cần thiết để che độ trễ đo được.

Không dồn mọi buffer vào một RAM nhiều cổng ở core. Có thể giữ RAM phân tán
theo lane/cụm, dùng chung địa chỉ và quyền sở hữu; như vậy không tạo thêm mạng
chọn 32 nguồn chỉ để tiết kiệm vài bộ đếm.

Phần ghép3M/rounding FFT rộng có thể dùng chung theo cụm nếu đủ throughput.
Đường FFT32 và NTT cần giữ đủ các lane cộng/trừ/ghi để không bị nghẽn.

## 6. Giới hạn tốc độ của phần xử lý chung

Đếm theo 16 multiplier 32×32, complex 3M và số tích thực của tile hiện tại:

| FFT W | BF/cycle, cận số học | Word32 output/cycle | Số lane tối thiểu nếu mỗi lane ghi hai word32/cycle |
|---:|---:|---:|---:|
| 32 | 16/3 | 64/3 | 11 |
| 64 | 16/12 | 32/3 | 6 |
| 128 | 16/45 | 256/45 | 3 |

Đây là cận để kiểm phương án, không phải throughput đã đạt. Chưa gồm bubble,
đọc root, dependency, burst output hay chi phí các bước cộng/rounding.
Vì vậy “bốn cụm” không đồng nghĩa “chỉ bốn bộ hậu xử lý đơn lane”: cách đó
có thể đủ average output của FFT128 nhưng thiếu cho FFT32/64. Phải phân biệt
chia sẻ điều khiển với giảm số cổng tính dữ liệu.

## 7. Mạng nối và điều khiển tối giản theo lịch thật

Mạng hiện đã giới hạn danh sách nguồn theo từng cổng; không phải crossbar
toàn phần. Hướng giảm tiếp:

1. Gộp low/high thành chọn word32, giảm selector/address/enable bị truyền lặp.
2. Đặt buffer và phép cộng theo cụm gần bank thường dùng; dùng kết nối cố định
   hoặc một số phép đổi chỗ giữa cụm có lịch rõ ràng.
3. Sinh địa chỉ/route theo stage và số thứ tự butterfly ở cấp cụm. Chỉ queue
   những thông tin không suy lại được; giữ write-context đến khi commit.
4. Xem root decode đang tiêu 2.665 LUT: thử ROM segment chặt hơn, RAM cổng đồng
   bộ và nạp descriptor mỗi tầng; không thêm decoder riêng ở mỗi tile.

Đổi topology/bank cần kiểm lại mọi N/width/hướng và trường hợp NTT có hai
operand cùng bank. Không thay mạng bằng mux tổng quát nếu chỉ dời tài nguyên
từ tile ra core. Broadcast đọc cùng địa chỉ được phép; không gộp write của
hai kết quả khác nhau. Chuyển tầng dựa vào commit/dependency đúng với latency
mới, tránh lặp lỗi FFT32 đã phát hiện.

## 8. Thứ tự làm để đo được lợi ích

| Bước | Thay đổi cần so | Giữ cố định |
|---|---|---|
| 1 | Gộp word32, selector và metadata trùng nhau | 16 tile, số học, lịch công việc |
| 2 | Precompute root sum và giảm root buffer lặp | Precision/root output bit-exact |
| 3 | Điều khiển/config chung theo cụm | Số multiplier và throughput yêu cầu |
| 4 | Buffer/hậu xử lý FFT rộng dùng chung có chia bank | Đủ cổng và context; không bỏ carry/round |
| 5 | Topology mạng ngắn hơn theo bank/cụm | Mọi dependency/port budget hợp lệ |

Mỗi bước báo LUT/FF/DSP/BRAM, timing và cycle cho cùng workload. Kiểm source
hash; không dùng số đo của bản cũ. Bắt đầu từ baseline đã sửa lỗi FFT32 hoặc
ghi rõ phần FFT nào chưa hợp lệ; không dùng output sai để tính hiệu quả.
Đây là thứ tự ưu tiên khảo sát, chưa cam kết một mức giảm LUT cụ thể.
