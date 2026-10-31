# 03 — Microarchitecture contracts and memory organization

## 03.1 Phân khối và responsibility

Tên module dưới đây là role đề xuất, không phải mã RTL hoặc hierarchy bắt buộc.
Private interface MAY đổi encoding nếu integration manifest ghi mapping và giữ
nguyên toàn bộ semantics. External interface ở 02 không được đổi tùy ý.

| Role | Trách nhiệm |
|---|---|
| command/control | Validate/latch command, job/stage loops, pause/flush/drain |
| host-memory adapter | 128-bit line, byte enables, outstanding/response ordering |
| bank service/gather | Chia request thành round hợp lệ theo bank/row, assemble operand |
| root prefetch | Fetch exact root, conjugate/quantize theo fmt, broadcast/cache |
| context/batch buffers | Hai context ping-pong, ownership operand/root/keep/addresses |
| FFT front-end | Butterfly prep, pre-add 3M, issue product phase0/1/2 |
| shared array | 16 tile, sign/limb mapping, CT/GS paired/tail/scalar |
| FFT fusion/collector | Exact real-product rounding, collect triplet, combine/scale |
| NTT reorder | Gather/scatter qua job-local index, active mask, normalization |
| retire/write-back | Giải bank conflicts, commit, ACK/count writes, release context |

Đồng thời đọc/tính/ghi được phép ở các context độc lập. Không có yêu cầu toàn
kernel II=1. Arithmetic array MUST có thể nhận một legal frame mỗi clock khi
continuously ready, không pause/flush và output không bị backpressure; internal
pipeline latency phải được công bố trước integration signoff. Output được
giữ ổn định khi blocked. Đường một tầng NTT không được làm metadata đi trước
data khi bypass. (FT-ARC-001..003)

## 03.2 Context và stage discipline

Context 0/1 lifecycle tối thiểu:

```text
FREE -> FILL -> READY -> ISSUE/COLLECT -> WRITE/RETIRE -> FREE
```

Một context có thể đồng thời collect product và chờ write đã issue; encoding
FSM tùy chọn nhưng không release khi còn partial product, output hoặc write
chưa commit. Context giữ epoch4, ctx_id1, command tag32, stage_id4,
job index3 và destination mapping cho từng active logical lane/tile,
logical lane/mask, product phase, op/fmt/profile và dst store/address. Context
ID không được reuse chỉ vì request cuối đã vào arithmetic array.

Mỗi FFT lane có một triplet scoreboard p0/p1/p2 valid. Duplicate phase,
unknown context trong current epoch hoặc phase3 trên FFT là invariant error,
không ghi đè product cũ rồi tiếp tục. Packet thuộc canceled epoch bị discard,
không báo lỗi cho command mới. NTT không dùng phase scoreboard nhưng giữ equivalent
result/write ownership. Packet từ canceled epoch không được tạo RAM write.
(FT-CTX-001..004)

Command config latch đến pipeline drain. Batch READY chỉ khi đủ coefficient,
root và capacity giữ output cho các lane hợp lệ. Không điền dữ liệu chưa có
bằng zero để phát cho kịp. Inactive lane được zero/invalid rõ ràng; không được
commit kết quả của lane inactive. Không dùng dữ liệu zero để suy ra lane invalid.
(FT-CTX-005..006)

Ranh giới **memory pass** là barrier trên committed writes, không chỉ arithmetic
valid/last. Với FFT một pass là một tầng; NTT paired gộp hai tầng thành một pass.
Hai tầng nội bộ tile trao đổi intermediate trực tiếp, không có RAM barrier giữa
chúng. Pass kế tiếp không đọc output pass trước chưa commit. Trong một pass,
butterfly có thể reorder nhưng memory scheduler phải giải RAW/WAW và bảo toàn
input cần đọc trước khi ghi đè. Chờ toàn pass commit là bắt buộc trong 1.0;
không speculate đọc pass sau. (FT-CTX-007)

## 03.3 Physical memory và bit/byte order

Ba store A/B/C độc lập. Mỗi store có 8192 word16, tức 16384 byte. Đặt k là
**word16 address** 0..8191, không phải coefficient index:

```text
bank(k) = (k & 63) XOR ((k >> 2) & 0x30) XOR ((k >> 4) & 0x30)
row(k)  = k >> 6
```

Mỗi `(bank,row)` xác định đúng một k. Bank có một read và một write mỗi edge,
mỗi write có byte-enable2. Memory adapter không đọc/ghi hai row trong cùng
bank ở cùng edge. Nếu nhiều request cùng bank/row, read MAY broadcast;
write chỉ merge nếu byte-enable disjoint và cùng row; hai write cùng byte
là WAW conflict phải serialize hoặc báo INTERNAL_FAULT, không last-wins.
Implementation SHOULD serialize mọi write cùng bank để đơn giản. (FT-MEM-007)

Macro read có one-cycle adapter response: request handshake tại E_t, read
response được dùng sớm nhất tại E_(t+1). Nếu adapter response bị blocked, giữ
data/valid và không ghi đè output latch. Với read và write cùng bank/row/byte,
scheduler MUST serialize; không phụ thuộc BRAM read-first/write-first/no-change.
Các bank khác hoặc cùng bank khác row có thể 1R+1W nếu macro hỗ trợ đúng port
contract. Cùng row với byte-enable disjoint vẫn SHOULD serialize read/write
để tránh phụ thuộc macro. (FT-MEM-008..009)

Host line byte addr a tương ứng k=(a>>1)+l cho l=0..7. `wdata[16l+:16]`
đến word k; strb[2l] chọn low byte, strb[2l+1] chọn high byte. Response chỉ OK
sau khi mọi byte đã commit, không chỉ sau khi request xếp vào write queue.

## 03.4 Logical coefficient mapping

FFT format: `LIMBS=W/16`; coefficient i chiếm word address `i*LIMBS+l`,
l=0..LIMBS−1, least-significant limb trước. N component split-real/imag theo
01. Thứ tự này là host-visible contract và không đổi khi batch/group lane đổi.

NTT RES16: job j, coefficient i đặt tại `k=j*N+i`. Với N*jobs<=64, các job
chiếm bank liên tiếp không chồng nhau vì bank(k)=k khi k<64. Đây là bank coloring
cố định cho batch nhỏ; không tùy ý đảo job trong RAM mà không đảo lại output.
Job lớn chỉ jobs=1; dùng cùng bank/row map. MODMUL áp dụng cùng k ở store B.
(FT-MEM-010..011)

| Kernel | Input footprint bytes | Output footprint bytes | Những store không bị sửa |
|---|---|---|---|
| FFT/IFFT | A: N*W/8 | A: N*W/8 | B,C |
| CMUL | A,B: N*W/8 mỗi store | A: N*W/8 | B,C |
| SPLIT | A: N*W/8 | C: N*W/8, f0 rồi f1 | A,B |
| MERGE | A,B: N*W/16 mỗi store | C: N*W/8 | A,B |
| NTT/INTT/TOMONT | A: jobs*N*2 | A: jobs*N*2 | B,C |
| MODMUL | A,B: jobs*N*2 mỗi store | A: jobs*N*2 | B,C |

Bytes ngoài output footprint MUST không bị thay đổi bởi command, kể cả các
byte cùng host line nhưng ngoài footprint. Host MAY đặt canary ở đó để kiểm.
Không đưa dummy write của inactive lane vào vùng lân cận. (FT-MEM-012)

## 03.5 Bank service và batching FFT

Lanes tích thực ở REF16: W32=16, W64=4, W128=1. FFT front-end SHOULD gom
nhiều butterfly độc lập cùng stage để dùng các lane này. Microbatch có thể
ít lane hơn khi stage/job không đủ butterfly; lane_mask chỉ rõ lane nào valid.
Mỗi product phase dùng cùng lane/context binding để collector ghép đúng.

Coefficient gather MAY tốn nhiều round: nhóm word theo bank/row, issue không
vượt một read/bank/edge, ghi request-to-slot map và capture về đúng operand.
Write-back thực hiện tương tự. Không xem mux/gather là một RAM có thêm cổng.
Với map đã khóa, real/imag của FFT rộng có thể cùng bank ở row khác nhau;
không được giả định 4 component luôn đọc được một clock. (FT-ARC-004)

Prefetch FFT dùng **một complex root/cycle** từ bảng Q64.64; conjugate trước
quantize cho inverse, rồi tạo sum root theo 01. Root buffer có slots cho
16/4/1 lane theo width. Root cùng index/config MAY broadcast; cache key gồm
root index, fmt và hướng. Tag/root không được dùng nhầm sau đổi config/epoch.
Hai context có vùng root độc lập hoặc ownership tương đương. Root-cache valid
clear tại command acceptance và flush để lịch cold-start tái lập được. Không
có giả định 16 root/cycle; batch chỉ READY khi root cần dùng đã tới. (FT-ARC-005)

## 03.6 NTT frame mapping và root bundle

Array paired/tail frame có 16 tile ×4 coefficient. Small-job frame đặt tile:
`tile = job*(N/4) + local_tile` cho N<64. Vì jobs*N<=64 nên không vượt 16 tile.
Job index không tham gia tính root; root index dùng coefficient index trong job.
Large job chia thành các warp tối đa 16 tile. (FT-ARC-006)

Reference schedule để giữ conflict-free supply của NTT:

- Gọi p là bit stride thấp của hai tầng. Paired: liệt kê g theo tăng dần trên
  các bit địa chỉ còn lại ngoài p,p+1; base=expand(g,free_bits). Một tile nhận
  `[base,base+2^p,base+2^(p+1),base+3*2^p]`.
- Tail: tạo pair `[base,base+2^p]`; hai pair/tile. CT x0=A0,x1=A1,x2=B0,x3=B1;
  GS x0=A0,x1=B0,x2=A1,x3=B1. Thứ tự free bits chọn các bank-column độc lập
  trước, rồi các bit còn lại theo tăng dần; column(b)=b nếu b<6, ngược lại
  4+((b−4)&1). Khi chọn front bits, bỏ column(p), mỗi column chỉ chọn một lần.
- Forward lấy các stride từ cao xuống; ghép hai stride liên tiếp, odd tail ở
  cuối. Inverse lấy từ thấp lên. q3329 N256 bắt đầu/dừng ở bit stride1.

Reference address schedule MAY thay nếu giữ cùng kernel output và port-budget
contract; nếu thay, MUST chứng minh gather/scatter bijective và không cross-job.

Với root index g của tầng common, bundle(g) low-to-high là
`[GM[g],GM[2g],GM[2g+1]]`, 48 bit. Bundle bank=g&15, row=g>>4.
Forward/inverse và q-profile chọn bảng tương ứng. Paired legal g>=1 và
2g+1<ROOT_COUNT. Tail có thể lấy child từ parent bundle `max(1,g>>1)`;
g=1 lấy common root của bundle1. Không đọc padded row như root hợp lệ.
Nhiều tile/job cùng g MAY broadcast một bundle. Hai g khác row nhưng cùng
root bank phải service nhiều round, không overwrite một root buffer slot.
(FT-ARC-007)

## 03.7 Arithmetic-array packet reference interface

Packet payload ở boundary shared array (REQ/RSP) có valid/ready độc lập.
REQ carries is_ntt1, fmt2, tile_mode2, profile2, direction1, epoch4, ctx_id1,
stage_id4, job-map, lane_mask16, product_sel2 và internal tag32. Destinations
có thể nằm trong context store keyed bởi epoch/ctx/lane thay vì lặp mọi frame.
Response MUST có đủ identity để lookup không nhầm. Không cắt context/epoch
để tái sử dụng một tag32 nếu có thể alias packet chưa retire. (FT-IF-009)

`tile_mode`: 0=NTT scalar/independent, 1=NTT paired, 2=NTT tail,
3=FFT raw-tile operation. FFT REQ chỉ mode3, NTT chỉ mode0..2.

Legal FFT frame: is_ntt=0, fmt0..2, profile0, tile_mode3, direction0,
product_sel0..2. Legal NTT frame: is_ntt=1, fmt3, profile0/1,
tile_mode0..2, product_sel0. Internal illegal frame phải được chặn và báo
INTERNAL_FAULT cho active command; không được tự sửa mode rồi tiếp tục.

| Domain/mode | data[2047:0] | roots[1023:0] | result[2047:0] |
|---|---|---|---|
| FFT | A packed low512, B packed bits512..1023; remainder zero | zero/ignored | packed lane products low bits |
| NTT mode0 | tile t: 8 word16 at t*128 | tile t:4 word16 at t*64 | tile t:8 word16 at t*128 |
| NTT mode1 | tile t:4 word16 at t*64 | tile t:3 word16 at t*48 | tile t:4 word16 at t*64 |
| NTT mode2 | tile t:4 word16 at t*64 | tile t:2 word16 at t*32 | tile t:4 word16 at t*64 |

FFT A/B lane l nằm ở `[l*W +: W]` bên trong half tương ứng. Output W32 low512,
W64 low256, W128 low128; phần còn lại zero. NTT paired/tail upper1024 zero.
Inactive tile/lane operands/root/result được zero; lane_mask quyết định side
effect. Với NTT mask là tile mask; FFT mask là real-product lane mask.
Full tile-mode0 independent và scalar use `(0,a)` khác nhau ở cách đóng gói của
caller; không thay công thức butterfly để ưu tiên scalar. (FT-IF-010)

Boundary REQ/RSP này bao gồm limb fusion và real-product rounding: FFT result
lane l là `mul(A_l,B_l)` đúng W bit theo 01.1. Raw65 của từng tile là interface
thấp hơn bên trong array wrapper, không phải output packet W32/64/128 này.
Collector bên ngoài giữ ba rounded products để tạo complex3M.

`direction=0` chọn CT, `direction=1` chọn GS cho NTT frame. FFT raw-product
frame đặt direction=0; hướng FFT/IFFT đã xử lý ở front-end/root, không thay phép
nhân thực. Scalar frame luôn mode0/direction0, kể cả normalization của INTT:

| Scalar operation | Mỗi cặp input | Root | Output được retire |
|---|---|---|---|
| TOMONT | (0,x) | R² modq | Tổng CT = xR modq |
| MODMUL | (0,A) | B | Tổng CT = ABR^-1 modq |
| INTT normalization | (0,x) | R*inverse(2^L) modq | Tổng CT = x/2^L modq |

Từng tile mode0 có bốn cặp; chỉ output tổng của mỗi cặp scalar được ghi.
Output hiệu vẫn canonical nhưng không thuộc output footprint. Do đó mode0
scalar có tối đa 64 scalar result/frame; không ghi cả 128 butterfly words.

## 03.8 Fusion topology và keep paths

W64 group lane l dùng tile 4l..4l+3, `(i,j)=(t%2,(t/2)%2)` trong group.
W128 dùng cả mảng với `i=(t&1)|((t>>1)&2)`, `j=((t>>1)&1)|((t>>2)&2)`.
Tile nhận limb32 tương ứng; sign của limb cao nhất chọn độc lập cho A/B.
Shift theo 32(i+j), modulo retained width, rounding đúng 01.

Trong tile FFT, M0/M1 tạo diagonal16 partial, M2/M3 tạo cross partial; giữa
hai compute stage giữ raw product **và** operand half cần cho cross term.
NTT CT giữ A, GS giữ A+B qua reduction. Root/tail/valid cũng được giữ. Không
được chỉ vẽ product path rồi tự dựng lại side-data từ RAM sau khi input đã đổi.
(FT-ARC-008..009)

## 03.9 Lifetime, flush và implementation manifest

Epoch tăng khi nhận command và khi flush hủy command, modulo 16. Wrap epoch
chỉ an toàn vì trước command mới pipeline đã drain và valid cũ không tồn tại;
không coi bốn bit epoch là cơ chế thay thế drain. Reset clear valid toàn bộ
pipeline. Flush discard pending command writes và trả context về FREE sau
khi mọi in-flight packet đã bị drain/invalidate. Host request đã nhận phải
được hoàn tất/preserve response riêng; không bị hủy cùng command.
(FT-CTX-008)

Implementation manifest MUST công bố: supported profiles, parameters, external
ports, pipeline latency không stall theo mode, bypass alignment, FIFO/context
depth, root-cache policy, memory macro timing/read-during-write handling,
arbitration/fairness, reset/flush strategy và bound, synthesis assumptions,
verification version/hash. Microarchitecture khác hình được phép nếu contract
giữ nguyên và có record review. (FT-ARC-010)
